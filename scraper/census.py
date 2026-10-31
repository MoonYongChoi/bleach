"""원본 대조 전수조사 — 분류(카테고리·체험 종류·리뷰 채널·지역)까지 사이트 상세 페이지와 맞춰 본다.

    python census.py --dump --only dinnerqueen      # 상세 페이지 글자 표본 출력 (사이트별 추출 규칙을 만들기 위한 조사)
    python census.py --only dinnerqueen             # 전수 대조 (추출 규칙이 있는 플랫폼)

verify.py가 "DB 값이 페이지 글자 안에 있는가"만 보는 것과 달리, 여기서는 사이트가 *라벨을 붙여*
보여 주는 값(체험 종류, 채널, 카테고리, 지역)을 읽어서 DB 값과 직접 비교한다. DB는 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import re
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True, help=f"커넥터 키 ({', '.join(BY_KEY)})")
    parser.add_argument("--dump", action="store_true", help="표본 상세 페이지 글자를 출력만 한다")
    parser.add_argument("--lines", type=int, default=40)
    parser.add_argument("--skip", type=int, default=0, help="앞쪽 메뉴·푸터를 건너뛸 줄 수")
    args = parser.parse_args()

    connectors = [BY_KEY[k.strip()] for k in args.only.split(",")]
    rows = sample_rows([c.label for c in connectors], 0)
    print(f"활성 캠페인 {len(rows)}건")
    if args.dump:
        dump(rows, args.lines, args.skip)
        return
    raise SystemExit("전수 대조는 사이트별 추출 규칙을 만든 뒤에 켭니다 (--dump 결과 확인 필요)")


if __name__ == "__main__":
    main()
