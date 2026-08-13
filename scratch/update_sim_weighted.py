import re

with open('server.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_logic = """                # 2. GERÇEKÇİ HEDEF: Puanı en yüksek olan (sistemin en çok güvendiği) ilk 5 hisseyi al
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
                    shares = math.floor(allocation_per_stock / morning_price)"""

new_logic = """                # 2. GERÇEKÇİ HEDEF: Puanı en yüksek olan (sistemin en çok güvendiği) ilk 5 hisseyi al
                # Sermaye, hisselerin Alış Puanına (Score) göre orantılı paylaştırılacak.
                selected_items = valid_items[:5]
                
                if not selected_items:
                    continue
                    
                stocks_count = len(selected_items)
                
                total_invested = 0.0
                total_return = 0.0
                trades = []
                
                # Tüm seçili hisselerin toplam puanını hesapla (Ağırlıklı dağılım için)
                total_score = sum(item.get("Score", 0) for item in selected_items)
                if total_score == 0:
                    total_score = stocks_count * 100 # Sıfıra bölünme hatasını engelle
                
                for idx, item in enumerate(selected_items):
                    morning_price = float(item.get("morning_price", 0))
                    max_gain_pct = float(item.get("max_gain_pct", 0))
                    item_score = item.get("Score", 100) if item.get("Score", 0) > 0 else 100
                    
                    # Sermayenin o hisseye düşen ağırlıklı payını hesapla (Örn: 90 puan alan, 40 alandan fazla bütçe alır)
                    allocation_per_stock = daily_budget * (item_score / total_score)
                    
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
                    
                    # Ağırlıklı sermaye ile alım yap
                    import math
                    shares = math.floor(allocation_per_stock / morning_price)"""

if old_logic in c:
    c = c.replace(old_logic, new_logic)
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED TO FIND OLD LOGIC')
