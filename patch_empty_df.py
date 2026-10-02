with open("services/simulation_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Find the block:
#         for trade in [t for t in active_trades if t['status'] == 'OPEN']:
#             sym = trade['symbol']
#             df = dfs[sym]
#             if not df.empty:

idx1 = text.find("for trade in [t for t in active_trades if t['status'] == 'OPEN']:")
# Wait, this appears twice! 
# First time: for trade in [t for t in active_trades if t['status'] == 'OPEN']: # SATISLARI KONTROL ET
# Second time: # Seans sonu: acik pozisyonlari kapat.
idx_seans_sonu = text.find("# Seans sonu: acik pozisyonlari kapat.")

if idx_seans_sonu != -1:
    text_before = text[:idx_seans_sonu]
    text_after = text[idx_seans_sonu:]
    
    # We want to replace the `if not df.empty:` block in text_after.
    # It ends at `completed_trades.append(trade)`
    idx_append = text_after.find("completed_trades.append(trade)")
    if idx_append != -1:
        # Include the append line
        end_idx = idx_append + len("completed_trades.append(trade)")
        old_block = text_after[:end_idx]
        
        new_block = """# Seans sonu: acik pozisyonlari kapat.
        # Ancak BUGUN icin seans henuz 17:50'den onceyse canli modda acik birak;
        # frontend "Islemde" olarak gostersin.
        now = datetime.now()
        is_today = date_str == now.strftime("%Y-%m-%d")
        close_open_now = is_today and now.time() >= time(17, 50)

        for trade in [t for t in active_trades if t['status'] == 'OPEN']:
            sym = trade['symbol']
            df = dfs.get(sym)
            if df is not None and not df.empty:
                last_time = df.index[-1]
                close = float(df.iloc[-1]['Close'])
                if close_open_now:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(last_time)
                    trade['exit_price'] = close
                    buy_volume = trade['shares'] * trade['entry_price']
                    sell_volume = trade['shares'] * close
                    commission = (buy_volume + sell_volume) * 0.0004
                    gross_pnl = trade['shares'] * (close - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl - commission
                    trade['pnl_pct'] = (trade['pnl_val'] / buy_volume) * 100
                    trade['exit_reason'] = 'SEANS SONU NAKITE GECIS (17:50)'
                    from services.telegram_bot import notify_sim_trade
                    notify_sim_trade(sym, "SAT (GUN SONU)", close, trade["pnl_pct"], "17:50 Otomatik Kapanis", str(last_time)[:10], trade)
                else:
                    trade['exit_time'] = None
                    trade['exit_price'] = None
                    buy_volume = trade['shares'] * trade['entry_price']
                    gross_pnl = trade['shares'] * (close - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl
                    trade['pnl_pct'] = (gross_pnl / buy_volume) * 100
                    trade['exit_reason'] = "\u23F3 ACIK POZISYON"
                completed_trades.append(trade)
            else:
                trade['exit_time'] = None
                trade['exit_price'] = None
                trade['pnl_val'] = 0.0
                trade['pnl_pct'] = 0.0
                trade['exit_reason'] = "\u23F3 ACIK POZISYON (Veri Bekleniyor)"
                completed_trades.append(trade)"""
        
        text_after = new_block + text_after[end_idx:]
        text = text_before + text_after

with open("services/simulation_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("PATCH EMPTY DF OK")
