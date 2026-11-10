# We want auto_send_v8_signals to:
# 1. Be called during the live background scan loop and whenever breakout radar updates
# 2. Use the same dynamic entry approval that the V8 breakout radar uses
# 3. Check v8_tg_sent table so every symbol is sent AT MOST ONCE per day!
# 4. Only send fresh/new ones that haven't been sent yet.

code_to_insert = '''
                    # V8 GİRİŞ ONAYLI YENİ HİSSELERİ TELEGRAM'A BİLDİR (Günde en fazla 1 kez / hisse)
                    try:
                        auto_send_v8_signals()
                    except Exception as _tg_v8_err:
                        print(f"[V8-TG] Otomatik bildirim döngü hatası: {_tg_v8_err}")
'''
print('Ready to plan patch')
