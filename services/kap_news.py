"""KAP (Kamuyu Aydinlatma Platformu) bulten filtresi.

Amac: giris oncesi hissenin son 24 saatte "Onemli Olay / Ozel Durum"
aciklamasi olup olmadigini kontrol etmek. Habersiz cikis, sermaye
olaylari, birlesme/bolunme gibi duyurular kirilim tuzaklarinin en
buyuk kaynaklarindan biridir.

Guvenli davranis: KAP'a erisilemezse (ag engeli, rate limit vb.)
filtre kendini sessizce devre disi birakir; hicbir sinyal engellenmez.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

_CACHE = {"ts": 0.0, "items": None, "ok": False, "error": ""}
_LOCK = threading.Lock()
CACHE_TTL = 300  # 5 dakikada bir tazele
LOOKBACK_HOURS = 24

# Giris engelleyen (riskli) duyuru anahtar kelimeri
_MATERIAL_KEYWORDS = [
    "özel durum", "önemli olay", "geri alım", "taahhüt", "ticari dava",
    "izahnameci", "bedelli", "sermaye azaltımı", "birleşme", "devralma",
    "bölünme", "tür değişikliği", "spk", "yatırım programı", "erişim engeli",
]
# Riskli sayilmayan (bilgi verici) duyurular
_NEUTRAL_HINTS = ["bedelsiz", "temettü", "kâr dağıtım", "yeni sipariş", "ihracat"]

_fetch_error_logged = False


def _date_str(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def _http_json(url: str, payload: dict = None, timeout: int = 8):
    import json as _json
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = _json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return _json.loads(raw.decode("utf-8", errors="replace"))


def _extract_text(item: dict) -> str:
    """Bir bulten kaydindan arama metnini cikarir (kodu iceren tum alanlar)."""
    keys = ("title", "bulletinTitle", "companyNameUx", "memberOid", "mkkMemberOid",
            "memberShortNameCod", "stockCode", "summary", "bulletinSummary")
    parts = []
    for k in keys:
        v = item.get(k)
        if v:
            parts.append(str(v))
    return " | ".join(parts)


def _parse_date(item: dict):
    for k in ("publishDate", "date", "disclosureDate", "publishedAt"):
        v = item.get(k)
        if not v:
            continue
        try:
            s = str(v).replace("Z", "").split(".")[0]
            return datetime.fromisoformat(s[:19])
        except Exception:
            continue
    return None


def _fetch_recent_disclosures() -> list:
    """Son 2 gunun KAP bultenlerini getirir. Basarisizsa exception firlatir."""
    today = datetime.now()
    frm = today - timedelta(days=2)
    candidates = [
        ("GET", f"https://www.kap.org.tr/tr/api/disclosures/fromDate/{_date_str(frm)}", None),
        ("POST", "https://www.kap.org.tr/tr/api/disclosures", {
            "fromDate": _date_str(frm), "toDate": _date_str(today + timedelta(days=1)),
            "bdkCod": 0, "mainSector": "", "subSector": "", "ruleType": "",
            "srcCategory": "", "index": [], "market": [],
        }),
        ("POST", "https://www.kap.org.tr/tr/api/disclosures/v2", {
            "fromDate": _date_str(frm), "toDate": _date_str(today + timedelta(days=1)),
            "bdkCod": 0, "mainSector": "", "subSector": "", "ruleType": "",
            "srcCategory": "", "index": [], "market": [],
        }),
    ]
    last_err = None
    for method, url, payload in candidates:
        try:
            data = _http_json(url, payload)
            if isinstance(data, list) and data:
                return data
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                return data["items"]
        except (URLError, HTTPError, TimeoutError, OSError, ValueError) as e:
            last_err = e
            continue
    raise RuntimeError(f"KAP erisilemedi: {last_err}")


def refresh(force: bool = False) -> dict:
    """Cache'i tazeler; donus: {"ok": bool, "item_count": int, "error": str}"""
    global _fetch_error_logged
    with _LOCK:
        if not force and _CACHE["items"] is not None and time.time() - _CACHE["ts"] < CACHE_TTL:
            return {"ok": _CACHE["ok"], "item_count": len(_CACHE["items"] or []),
                    "error": _CACHE["error"]}
        try:
            items = _fetch_recent_disclosures()
            _CACHE["items"] = items
            _CACHE["ts"] = time.time()
            _CACHE["ok"] = True
            _CACHE["error"] = ""
        except Exception as e:
            # Erisim yoksa filtre devre disi: sinyaller engellenmez.
            if not _fetch_error_logged:
                logger.warning("[KAP] Bulten servisi erisilemiyor, filtre pasif: %s", e)
                _fetch_error_logged = True
            if _CACHE["items"] is None:
                _CACHE["items"] = []
            _CACHE["ts"] = time.time()
            _CACHE["ok"] = False
            _CACHE["error"] = str(e)
        return {"ok": _CACHE["ok"], "item_count": len(_CACHE["items"] or []),
                "error": _CACHE["error"]}


def _symbol_codes(symbol: str) -> set:
    """DCTTR.IS -> {"DCTTR", "DCTTR.IS"} gibi arama kodlari uretir."""
    s = str(symbol).upper().strip()
    base = s.split(".")[0]
    return {base, s}


def check_symbol(symbol: str) -> dict:
    """Hissenin son 24 saatteki KAP durumunu doner.
    {"blocked": bool, "reason": str, "count": int, "kap_ok": bool}"""
    st = refresh()
    res = {"blocked": False, "reason": "", "count": 0, "kap_ok": st["ok"]}
    if not st["ok"]:
        return res
    now = datetime.now()
    codes = _symbol_codes(symbol)
    hits = []
    for item in (_CACHE["items"] or []):
        text = _extract_text(item).upper()
        if not any(c in text for c in codes):
            continue
        d = _parse_date(item)
        if d and (now - d) > timedelta(hours=LOOKBACK_HOURS):
            continue
        hits.append((item, text, d))
    res["count"] = len(hits)
    if not hits:
        return res
    blocked = []
    for item, text, d in hits:
        if any(kw.upper() in text for kw in _MATERIAL_KEYWORDS):
            title = str(item.get("title") or item.get("bulletinTitle") or "Önemli olay açıklaması")[:120]
            when = d.strftime("%d.%m %H:%M") if d else "yakın zamanda"
            blocked.append(f"{title} ({when})")
    if blocked:
        res["blocked"] = True
        res["reason"] = "KAP duyurusu: " + " | ".join(blocked[:2])
    return res
