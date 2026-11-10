with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        valid_signals.sort(key=lambda x: (x.get('_total_rank_score', 0), float(x.get('score', 0))), reverse=True)
        selected = valid_signals[:self.max_positions]
        if not selected:
            return"""

replacement = """        valid_signals.sort(key=lambda x: (x.get('_total_rank_score', 0), float(x.get('score', 0))), reverse=True)

        # KULLANICI KURALI (KİLİTLİ TRADE LOG):
        # Eğer gün içinde daha önce işlem açılmış hisseler varsa (örneğin sabah girilen EPLAS),
        # bu hisseler yeni taramada skorları düşse dahi 'selected' listesinde KORUNUR ve terk edilmez.
        locked_symbols = set()
        try:
            conn_l = get_connection()
            cur_l = conn_l.cursor()
            cur_l.execute("SELECT DISTINCT symbol FROM trades WHERE owner=? AND date_str=?", (self.owner, date_str))
            locked_symbols = {r['symbol'] if isinstance(r, dict) or hasattr(r, 'keys') else r[0] for r in cur_l.fetchall()}
            conn_l.close()
        except Exception as e_lock:
            print(f"[SimEngine] Locked symbols read err: {e_lock}")

        selected = []
        selected_symbols = set()

        # 1. Öncelik: Zaten bugün işlem görmüş/alınmış hisseler
        for s in valid_signals:
            if s['symbol'] in locked_symbols:
                selected.append(s)
                selected_symbols.add(s['symbol'])

        # Eğer DB'de işlem görmüş ama bugünkü valid_signals içinde elenmiş bir hisse varsa (örn. gün ortası skoru değişti),
        # signals tablosundan orijinal sinyalini çekip listeye geri ekle
        missing_locked = locked_symbols - selected_symbols
        if missing_locked:
            for s in signals:
                if s['symbol'] in missing_locked:
                    selected.append(s)
                    selected_symbols.add(s['symbol'])

        # 2. Öncelik: Kalan kontenjanı en yüksek skorlu yeni adaylarla doldur
        for s in valid_signals:
            if len(selected) >= max(self.max_positions, len(locked_symbols)):
                break
            if s['symbol'] not in selected_symbols:
                selected.append(s)
                selected_symbols.add(s['symbol'])

        if not selected:
            return"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Target replaced!")
else:
    target_crlf = target.replace("\n", "\r\n")
    if target_crlf in content:
        content = content.replace(target_crlf, replacement.replace("\n", "\r\n"), 1)
        with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS: CRLF Target replaced!")
    else:
        print("FAILED to find target!")
