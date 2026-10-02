import re

with open('server.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_logic = """                # 2. GERÇEKÇİ HEDEF: Puanı en yüksek olan (sistemin en çok güvendiği) ilk 15 hisseyi al
                # Aralarında zarar edenler de olabilir, bunlara Stop-Loss (Zarar Kes) uygulanacak.
                selected_items = valid_items[:15]
                
                if not selected_items:
                    continue
                    
                stocks_count = len(selected_items)
                
                total_invested = 0.0
                total_return = 0.0
                trades = []
                
                current_capital = daily_budget
                current_hour = 10
                current_min = 0 # Güne 10:00'da başla
                
                for idx, item in enumerate(selected_items):
                    morning_price = float(item.get("morning_price", 0))
                    max_gain_pct = float(item.get("max_gain_pct", 0))
                    
                    # STOP-LOSS KONTROLÜ
                    # Eğer hisse o gün %1.5'ten fazla kâr bırakmışsa (başarılı setup), zirveden kâr al
                    if max_gain_pct > 1.5:
                        sell_price = float(item.get("daily_high", 0))
                        pnl_pct_final = max_gain_pct
                    else:
                        # Eğer hisse yeterince yükselmediyse (veya düştüyse), zarar kes işlemi (Örn: -2%)
                        sell_price = morning_price * (1.0 + (sl_input / 100.0))
                        pnl_pct_final = sl_input
                    
                    # 1. Akıllı Bekleme (Fırsat Tarama / Setup Bekleme)
                    # Hisseden hisseye değişen, organik 15-90 dk arası bekleme
                    wait_mins = 15 + int((abs(max_gain_pct) * 17 + idx) % 75)
                    
                    # Eğer ilk hisseyse ve puanı yüksekse, hızlı gir
                    if idx == 0 and item.get("Score", 0) > 70:
                        wait_mins = 15
                        
                    current_hour = current_hour + (current_min + wait_mins) // 60
                    current_min = (current_min + wait_mins) % 60
                    
                    # Eğer alış saati + 30 dk tutma süresi 17:50'yi geçiyorsa, artık fırsat arama, günü kapat!
                    # 17:50 = 17 * 60 + 50 = 1070
                    if (current_hour * 60 + current_min) + 30 > 1070:
                        break 
                        
                    buy_time_str = f"{current_hour:02d}:{current_min:02d}"
                    
                    # 2. Elde Tutma Süresi (En az 30 dk)
                    hold_mins = 30 + int((abs(max_gain_pct) * 23 + idx) % 60) # 30 ile 90 dk arası elinde tut
                    
                    sell_hour = current_hour + (current_min + hold_mins) // 60
                    sell_min = (current_min + hold_mins) % 60
                    
                    # 3. Kapanış Limiti (17:50'yi geçemez)
                    if (sell_hour * 60 + sell_min) > 1070:
                        sell_hour = 17
                        sell_min = 50
                        
                    sell_time_str = f"{sell_hour:02d}:{sell_min:02d}"
                    
                    # Tüm Büyüyen Sermaye Tek İşleme (Bileşik Etki)
                    allocation = current_capital
                    shares = math.floor(allocation / morning_price)
                    
                    if shares == 0:
                        continue
                        
                    invested = shares * morning_price
                    return_val = shares * sell_price
                    pnl = return_val - invested
                    
                    trades.append({
                        "symbol": item.get("symbol"),
                        "buy_price": morning_price,
                        "sell_price": sell_price,
                        "buy_time": buy_time_str,
                        "sell_time": sell_time_str,
                        "shares": shares,
                        "invested": invested,
                        "return_val": return_val,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct_final
                    })
                    
                    total_invested += invested
                    total_return += return_val
                    current_capital = current_capital - invested + return_val
                    
                    # Yeni saat, satılan saate eşitlenir (sonraki döngüde akıllı wait_mins eklenecek)
                    current_hour = sell_hour
                    current_min = sell_min"""

new_logic = """                # 2. GERÇEKÇİ HEDEF: Puanı en yüksek olan (sistemin en çok güvendiği) ilk 5 hisseyi al
                # Sermaye bu hisselere EŞİT bölünecek.
                selected_items = valid_items[:5]
                
                if not selected_items:
                    continue
                    
                stocks_count = len(selected_items)
                
                total_invested = 0.0
                total_return = 0.0
                trades = []
                
                allocation_per_stock = daily_budget / stocks_count
                
                for idx, item in enumerate(selected_items):
                    morning_price = float(item.get("morning_price", 0))
                    max_gain_pct = float(item.get("max_gain_pct", 0))
                    
                    # STOP-LOSS KONTROLÜ
                    # Eğer hisse o gün %1.5'ten fazla kâr bırakmışsa (başarılı setup), zirveden kâr al
                    if max_gain_pct > 1.5:
                        sell_price = float(item.get("daily_high", 0))
                        pnl_pct_final = max_gain_pct
                    else:
                        # Eğer hisse yeterince yükselmediyse (veya düştüyse), zarar kes işlemi (Örn: -2%)
                        sell_price = morning_price * (1.0 + (sl_input / 100.0))
                        pnl_pct_final = sl_input
                    
                    # 1. Alış ve Satış Saatleri (Eşzamanlı Dağılım)
                    # Hisseler peş peşe değil, gün içinde eşzamanlı olarak hedeflenir.
                    buy_hour = 10
                    buy_min = 15 + (idx * 5) # 10:15, 10:20, 10:25...
                    
                    hold_mins = 60 + int((abs(max_gain_pct) * 23 + idx) % 120)
                    
                    sell_hour = buy_hour + (buy_min + hold_mins) // 60
                    sell_min = (buy_min + hold_mins) % 60
                    
                    if (sell_hour * 60 + sell_min) > 1070: # 17:50 sınırı
                        sell_hour = 17
                        sell_min = 50
                        
                    buy_time_str = f"{buy_hour:02d}:{buy_min:02d}"
                    sell_time_str = f"{sell_hour:02d}:{sell_min:02d}"
                    
                    # Sermayenin o hisseye düşen payı ile alım yap
                    import math
                    shares = math.floor(allocation_per_stock / morning_price)
                    
                    if shares == 0:
                        continue
                        
                    invested = shares * morning_price
                    return_val = shares * sell_price
                    pnl = return_val - invested
                    
                    trades.append({
                        "symbol": item.get("symbol"),
                        "buy_price": morning_price,
                        "sell_price": sell_price,
                        "buy_time": buy_time_str,
                        "sell_time": sell_time_str,
                        "shares": shares,
                        "invested": invested,
                        "return_val": return_val,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct_final
                    })
                    
                    total_invested += invested
                    total_return += return_val"""

if old_logic in c:
    c = c.replace(old_logic, new_logic)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED TO FIND OLD LOGIC')
