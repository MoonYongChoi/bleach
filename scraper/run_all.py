"""레뷰/파블로/리뷰노트를 모두 긁어서 정제 후 Supabase에 적재. GitHub Actions에서 호출.

    python run_all.py            # 수집 → 정제 → 적재
    python run_all.py --dry-run  # 수집 → 정제 → 품질 리포트만 출력 (DB 안 건드림)
"""

from __future__ import annotations

import argparse

from normalize import normalize_all
from pavlovu_scraper import fetch_campaigns as fetch_pavlovu
from quality import print_report
from reviewnote_scraper import fetch_campaigns as fetch_reviewnote


def fetch_revu() -> list[dict]:
    # Playwright는 레뷰에만 필요하니, 설치 안 된 환경에서도 나머지는 돌 수 있게 지연 import
    from revu_scraper import fetch_campaigns

    return fetch_campaigns()


def run(scraper_name: str, fetch_fn) -> list[dict]:
    try:
        items = fetch_fn()
        print(f"[{scraper_name}] 수집 {len(items)}건")
        return items
    except Exception as e:  # noqa: BLE001 - 한 플랫폼 실패가 전체를 막으면 안 됨
        print(f"[{scraper_name}] 실패: {e}")
        return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 정제 결과 리포트만 출력")
    args = parser.parse_args()

    raw_campaigns: list[dict] = []
    raw_campaigns += run("파블로", lambda: fetch_pavlovu(max_pages=5))
    raw_campaigns += run("리뷰노트", fetch_reviewnote)
    raw_campaigns += run("레뷰", fetch_revu)

    records, report = normalize_all(raw_campaigns)
    print_report(report)

    if args.dry_run:
        print(f"[dry-run] 총 {len(raw_campaigns)}건 수집 → 정제 후 {len(records)}건 (적재 안 함)")
        return

    from loader import upsert_campaigns

    n, expired = upsert_campaigns(records)
    print(f"총 {len(raw_campaigns)}건 수집 → {n}건 upsert, 마감 지난 {expired}건 비활성화")


if __name__ == "__main__":
    main()
