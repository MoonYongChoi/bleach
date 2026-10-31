"""원본 대조 전수조사 — 분류(카테고리·체험 종류·리뷰 채널·지역)까지 사이트 상세 페이지와 맞춰 본다.

    python census.py --dump --only dinnerqueen      # 상세 페이지 글자 표본 출력 (사이트별 추출 규칙을 만들기 위한 조사)
    python census.py --only dinnerqueen             # 전수 대조 (추출 규칙이 있는 플랫폼)

verify.py가 "DB 값이 페이지 글자 안에 있는가"만 보는 것과 달리, 여기서는 사이트가 *라벨을 붙여*
보여 주는 값(체험 종류, 채널, 카테고리, 지역)을 읽어서 DB 값과 직접 비교한다. DB는 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from datetime import date
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

from connectors import BY_KEY, BY_LABEL
from verify import fetch_static, fetch_with_browser, sample_rows, uses_browser


def fetch_static_lines(url: str) -> tuple[str | None, str | None, int | None]:
    """verify.fetch_static은 글자를 한 줄로 합친다 — 라벨을 보려고 줄바꿈을 살려서 읽는다."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (BleachBot/1.0; +https://bleach.app)"}, timeout=15)
    except requests.RequestException:
        return None, None, None
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True), resp.url, resp.status_code


def pick_dump_rows(rows: list[dict], per_group: int = 1) -> list[dict]:
    """campaign_type별 몇 건 + 채널·카테고리·지역이 비어 있는 건을 섞어서 고른다."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[f"type={r.get('campaign_type')}"].append(r)
        if not r.get("review_channels"):
            groups["no_channel"].append(r)
        if not r.get("category"):
            groups["no_category"].append(r)
        if not r.get("region_sido"):
            groups["no_region"].append(r)
    picked: dict[str, dict] = {}
    for key, items in groups.items():
        for r in items[:per_group]:
            r["_why"] = key
            picked.setdefault(r["source_url"], r)
    return list(picked.values())


def dump(rows: list[dict], lines: int, skip: int = 0) -> None:
    chosen = pick_dump_rows(rows)
    browser_rows = [r for r in chosen if uses_browser(BY_LABEL[r["platform"]])]
    pages = fetch_with_browser(browser_rows) if browser_rows else {}
    for r in chosen:
        page = pages.get(r["source_url"]) if uses_browser(BY_LABEL[r["platform"]]) else fetch_static_lines(r["source_url"])
        text, final_url, status = page or (None, None, None)
        print(f"\n===== [{r['platform']}] {r['_why']} | {r['source_url']}")
        print(
            f"  DB: title={r['title']!r} type={r.get('campaign_type')} channels={r.get('review_channels')} "
            f"category={r.get('category')} raw_category={r.get('category_raw')} "
            f"region={r.get('region_sido')}/{r.get('region_gugun')} guguns={r.get('region_guguns')}"
        )
        print(f"  status={status} final={final_url} chars={len(text or '')}")
        body = [ln.strip() for ln in re.split(r"[\r\n]+", text or "") if ln.strip()]
        # 달력 숫자·마스킹된 신청자 이름 같은 잡음은 건너뛴다
        shown = [ln for ln in body if not re.fullmatch(r"[\d<>]{1,2}|.{1,2}\*{2,}", ln)]
        for i, ln in enumerate(shown[skip : skip + lines], start=skip):
            print(f"  {i:3d} | {ln[:150]}")



# ---------------------------------------------------------------------------
# 전수 대조: 사이트 상세 페이지의 라벨 → facts → DB 값과 비교
# ---------------------------------------------------------------------------
from collections import Counter

from normalize import CATEGORY_ALIASES, GENERIC_RAW_CATEGORIES, STANDARD_CATEGORIES, today_kst
from verify import CLOSED_RE

CHANNEL_TOKENS = [("릴스", "reels"), ("쇼츠", "shorts"), ("숏츠", "shorts"), ("클립", "clip"),
                  ("유튜브", "youtube"), ("틱톡", "tiktok"), ("블로그", "blog"), ("인스타", "instagram")]
SITE_TYPE_TO_DB = {"방문": "방문", "배송": "배송", "페이백": "구매", "구매": "구매", "기자단": "기자단", "블로그": None, "쇼핑몰": "구매"}
DQ_CATEGORY_BADGES = {"맛집", "뷰티", "배송", "기타", "기자단", "여가", "맞춤"}


def channels_in(text: str) -> set[str]:
    found = {code for word, code in CHANNEL_TOKENS if word in text}
    if "reels" in found:
        found.discard("instagram")  # "인스타 릴스"는 릴스 하나다
    return found


def _num(value: str | None) -> int | None:
    return int(value.replace(",", "")) if value and value.replace(",", "").isdigit() else None


def facts_dinnerqueen(lines: list[str]) -> dict:
    text = "\n".join(lines)
    f: dict = {}
    sentence = next((ln for ln in lines if ln.endswith("캠페인이에요")), None)
    if sentence:
        body = sentence[: -len("캠페인이에요")].strip()
        f["type_label"] = body.split()[-1] if body.split() else None
        f["channels"] = channels_in(body)
    f["category_label"] = next((ln for ln in lines[:25] if ln in DQ_CATEGORY_BADGES), None)
    m = re.search(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)\s*명", text)
    if m:
        f["applicant"], f["recruit"] = _num(m.group(1)), _num(m.group(2))
    m = re.search(r"신청 기간이\s*(\d+)\s*일\s*남았어요", text)
    f["days_left"] = int(m.group(1)) if m else (0 if "오늘" in text and "마감" in text else None)
    title = next((ln for ln in lines if ln.startswith("[")), "")
    brackets = re.findall(r"\[([^\]]+)\]", title)
    region = next((b for b in brackets if not channels_in(b) and b not in ("프리미엄", "페이백", "포장")), None)
    f["region_label"] = region.split()[0] if region else None
    return f


def facts_revu(lines: list[str]) -> dict:
    text = "\n".join(lines)
    f: dict = {}
    mission = ""
    if "캠페인 미션" in lines:
        i = lines.index("캠페인 미션")
        mission = "\n".join(lines[i : i + 8])
    notice = "\n".join(ln for ln in lines if "캠페인입니다" in ln or "업로드" in ln and "릴스" in ln)
    f["channels"] = channels_in(mission + "\n" + notice)
    addr = next((ln for ln in lines if ln.endswith("주소 복사")), None)
    if addr:
        parts = addr.split()
        f["region_label"] = " ".join(parts[:2])
        f["type_label"] = "방문"
    f["blank"] = not text.strip()
    return f


def facts_modublog(lines: list[str]) -> dict:
    f: dict = {}
    if "포인트 충전소" in lines:
        i = lines.index("포인트 충전소")
        # 뒤따르는 "+ 9,600" 같은 포인트·숫자 줄은 건너뛰고 처음 나오는 글자 줄이 분류 태그(블로그/쇼핑몰 …)
        f["type_label"] = next((ln for ln in lines[i + 1 : i + 8] if not re.fullmatch(r"[+\-P\s\d,.]+", ln)), None)
    f["channels"] = channels_in(f.get("type_label") or "")
    def after(label: str) -> str | None:
        return lines[lines.index(label) + 1] if label in lines and lines.index(label) + 1 < len(lines) else None
    f["period_label"] = after("모집 기간")
    f["recruit"] = _num(re.sub(r"\D", "", after("모집 인원") or ""))
    f["applicant"] = _num(re.sub(r"\D", "", after("신청 인원") or ""))
    m = re.search(r"(\d+)\s*일\s*남음", f["period_label"] or "")
    f["days_left"] = int(m.group(1)) if m else None
    return f


PAVLOVU_TYPES = {"방문형": "방문", "배송형": "배송", "구매형": "구매", "기자단형": "기자단", "기자단": "기자단"}


def facts_pavlovu(lines: list[str]) -> dict:
    f: dict = {}
    for ln in lines:
        m = re.search(r"·\s*(방문형|배송형|구매형|기자단형|기자단)\s*$", ln)
        if m:
            f["type_label"] = PAVLOVU_TYPES[m.group(1)]
            break
    cat = next((re.match(r"^(방문|배송|기자단|출장|구매)\s*·\s*(\S+)", ln) for ln in lines if re.match(r"^(방문|배송|기자단|출장|구매)\s*·\s*\S+", ln)), None)
    if cat:
        f["category_label"] = cat.group(2)
    if "미션" in lines:
        i = lines.index("미션")
        f["channels"] = channels_in(" ".join(lines[i + 1 : i + 4]))
    if "모집" in lines:
        i = lines.index("모집")
        f["recruit"] = _num(re.sub(r"\D", "", lines[i + 1])) if i + 1 < len(lines) else None
    f["realtime"] = "실시간 모집" in lines
    return f


FACTS = {"dinnerqueen": facts_dinnerqueen, "revu": facts_revu, "modublog": facts_modublog, "pavlovu": facts_pavlovu}


def _category_ok(site_label: str | None, db_category: str | None) -> bool | None:
    """None = 판단 불가(사이트 값이 범용 이름이거나 없음)."""
    if not site_label or site_label in GENERIC_RAW_CATEGORIES:
        return None
    std = CATEGORY_ALIASES.get(site_label) or (site_label if site_label in STANDARD_CATEGORIES else None)
    if std is None:
        return None
    if db_category == std:
        return True
    # normalize가 의도적으로 바꾸는 경우: 맛집↔카페, 배송형 음식은 식품·배송
    return std in ("맛집", "카페·디저트") and db_category in ("맛집", "카페·디저트", "식품·배송")


def compare(row: dict, f: dict, today) -> dict[str, str]:
    res: dict[str, str] = {}
    label = f.get("type_label")
    if label:
        expected = SITE_TYPE_TO_DB.get(label)
        res["type"] = "unmapped" if expected is None else ("ok" if expected == row.get("campaign_type") else "mismatch")
    if f.get("channels") is not None and f["channels"]:
        db = set(row.get("review_channels") or [])
        res["channel"] = "ok" if db == f["channels"] else ("db_empty" if not db else "mismatch")
    elif "channels" in f:
        res["channel"] = "site_none"
    ok = _category_ok(f.get("category_label"), row.get("category"))
    if ok is not None:
        res["category"] = "ok" if ok else "mismatch"
    if f.get("recruit") is not None and row.get("recruit_count") is not None:
        res["recruit"] = "ok" if f["recruit"] == row["recruit_count"] else "mismatch"
    if f.get("applicant") is not None and row.get("applicant_count") is not None:
        res["applicant"] = "ok" if f["applicant"] == row["applicant_count"] else "changed"
    if f.get("days_left") is not None and row.get("deadline_date"):
        d = row["deadline_date"]
        d = date.fromisoformat(d) if isinstance(d, str) else d
        res["deadline"] = "ok" if abs((d - today).days - f["days_left"]) <= 1 else "mismatch"
    region = f.get("region_label")
    if region and region != "전국":
        sido = row.get("region_sido") or ""
        gugun_names = " ".join(row.get("region_guguns") or [])
        res["region"] = "ok" if (region[:2] in sido or sido[:2] in region or region.split()[0][:2] in gugun_names) else "mismatch"
    return res


def run(rows: list[dict], key: str) -> None:
    import csv

    today = today_kst()
    extract = FACTS[key]
    browser_rows = [r for r in rows if uses_browser(BY_LABEL[r["platform"]])]
    pages = fetch_with_browser(browser_rows) if browser_rows else {}
    verdicts: dict[str, Counter] = defaultdict(Counter)
    crosstabs: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    closed = blank = unreadable = 0
    out = []
    for r in rows:
        text, final_url, status = pages.get(r["source_url"], (None, None, None)) if uses_browser(BY_LABEL[r["platform"]]) else fetch_static_lines(r["source_url"])
        if text is None or (status and status >= 400) or (final_url and "/login" in final_url):
            unreadable += 1
            continue
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln.strip()]
        if not lines:
            blank += 1
            continue
        if CLOSED_RE.search(text):
            closed += 1
        f = extract(lines)
        res = compare(r, f, today)
        if f.get("period_label") == "마감" and len(examples["사이트는 마감인데 DB는 진행 중"]) < 20:
            examples["사이트는 마감인데 DB는 진행 중"].append(f"- {r['title'][:28]} | DB 마감일 {r.get('deadline_date')} | {r['source_url']}")
        if not uses_browser(BY_LABEL[r["platform"]]):
            time.sleep(0.2)
        for field, v in res.items():
            verdicts[field][v] += 1
            if v in ("mismatch", "db_empty") and len(examples[f"{field}:{v}"]) < 6:
                site = {"type": f.get("type_label"), "channel": sorted(f.get("channels") or []), "category": f.get("category_label"),
                        "recruit": f.get("recruit"), "deadline": f.get("days_left"), "region": f.get("region_label")}.get(field)
                dbv = {"type": r.get("campaign_type"), "channel": r.get("review_channels"), "category": r.get("category"),
                       "recruit": r.get("recruit_count"), "deadline": str(r.get("deadline_date")), "region": f"{r.get('region_sido')}/{r.get('region_gugun')}"}.get(field)
                examples[f"{field}:{v}"].append(f"- {r['title'][:28]} | 사이트: {site} | DB: {dbv} | {r['source_url']}")
        crosstabs["체험종류 (사이트 → DB)"][(f.get("type_label"), r.get("campaign_type"))] += 1
        crosstabs["채널 (사이트 → DB)"][(",".join(sorted(f.get("channels") or [])) or "-", ",".join(sorted(r.get("review_channels") or [])) or "-")] += 1
        if "category_label" in f:
            crosstabs["카테고리 (사이트 → DB)"][(f.get("category_label"), r.get("category"))] += 1
        if "period_label" in f and not f.get("days_left"):
            crosstabs["모집기간 표기 (사이트 → DB 마감일 유무)"][(f.get("period_label"), "있음" if r.get("deadline_date") else "없음")] += 1
        out.append([r["platform"], r["title"], r["source_url"], *(f"{k}={v}" for k, v in res.items())])

    lines_out = [f"## 전수 대조: {rows[0]['platform']} (활성 {len(rows)}건)", "",
                 f"- 페이지 읽음 {len(rows) - unreadable - blank}건 · 읽기 실패/로그인 {unreadable} · 빈 페이지 {blank} · 마감 문구 {closed}", "",
                 "| 항목 | " + " | ".join(["ok", "mismatch", "changed", "db_empty", "unmapped", "site_none"]) + " |", "|---|---|---|---|---|---|---|"]
    for field, c in sorted(verdicts.items()):
        lines_out.append(f"| {field} | " + " | ".join(str(c.get(k, 0)) for k in ["ok", "mismatch", "changed", "db_empty", "unmapped", "site_none"]) + " |")
    for name, c in crosstabs.items():
        lines_out += ["", f"### {name}", "", "| 사이트 | DB | 건수 |", "|---|---|---|"]
        lines_out += [f"| {a} | {b} | {n} |" for (a, b), n in c.most_common(30)]
    lines_out += ["", "### 어긋난 예시"]
    for k, v in sorted(examples.items()):
        lines_out += ["", f"**{k}**", *v]
    report = "\n".join(lines_out)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    with open("census_result.csv", "w", newline="", encoding="utf-8-sig") as fh:
        csv.writer(fh).writerows([["platform", "title", "source_url", "verdicts..."], *out])


def fix_categories(rows: list[dict], key: str, apply: bool) -> None:
    """원본 카테고리(category_raw)가 비어 있는 캠페인을 상세 페이지의 사이트 카테고리로 채우고, 표준 카테고리를 다시 계산한다.
    기본은 미리보기(DB 변경 없음). apply=True일 때만 한 트랜잭션으로 쓴다. category_raw가 이미 있는 행은 건드리지 않는다."""
    from normalize import normalize_category

    targets = [r for r in rows if not r.get("category_raw")]
    print(f"카테고리 원본이 비어 있는 활성 캠페인 {len(targets)}건 (전체 {len(rows)}건)")
    pages = fetch_with_browser([r for r in targets if uses_browser(BY_LABEL[r["platform"]])])
    updates: list[tuple[str, str, str | None]] = []
    changes: Counter = Counter()
    no_label = unreadable = 0
    for r in targets:
        if uses_browser(BY_LABEL[r["platform"]]):
            text, final_url, status = pages.get(r["source_url"], (None, None, None))
        else:
            text, final_url, status = fetch_static_lines(r["source_url"])
            time.sleep(0.2)
        if text is None or (status and status >= 400) or (final_url and "/login" in final_url):
            unreadable += 1
            continue
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln.strip()]
        label = FACTS[key](lines).get("category_label")
        if not label:
            no_label += 1
            continue
        new_category = normalize_category(label, r["title"], r.get("description"), r.get("campaign_type") or "기타")
        updates.append((r["id"], label, new_category))
        changes[(r.get("category"), new_category)] += 1
    changed = sum(n for (old, new), n in changes.items() if old != new)
    lines_out = [f"## 카테고리 채우기 {'(적용)' if apply else '(미리보기 — DB 변경 없음)'}: {targets[0]['platform'] if targets else key}", "",
                 f"- 대상 {len(targets)}건 · 사이트 카테고리를 읽음 {len(updates)}건 · 라벨 없음 {no_label} · 읽기 실패 {unreadable}",
                 f"- 이 중 표준 카테고리가 바뀌는 건 {changed}건, 같은 건 {len(updates) - changed}건", "",
                 "| 지금(DB) | 바뀐 뒤 | 건수 |", "|---|---|---|"]
    lines_out += [f"| {old} | {new} | {n} |" for (old, new), n in changes.most_common(40) if old != new]
    report = "\n".join(lines_out)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")
    if not apply:
        print("\n(미리보기라 DB는 그대로입니다. 적용하려면 --apply)")
        return
    if not updates:
        return
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            execute_values(
                cur,
                "update public.campaigns c set category_raw = v.raw, category = v.cat "
                "from (values %s) as v(id, raw, cat) "
                "where c.id = v.id::uuid and c.category_raw is null",
                updates,
            )
            print(f"\n{cur.rowcount}건 적용 완료")
    finally:
        conn.close()


def drift_check(rows: list[dict], connector) -> None:
    """상세 페이지가 로그인 뒤에 있는 사이트용: 지금 목록을 다시 수집해 정제한 값과 DB 값을 비교한다.
    사이트 원본(목록 API)과 현재 정제 규칙 기준으로 DB가 얼마나 어긋났는지 본다 — 목록에 있는 캠페인만 해당."""
    from normalize import normalize_for

    fresh: dict[str, dict] = {}
    for raw in connector.fetch():
        result = normalize_for(connector, raw)
        if result.record:
            fresh[result.record["source_url"]] = result.record
    in_list = [r for r in rows if r["source_url"] in fresh]
    fields = ["title", "campaign_type", "review_channels", "category", "region_sido", "region_gugun", "recruit_count", "deadline_date", "applicant_count"]
    bad: dict[str, list[str]] = defaultdict(list)
    for r in in_list:
        new = fresh[r["source_url"]]
        for fld in fields:
            if (r.get(fld) or None) != (new.get(fld) or None):
                bad[fld].append(f"- {r['title'][:24]} | DB: {r.get(fld)} | 목록: {new.get(fld)} | {r['source_url']}")
    lines = [f"## 목록 재수집 대조: {connector.label}", "",
             f"- DB 활성 {len(rows)}건 중 현재 목록에 있는 건 {len(in_list)}건 (목록에 없는 {len(rows) - len(in_list)}건은 상세 페이지가 로그인 필요라 확인 못 함)", "",
             "| 항목 | 어긋남 | 검사 |", "|---|---|---|"]
    for fld in fields:
        lines.append(f"| {fld} | {len(bad[fld])} | {len(in_list)} |")
    for fld, items in bad.items():
        if fld != "applicant_count":
            lines += ["", f"**{fld}**", *items[:8]]
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True, help=f"커넥터 키 ({', '.join(BY_KEY)})")
    parser.add_argument("--dump", action="store_true", help="표본 상세 페이지 글자를 출력만 한다")
    parser.add_argument("--lines", type=int, default=40)
    parser.add_argument("--fix-category", action="store_true", help="비어 있는 category_raw를 사이트 카테고리로 채운다 (기본은 미리보기)")
    parser.add_argument("--apply", action="store_true", help="--fix-category를 실제로 DB에 쓴다")
    parser.add_argument("--skip", type=int, default=0, help="앞쪽 메뉴·푸터를 건너뛸 줄 수")
    args = parser.parse_args()

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")]
    rows = sample_rows([c.label for c in connectors], 0)
    print(f"활성 캠페인 {len(rows)}건")
    if args.dump:
        dump(rows, args.lines, args.skip)
        return
    key = connectors[0].key
    if args.fix_category:
        if key not in FACTS:
            raise SystemExit(f"{key}: 추출 규칙이 아직 없습니다")
        fix_categories(rows, key, args.apply)
        return
    if key == "reviewnote":
        drift_check(rows, connectors[0])
        return
    if key not in FACTS:
        raise SystemExit(f"{key}: 추출 규칙이 아직 없습니다")
    run(rows, key)


if __name__ == "__main__":
    main()
