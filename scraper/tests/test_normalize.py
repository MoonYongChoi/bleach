"""normalize.py 회귀 테스트 — 실제로 수집됐던 레뷰/파블로/리뷰노트 원본 값으로 검증.

    cd scraper && python -m unittest discover -s tests
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from connectors import BY_LABEL, REGISTRY  # noqa: E402
from connectors.base import RawCampaign  # noqa: E402
from normalize import normalize_all, normalize_campaign, normalize_for  # noqa: E402
from regions import resolve_region  # noqa: E402

TODAY = date(2026, 10, 28)


def norm(raw):
    """실제 파이프라인과 같이 platform에 맞는 커넥터의 힌트를 붙여서 정제."""
    connector = BY_LABEL.get(raw.get("platform"))
    if connector is None:
        return normalize_campaign(raw, today=TODAY)
    fields = {k: v for k, v in raw.items() if k != "platform"}
    return normalize_for(connector, RawCampaign(**fields), today=TODAY)


class RevuTest(unittest.TestCase):
    def product(self, **kw):
        base = {
            "platform": "레뷰",
            "title": "스타일 보온텀블러",
            "region_raw": None,
            "deadline_date": date(2026, 10, 28),
            "source_url": "https://www.revu.net/campaign/1427250",
            "category_raw": None,
            "type_hint": "제품",
            "description": "보온텀블러 1개",
            "image_url": "https://files.weble.net/campaign/data/1427250/thumb200_x.jpg?bust=1",
            "vendor": "라포레",
            "recruit_count": 10,
            "applicant_count": 545,
        }
        return {**base, **kw}

    def test_product_is_delivery_without_region(self):
        r = norm(self.product()).record
        self.assertEqual(r["campaign_type"], "배송")
        self.assertIsNone(r["region_sido"])
        self.assertIsNone(r["region_gugun"])
        self.assertEqual(r["category"], "생활")  # 텀블러
        self.assertTrue(r["is_active"])  # 오늘 마감은 아직 유효

    def test_food_product_goes_to_food_delivery_not_matjip(self):
        r = norm(self.product(title="오리주물럭_릴스", description="오리주물럭 2팩")).record
        self.assertEqual(r["category"], "식품·배송")

    def test_beauty_product(self):
        r = norm(self.product(title="엑토인7퍼센트3종세트_릴스", description="엑토인 크림 3종세트")).record
        self.assertEqual(r["category"], "뷰티")

    def test_region_page_bracket_resolves(self):
        cases = {
            "수원": ("경기", "수원시"),
            "일산": ("경기", "고양시"),
            "코엑스": ("서울", "강남구"),
            "인천": ("인천", None),
        }
        for bracket, expected in cases.items():
            r = norm(self.product(type_hint="지역", region_raw=bracket, vendor=None)).record
            self.assertEqual(r["campaign_type"], "방문", bracket)
            self.assertEqual((r["region_sido"], r["region_gugun"]), expected, bracket)

    def test_expo_ticket_is_culture(self):
        r = norm(
            self.product(type_hint="지역", region_raw="코엑스", title="푸드위크 코리아 오뚜기부스", description="입장권 2매")
        ).record
        self.assertEqual(r["category"], "문화·여가")

    def test_short_keywords_do_not_false_match(self):
        # "박람회 " 가 '회'(횟집), "알마슬립"이 '립'(뷰티)에 걸리던 문제
        r = norm(
            self.product(type_hint="지역", region_raw="일산", title="2026고양가구박람회 알마슬립", description="레뷰포인트")
        ).record
        self.assertEqual(r["category"], "문화·여가")

    def test_expired(self):
        res = norm(self.product(deadline_date=date(2026, 10, 27)))
        self.assertFalse(res.record["is_active"])
        self.assertIn("expired", res.issues)


class ReviewnoteTest(unittest.TestCase):
    RAW = {
        "platform": "리뷰노트",
        "title": "서울 코엑스 글로벌 베이비페어",
        "region_sido": "서울",
        "region_gugun": "강남구",
        "deadline_date": "2026-11-13T14:59:59.999Z",
        "source_url": "https://www.reviewnote.co.kr/campaigns/1507714",
        "category_raw": "기타",
        "type_hint": "VISIT",
        "description": "드림상품권 5만원 (별도 상세 안내 예정)",
        "image_url": "https://img.reviewnote.cloud/x.jpg",
        "vendor": None,
        "recruit_count": 10,
        "applicant_count": 84,
    }

    def test_deadline_converted_to_kst(self):
        r = norm(self.RAW).record
        self.assertEqual(r["deadline_date"], date(2026, 11, 13))
        # UTC 자정 직전 마감 = KST 다음날 아침 → KST 날짜를 써야 한다
        r2 = norm({**self.RAW, "deadline_date": "2026-11-13T15:30:00Z"}).record
        self.assertEqual(r2["deadline_date"], date(2026, 11, 14))

    def test_generic_category_inferred(self):
        r = norm(self.RAW).record
        self.assertEqual(r["category_raw"], "기타")
        self.assertIn(r["category"], ("문화·여가", "생활"))
        self.assertEqual(r["campaign_type"], "방문")
        self.assertEqual((r["region_sido"], r["region_gugun"]), ("서울", "강남구"))

    def test_long_sido_name_normalized(self):
        r = norm({**self.RAW, "region_sido": "경기도", "region_gugun": "수원시"}).record
        self.assertEqual(r["region_sido"], "경기")

    def test_delivery_drops_region(self):
        r = norm({**self.RAW, "type_hint": "DELIVERY", "title": "유기농 샐러드 정기배송"}).record
        self.assertEqual(r["campaign_type"], "배송")
        self.assertIsNone(r["region_sido"])
        self.assertEqual(r["category"], "식품·배송")

    def test_remote_campaign(self):
        # 실제 DB: 리뷰노트 재택 캠페인은 city/sido 둘 다 "재택"
        r = norm({**self.RAW, "region_sido": "재택", "region_gugun": "재택", "type_hint": "ETC"}).record
        self.assertEqual(r["campaign_type"], "재택")
        self.assertEqual((r["region_sido"], r["region_gugun"]), (None, None))

    def test_string_counts(self):
        r = norm({**self.RAW, "recruit_count": "5", "applicant_count": "1,678"}).record
        self.assertEqual((r["recruit_count"], r["applicant_count"]), (5, 1678))


class PavlovuTest(unittest.TestCase):
    RAW = {
        "platform": "파블로",
        "title": "[용산] 한우 오마카세",
        "region_raw": "용산/중구",
        "deadline_date": None,
        "deadline_days_left": 4,
        "source_url": "https://pavlovu.com/review_campaign.php?cp_id=1",
        "category_raw": "맛집",
        "description": "불고기 2인분+설렁탕 1그릇 (3.5만원 상당)",
        "image_url": "/data/campaign/1.jpg",
        "vendor": "OO식당",
        "recruit_count": 10,
        "applicant_count": 3,
    }

    def test_visit_campaign(self):
        res = norm(self.RAW)
        r = res.record
        self.assertEqual(r["title"], "한우 오마카세")  # [괄호] 프리픽스 제거
        self.assertEqual((r["region_sido"], r["region_gugun"]), ("서울", "용산구/중구"))
        self.assertEqual(r["deadline_date"], date(2026, 11, 1))  # D-4 fallback
        self.assertEqual(r["category"], "맛집")
        self.assertEqual(r["campaign_type"], "방문")
        self.assertIsNone(r["image_url"])  # 상대경로는 스크래퍼가 절대경로로 바꿔야 함
        self.assertIn("no_image", res.issues)

    def test_reward_only_title_hidden(self):
        # 실제 DB: 파블로 기자단 39건이 제목 "5,000포인트", 제공내역 "추가 안내사항"
        res = norm({**self.RAW, "title": "5,000포인트", "description": "추가 안내사항", "region_raw": "기자단"})
        self.assertFalse(res.record["is_active"])
        self.assertIn("title_is_reward", res.issues)
        self.assertIsNone(res.record["description"])
        self.assertEqual(res.record["campaign_type"], "기자단")

    def test_cafe_refines_matjip(self):
        r = norm({**self.RAW, "title": "성수 베이커리 카페", "region_raw": "성수"}).record
        self.assertEqual(r["category"], "카페·디저트")
        self.assertEqual(r["region_sido"], "서울")

    def test_delivery_label_in_region(self):
        r = norm({**self.RAW, "region_raw": "배송", "category_raw": "뷰티", "title": "수분 크림"}).record
        self.assertEqual(r["campaign_type"], "배송")
        self.assertIsNone(r["region_gugun"])
        self.assertEqual(r["category"], "뷰티")


class ChannelAndTypeTest(unittest.TestCase):
    def test_title_suffix_becomes_channel(self):
        # 실제 DB: 레뷰 "오리주물럭_릴스"
        r = norm({"platform": "레뷰", "title": "오리주물럭_릴스", "source_url": "u", "type_hint": "제품"}).record
        self.assertEqual(r["title"], "오리주물럭")
        self.assertEqual(r["review_channels"], ["reels"])

    def test_platform_channel_codes(self):
        r = norm({**ReviewnoteTest.RAW, "channels_raw": ["BLOG"]}).record
        self.assertEqual(r["review_channels"], ["blog"])
        r = norm({**PavlovuTest.RAW, "channels_raw": ["인스타", "블로그", "모름"]}).record
        self.assertEqual(r["review_channels"], ["blog", "instagram"])  # 표시 순서로 정렬, 모르는 값 무시

    def test_no_channel_flagged(self):
        res = norm(ReviewnoteTest.RAW)
        self.assertEqual(res.record["review_channels"], [])
        self.assertIn("no_channel", res.issues)

    def test_payback_is_purchase_type(self):
        r = norm({**ReviewnoteTest.RAW, "type_hint": "DELIVERY", "is_payback": True}).record
        self.assertEqual(r["campaign_type"], "구매")
        self.assertIsNone(r["region_sido"])

    def test_platform_hints_do_not_leak(self):
        # 리뷰노트 고유 코드 "VISIT"은 다른 플랫폼에서는 의미가 없다
        r = norm({"platform": "파블로", "title": "t", "source_url": "u", "type_hint": "VISIT"}).record
        self.assertEqual(r["campaign_type"], "기타")


class ConnectorTest(unittest.TestCase):
    def test_registry_contract(self):
        keys = [c.key for c in REGISTRY]
        self.assertEqual(len(keys), len(set(keys)))
        for c in REGISTRY:
            self.assertTrue(c.key and c.label and c.base_url, c)
            self.assertTrue(callable(c.fetch))
            for value in c.type_hints.values():
                self.assertIn(value, ("방문", "배송", "구매", "기자단", "재택", "기타"))

    def test_from_db_row_is_idempotent(self):
        # 이미 정제된 행을 다시 backfill해도 값이 바뀌지 않아야 한다
        for raw in (ReviewnoteTest.RAW, PavlovuTest.RAW, RevuTest().product()):
            connector = BY_LABEL[raw["platform"]]
            first = norm(raw).record
            again = normalize_for(connector, connector.from_db_row(first), today=TODAY).record
            for key in ("title", "region_sido", "region_gugun", "category", "campaign_type", "review_channels"):
                self.assertEqual(first[key], again[key], (raw["platform"], key))

    def test_reviewnote_legacy_title_restored(self):
        c = BY_LABEL["리뷰노트"]
        raw = c.from_db_row({"source_url": "u", "title": "베이글모닝 - 키링 1개", "description": "키링 1개"})
        self.assertEqual(raw.title, "베이글모닝")


class GenericTest(unittest.TestCase):
    def test_missing_required_dropped(self):
        records, report = normalize_all([{"platform": "파블로", "title": " ", "source_url": "x"}], today=TODAY)
        self.assertEqual(records, [])
        self.assertIn("missing_required", report[0][1])

    def test_dedup_by_source_url(self):
        raw = {"platform": "레뷰", "title": "a", "source_url": "u", "type_hint": "제품"}
        records, _ = normalize_all([raw, {**raw, "title": "b"}], today=TODAY)
        self.assertEqual([r["title"] for r in records], ["b"])

    def test_bad_values(self):
        r = norm(
            {
                "platform": "레뷰",
                "title": "  여러   칸   공백  ",
                "source_url": "u",
                "recruit_count": 0,
                "applicant_count": -3,
                "image_url": "https://x.com/img/noimage.png",
                "deadline_date": date(2030, 1, 1),
            }
        ).record
        self.assertEqual(r["title"], "여러 칸 공백")
        self.assertIsNone(r["recruit_count"])
        self.assertIsNone(r["applicant_count"])
        self.assertIsNone(r["image_url"])
        self.assertIsNone(r["deadline_date"])

    def test_http_image_upgraded(self):
        r = norm({"platform": "파블로", "title": "t", "source_url": "u", "image_url": "//pavlovu.com/a.jpg"}).record
        self.assertEqual(r["image_url"], "https://pavlovu.com/a.jpg")

    def test_real_pavlovu_regions(self):
        # 실제 DB에 있던 파블로 지역 값들
        self.assertEqual(resolve_region("서초/강남"), ("서울", "서초구/강남구"))
        self.assertEqual(resolve_region("인천/송도"), ("인천", "연수구"))
        self.assertEqual(resolve_region("충남/세종")[0], "충남")
        self.assertEqual(resolve_region("구매"), (None, None))
        r = norm({"platform": "파블로", "title": "t", "source_url": "u", "region_raw": "구매"}).record
        self.assertEqual(r["campaign_type"], "구매")

    def test_region_guguns_array(self):
        r = norm({**PavlovuTest.RAW, "region_raw": "서초/강남"}).record
        self.assertEqual(r["region_guguns"], ["서초구", "강남구"])
        r = norm({**PavlovuTest.RAW, "region_raw": "부천/부평"}).record  # 부평구는 인천
        self.assertEqual((r["region_sido"], r["region_guguns"]), ("경기", ["부천시"]))
        r = norm({**PavlovuTest.RAW, "region_raw": "중구"}).record  # 시/도 모르면 하위 지역 필터 대상 아님
        self.assertEqual(r["region_guguns"], [])

    def test_regions(self):
        self.assertEqual(resolve_region("중구"), (None, "중구"))  # 여러 시/도에 있음 → 모호
        self.assertEqual(resolve_region("서울 중구"), ("서울", "중구"))
        self.assertEqual(resolve_region("서울특별시 마포구"), ("서울", "마포구"))
        self.assertEqual(resolve_region("배송"), (None, None))


if __name__ == "__main__":
    unittest.main()
