"""DB에 적재된 캠페인을 원본 사이트의 상세 페이지와 대조하는 표본 검수.

    python verify.py              # 플랫폼별 15건씩 무작위 표본
    python verify.py --per 30     # 표본 크기
    python verify.py --only revu  # 일부 플랫폼만

스크래퍼는 목록 페이지를 읽지만 검수는 각 캠페인의 상세 페이지(source_url)를 따로 연다 — 같은
페이지를 다시 읽으면 같은 버그를 그대로 통과시키기 때문이다. 사이트마다 마크업이 달라도 쓸 수
있게, 셀렉터 대신 "DB 값이 페이지 글자 안에 있는가"로 판정한다.

결과는 표준출력과 GitHub Actions 요약($GITHUB_STEP_SUMMARY)에 마크다운 표로 남는다.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict
from datetime import date

import requests
from bs4 import BeautifulSoup

from connectors import BY_KEY, BY_LABEL, REGISTRY

HEADERS = {"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}

# 판정 값: ok / mismatch / missing(페이지에서 못 찾음) / skip(DB에 값이 없어 검사 안 함) / changed(값이 바뀜 — 실시간 변동)
FIELDS = ["page", "open", "title", "deadline", "recruit", "applicant", "region", "channel", "image"]
FIELD_LABELS = {
    "page": "페이지 열림",
    "open": "모집중",
    "title": "제목",
    "deadline": "마감일",
    "recruit": "모집인원",
    "applicant": "신청인원",
    "region": "지역",
    "channel": "채널",
    "image": "이미지",
}

CLOSED_RE = re.compile(r"모집\s*마감|모집이\s*마감|마감된\s*(캠페인|체험단)|종료된\s*(캠페인|체험단)|모집\s*종료|존재하지\s*않는")
CHANNEL_WORDS = {
    "blog": ("블로그", "blog"),
    "instagram": ("인스타", "instagram"),
    "reels": ("릴스", "reels"),
    "youtube": ("유튜브", "youtube"),
    "shorts": ("쇼츠", "숏츠", "shorts"),
    "tiktok": ("틱톡", "tiktok"),
    "clip": ("클립", "clip"),
}
APPLICANT_RE = re.compile(r"(?:신청|지원|대기)\s*(?:자|인원)?\s*[:：]?\s*([\d,]+)\s*명?")


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def deadline_patterns(d: date) -> list[str]:
    m, dd = d.month, d.day
    return [
        f"{m:02d}.{dd:02d}", f"{m}.{dd}", f"{m:02d}/{dd:02d}", f"{m}/{dd}",
        f"{m}월{dd}일", f"{d.year}-{m:02d}-{dd:02d}", f"{d.year}.{m:02d}.{dd:02d}",
    ]


def check_row(row: dict, page_text: str | None, final_url: str | None, status: int | None) -> dict[str, str]:
    """한 캠페인의 필드별 판정. page_text는 상세 페이지의 보이는 글자 + 페이지 데이터(JSON 포함)."""
    result: dict[str, str] = {f: "skip" for f in FIELDS}
    if page_text is None or (status and status >= 400) or (final_url and "/login" in final_url):
        result["page"] = "mismatch"
        return result
    result["page"] = "ok"
    text = compact(page_text)

    result["open"] = "mismatch" if CLOSED_RE.search(page_text) else "ok"

    title = compact(row["title"])
    # 긴 제목은 사이트가 줄여 보여줄 수 있어 앞 20자만 본다
    result["title"] = "ok" if title[:20] in text else "missing"

    if row.get("deadline_date"):
        d = row["deadline_date"]
        d = date.fromisoformat(d) if isinstance(d, str) else d
        result["deadline"] = "ok" if any(compact(p) in text for p in deadline_patterns(d)) else "missing"

    if row.get("recruit_count"):
        n = row["recruit_count"]
        result["recruit"] = "ok" if re.search(rf"(?<!\d){n}명", text) or re.search(rf"/{n}(?!\d)", text) else "missing"

    if row.get("applicant_count") is not None:
        found = [int(v.replace(",", "")) for v in APPLICANT_RE.findall(page_text) if v.replace(",", "").isdigit()]
        if row["applicant_count"] in found:
            result["applicant"] = "ok"
        elif found:
            result["applicant"] = "changed"  # 신청자는 실시간으로 늘어나므로 불일치가 아니라 변동
        else:
            result["applicant"] = "missing"

    if row.get("campaign_type") == "방문":
        names = row.get("region_guguns") or ([row["region_sido"]] if row.get("region_sido") else [])
        if names:
            stems = [re.sub(r"(특별시|광역시|시|군|구)$", "", n) or n for n in names]
            result["region"] = "ok" if any(compact(s) in text for s in stems) else "missing"

    channels = row.get("review_channels") or []
    if channels:
        result["channel"] = "ok" if all(
            any(w in text for w in CHANNEL_WORDS.get(c, (c,))) for c in channels
        ) else "missing"

    return result


def check_image(url: str | None) -> str:
    if not url:
        return "skip"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, stream=True)
        ok = resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/")
        resp.close()
        return "ok" if ok else "mismatch"
    except requests.RequestException:
        return "mismatch"


def fetch_static(url: str) -> tuple[str | None, str | None, int | None]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException:
        return None, None, None
    soup = BeautifulSoup(resp.text, "html.parser")
    data = " ".join(s.get_text(" ") for s in soup.select('script[type="application/json"], script#__NEXT_DATA__'))
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(" ", strip=True) + " " + data, resp.url, resp.status_code


def fetch_with_browser(rows: list[dict]) -> dict[str, tuple[str | None, str | None, int | None]]:
    """레뷰처럼 로그인 + JS 렌더링이 필요한 사이트."""
    from playwright.sync_api import sync_playwright

    from connectors.revu import _login

    pages: dict[str, tuple[str | None, str | None, int | None]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        if not _login(context):
            browser.close()
            raise RuntimeError("레뷰 로그인 실패 — REVU_ID / REVU_PW 확인")
        page = context.new_page()
        for row in rows:
            try:
                resp = page.goto(row["source_url"], wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1000)
                pages[row["source_url"]] = (page.inner_text("body"), page.url, resp.status if resp else None)
            except Exception:  # noqa: BLE001 - 한 페이지 실패가 검수 전체를 막으면 안 됨
                pages[row["source_url"]] = (None, None, None)
        browser.close()
    return pages


def sample_rows(platform_labels: list[str], per: int) -> list[dict]:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            rows: list[dict] = []
            for label in platform_labels:
                cur.execute(
                    "select * from public.campaigns where is_active and platform = %s order by random() limit %s",
                    (label, per),
                )
                rows += cur.fetchall()
            return rows
    finally:
        conn.close()


def report(results: list[tuple[dict, dict[str, str]]]) -> str:
    by_platform: dict[str, list[dict[str, str]]] = defaultdict(list)
    problems: list[str] = []
    for row, res in results:
        by_platform[row["platform"]].append(res)
        bad = [FIELD_LABELS[f] for f in FIELDS if res[f] in ("mismatch", "missing")]
        if bad:
            problems.append(f"| {row['platform']} | {row['title'][:30]} | {', '.join(bad)} | {row['source_url']} |")

    lines = ["## 원본 대조 검수", "", "일치율 = ok ÷ (검사한 건수). 괄호는 검사한 건수, '변동'은 신청인원이 그새 바뀐 건수.", ""]
    lines.append("| 플랫폼 | 표본 | " + " | ".join(FIELD_LABELS[f] for f in FIELDS) + " |")
    lines.append("|---|---|" + "---|" * len(FIELDS))
    for platform, items in sorted(by_platform.items()):
        cells = []
        for f in FIELDS:
            c = Counter(r[f] for r in items)
            checked = len(items) - c["skip"]
            if checked == 0:
                cells.append("–")
                continue
            ok = c["ok"] + (c["changed"] if f == "applicant" else 0)
            cell = f"{round(100 * ok / checked)}% ({checked})"
            if f == "applicant" and c["changed"]:
                cell += f" 변동 {c['changed']}"
            cells.append(cell)
        lines.append(f"| {platform} | {len(items)} | " + " | ".join(cells) + " |")

    lines += ["", f"### 확인이 필요한 캠페인 ({len(problems)}건)", ""]
    if problems:
        lines += ["| 플랫폼 | 제목 | 안 맞는 항목 | 원본 |", "|---|---|---|---|", *problems]
    else:
        lines.append("없음")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per", type=int, default=15, help="플랫폼별 표본 수")
    parser.add_argument("--only", help=f"쉼표로 구분한 커넥터 키 ({', '.join(BY_KEY)})")
    args = parser.parse_args()

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")] if args.only else REGISTRY
    rows = sample_rows([c.label for c in connectors], args.per)

    results: list[tuple[dict, dict[str, str]]] = []
    browser_rows = [r for r in rows if BY_LABEL[r["platform"]].needs_browser]
    browser_pages = fetch_with_browser(browser_rows) if browser_rows else {}
    for row in rows:
        page = browser_pages.get(row["source_url"]) if BY_LABEL[row["platform"]].needs_browser else fetch_static(row["source_url"])
        res = check_row(row, *(page or (None, None, None)))
        res["image"] = check_image(row.get("image_url"))
        results.append((row, res))

    md = report(results)
    print(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md + "\n")


if __name__ == "__main__":
    main()
