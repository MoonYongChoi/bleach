"""신규 커넥터 파서 테스트 — probe.py로 캡처한 실제 카드 마크업 기준 (tests/fixtures/)."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from connectors import BY_KEY  # noqa: E402
from connectors.base import split_title_brackets  # noqa: E402
from connectors.dinnerqueen import parse_cards  # noqa: E402
from connectors.modublog import to_raw  # noqa: E402
from normalize import normalize_for  # noqa: E402

TODAY = date(2026, 10, 29)
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def norm(key, raw):
    return normalize_for(BY_KEY[key], raw, today=TODAY).record


class BracketTest(unittest.TestCase):
    def test_split(self):
        title, b = split_title_brackets("[프리미엄][릴스][에이지투웨니스] 시그니처 에센스팩트 기획세트")
        self.assertEqual(title, "시그니처 에센스팩트 기획세트")
        self.assertEqual((b["channels"], b["others"]), (["릴스"], ["에이지투웨니스"]))
        title, b = split_title_brackets("[인천/서구] 스튜디오시루아")  # 서울오빠 카드에서 온 예시
        self.assertEqual((title, b["regions"]), ("스튜디오시루아", ["인천/서구"]))
        title, b = split_title_brackets("[촬영기자단] 멜킨 스마트 스텝플립 프로")
        self.assertEqual(b["types"], ["촬영기자단"])


class DinnerqueenTest(unittest.TestCase):
    def test_card(self):
        raws = parse_cards(fixture("dinnerqueen_card.html"))
        self.assertEqual(len(raws), 1)
        r = norm("dinnerqueen", raws[0])
        self.assertEqual(r["source_url"], "https://dinnerqueen.net/taste/1617679")
        self.assertEqual(r["title"], "시그니처 에센스팩트 기획세트")
        self.assertEqual(r["vendor"], "에이지투웨니스")
        self.assertEqual(r["review_channels"], ["reels"])
        self.assertEqual((r["applicant_count"], r["recruit_count"]), (218, 30))
        self.assertEqual(r["deadline_date"], TODAY)  # 오늘까지
        self.assertEqual(r["campaign_type"], "배송")
        self.assertTrue(r["image_url"].startswith("https://dq-files.gcdn.ntruss.com/"))


    def test_region_card_uses_site_category_badge(self):
        # 실제 카드 #37: [지역][릴스] 형태 + 사이트가 직접 붙인 "맛집" 분류 뱃지
        raws = parse_cards(fixture("dinnerqueen_region_card.html"))
        self.assertEqual(len(raws), 1)
        self.assertEqual(raws[0].category_raw, "맛집")
        r = norm("dinnerqueen", raws[0])
        self.assertEqual(r["title"], "초대창 청주동남지구점")
        self.assertEqual((r["region_sido"], r["region_gugun"]), ("충북", "청주시"))
        self.assertEqual(r["campaign_type"], "방문")
        self.assertEqual(r["category"], "맛집")
        self.assertEqual(r["review_channels"], ["reels"])
        self.assertEqual((r["applicant_count"], r["recruit_count"]), (2, 1))
        self.assertEqual(r["deadline_date"], date(2026, 11, 4))  # 6일 남음 (기준일 2026-10-29)
        self.assertEqual(r["description"], "모둠구이 B 체험권")

    def test_site_delivery_badge_wins_over_missing_region(self):
        card = fixture("dinnerqueen_region_card.html").replace("[충북 청주]", "").replace(">맛집<", ">배송<")
        r = parse_cards(card)[0]
        self.assertEqual(r.type_hint, "배송")


class ModublogTest(unittest.TestCase):
    # probe 로그의 실제 카드를 CARD_JS가 돌려주는 모양으로
    CARD = {
        "href": "https://www.modublog.co.kr/product/49263",
        "title": "[서울/둔촌동역] 에이유주얼리 1기",
        "offer": "실버 목걸이",
        "image": "https://www.modublog.co.kr/data/list_thumb/fashion/thumb_49263_247742.jpg",
        "channels": ["블로그"],
        "recruit": "신청 1/7",
        "deadline": "13일 남음",
    }

    def test_card(self):
        r = norm("modublog", to_raw(self.CARD))
        self.assertEqual(r["title"], "에이유주얼리 1기")
        self.assertEqual((r["region_sido"], r["region_gugun"]), ("서울", "둔촌동역"))
        self.assertEqual(r["region_guguns"], [])  # 역 이름은 하위 지역 필터 선택지가 아님
        self.assertEqual(r["campaign_type"], "방문")
        self.assertEqual((r["applicant_count"], r["recruit_count"]), (1, 7))
        self.assertEqual(r["deadline_date"], date(2026, 11, 11))
        self.assertEqual(r["review_channels"], ["blog"])
        self.assertEqual(r["category"], "뷰티")  # 썸네일 경로 fashion


if __name__ == "__main__":
    unittest.main()
