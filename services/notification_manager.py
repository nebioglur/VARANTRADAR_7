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
        """Ayarları veritabanından, ortam değişkenlerinden veya telegram_bot modülünden yükler."""
        try:
            from services.telegram_bot import get_telegram_credentials
            token, chat_id = get_telegram_credentials(force=True)
            if token and chat_id:
                self.telegram_token = str(token).strip()
                self.telegram_chat_id = str(chat_id).strip()
                try:
                    self.db.save_setting('telegram_token', self.telegram_token)
                    self.db.save_setting('telegram_chat_id', self.telegram_chat_id)
                except Exception:
                    pass
                return

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
        """Belirtilen Chat ID'ye veya kanala Telegram mesajı gönderir (telegram_bot ile senkron)."""
        from services.telegram_bot import send_telegram_message as _tb_send
        return _tb_send(message)

    def send_system_startup_alert(self) -> bool:
        """Sunucu başladığında Telegram bağlantısının çalıştığını bildiren ilk mesaj. KULLANICI İSTEĞİ: İptal edildi."""
        return True

    def send_tavan_alert(self, symbol: str, score: int, reason: str, position: dict = None, extra: dict = None) -> bool:
        """Yüksek Tavan Olasılığı tespit edildiğinde profesyonel detaylı şablonla tetiklenir."""
        extra = extra or {}
        phase = str(extra.get("Phase_Badge", "TAVAN RADARI"))
        if score < 75:
            return True  # Kalite filtresi: Puanı yüksek güçlü adaylar gitsin
        
        clean_sym = symbol.replace(".IS", "").upper()
        
        # Fiyat Bilgisi
        raw_price = extra.get("Price") or extra.get("Close") or (position.get("Entry") if position else None)
        price_val = float(raw_price) if raw_price is not None else 0.0
        price_str = f"{price_val:.2f}" if price_val > 0 else "-"
        
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

        # Dağ Kekliği / Erken Kopuş veya Klasik Tavan başlığı
        if "Erken" in phase or "DAĞ" in phase.upper() or "KEK" in phase.upper():
            badge_title = "🚀 <b>[ERKEN KOPUŞ] DAĞ KEKLİĞİ TAVAN RADARI</b> 🚀"
        else:
            badge_title = f"🚀 <b>[{phase}] VIP TAVAN RADARI</b> 🚀"
        
        msg = f"{badge_title}\n\n"
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

        # Destek ve Direnç Seviyeleri (Saatlik ve Günlük)
        try:
            high_val = float(extra.get("High") or (price_val * 1.02 if price_val else 0))
            low_val = float(extra.get("Low") or (price_val * 0.98 if price_val else 0))
            if price_val and price_val > 0:
                p_val = (high_val + low_val + price_val) / 3.0
                d_r1 = (2 * p_val) - low_val
                d_s1 = (2 * p_val) - high_val
                if price_val > d_r1: d_r1 = p_val + (high_val - low_val)
                if price_val < d_s1: d_s1 = p_val - (high_val - low_val)
                h_r1 = price_val + (d_r1 - price_val) * 0.4
                h_s1 = price_val - (price_val - d_s1) * 0.4
                if d_r1 <= price_val: d_r1 = price_val * 1.025
                if d_s1 >= price_val: d_s1 = price_val * 0.975
                if h_r1 <= price_val: h_r1 = price_val * 1.012
                if h_s1 >= price_val: h_s1 = price_val * 0.988
                msg += f"\n🛡️ <b>Destek:</b> ₺{h_s1:.2f} <i>(Saatlik)</i> | ₺{d_s1:.2f} <i>(Günlük)</i>\n"
                msg += f"🎯 <b>Direnç:</b> ₺{h_r1:.2f} <i>(Saatlik)</i> | ₺{d_r1:.2f} <i>(Günlük)</i>\n"
        except Exception:
            pass
            
        if reason:
            msg += f"\n💡 <b>Teknik Gerekçe:</b> {reason}\n"
            
        msg += f"\n🤖 <i>VarantRadar Pro Otomasyon Sistemi</i>"
        return self.send_telegram_message(msg)

    def send_1h_opportunity_alert(self, opp: dict) -> bool:
        """1 Saatlik grafikte fırsat tespit edildiğinde atılacak mesaj."""
        return True # Kullanıcı isteği: Devre dışı bırakıldı
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
        """5 Dakikalık grafikte aşırı alım/satım veya RSI uyumsuzluğu tespit edildiğinde."""
        return True # Kullanıcı isteği: Devre dışı bırakıldı
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
        """Genel Radar uyarıları (düşük skorlular için vs. yedek amaçlı)."""
        if score < 100:
            return True # Kullanıcı isteği: Yalnızca VIP mesajlar

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
