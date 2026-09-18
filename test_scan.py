# -*- coding: utf-8 -*-
from server import BACKGROUND_ERROR
from core.pipeline import DataPipeline
from scanner.universal_scanner import UniversalScanner
from config.bist_symbols import BIST50_SYMBOLS

print("Init Pipeline...")
pipeline = DataPipeline()
scanner = UniversalScanner(pipeline)

print("Starting scan...")
try:
    results = scanner.scan_pool_bulk(BIST50_SYMBOLS[:10])
    print("Scan success:", type(results))
    if isinstance(results, dict):
        print("Keys:", results.keys())
except Exception as e:
    import traceback
    traceback.print_exc()
