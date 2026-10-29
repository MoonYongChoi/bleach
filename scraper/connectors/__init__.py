"""등록된 체험단 플랫폼 커넥터. 새 플랫폼은 connectors/<key>.py 에 Connector를 만들고 여기에 한 줄 추가한다."""

from __future__ import annotations

from connectors.base import Connector, RawCampaign
from connectors.pavlovu import PavlovuConnector
from connectors.reviewnote import ReviewnoteConnector
from connectors.revu import RevuConnector

REGISTRY: list[Connector] = [
    PavlovuConnector(),
    ReviewnoteConnector(),
    RevuConnector(),
]

BY_KEY: dict[str, Connector] = {c.key: c for c in REGISTRY}
# 현재 campaigns.platform 에는 표시 이름이 들어 있다 (키로 바꾸는 건 platforms 테이블 도입 때).
BY_LABEL: dict[str, Connector] = {c.label: c for c in REGISTRY}

__all__ = ["BY_KEY", "BY_LABEL", "REGISTRY", "Connector", "RawCampaign"]
