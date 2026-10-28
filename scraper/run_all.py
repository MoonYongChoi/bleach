"""레뷰/파블로/리뷰노트를 모두 긁어서 Supabase에 적재. GitHub Actions에서 호출."""

from __future__ import annotations

from loader import upsert_campaigns
from pavlovu_scraper import fetch_campaigns as fetch_pavlovu
from reviewnote_scraper import fetch_campaigns as fetch_reviewnote
from revu_scraper import fetch_campaigns as fetch_revu


def run(scraper_name: str, fetch_fn) -> list[dict]:
    try:
        items = fetch_fn()
        print(f"[{scraper_name}] 수집 {len(items)}건")
        return items
    except Exception as e:  # noqa: BLE001 - 한 플랫폼 실패가 전체를 막으면 안 됨
        print(f"[{scraper_name}] 실패: {e}")
        return []


def main() -> None:
    all_campaigns: list[dict] = []
    all_campaigns += run("파블로", lambda: fetch_pavlovu(max_pages=5))
    all_campaigns += run("리뷰노트", fetch_reviewnote)
    all_campaigns += run("레뷰", fetch_revu)

    n = upsert_campaigns(all_campaigns)
    print(f"총 {len(all_campaigns)}건 수집 → {n}건 upsert 완료")


if __name__ == "__main__":
    main()
