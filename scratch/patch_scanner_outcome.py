import os

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'tech_result["v8_execution"] = v8_exec'
idx = text.find(target)
if idx != -1:
    insert = """
        # --- V8 OUTCOME REGISTRATION ---
        try:
            if v8_exec.get('entry_status') in ['ENTER', 'WAIT_PULLBACK']:
                from v8_engine.learning import OutcomeEngine
                from datetime import datetime
                
                if not hasattr(self, 'registered_v8_signals'):
                    self.registered_v8_signals = {}
                    self.registered_v8_date = datetime.now().date()
                    
                if self.registered_v8_date != datetime.now().date():
                    self.registered_v8_signals = {}
                    self.registered_v8_date = datetime.now().date()
                    
                # Sinyal daha once kaydedilmediyse kaydet
                if symbol not in self.registered_v8_signals:
                    oe = OutcomeEngine()
                    price = float(df['close'].iloc[-1] if 'close' in df.columns else df['Close'].iloc[-1])
                    sig_id = oe.register_signal(symbol, price, v8_breakout, v8_exec, regime)
                    self.registered_v8_signals[symbol] = sig_id
                    print(f"[V8 LEARNING] Registered Signal for {symbol}: {v8_exec.get('entry_status')}")
        except Exception as e:
            print(f"[V8 LEARNING ERROR] {e}")
        # -------------------------------
"""
    if 'V8 OUTCOME REGISTRATION' not in text:
        text = text[:idx + len(target)] + "\n" + insert + text[idx + len(target):]
        with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
            f.write(text)
        print('Patched Outcome Engine')
    else:
        print('Already patched')
else:
    print('Target not found')
