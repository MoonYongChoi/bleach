"""verify.py 판정 규칙 테스트 — 2026-10-31 원본 대조에서 본 실제 페이지 문구 기준."""

import os
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import verify  # noqa: E402

TODAY = date(2026, 10, 31)


def row(**kw):
    base = {
        "platform": "모두블로그",
        "title": "BMW 강남전시장 황준영 딜러 18기",
        "deadline_date": date(2026, 11, 3),
        "recruit_count": 10,
        "applicant_count": 79,
        "campaign_type": "배송",
        "region_guguns": [],
        "region_sido": None,
        "review_channels": ["blog"],
    }
    return {**base, **kw}


class DeadlineTest(unittest.TestCase):
    PAGE = "블로그 P 8,000 [서포터] BMW 강남전시장 황준영 딜러 18기 모집 기간 3일 남음 선정 발표 11월 04일 모집 인원 10명 신청 인원 79명"

    def check(self, page, **kw):
        with patch("verify.today_kst", return_value=TODAY):
            return verify.check_row(row(**kw), page, "https://x/1", 200)

    def test_relative_days_left_matches(self):
        # 페이지에는 11/03이라는 날짜가 없고 "3일 남음"만 있다 (10/31 + 3 = 11/03)
        self.assertEqual(self.check(self.PAGE)["deadline"], "ok")

    def test_relative_days_left_mismatch(self):
        res = self.check(self.PAGE.replace("3일 남음", "9일 남음"))
        self.assertEqual(res["deadline"], "mismatch")

    def test_no_deadline_info_on_page(self):
        self.assertEqual(self.check("모집 인원 10명 BMW 강남전시장 황준영 딜러 18기")["deadline"], "missing")

    def test_absolute_date_still_works(self):
        self.assertEqual(self.check("신청기간 10.28(수) ~ 11.03(화) BMW 강남전시장 황준영 딜러 18기")["deadline"], "ok")

    def test_today_words(self):
        self.assertEqual(verify.days_left_on_page("신청 218 오늘까지"), 0)
        self.assertEqual(verify.days_left_on_page("내일마감"), 1)
        self.assertIsNone(verify.days_left_on_page("모집 중"))


class RealtimeTest(unittest.TestCase):
    def test_empty_page_counts_as_not_opened(self):
        # 레뷰 닫힌 캠페인: 페이지는 200인데 글자가 0자
        res = verify.check_row(row(), "", "https://www.revu.net/campaign/1", 200)
        self.assertIn(res["title"], ("missing", "skip"))


if __name__ == "__main__":
    unittest.main()
