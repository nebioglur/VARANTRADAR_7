import sys
import json
from scanner.universal_scanner import UniversalScanner
from data.pipeline import DataPipeline
from config.bist_symbols import BIST30_SYMBOLS

print("--- TEST SCANNER ---")
try:
    pipeline = DataPipeline()
    scanner = UniversalScanner(pipeline)
    # Sadece 2 hisse tarayalim ki hizli bitsin
    res = scanner.scan_pool_bulk(BIST30_SYMBOLS[:2])
    print("SCANNER BASARILI! Ozet:")
    print("Opportunities:", len(res.get("opportunities", [])))
    print("All Symbols Stats:", list(res.get("all_symbols_stats", {}).keys()))
except Exception as e:
    import traceback
    traceback.print_exc()
