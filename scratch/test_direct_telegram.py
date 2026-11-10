import requests

token = "8841122189:AAG4dMDnOS1hv9V_CD2mWCtsuz3Xf0x38tw"
chat_id = "-1004489296054"

url = f"https://api.telegram.org/bot{token}/sendMessage"

# Test 1: Simple message
resp1 = requests.post(url, json={
    "chat_id": chat_id,
    "text": "Test from Antigravity bot check",
    "parse_mode": "HTML"
}, timeout=10)
print("Test 1 status:", resp1.status_code, resp1.text)

# Test 2: The exact test message from api_telegram_test
resp2 = requests.post(url, json={
    "chat_id": chat_id,
    "text": "✅ <b>VarantRadar Pro</b> — Telegram baglanti testi basarili!\n🤖 Simulasyon AL/SAT bildirimleri bu kanala gelecek.",
    "parse_mode": "HTML"
}, timeout=10)
print("Test 2 status:", resp2.status_code, resp2.text)

# Test 3: The morning compass message
from datetime import datetime
today_date = datetime.now().strftime("%d.%m.%Y")
text3 = "🧭 <b>GÜNÜN PİYASA PUSULASI & SEANS STRATEJİSİ</b> 🧭\n"
text3 += f"📅 <i>{today_date} | Seans Öncesi Taktik Bülteni</i>\n\n"
text3 += "📊 <b>Piyasa Genel Durumu:</b>\n"
text3 += "• <b>BIST 100:</b> Seans açılışındaki ilk 15 dakika (10:00 - 10:15) volatiliteye karşı temkinli izleme önerilir.\n"
text3 += "• <b>Odak Sektörler:</b> Hacim toplanması Savunma, Havacılık ve Enerji kümelerinde yoğunlaşıyor.\n\n"
text3 += "🏆 <b>BUGÜNÜN 4 ALTIN KAZANÇ KURALI:</b>\n"
text3 += "1️⃣ <b>10:15 - 11:30 Dağ Kekliği Avı:</b> Hacmi katlamış ama primi +%1.5 ile +%4 arasında kalmış erken kopuş adaylarına odaklanın.\n"
text3 += "2️⃣ <b>Destek Altı Stop:</b> Bildirimdeki 'Saatlik Destek' seviyesinin altına mutlaka zarar kes stopu koyun.\n"
text3 += "3️⃣ <b>+%3.5 Kârda %50 Satış:</b> İlk hedefe ulaşıldığında pozisyonun yarısını satın, kalan için stopu maliyet seviyenize çekin. (Sıfır Risk Prensibi)\n"
text3 += "4️⃣ <b>Tuzaklara Düşmeyin:</b> %6 üzeri aşırı koşmuş veya üst fitili uzamış hisselere tepeden FOMO ile girmeyin.\n\n"
text3 += "💡 <i>Özel Sıralama (Aksiyon Planlı) ve Dağ Kekliği sinyalleri 10:15'ten itibaren anlık olarak kanala iletilecektir. Bol kazançlar dileriz!</i> 🚀"

resp3 = requests.post(url, json={
    "chat_id": chat_id,
    "text": text3,
    "parse_mode": "HTML"
}, timeout=10)
print("Test 3 status:", resp3.status_code, resp3.text)
