from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PricePoint:
    ts: datetime
    price: float


class PricingProvider:
    """Abstraction for current and forecast electricity prices."""

    def get_current_price(self) -> PricePoint:
        raise NotImplementedError

    def get_upcoming_prices(self) -> list[PricePoint]:
        raise NotImplementedError
