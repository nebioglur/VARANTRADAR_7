# -*- coding: utf-8 -*-
with open('analysis/technical.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_vol = """            avg_vol_20 = float(volume.iloc[-21:-1].mean()) if len(volume) > 20 else float(volume.iloc[:-1].mean())
            vol_multiplier = round(current_vol / avg_vol_20, 1) if avg_vol_20 > 0 else 1.0
            
            if avg_vol_20 > 0:
                if current_vol > avg_vol_20 * 2.5:
                    score += 25
                    details.append(f"Y" Agresif Hacim Patlamas ({vol_multiplier}x).")
                elif current_vol > avg_vol_20 * 1.5:
                    score += 15
                    details.append(f"YOksek Hacim GiriYi ({vol_multiplier}x).")"""

new_vol = """            avg_vol_20 = float(volume.iloc[-21:-1].mean()) if len(volume) > 20 else float(volume.iloc[:-1].mean())
            vol_multiplier = round(current_vol / avg_vol_20, 1) if avg_vol_20 > 0 else 1.0
            
            # KULLANICI ISTEGI: En az %150 (1.5x) hacim gucu zorunlu
            if vol_multiplier < 1.5:
                return None
                
            if avg_vol_20 > 0:
                if current_vol > avg_vol_20 * 2.5:
                    score += 25
                    details.append(f"?? Agresif Hacim Patlamasý ({vol_multiplier}x).")
                elif current_vol > avg_vol_20 * 1.5:
                    score += 15
                    details.append(f"Yüksek Hacim Giriþi ({vol_multiplier}x).")"""

text = text.replace(old_vol, new_vol)

with open('analysis/technical.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("TECH PATCH OK")
