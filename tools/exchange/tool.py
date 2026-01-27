from typing import Any, Dict, Optional

from hala_orchestrator.tools import Tool
from services.exchange.exchange_rates import convert_currency


class ExchangeRatesTool(Tool):
    name = "exchange_rates"

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        base = kwargs.get("base") or "USD"
        target = kwargs.get("target")
        amount = kwargs.get("amount")
        if not target:
            raise ValueError("ExchangeRatesTool requires a target currency.")
        return await convert_currency(amount=amount, base=base, target=target)
