"""reaper.judge 규칙 — 확실한 증거가 있을 때만 종료하고, 모르면 그대로 둔다."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from connectors import BY_LABEL  # noqa: E402
from reaper import judge  # noqa: E402

# 2026-10-31 probe.py --text 로 받은 파블로 상세 페이지의 실제 줄 (진행 중 캠페인)
PAVLOVU_OPEN = (
    "스시오마카세 런치 2인 제공 (14만원 상당) 체험단 | 파블로 체험단 전체보기 방문 배송 기자단 "
    "모집 5명 신청 마감 11.04(수) · D-4 발표 11.05(목) 리뷰어 신청기간 10.28(수) ~ 11.04(수) 신청하기"
)


class JudgeTest(unittest.TestCase):
    def test_open_campaign_with_field_named_deadline_is_not_closed(self):
        # "신청 마감"은 항목 이름일 뿐이다
        self.assertEqual(judge((PAVLOVU_OPEN, "https://pavlovu.com/x", 200))[0], "open")

    def test_closed_text(self):
        verdict, reason = judge(("이 캠페인은 모집 마감 되었습니다", "https://x/1", 200))
        self.assertEqual((verdict, reason), ("gone", "모집 마감 문구"))

    def test_deleted_page(self):
        self.assertEqual(judge(("Not Found", "https://x/1", 404))[0], "gone")
        self.assertEqual(judge(("", "https://x/1", 410))[0], "gone")

    def test_blocked_or_unreachable_is_unknown_not_closed(self):
        # 디너의여왕 상세 페이지는 HeadlessChrome에 403을 준다 — 닫힌 게 아니다
        self.assertEqual(judge(("Forbidden", "https://x/1", 403))[0], "unknown")
        self.assertEqual(judge((None, None, None))[0], "unknown")
        self.assertEqual(judge(("", "https://x/login?redirect=1", 200))[0], "unknown")
        self.assertEqual(judge(("서버 오류", "https://x/1", 503))[0], "unknown")

    def test_empty_page_only_counts_where_the_site_does_that(self):
        self.assertEqual(judge(("", "https://x/1", 200), empty_means_gone=False)[0], "open")
        self.assertEqual(judge(("  \n ", "https://x/1", 200), empty_means_gone=True)[0], "empty")

    def test_only_revu_treats_empty_pages_as_closed(self):
        flags = {label: c.empty_page_means_closed for label, c in BY_LABEL.items()}
        self.assertEqual([l for l, v in flags.items() if v], ["레뷰"])


if __name__ == "__main__":
    unittest.main()
