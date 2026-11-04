"""V8 real BIST warrant lookup.

No licensed/live warrant-chain provider is configured in this repository.
This module therefore refuses to invent codes, expiry dates, Greeks or leverage.
"""
from typing import Dict, Any


class VarrantEngine:
    def __init__(self, warrant_provider=None):
        self.warrant_provider = warrant_provider

    def find_best_varrant(self, symbol: str, direction: str = "CALL") -> Dict[str, Any]:
        clean_symbol = str(symbol or "").upper().replace(".IS", "")
        side = str(direction or "").upper()
        if side not in {"CALL", "PUT"}:
            return self._unavailable(clean_symbol, "INVALID_DIRECTION")
        if self.warrant_provider is None:
            return self._unavailable(clean_symbol, "REAL_CHAIN_PROVIDER_NOT_CONFIGURED")
        try:
            result = self.warrant_provider.find_best(clean_symbol, side)
        except Exception:
            return self._unavailable(clean_symbol, "PROVIDER_ERROR")
        if not isinstance(result, dict) or not result.get("warrant_code"):
            return self._unavailable(clean_symbol, "NO_VERIFIED_INSTRUMENT")
        # Provider results must carry their provenance; never label an estimate as a real quote.
        if result.get("instrument_source") not in {"BIST_REAL", "LICENSED_PROVIDER"}:
            return self._unavailable(clean_symbol, "UNVERIFIED_INSTRUMENT_SOURCE")
        result["status"] = "REAL_WARRANT_FOUND"
        return result

    @staticmethod
    def _unavailable(symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "status": "REAL_CHAIN_UNAVAILABLE",
            "reason": reason,
            "instrument_source": None,
            "warrant_code": None,
            "estimated_leverage": None,
            "message": "Güncel ve doğrulanmış BIST varant zinciri bağlı değil. Sentetik varant gerçek ürün gibi sunulmayacak."
        }
