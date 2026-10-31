"""DB에 적재된 캠페인을 원본 사이트의 상세 페이지와 대조하는 검수 (기본: 전수, 옵션: 표본).

    python verify.py              # 활성 캠페인 전수 검사
    python verify.py --per 30     # 플랫폼별 30건 무작위 표본만
    python verify.py --only revu  # 일부 플랫폼만

스크래퍼는 목록 페이지를 읽지만 검수는 각 캠페인의 상세 페이지(source_url)를 따로 연다 — 같은
페이지를 다시 읽으면 같은 버그를 그대로 통과시키기 때문이다. 사이트마다 마크업이 달라도 쓸 수
있게, 셀렉터 대신 "DB 값이 페이지 글자 안에 있는가"로 판정한다.

결과는 표준출력과 GitHub Actions 요약($GITHUB_STEP_SUMMARY)에 마크다운 표로 남는다.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
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


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


def _image_status(url: str, headers: dict) -> str:
    try:
        resp = requests.get(url, headers=headers, timeout=10, stream=True)
        out = f"{resp.status_code} {resp.headers.get('content-type', '-').split(';')[0]}"
        resp.close()
        return out
    except requests.RequestException as e:
        return f"오류 {type(e).__name__}"


def check_image(url: str | None) -> tuple[str, str]:
    """(판정, 자세한 내용). 봇 User-Agent로 막히는 사이트인지 가리려고 브라우저 UA로도 한 번 더 본다."""
    if not url:
        return "skip", ""
    bot = _image_status(url, HEADERS)
    if bot.startswith("200 image/"):
        return "ok", bot
    browser = _image_status(url, {"User-Agent": BROWSER_UA, "Referer": url.split("/", 3)[0] + "//" + url.split("/")[2] + "/"})
    # 브라우저 UA로는 열리면 사용자 화면에서는 이미지가 보이는 것 → 데이터 오류가 아니라 검수 도구 쪽 한계
    verdict = "ok" if browser.startswith("200 image/") else "mismatch"
    return verdict, f"봇 UA: {bot} | 브라우저 UA: {browser}"


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
    """로그인(레뷰)이나 JS 렌더링·봇 확인(모두블로그)이 필요한 사이트 — 플랫폼별로 브라우저를 따로 연다."""
    from playwright.sync_api import sync_playwright

    pages: dict[str, tuple[str | None, str | None, int | None]] = {}
    by_platform: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_platform[row["platform"]].append(row)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, platform_rows in by_platform.items():
            context = browser.new_context()
            try:
                BY_LABEL[label].prepare_browser(context)
            except Exception as e:  # noqa: BLE001 - 준비 실패면 그 플랫폼 행은 '페이지 열림' 실패로 남긴다
                print(f"[{label}] 브라우저 준비 실패: {e}")
                context.close()
                continue
            page = context.new_page()
            _fetch_pages(page, platform_rows, pages)
            context.close()
        browser.close()
    return pages


def _fetch_pages(page, rows: list[dict], pages: dict) -> None:
    for row in rows:
        try:
            resp = page.goto(row["source_url"], wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)
            pages[row["source_url"]] = (page.inner_text("body"), page.url, resp.status if resp else None)
        except Exception:  # noqa: BLE001 - 한 페이지 실패가 검수 전체를 막으면 안 됨
            pages[row["source_url"]] = (None, None, None)


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
                if per > 0:
                    cur.execute(
                        "select * from public.campaigns where is_active and platform = %s order by random() limit %s",
                        (label, per),
                    )
                else:  # 전수
                    cur.execute(
                        "select * from public.campaigns where is_active and platform = %s order by source_url",
                        (label,),
                    )
                rows += cur.fetchall()
            return rows
    finally:
        conn.close()


def diagnostics_for(row: dict, res: dict[str, str], page_text: str | None, image_detail: str, seen: Counter) -> list[str]:
    """틀린 항목마다 플랫폼별 앞 3건만, DB 값과 검수 도구가 본 페이지 글자(앞부분)를 남긴다."""
    snippet = re.sub(r"\s+", " ", page_text or "")[:260]
    db_value = {
        "title": row.get("title"),
        "deadline": row.get("deadline_date"),
        "recruit": row.get("recruit_count"),
        "applicant": row.get("applicant_count"),
        "region": row.get("region_guguns") or row.get("region_sido"),
        "channel": row.get("review_channels"),
        "image": row.get("image_url"),
        "open": "(모집중이어야 함)",
        "page": row.get("source_url"),
    }
    lines = []
    for field in FIELDS:
        if res[field] not in ("mismatch", "missing"):
            continue
        key = (row["platform"], field)
        if seen[key] >= 3:
            continue
        seen[key] += 1
        extra = image_detail if field == "image" else f"페이지 글자 {len(page_text or '')}자, 앞부분: {snippet}"
        lines.append(f"- [{row['platform']}] {FIELD_LABELS[field]} | DB: {db_value[field]} | {extra} | {row['source_url']}")
    return lines


def report(results: list[tuple[dict, dict[str, str]]], diagnostics: list[str] | None = None) -> str:
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
        shown = problems[:150]
        lines += ["| 플랫폼 | 제목 | 안 맞는 항목 | 원본 |", "|---|---|---|---|", *shown]
        if len(problems) > len(shown):
            lines.append(f"\n… 외 {len(problems) - len(shown)}건은 첨부된 verify_result.csv 참고")
    else:
        lines.append("없음")
    if diagnostics:
        lines += ["", "### 진단 표본 (틀린 항목별 플랫폼당 3건: DB 값 vs 검수 도구가 읽은 페이지)", "", *diagnostics]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per", type=int, default=0, help="플랫폼별 표본 수 (0 = 전수)")
    parser.add_argument("--csv", default="verify_result.csv", help="캠페인별 판정 결과 CSV 경로")
    parser.add_argument("--only", help=f"쉼표로 구분한 커넥터 키 ({', '.join(BY_KEY)})")
    args = parser.parse_args()

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")] if args.only else REGISTRY
    rows = sample_rows([c.label for c in connectors], args.per)

    results: list[tuple[dict, dict[str, str]]] = []
    diagnostics: list[str] = []
    seen_diag: Counter = Counter()
    browser_rows = [r for r in rows if BY_LABEL[r["platform"]].needs_browser]
    browser_pages = fetch_with_browser(browser_rows) if browser_rows else {}
    for row in rows:
        page = browser_pages.get(row["source_url"]) if BY_LABEL[row["platform"]].needs_browser else fetch_static(row["source_url"])
        res = check_row(row, *(page or (None, None, None)))
        res["image"], image_detail = check_image(row.get("image_url"))
        results.append((row, res))
        diagnostics += diagnostics_for(row, res, (page or (None,))[0], image_detail, seen_diag)
        if not BY_LABEL[row["platform"]].needs_browser:
            time.sleep(0.3)  # 원본 사이트에 부담 주지 않게 (전수 검사는 수백 건)
    print(f"검사 {len(results)}건 완료")

    with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["platform", "title", "source_url", *FIELDS])
        for row, res in results:
            writer.writerow([row["platform"], row["title"], row["source_url"], *(res[f] for f in FIELDS)])

    md = report(results, diagnostics)
    print(md)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(md + "\n")


if __name__ == "__main__":
    main()
