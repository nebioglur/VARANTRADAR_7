import requests
import json
import logging
from typing import Optional

# Telegram Bot Token ve Chat ID
BOT_TOKEN = "8841122189:AAG4dMDnOS1hv9V_CD2mWCtsuz3Xf0x38tw"
CHAT_ID = "6105241519"

logger = logging.getLogger(__name__)

def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """
    Belirlenen Chat ID'ye Telegram üzerinden mesaj gönderir.
    """
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": parse_mode
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get("ok"):
            logger.info(f"Telegram mesajı başarıyla gönderildi: {text[:50]}...")
            return True
        else:
            logger.error(f"Telegram mesajı gönderilemedi! Hata: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Telegram API çağrısı sırasında hata oluştu: {str(e)}")
        return False

def send_vip_signal(stock_data: dict) -> bool:
    """
    100 AL puanına sahip elit hisseler için VIP sinyal mesajı oluşturur ve gönderir.
    """
    symbol = stock_data.get("Symbol", "Bilinmiyor")
    price = stock_data.get("Price", 0)
    score = stock_data.get("Score", 0)
    alpha = stock_data.get("Alpha_Str", "Nötr")
    cmf = stock_data.get("Smart_Money", "Nötr")
    squeeze = stock_data.get("Short_Squeeze", "Yok")
    domino = stock_data.get("Domino_Str", "Yok")
    
    text = f"🚨 <b>VIP SİNYAL TESPİT EDİLDİ</b> 🚨\n\n"
    text += f"💎 <b>Hisse:</b> #{symbol}\n"
    text += f"🔥 <b>AL Puanı:</b> {score}/100 (Kusursuz)\n"
    text += f"💵 <b>Anlık Fiyat:</b> ₺{price}\n\n"
    
    text += f"📊 <b>AR-GE Laboratuvar Verileri:</b>\n"
    text += f"🐺 <b>Alpha:</b> {alpha}\n"
    text += f"💸 <b>Para Akışı:</b> {cmf}\n"
    text += f"🧨 <b>Şort Durumu:</b> {squeeze}\n"
    text += f"♟️ <b>Domino:</b> {domino}\n\n"
    text += f"<i>Not: Bu hisse tüm teknik filtreleri geçerek 100 tam puan almıştır!</i>"
    
    return send_telegram_message(text)

def send_batch_vip_signals(vip_list: list) -> bool:
    """
    Birden fazla VIP hisseyi tek bir mesajda gönderir. En iyiden kötüye sıralar ve numaralandırır.
    """
    if not vip_list:
        return False
        
    def is_super_green(d):
        alpha = d.get("Alpha_Str", "")
        sm = d.get("Smart_Money", "")
        sqz = d.get("Short_Squeeze", "")
        return (
            "Pozitif" in alpha and 
            ("Giriş" in sm or "Akümülasyon" in sm) and 
            ("Yükseliyor" in sqz or "Patlatma" in sqz)
        )

    # Sıralama: Önce Super Green olanlar, sonra Puan 100 olduğu için Vol_Multiplier ve Hacim gibi değerlere göre
    sorted_vips = sorted(
        vip_list,
        key=lambda x: (-1 if is_super_green(x) else 0, -x.get("Vol_Multiplier", 0), x.get("Distance_To_Ceiling_Pct", 99))
    )
    
    text = f"🚨 <b>YENİ VIP SİNYALLERİ TESPİT EDİLDİ!</b> 🚨\n\n"
    text += f"🏆 <b>GÜNÜN EN İYİ VIP HİSSELERİ (100 Puan)</b> 🏆\n\n"
    
    for idx, data in enumerate(sorted_vips, 1):
        symbol = data.get("Symbol", "Bilinmiyor")
        price = data.get("Price", 0)
        alpha = data.get("Alpha_Str", "Nötr")
        cmf = data.get("Smart_Money", "Nötr")
        squeeze = data.get("Short_Squeeze", "Yok")
        domino = data.get("Domino_Str", "Yok")
        
        is_sg = is_super_green(data)
        
        # İlk 5 hisseye özel görünüm veya Süper Kesişim
        if is_sg:
            text += f"🟢🚀 <b>{idx}. #{symbol} [SÜPER KESİŞİM]</b> (₺{price})\n"
            text += f"   🐺 Alpha: <b>{alpha}</b> | 💸 Para Akışı: <b>{cmf}</b>\n"
            text += f"   🧨 Şort: <b>{squeeze}</b> | ♟️ Domino: {domino}\n\n"
        elif idx <= 5:
            medals = {1: "🥇", 2: "🥈", 3: "🥉", 4: "🎖️", 5: "🏅"}
            medal = medals.get(idx, "💎")
            text += f"{medal} <b>{idx}. #{symbol}</b> (₺{price})\n"
            text += f"   🐺 Alpha: {alpha} | 💸 Para Akışı: {cmf}\n"
            text += f"   🧨 Şort: {squeeze} | ♟️ Domino: {domino}\n\n"
        else:
            # 6 ve sonrası daha sade bir görünüm
            text += f"🔹 <b>{idx}. #{symbol}</b> (₺{price})\n"
            
    text += f"\n<i>Not: Bu hisseler tüm teknik filtreleri geçerek AR-GE sisteminden 100 tam puan almıştır!</i>"
    
    return send_telegram_message(text)

def send_simulation_report(total_trades: int, total_profit: float, return_pct: float) -> bool:
    """
    Gün sonu simülasyon raporunu gönderir.
    """
    text = f"🧪 <b>Simülasyon Gün Sonu Raporu</b> 🧪\n\n"
    
    if total_profit > 0:
        text += f"✅ <b>Günün Kârı:</b> +{total_profit:,.2f} TL\n"
        text += f"📈 <b>Getiri Oranı:</b> +%{return_pct:.2f}\n"
    else:
        text += f"❌ <b>Günün Zararı:</b> {total_profit:,.2f} TL\n"
        text += f"📉 <b>Getiri Oranı:</b> %{return_pct:.2f}\n"
        
    text += f"🛒 <b>Toplam İşlem:</b> {total_trades} adet al-sat\n\n"
    text += f"<i>Sistem yarın için tekrar taranmaya hazır.</i>"
    
    return send_telegram_message(text)
