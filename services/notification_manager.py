import os
import requests
from datetime import datetime
from database.db_manager import DBManager
from config.settings import TELEGRAM_BOT_TOKEN as DEFAULT_TOKEN, TELEGRAM_CHAT_ID as DEFAULT_CHAT_ID
from utils.logger import logger

class NotificationManager:
    """
    VarantRadar Pro V7 - Profesyonel Bildirim ve Sinyal Merkezi
    Telegram Bot API üzerinden kullanıcılara anlık fiyatlı tavan, 1 saatlik ve 5 dakikalık sinyalleri iletir.
    """
    def __init__(self):
        self.db = DBManager()
        self._load_settings()

    def _load_settings(self):
        """Ayarları veritabanından, ortam değişkenlerinden veya varsayılanlardan yükler."""
        try:
            token = self.db.get_setting('telegram_token')
            chat_id = self.db.get_setting('telegram_chat_id')
            
            # Geçersiz veya placeholder ise fallback yap
            if not token or "BURAYA_" in str(token):
                token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN") or DEFAULT_TOKEN
                if token and "BURAYA_" not in str(token):
                    self.db.save_setting('telegram_token', token)
                    
            if not chat_id or "BURAYA_" in str(chat_id):
                chat_id = os.environ.get("TELEGRAM_CHAT_ID") or DEFAULT_CHAT_ID
                if chat_id and "BURAYA_" not in str(chat_id):
                    self.db.save_setting('telegram_chat_id', chat_id)
                    
            self.telegram_token = str(token).strip() if token else None
            self.telegram_chat_id = str(chat_id).strip() if chat_id else None
        except Exception as e:
            logger.error(f"Telegram ayarları yüklenirken hata: {e}")
            self.telegram_token = DEFAULT_TOKEN
            self.telegram_chat_id = DEFAULT_CHAT_ID

    def send_telegram_message(self, message: str) -> bool:
        """Belirtilen Chat ID'ye veya virgülle ayrılmış ID'lere Telegram mesajı gönderir."""
        if not self.telegram_token or not self.telegram_chat_id or "BURAYA_" in str(self.telegram_token):
            self._load_settings()
            
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram ayarları eksik. Bildirim gönderilemedi.")
            return False
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        chat_ids = [cid.strip() for cid in str(self.telegram_chat_id).split(',') if cid.strip()]
        all_success = True
        
        for chat_id in chat_ids:
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code == 200:
                    self._log_alert(message, "TELEGRAM", f"SUCCESS_{chat_id}")
                    logger.info(f"Telegram bildirimi başarıyla iletildi (Chat ID: {chat_id})")
                else:
                    logger.error(f"Telegram API Hatası ({chat_id}): {response.text}")
                    self._log_alert(message, "TELEGRAM", f"FAILED_{chat_id}")
                    all_success = False
            except Exception as e:
                logger.error(f"Telegram gönderim istisnası ({chat_id}): {e}")
                self._log_alert(message, "TELEGRAM", f"ERROR_{chat_id}")
                all_success = False
                
        return all_success

    def send_system_startup_alert(self) -> bool:
        """Sunucu başladığında Telegram bağlantısının çalıştığını bildiren ilk mesaj."""
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        msg = (
            f"🚀 <b>VARANTRADAR PRO AKTİF!</b> 🚀\n\n"
            f"🤖 <b>Sistem:</b> Canlı Tarama & Algoritmik Sinyal Motoru Devrede\n"
            f"📊 <b>Kapsam:</b> BIST Evreni, 1 Saatlik Fırsatlar, Tavan Radarı ve 5D RSI\n"
            f"⏱ <b>Başlangıç:</b> {now_str}\n\n"
            f"✨ <i>Piyasa fırsatları ve tavan alarmları anlık olarak iletilecektir.</i>"
        )
        return self.send_telegram_message(msg)

    def send_tavan_alert(self, symbol: str, score: int, reason: str, position: dict = None, extra: dict = None) -> bool:
        """Yüksek Tavan Olasılığı tespit edildiğinde profesyonel detaylı şablonla tetiklenir."""
        extra = extra or {}
        clean_sym = symbol.replace(".IS", "").upper()
        
        # Fiyat Bilgisi
        raw_price = extra.get("Price") or extra.get("Close") or (position.get("Entry") if position else None)
        price_str = f"{float(raw_price):.2f}" if raw_price is not None else "-"
        
        # Yüzde Değişim
        chg_val = extra.get("Daily_Change_Pct") or extra.get("Change_Pct")
        if chg_val is not None:
            try:
                chg_num = float(chg_val)
                chg_sign = "+" if chg_num > 0 else ""
                chg_str = f"({chg_sign}%{chg_num:.2f})"
            except:
                chg_str = f"(%{chg_val})"
        else:
            chg_str = ""

        # Tavan ve Mesafe
        tavan_price = extra.get("Ceiling_Price", position.get("TP2", "-") if position else "-")
        if isinstance(tavan_price, (int, float)):
            tavan_price_str = f"₺{float(tavan_price):.2f}"
        else:
            tavan_price_str = f"₺{tavan_price}" if tavan_price != "-" else "-"
            
        dist = extra.get("Distance_To_Ceiling_Pct", "-")
        dist_str = f"+%{float(dist):.1f}" if isinstance(dist, (int, float)) else f"%{dist}"
        
        vol_m = extra.get("Vol_Multiplier", "-")
        vol_str = f"{float(vol_m):.1f}x" if isinstance(vol_m, (int, float)) else f"{vol_m}x"
        
        phase = extra.get("Phase_Badge", "TAVAN RADARI")
        candle_st = extra.get("Candle_Strength", "")
        trap = extra.get("Trap_Risk", False)
        v_rev = extra.get("V_Reversal", False)
        v_pow = extra.get("V_Power", 0.0)
        eta = extra.get("ETA", position.get("Projection", "-") if position else "-")
        domino_sec = extra.get("Domino_Sector")
        domino_peers = extra.get("Domino_Peers", [])
        warrant = extra.get("Warrant_Match")
        streak = extra.get("Streak_Potential")
        breakdown = extra.get("Breakdown_Warning")
        
        msg = f"🚀 <b>[{phase}] DAĞ KEKLİĞİ TAVAN RADARI</b> 🚀\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{price_str} {chg_str}\n"
        msg += f"🎯 <b>Tavan Hedefi:</b> {tavan_price_str} (Kalan: {dist_str})\n"
        msg += f"⭐ <b>AI Tavan Skoru:</b> {score}/100\n"
        msg += f"🔥 <b>Hacim Gücü:</b> {vol_str} Katlama\n"
        msg += f"⏱ <b>Tahmini Tavan Saati (ETA):</b> {eta}\n"
        
        if streak:
            msg += f"🔗 <b>Tavan Zinciri:</b> {streak}\n"
            
        if v_rev:
            msg += f"⚡ <b>V-Dönüş Gücü:</b> Dipten +%{v_pow} Hızlı Sıçrama!\n"
            
        if candle_st:
            msg += f"🕯 <b>Mum Durumu:</b> {candle_st}\n"
            
        if trap:
            msg += f"⚠️ <b>UYARI:</b> Üst fitil uzun (Satış Baskısı / Tuzak Riski!)\n"
            
        if breakdown:
            msg += f"\n🚨 <b>ACİL UYARI:</b> {breakdown}\n"
            
        if domino_sec and domino_peers:
            peer_txt = ", ".join([f"#{p}" for p in domino_peers[:3]])
            msg += f"\n♟️ <b>Domino Etkisi ({domino_sec}):</b> Peşinden gelebilecek kardeşler: {peer_txt}\n"
            
        if warrant:
            msg += f"\n🎯 <b>VARANT ROKETİ EŞLEŞMESİ:</b>\n"
            msg += f"   • Dayanak: #{clean_sym} ➡️ Varant Grubu: <b>{warrant.get('Name')} ({warrant.get('Leverage')})</b>\n"
            msg += f"   • Potansiyel Getiri: <b>+%{warrant.get('Potential_Gain_Pct')}%</b>\n"
            
        if position:
            sl_val = position.get('SL', '-')
            tp1_val = position.get('TP1', '-')
            msg += f"\n🛡 <b>İz Süren Stop (SL):</b> ₺{sl_val}\n"
            msg += f"🎯 <b>İlk Kâr Al (TP1):</b> ₺{tp1_val}\n"
            msg += f"⚖️ <b>Risk/Kazanç (R:R):</b> 1:{position.get('RR', '-')}\n"
            
        if reason:
            msg += f"\n💡 <b>Teknik Gerekçe:</b> {reason}\n"
            
        msg += f"\n🤖 <i>VarantRadar Pro Otomasyon Sistemi</i>"
        return self.send_telegram_message(msg)

    def send_1h_opportunity_alert(self, opp: dict) -> bool:
        """1 Saatlik Güçlü Teknik Fırsat tespit edildiğinde tetiklenir."""
        clean_sym = opp.get("Symbol", "").replace(".IS", "").upper()
        raw_price = opp.get("Price")
        price_str = f"{float(raw_price):.2f}" if raw_price is not None else "-"
        
        chg_val = opp.get("Daily_Change_Pct") or opp.get("Change_Pct")
        if chg_val is not None:
            try:
                chg_num = float(chg_val)
                chg_sign = "+" if chg_num > 0 else ""
                chg_str = f"({chg_sign}%{chg_num:.2f})"
            except:
                chg_str = f"(%{chg_val})"
        else:
            chg_str = ""
            
        score_5 = opp.get("Score_5", 0)
        bars_ago = opp.get("Crossover_Bars_Ago", "?")
        ema_gap = opp.get("EMA_Gap_Pct", "-")
        rsi_val = opp.get("RSI_Val", "-")
        adx_val = opp.get("ADX_Val", "-")
        
        indicators = []
        if opp.get("EMA_Crossover_Bullish"):
            indicators.append(f"🔀 EMA 20/50 Kesişimi ({bars_ago} bar önce, Fark: %{ema_gap})")
        if opp.get("MACD_Match"):
            indicators.append("📈 MACD Pozitif AL Sinyali")
        if opp.get("RSI_Match"):
            indicators.append(f"📊 RSI > 50 Güçlü Bölge (RSI: {rsi_val})")
        if opp.get("ADX_Match"):
            indicators.append(f"💪 ADX Trend Gücü Yüksek (ADX: {adx_val})")
        if opp.get("MOM_Match"):
            indicators.append("⚡ Pozitif İvme / Momentum Artışı")

        msg = f"🔥 <b>1 SAATLİK TEKNİK FIRSAT</b> 🔥\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{price_str} {chg_str}\n"
        msg += f"⭐ <b>Teknik Filtre Skoru:</b> {score_5} / 5\n\n"
        msg += f"📋 <b>Tetiklenen İndikatörler:</b>\n"
        for ind in indicators:
            msg += f"  • {ind}\n"
            
        msg += f"\n🤖 <i>VarantRadar Pro 1 Saatlik Tarama</i>"
        return self.send_telegram_message(msg)

    def send_5m_rsi_alert(self, symbol: str, signal: str, rsi: float, price: float) -> bool:
        """5 Dakikalık Kısa Vade RSI Kesişimi."""
        clean_sym = symbol.replace(".IS", "").upper()
        icon = "🟢" if signal == "AL" else "🔴"
        action_text = "GÜÇLÜ AL (Dipten Dönüş)" if signal == "AL" else "GÜÇLÜ SAT (Tepeden Çıkış)"
        price_str = f"{float(price):.2f}" if price else "-"
        rsi_str = f"{float(rsi):.1f}" if rsi else "-"
        
        msg = f"⚡ <b>5 Dk KISA VADE SCALP SİNYALİ</b> ⚡\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        msg += f"{icon} <b>Sinyal:</b> {action_text}\n"
        msg += f"💰 <b>Anlık Fiyat:</b> ₺{price_str}\n"
        msg += f"📈 <b>RSI (5m):</b> {rsi_str}\n\n"
        msg += f"⏱ <b>Zaman Dilimi:</b> 5 Dakikalık İntraday\n"
        msg += f"🤖 <i>VarantRadar Pro Hızlı Sinyal Motoru</i>"
        return self.send_telegram_message(msg)

    def send_radar_alert(self, symbol: str, score: int, level: str, reason: str, price: float = None, change_pct: float = None) -> bool:
        """Radar yeni bir fırsat bulduğunda tetiklenir."""
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"🚨 <b>YENİ RADAR FIRSATI</b> 🚨\n\n"
        msg += f"📌 <b>Hisse:</b> #{clean_sym}\n"
        if price is not None:
            chg_str = f" (%+{change_pct:.2f})" if change_pct and change_pct > 0 else (f" (%{change_pct:.2f})" if change_pct else "")
            msg += f"💰 <b>Anlık Fiyat:</b> ₺{price:.2f}{chg_str}\n"
        msg += f"⭐ <b>Puan:</b> {score}/100\n"
        msg += f"📊 <b>Seviye:</b> {level}\n"
        msg += f"💡 <b>Neden:</b> {reason}\n\n"
        msg += f"🤖 <i>VarantRadar Pro Otomasyon Sistemi</i>"
        return self.send_telegram_message(msg)

    def send_portfolio_alert(self, symbol: str, pnl_pct: float, action: str, price: float = None) -> bool:
        """Stop veya Take Profit seviyesine gelindiğinde tetiklenir."""
        icon = "🟢" if pnl_pct > 0 else "🔴"
        clean_sym = symbol.replace(".IS", "").upper()
        msg = f"{icon} <b>PORTFÖY ALARMI</b> {icon}\n\n"
        msg += f"📌 <b>İşlem:</b> {action} #{clean_sym}\n"
        if price is not None:
            msg += f"💵 <b>Fiyat:</b> ₺{price:.2f}\n"
        msg += f"💰 <b>Kâr/Zarar:</b> %{round(pnl_pct, 2)}\n\n"
        msg += f"🤖 <i>Lütfen sistemden kontrol ediniz.</i>"
        return self.send_telegram_message(msg)

    def _log_alert(self, message: str, channel: str, status: str):
        """Gönderilen alarmları veritabanına kaydeder."""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO system_logs (level, message, created_at) 
                              VALUES (?, ?, ?)''',
                           (f"ALERT_{channel}_{status}", message[:120] + "...", datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Alert loglama hatası: {e}")

    def update_settings(self, token: str, chat_id: str):
        """Telegram ayarlarını günceller."""
        try:
            token = str(token).strip() if token else ""
            chat_id = str(chat_id).strip() if chat_id else ""
            self.db.save_setting('telegram_token', token)
            self.db.save_setting('telegram_chat_id', chat_id)
            self.telegram_token = token
            self.telegram_chat_id = chat_id
            return True
        except Exception as e:
            logger.error(f"Ayarlar güncellenemedi: {e}")
            return False
