import sys
import logging

# Set up simple logging for test
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

print("--- 1. Testing Core and Analyzer ---")
try:
    from services.antigravity_core import AntigravityCore
    core = AntigravityCore()
    df = core.analyzer.calculate_indicators("ASELS.IS", "1d")
    print(f"[OK] Core Analyzer works. Rows fetched: {len(df)}")
except Exception as e:
    print(f"[ERROR] Core failed: {e}")

print("\n--- 2. Testing Screener (Multithreading) ---")
try:
    from services.screener import MarketScreener
    from config.bist_symbols import BIST30_SYMBOLS
    screener = MarketScreener()
    # Test with just 3 symbols to be fast
    test_symbols = BIST30_SYMBOLS[:3] 
    df_res = screener.run_screener(test_symbols)
    print(f"[OK] Screener works. Symbols tested: {test_symbols}")
    print(f"Screener returned {len(df_res)} rows.")
except Exception as e:
    print(f"[ERROR] Screener failed: {e}")

print("\n--- 3. Testing Telegram Service Configuration ---")
try:
    from services.telegram_bot import TelegramService
    ts = TelegramService()
    print(f"Is Telegram Configured? {ts.is_configured()}")
    print("[OK] Telegram Service initialized successfully.")
except Exception as e:
    print(f"[ERROR] Telegram Service failed: {e}")

print("\n--- 4. Testing Automation Bot Class ---")
try:
    from run_bot import AutomationBot
    bot = AutomationBot()
    print("[OK] AutomationBot initialized successfully.")
except Exception as e:
    print(f"[ERROR] AutomationBot failed: {e}")
