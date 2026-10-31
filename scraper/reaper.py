"""수집 목록에서 한동안 안 보인 캠페인이 사이트에서도 사라졌는지 확인해 종료(is_active=false) 처리한다.

    python reaper.py                 # 미리보기 (DB를 바꾸지 않음)
    python reaper.py --apply         # 실제로 종료 처리
    python reaper.py --per 25        # 플랫폼별 25건만 (시험용)
    python reaper.py --stale-hours 24 --only revu,reviewnote

"목록에 없다"만으로는 종료하지 않는다 — 사이트 목록은 개수 한도가 있어서(리뷰노트 최신 96개 등) 아직
모집 중인 캠페인도 밀려나기 때문이다. 대신 그 캠페인 자신의 페이지를 열어서
  - 404/410 이거나
  - "모집 마감/종료" 문구가 있거나
  - (레뷰) 두 번 열어도 빈 페이지
일 때만 종료한다. 403·접속 실패·로그인 화면처럼 *모르는* 경우는 그대로 둔다.
마감일이 지난 캠페인은 loader.py가 매 수집마다 이미 종료 처리한다.

다시 목록에 나타난 캠페인은 다음 수집에서 loader가 is_active=true로 되살린다.
"""

from __future__ import annotations

import argparse
import os
from collections import Counter, defaultdict

from connectors import BY_KEY, BY_LABEL, REGISTRY
from verify import CLOSED_RE, compact, fetch_static, fetch_with_browser, uses_browser

# 한 플랫폼에서 이 비율 넘게 "사라짐"으로 나오면 검사 쪽 문제로 보고 그 플랫폼은 적용하지 않는다
SUSPICIOUS_RATIO = 0.6


def judge(page: tuple, empty_means_gone: bool = False) -> tuple[str, str]:
    """(판정, 이유). 판정: gone(종료) / open(진행 중) / unknown(모름 — 건드리지 않음) / empty(1차 빈 페이지)."""
    text, final_url, status = page
    if text is None:
        return "unknown", "접속 실패"
    if status in (404, 410):
        return "gone", f"HTTP {status}"
    if status and status >= 400:
        return "unknown", f"HTTP {status}"  # 403 같은 차단은 닫힌 게 아니다
    if final_url and "/login" in final_url:
        return "unknown", "로그인 화면으로 이동"
    if CLOSED_RE.search(text):
        return "gone", "모집 마감 문구"
    if empty_means_gone and not compact(text):
        return "empty", "빈 페이지"
    return "open", ""


def load_stale_rows(labels: list[str], stale_hours: int, per: int) -> list[dict]:
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            rows: list[dict] = []
            for label in labels:
                cur.execute(
                    "select id, platform, title, source_url, deadline_date, updated_at from public.campaigns "
                    "where is_active and platform = %s and updated_at < now() - make_interval(hours => %s) "
                    + ("order by random() limit %s" if per > 0 else "order by updated_at"),
                    (label, stale_hours, per) if per > 0 else (label, stale_hours),
                )
                rows += cur.fetchall()
            return rows
    finally:
        conn.close()


def deactivate(ids: list[str]) -> int:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute("update public.campaigns set is_active = false where id = any(%s::uuid[]) and is_active", (ids,))
            return cur.rowcount
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="실제로 종료 처리 (없으면 미리보기)")
    parser.add_argument("--stale-hours", type=int, default=24, help="이 시간 넘게 수집 목록에서 안 보인 캠페인만 검사")
    parser.add_argument("--per", type=int, default=0, help="플랫폼별 검사 건수 제한 (0 = 전부)")
    parser.add_argument("--only", help=f"쉼표로 구분한 커넥터 키 ({', '.join(BY_KEY)})")
    args = parser.parse_args()

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")] if args.only else REGISTRY
    rows = load_stale_rows([c.label for c in connectors], args.stale_hours, args.per)
    print(f"검사 대상 {len(rows)}건 (최근 {args.stale_hours}시간 동안 수집 목록에 없던 활성 캠페인)")

    # 1) 페이지 열기
    pages: dict[str, tuple] = {}
    browser_rows = [r for r in rows if uses_browser(BY_LABEL[r["platform"]])]
    if browser_rows:
        pages.update(fetch_with_browser(browser_rows))
    for row in rows:
        if row["source_url"] not in pages:
            pages[row["source_url"]] = fetch_static(row["source_url"])

    # 2) 판정 (빈 페이지는 한 번 더 열어서 확인)
    results: dict[str, tuple[str, str]] = {}
    recheck = []
    for row in rows:
        connector = BY_LABEL[row["platform"]]
        verdict = judge(pages[row["source_url"]], connector.empty_page_means_closed)
        results[row["source_url"]] = verdict
        if verdict[0] == "empty":
            recheck.append(row)
    if recheck:
        print(f"빈 페이지 {len(recheck)}건을 한 번 더 확인")
        second = fetch_with_browser(recheck)
        for row in recheck:
            verdict = judge(second.get(row["source_url"], (None, None, None)), True)
            results[row["source_url"]] = ("gone", "빈 페이지(2회)") if verdict[0] == "empty" else verdict

    # 3) 요약 + 안전장치 + 적용
    by_platform: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_platform[row["platform"]].append(row)

    lines = ["## 사라진 캠페인 종료 " + ("(적용)" if args.apply else "(미리보기 — DB 변경 없음)"), ""]
    lines += ["| 플랫폼 | 검사 | 종료 | 진행 중 | 모름 | 종료 이유 |", "|---|---|---|---|---|---|"]
    to_end: list[str] = []
    examples: list[str] = []
    for platform, items in sorted(by_platform.items()):
        verdicts = [results[r["source_url"]] for r in items]
        count = Counter(v[0] for v in verdicts)
        reasons = Counter(v[1] for v in verdicts if v[0] == "gone")
        gone = [r for r, v in zip(items, verdicts) if v[0] == "gone"]
        suspicious = len(items) >= 10 and len(gone) / len(items) > SUSPICIOUS_RATIO
        note = ", ".join(f"{k} {n}" for k, n in reasons.most_common()) or "-"
        if suspicious:
            note += " ⚠ 비율이 너무 높아 적용 보류(검사 방식 점검 필요)"
        lines.append(
            f"| {platform} | {len(items)} | {len(gone)} | {count['open']} | {count['unknown']} | {note} |"
        )
        if not suspicious:
            to_end += [r["id"] for r in gone]
        for r in gone[:3]:
            examples.append(f"- [{platform}] {r['title']} ({results[r['source_url']][1]}) {r['source_url']}")
        for r, v in list(zip(items, verdicts)):
            if v[0] == "unknown" and len([e for e in examples if e.startswith(f"- [{platform}] (모름")]) < 2:
                examples.append(f"- [{platform}] (모름: {v[1]}) {r['title']} {r['source_url']}")

    lines += ["", f"종료 대상 {len(to_end)}건", ""] + examples
    report = "\n".join(lines)
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")

    if args.apply and to_end:
        print(f"\n{deactivate(to_end)}건 종료 처리 완료")
    elif not args.apply:
        print("\n(미리보기라 DB는 그대로입니다. 적용하려면 --apply)")


if __name__ == "__main__":
    main()
