"""Detective engine hizli yerel test (6 sembol)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import detective_engine as de

de.SYMBOLS = ["ASELS.IS", "THYAO.IS", "AKBNK.IS", "FROTO.IS", "SISE.IS", "TUPRS.IS"]
res = de.get_rows()
print("durum:", res["status"])
if res["status"] == "building":
    import time
    for _ in range(60):
        time.sleep(5)
        res = de.get_rows()
        if res["status"] == "ok":
            break
if res["status"] != "ok":
    print("HATA:", res.get("error"))
    sys.exit(1)

print("built_at:", res["built_at"], "| satir:", len(res["rows"]))
print("ozet:", res["summary"])
for r in res["rows"]:
    print(f"{r['symbol']:8} {r['status']:9} anom={r['anomaly']:3} yas={str(r['move_age']):>4} "
          f"ener={r['energy']:3} onay={r['confirm']:3} gec={r['delay']:3} kal={r['crowd']:3} "
          f"tuzak={r['trap']:3} rol={r['role']:11} fp={r['fingerprint']} frs={r['opportunity']:3}{r['opportunity_tag']}")

d = de.get_detail("ASELS")
if d:
    print("\n--- ASELS panel ---")
    print("zaman cizelgesi:", len(d["timeline"]), "olay")
    for e in d["timeline"][:6]:
        print("  ", e["time"], e["kind"], e["text"])
    print("ayni gecmis:", d["similar"])
    print("karakter:", d["character"])
    print("zincir:", d["chain"]["sector"], "uye:", len(d["chain"]["members"]), "sirada:", d["chain"]["next"])
    print("neden:", [w[1] for w in d["why"][:4]])
print("\nTEST TAMAM")
