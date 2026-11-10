with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """        conn = get_connection()
        cursor = conn.cursor()
        # Idempotent yeniden calistirma: ayni gunun eski islemleri temizlenir,
        # boylece farkli motor surumlerinin kayitlari karismaz.
        try:
            cursor.execute("DELETE FROM trades WHERE owner=? AND date_str=?", (self.owner, date_str))
        except Exception as e:
            print(f"[SimEngine] Eski trade temizleme hatasi: {e}")
        for key in order:"""

replacement = """        conn = get_connection()
        cursor = conn.cursor()
        # KULLANICI KURALI: Bir kez pozisyona girilen ve loga dusen islem ASLA silinmez.
        # DELETE FROM trades kaldirildi; ON CONFLICT DO UPDATE ile guncellenir.
        for key in order:"""

if target in content:
    new_content = content.replace(target, replacement, 1)
    with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Target replaced successfully!")
else:
    print("TARGET NOT FOUND! Let's check line endings or partial match.")
    target_crlf = target.replace("\n", "\r\n")
    if target_crlf in content:
        new_content = content.replace(target_crlf, replacement.replace("\n", "\r\n"), 1)
        with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("SUCCESS: CRLF Target replaced successfully!")
    else:
        print("CRLF also not found!")
