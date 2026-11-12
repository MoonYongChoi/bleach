"""등록된 커넥터(connectors.REGISTRY)를 모두 돌려 정제 후 Supabase에 적재. GitHub Actions에서 호출.

    python run_all.py                    # 수집 → 정제 → 적재
    python run_all.py --dry-run          # 수집 → 정제 → 품질 리포트만 출력 (DB 안 건드림)
    python run_all.py --only revu,pavlovu  # 일부 커넥터만
"""

from __future__ import annotations

import argparse
import os
import uuid
from datetime import datetime, timezone

from connectors import BY_KEY, DEFAULT_REGISTRY, Connector
from normalize import normalize_all
from quality import print_report


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run(connector: Connector, log: list[dict] | None = None) -> list:
    """커넥터 하나를 돌린다. log를 주면 플랫폼별 수집 기록(scrape_runs 한 줄)을 덧붙인다."""
    entry = {"platform": connector.label, "started_at": _now(), "status": "ok", "fetched": 0, "error": None,
             "complete": False}
    result: list = []
    missing = [name for name in connector.required_env if not os.environ.get(name)]
    if missing:
        print(f"[{connector.label}] 건너뜀: 환경변수 {', '.join(missing)} 없음")
        entry.update(status="skipped", error=f"환경변수 없음: {', '.join(missing)}")
    else:
        try:
            items = connector.fetch()
            print(f"[{connector.label}] 수집 {len(items)}건")
            entry["fetched"] = len(items)
            # 목록을 끝까지 읽은 회차만, 목록에서 사라진 캠페인을 모집 종료로 내릴 수 있다
            entry["complete"] = bool(getattr(connector, "complete", False))
            result = [(connector, item) for item in items]
        except Exception as e:  # noqa: BLE001 - 한 플랫폼 실패가 전체를 막으면 안 됨
            print(f"[{connector.label}] 실패: {e}")
            entry.update(status="failed", error=f"{type(e).__name__}: {e}")
    entry["finished_at"] = _now()
    if log is not None:
        log.append(entry)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 정제 결과 리포트만 출력")
    parser.add_argument("--only", help=f"쉼표로 구분한 커넥터 키 ({', '.join(BY_KEY)})")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env.local"))

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")] if args.only else DEFAULT_REGISTRY

    raw_campaigns: list = []
    run_log: list[dict] = []
    for connector in connectors:
        raw_campaigns += run(connector, run_log)

    records, report = normalize_all(raw_campaigns)
    print_report(report)

    if args.dry_run:
        print(f"[dry-run] 총 {len(raw_campaigns)}건 수집 → 정제 후 {len(records)}건 (적재 안 함)")
        return

    from loader import upsert_campaigns

    run_id = str(uuid.uuid4())
    n, expired = upsert_campaigns(records, [{**e, "run_id": run_id} for e in run_log])
    print(f"총 {len(raw_campaigns)}건 수집 → {n}건 upsert, 마감 지난 {expired}건 비활성화")


if __name__ == "__main__":
    main()
