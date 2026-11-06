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
from connectors.seoulouba import SeouloubaConnector, parse_list, with_area_hint  # noqa: E402
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
        title, b = split_title_brackets("[인천/서구] 스튜디오시루아")
        self.assertEqual((title, b["regions"]), ("스튜디오시루아", ["인천/서구"]))
        title, b = split_title_brackets("[촬영기자단] 멜킨 스마트 스텝플립 프로")
        self.assertEqual(b["types"], ["촬영기자단"])


class SeouloubaTest(unittest.TestCase):
    def setUp(self):
        self.raws = parse_list(fixture("seoulouba_cards.html"), "방문형")

    def test_visit_card(self):
        raw = self.raws[0]
        self.assertEqual(raw.source_url, "https://www.seoulouba.co.kr/campaign/?c=429685")
        r = norm("seoulouba", raw)
        self.assertEqual(r["title"], "스튜디오시루아")
        self.assertEqual((r["region_sido"], r["region_gugun"]), ("인천", "서구"))
        self.assertEqual(r["campaign_type"], "방문")
        self.assertEqual((r["applicant_count"], r["recruit_count"]), (1, 5))
        self.assertEqual(r["deadline_date"], TODAY)  # D-day
        self.assertEqual(r["review_channels"], ["blog"])
        self.assertEqual(r["description"], "헤어스트록 눈썹 or 틴트입술 중 택 1")
        self.assertTrue(r["image_url"].startswith("https://www.seoulouba.co.kr/data/campaign_list/"))
        self.assertEqual(r["category"], "뷰티")

    def test_delivery_and_reporter(self):
        delivery = norm("seoulouba", self.raws[1])
        self.assertEqual(delivery["title"], "멜킨 천국의 돌돌이")
        self.assertEqual(delivery["campaign_type"], "배송")
        self.assertIsNone(delivery["region_sido"])
        self.assertEqual((delivery["applicant_count"], delivery["recruit_count"]), (94, 1))
        reporter = norm("seoulouba", self.raws[2])
        self.assertEqual(reporter["title"], "멜킨 스마트 스텝플립 프로")
        # 카드 태그는 "배송형"이지만 제목에 [촬영기자단] — 카드 태그를 우선한다
        self.assertIn(reporter["campaign_type"], ("배송", "기자단"))

    def test_closed_cards_are_skipped(self):
        html = fixture("seoulouba_cards.html").replace("<span> D-day</span>", "<span>마감</span>", 1)
        raws = parse_list(html, "방문형")
        self.assertEqual(len(raws), 2)
        self.assertNotIn("?c=429685", " ".join(r.source_url for r in raws))

    def test_site_category_and_dday(self):
        html = fixture("seoulouba_cards.html").replace("<span> D-day</span>", "<span>D-6</span>", 1)
        raw = parse_list(html, "방문형", "뷰티/패션")[0]
        r = norm("seoulouba", raw)
        self.assertEqual(r["category_raw"], "뷰티/패션")
        self.assertEqual(r["category"], "뷰티")
        self.assertEqual(r["deadline_date"].toordinal() - TODAY.toordinal(), 6)

    def test_area_hint_fills_sido(self):
        raw = parse_list(fixture("seoulouba_cards.html").replace("[인천/서구]", "[가산]"), "방문형")[0]
        self.assertIsNone(norm("seoulouba", raw)["region_sido"])
        r = norm("seoulouba", with_area_hint(raw, "서울"))
        self.assertEqual(r["region_sido"], "서울")
        # 제목 괄호로 이미 시/도가 정해지면 손대지 않는다
        raw2 = with_area_hint(parse_list(fixture("seoulouba_cards.html"), "방문형")[0], "서울")
        self.assertEqual(norm("seoulouba", raw2)["region_sido"], "인천")

    def test_paging_until_closed_page(self):
        cards = fixture("seoulouba_cards.html")
        one = cards.split("</li>")[0] + "</li>"

        def card(i, closed=False):
            c = one.replace("429685", str(500000 + i))
            return c.replace("<span> D-day</span>", "<span>마감</span>") if closed else c

        first = "<ul>" + "".join(card(i) for i in range(192)) + "</ul>"
        page2 = "".join(card(192 + i) for i in range(36))
        page3 = "".join(card(300 + i, closed=True) for i in range(36))
        calls = []

        class Resp:
            def __init__(self, text):
                self.text = text

            def raise_for_status(self):
                pass

        class Session:
            headers: dict = {}

            def request(self, method, url, **kw):
                calls.append((method, kw.get("data", {}).get("more")))
                if method == "GET":
                    return Resp(first)
                return Resp({192: page2, 228: page3}.get(kw["data"]["more"], ""))

        import connectors.seoulouba as so
        so.DELAY, delay = 0, so.DELAY
        try:
            c = SeouloubaConnector()
            c.session = Session()
            got = c._list("378", "방문형", "맛집")
        finally:
            so.DELAY = delay
        self.assertEqual(len(got), 228)  # 192 + 36, 통째로 마감인 3쪽에서 멈춤
        self.assertEqual(calls, [("GET", None), ("POST", 192), ("POST", 228)])
        self.assertTrue(all(r.category_raw == "맛집" for r in got))


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

    def test_payback_bracket_is_purchase_type_and_real_vendor(self):
        # 2026-10-31 전수 대조: 사이트는 "페이백 캠페인"인데 배송으로 들어가고 업체가 "전국"이던 카드
        card = (
            '<div class="qz-dq-card campaign"><a class="qz-dq-card__link" href="/taste/1614101" '
            'title="[전국][페이백][포장][교촌치킨] 오리지널 찰도그 신청하기"><img src="/a.jpg"></a>'
            '<div class="qz-dq-card__text"><p>[전국][페이백][포장][교촌치킨] 오리지널 찰도그</p>'
            "<p>찰도그 2종</p><p>8일 남음 | 신청 11 / 6</p></div></div>"
        )
        r = norm("dinnerqueen", parse_cards(card)[0])
        self.assertEqual(r["campaign_type"], "구매")
        self.assertEqual(r["vendor"], "교촌치킨")
        self.assertEqual((r["region_sido"], r["region_gugun"]), (None, None))


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

    def test_sns_category_prefix(self):
        card = {**self.CARD, "image": "https://www.modublog.co.kr/data/list_thumb/sns_fashion/thumb_49182_27039.jpg"}
        r = norm("modublog", to_raw(card))
        self.assertEqual((r["category_raw"], r["category"]), ("fashion", "뷰티"))


if __name__ == "__main__":
    unittest.main()
