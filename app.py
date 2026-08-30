import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import requests
import sqlite3

from config.bist_symbols import BIST30_SYMBOLS
from database.db_manager import DBManager
db = DBManager()

# Initialize system
st.set_page_config(page_title="VARANTRADAR PRO Workspace", layout="wide", page_icon="🏦")

# --- API İstemcisi (Client) ---
# Flask sunucusunun adresi
# Ortam değişkeninden üretim API adresini oku, eğer yoksa yerel adresi kullan.
# Bu sayede kod hem yerelde hem de bulutta değişiklik yapmadan çalışabilir.
API_BASE_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")
st.sidebar.caption(f"API Sunucusu: {API_BASE_URL}")

@st.cache_data(ttl=60) # Verileri 60 saniye önbellekte tut
def get_dashboard_data():
    """Flask API'sinden ana tarama verilerini çeker."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/dashboard_init")
        response.raise_for_status() # Hata durumunda exception fırlat
        data = response.json()
        if data.get("status") == "success" and data.get("dashboard_data"):
            # Gelen JSON verisini DataFrame'e çevir
            df = pd.DataFrame(data["dashboard_data"].get("opportunities", []))
            # Veri güncelleme saatini kaydet
            st.session_state['last_updated'] = data.get("last_updated", "Bilinmiyor")
            st.session_state['total_analyzed'] = data.get("total_analyzed", 0)
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"API Sunucusuna Bağlanılamadı: {e}")
        return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=300) # AI Raporunu 5 dakika cache'le
def get_ai_report_from_api(symbol):
    """Seçilen hisse için AI analizini API'den çeker."""
    try:
        # API endpoint'i .IS olmadan sembol bekliyorsa
        api_symbol = symbol.replace(".IS", "")
        response = requests.get(f"{API_BASE_URL}/api/analyze?symbol={api_symbol}")
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            return data.get("report")
    except requests.exceptions.RequestException as e:
        st.error(f"AI Raporu alınamadı: {e}")
    return None

@st.cache_data(ttl=3600) # Ayarları 1 saat cache'le
def get_settings_from_api():
    """Mevcut ayarları API'den çeker."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/settings")
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            return data
    except requests.exceptions.RequestException as e:
        st.error(f"Ayarlar alınamadı: {e}")
    return {}

def save_settings_to_api(telegram_token, telegram_chat_id, gemini_key):
    """Ayarları API'ye göndererek kaydeder."""
    try:
        payload = {
            "telegram_token": telegram_token,
            "telegram_chat_id": telegram_chat_id,
            "gemini_api_key": gemini_key
        }
        response = requests.post(f"{API_BASE_URL}/api/settings", json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            st.success("Ayarlar başarıyla kaydedildi!")
            st.cache_data.clear() # Ayarlar değiştiği için cache'i temizle
    except requests.exceptions.RequestException as e:
        st.error(f"Ayarlar kaydedilemedi: {e}")

"""
# --- ESKİ YAPI (Direkt Servisleri Çağırma) ---
# Bu bloklar artık kullanılmayacak, yerini API çağrıları aldı.
@st.cache_resource
def get_core():
    core = AntigravityCore()
    core.initialize_system()
    return core

@st.cache_resource
def get_matcher():
    return WarrantMatcher()

@st.cache_resource
def get_scanner():
    return ScannerService()

core = get_core()
matcher = get_matcher()
scanner = get_scanner()
"""

# --- SIDEBAR (AYARLAR VE TARAMA) ---
st.sidebar.title("⚙️ Radar Kontrol Merkezi")
st.sidebar.info("Tarama artık sunucu tarafında otonom olarak çalışıyor. Arayüz her zaman en güncel veriyi gösterir.")
if st.sidebar.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

# Veri güncelleme saati göster
last_upd = st.session_state.get('last_updated', 'Bilinmiyor')
st.sidebar.caption(f"📅 Son Güncelleme: {last_upd}")

# Telegram / Gemini Ayarları (Eski App'ten Kalan)
with st.sidebar.expander("🤖 Otomasyon & Kurumsal Ayarlar", expanded=False):
    # Bu kısım da idealde API üzerinden yönetilmelidir. Şimdilik bırakıyorum.
    # API'den mevcut ayarları çek
    current_settings = get_settings_from_api()

    t_token = st.text_input("Telegram Bot Token", value=current_settings.get("telegram_token", ""), type="password")
    t_chat = st.text_input("Telegram Chat ID", value=current_settings.get("telegram_chat_id", ""))
    g_token = st.text_input("Gemini API Key", value=current_settings.get("gemini_api_key", ""), type="password")
    
    if st.button("💾 Kaydet"):
        save_settings_to_api(t_token, t_chat, g_token)


# --- ANA EKRAN (INSTITUTIONAL WORKSPACE) ---
st.markdown("<h1 style='text-align: center; border-bottom: 2px solid #ddd; padding-bottom: 10px;'>🏦 INSTITUTIONAL TRADING WORKSPACE 🏦</h1>", unsafe_allow_html=True)

# Tarama sonuçlarını getir
df_results = get_dashboard_data()

if df_results.empty:
    st.warning("API sunucusundan veri alınamadı veya sunucu çalışmıyor. Lütfen `server.py` dosyasını başlattığınızdan emin olun.")
    st.stop()

# Radar Hit Rate (İsabet Oranı) Hesaplama
from engines.history_engine import HistoryEngine
history_engine = HistoryEngine()
hit_rate = history_engine.get_signal_hit_rate()

# 18 SEKME (TABS) OLUŞTUR
(tab_market, tab_scanner, tab_chart, tab_watchlist, tab_portfolio, tab_ai, tab_research,
 tab_smart_money, tab_ai_intel, tab_collaboration, tab_auto_radar,
 tab_finos, tab_automation, tab_digital_twin,
 tab_market_intel, tab_sentiment_alerts, tab_ecosystem, tab_stats) = st.tabs([
    "🌍 Market Overview", 
    "🔍 Asset Scanner", 
    "📈 Chart Center", 
    "⭐ Watchlist Manager", 
    "💼 Portfolio Intelligence",
    "🤖 AI Command Center",
    "🧪 Quant Research Lab",
    "🐋 Smart Money",
    "🧠 AI Intelligence",
    "🤝 AI Collaboration",
    "🛸 Auto Radar",
    "⚙️ FinOS Kernel",
    "⚡ Automation",
    "🕰️ Digital Twin",
    "🏢 Market Intel",
    "📰 Sentiment & Alerts",
    "👑 Investment Office",
    "📊 Win Rate & Stats"
])

# ---------------------------------------------------------
# TAB 1: MARKET OVERVIEW (TRADER KOKPİTİ)
# ---------------------------------------------------------
with tab_market:
    st.markdown("### 🛩️ Kurumsal Trader Kokpiti")
    
    # 1. PİYASA NABZI & ENDEKS
    import yfinance as yf
    try:
        xu = yf.download("XU100.IS", period="5d", interval="1d", progress=False)
        close_col = 'Close' if 'Close' in xu.columns else 'close'
        xu_close = float(xu[close_col].iloc[-1])
        xu_prev = float(xu[close_col].iloc[-2])
        xu_change = ((xu_close - xu_prev) / xu_prev) * 100
        
        shield_color = "🔴 KAPALI" if xu_change <= -1.5 else "🟢 AÇIK"
        shield_text = "Riskli Piyasa (Alım Durduruldu)" if xu_change <= -1.5 else "Güvenli (Taramalar Aktif)"
    except:
        xu_close, xu_change, shield_color, shield_text = 0, 0, "⚠️ BİLİNMİYOR", "Veri Çekilemedi"
        
    # 2. GÜNLÜK PNL & SİMÜLASYON DURUMU
    import sqlite3
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_pnl = 0.0
    open_positions = 0
    win_count = 0
    loss_count = 0
    
    try:
        conn = sqlite3.connect('database/bist_data.db')
        c = conn.cursor()
        c.execute("SELECT pnl_val FROM trades WHERE date_str = ?", (today_str,))
        trades = c.fetchall()
        for t in trades:
            if t[0] is not None:
                total_pnl += float(t[0])
                if float(t[0]) > 0:
                    win_count += 1
                else:
                    loss_count += 1
        
        c.execute("SELECT COUNT(*) FROM trades WHERE date_str = ? AND status = 'OPEN'", (today_str,))
        row = c.fetchone()
        if row:
            open_positions = row[0]
        conn.close()
    except Exception as e:
        pass
        
    # AI Yorumu
    ai_comment = "BIST100'de stabil görünüm devam ediyor. Seçici alımlar ve MTF ivme fırsatları değerlendirilebilir."
    if xu_change <= -1.5:
        ai_comment = "⚠️ Endekste sert satış baskısı var. Robot alım motorları (Şalter) uyku moduna alındı. Nakitte kalın."
    elif xu_change > 1.5:
        ai_comment = "🚀 Endeks çok güçlü. Tavan adaylarında hedefler daha esnek tutulabilir. Boğa piyasası aktif."
    elif total_pnl > 0 and xu_change > 0:
        ai_comment = f"Endeks pozitif ayrışıyor. Bugün simülasyonda başarılı işlemler kilitlendi. Güçlü adaylar takipte."
        
    st.info(f"**🤖 AI Kurumsal Özet:** {ai_comment}")
    
    st.markdown("#### 1️⃣ Piyasa Sağlığı & Güvenlik Kalkanı")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BIST100 (XU100)", f"{xu_close:,.2f}", f"{xu_change:.2f}%")
    c2.metric("Robot Şalter Durumu", shield_color, shield_text, delta_color="off")
    c3.metric("Potansiyel Fırsatlar", f"{len(df_results[df_results['final_score'] >= 75]) if not df_results.empty else 0}")
    c4.metric("Radar Hit Rate", f"%{hit_rate}")
    
    st.markdown("#### 2️⃣ Simülasyon Cüzdanı (Günün Özeti)")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Günlük Realize Kâr/Zarar", f"{total_pnl:,.2f} ₺", f"{win_count} Kazanç / {loss_count} Kayıp")
    sc2.metric("Açık Pozisyonlar", f"{open_positions} İşlem", "Takip ediliyor", delta_color="off")
    
    if not df_results.empty:
        sc3.metric("En Güçlü Varlık", f"{df_results.iloc[0]['symbol']}")
        sc4.metric("Max Kalite Skoru", f"%{int(df_results.iloc[0]['final_score'])}")
    
    st.markdown("#### BIST30 Asset Quality Heatmap")
    if not df_results.empty:
        try:
            import plotly.express as px
            fig = px.treemap(
                df_results, 
                path=[px.Constant("BIST30 Market"), 'symbol'], 
                values='final_score',
                color='final_score', 
                hover_data=['decision', 'confidence'], 
                color_continuous_scale='RdYlGn',
                title='Asset Quality Score Dağılımı'
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.warning("⚠️ Plotly kütüphanesi yüklü değil.")

# ---------------------------------------------------------
# TAB 2: ASSET SCANNER
# ---------------------------------------------------------
with tab_scanner:
    st.markdown("### 🚀 TOP 10 ASSET OPPORTUNITIES")
    # Son güncelleme saatini göster
    st.caption(f"📅 Son Veri Güncellemesi: {st.session_state.get('last_updated', 'Bilinmiyor')}")
    
    # EMA sütunları varsa ekle
    base_cols = ['symbol', 'decision', 'final_score', 'confidence', 'risk_level', 'eta']
    col_names = ['Varlık', 'Karar', 'Skor', 'Güven', 'Risk', 'Hedef Süre']
    
    # EMA 50 ve EMA 200 sütunlarını kontrol et ve ekle
    for ema_col, ema_name in [('Daily_EMA50', 'EMA 50'), ('Daily_EMA200', 'EMA 200'), ('EMA_50', 'EMA 50'), ('EMA_200', 'EMA 200')]:
        if ema_col in df_results.columns and ema_col not in base_cols:
            base_cols.append(ema_col)
            col_names.append(ema_name)
    
    available_cols = [c for c in base_cols if c in df_results.columns]
    available_names = [col_names[base_cols.index(c)] for c in available_cols]
    
    top_10 = df_results.head(10)[available_cols]
    top_10.columns = available_names
    st.dataframe(top_10, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🤖 ASSET EXPLORER & AI ADVISOR")
    selected_stock = st.selectbox("Detaylı AI Kurumsal Raporu için Varlık Seçin:", df_results['symbol'].tolist())

    if selected_stock:
        with st.spinner("AI Raporu Hazırlanıyor..."):
            # ESKİ YAPI:
            # df_stock = core.analyzer.calculate_indicators(selected_stock, "1d")
            # YENİ YAPI (API'den çek):
            ai_report = get_ai_report_from_api(selected_stock)
            
            if ai_report:
                # API'den gelen raporun yapısına göre alanları doldur
                reasons = ai_report.get("executive_summary", {}).get("positive_points", [])
                risks = ai_report.get("executive_summary", {}).get("negative_points", [])
                scenarios = ai_report.get("trade_plan", {})
                
                t1, t2 = st.columns(2)
                with t1:
                    st.info(f"**Neden {selected_stock}?**\n\n" + "\n".join([f"- {r}" for r in reasons]))
                with t2:
                    st.warning(f"**Riskler ve Karşıt Görüşler:**\n\n" + "\n".join([f"- {r}" for r in risks]))
                
                st.markdown("#### Trading Plan & Asset Valuation")
                s1, s2, s3 = st.columns(3)
                scenarios = ai_report.get('Scenarios', ai_report.get('trade_plan', {}))
                s1.success(f"**Hedef / Fair Value:**\n{scenarios.get('En_Iyi', scenarios.get('best_case', 'Veri Yok'))}")
                s2.info(f"**Beklenen Senaryo:**\n{scenarios.get('Normal', scenarios.get('base_case', 'Veri Yok'))}")
                s3.error(f"**Stop Risk:**\n{scenarios.get('Kotu_Stop', scenarios.get('worst_case', 'Veri Yok'))}")
                
                st.markdown("#### Asset History & AI Insights")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Güven Aralığı (95%)", ai_report.get('Confidence_Interval', 'Belirsiz'))
                hist_sim = ai_report.get('Historical_Similarity', {})
                m2.metric("Tarihsel Eşleşme", hist_sim.get('Similar_Date', 'Yok'))
                m3.metric("Benzer Dönem Sonucu", hist_sim.get('Outcome', 'Belirsiz'))
                m4.metric("Multi-Timeframe Uyumu", f"+{ai_report.get('Scores', {}).get('Multi_Timeframe', 0)} Puan")
                
                st.markdown("#### Risk Center & Asset Quality Score")
                p1, p2, p3 = st.columns(3)
                risk = ai_report.get('Risk_Metrics', {})
                p1.metric("Volatilite (Risk)", f"%{risk.get('Volatility', 0)}")
                p2.metric("Maksimum Düşüş (Drawdown)", f"%{risk.get('Drawdown', 0)}")
                p3.metric("Beta (Tahmini)", risk.get('Beta', 1.0))
                
                r1, r2, r3 = st.columns(3)
                r1.metric("Risk / Getiri Oranı", ai_report.get('Risk_Reward', 'Belirsiz'))
                r2.metric("Tahmini Süre (ETA)", ai_report.get('ETA', 'Belirsiz'))
                r3.metric("Asset Quality Score", ai_report.get('Total_Score', 0))

# ---------------------------------------------------------
# TAB 3: CHART CENTER
# ---------------------------------------------------------
with tab_chart:
    st.markdown("### 📈 Live Chart Center")
    chart_symbol = st.selectbox("Grafik Çizilecek Varlığı Seçin:", df_results['symbol'].tolist())
    if st.button("Canlı Grafiği Yükle"):
        with st.spinner("Grafik Motoru Yükleniyor..."):
            try:
                # API tabanlı grafik verisi çek
                api_sym = chart_symbol.replace(".IS", "")
                chart_resp = requests.get(f"{API_BASE_URL}/api/chart_data?symbol={api_sym}&interval=1d")
                chart_resp.raise_for_status()
                chart_data = chart_resp.json()
                
                if chart_data.get("status") != "error" and chart_data.get("candles"):
                    df_chart = pd.DataFrame(chart_data["candles"])
                    
                    import plotly.graph_objects as go
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_chart['date'] if 'date' in df_chart.columns else df_chart.index,
                        open=df_chart['open'],
                        high=df_chart['high'],
                        low=df_chart['low'],
                        close=df_chart['close'],
                        name='Fiyat'
                    )])
                    # EMA Çizgileri Ekle
                    close = df_chart['close'].astype(float)
                    x_axis = df_chart['date'] if 'date' in df_chart.columns else df_chart.index
                    
                    ema20 = close.ewm(span=20, adjust=False).mean()
                    ema50 = close.ewm(span=50, adjust=False).mean()
                    ema200 = close.ewm(span=200, adjust=False).mean()
                    
                    fig.add_trace(go.Scatter(x=x_axis, y=ema20, mode='lines', name='EMA(20)', line=dict(color='orange', width=1)))
                    fig.add_trace(go.Scatter(x=x_axis, y=ema50, mode='lines', name='EMA(50)', line=dict(color='blue', width=1.5)))
                    fig.add_trace(go.Scatter(x=x_axis, y=ema200, mode='lines', name='EMA(200)', line=dict(color='red', width=2)))
                        
                    fig.update_layout(title=f"{chart_symbol} Kurumsal Mum Grafiği", xaxis_title='Tarih', yaxis_title='Fiyat ₺', height=600)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Grafik verisi alınamadı.")
            except requests.exceptions.RequestException as e:
                st.error(f"API Bağlantı Hatası: {e}")
            except ImportError:
                st.error("⚠️ Plotly kütüphanesi eksik.")

# ---------------------------------------------------------
# TAB 4: WATCHLIST MANAGER
# ---------------------------------------------------------
with tab_watchlist:
    st.markdown("### ⭐ Akıllı İzleme Listesi (Watchlist)")
    w_col1, w_col2 = st.columns([1, 2])
    
    with w_col1:
        new_fav = st.selectbox("Favorilere Varlık Ekle:", BIST30_SYMBOLS)
        if st.button("Listeye Ekle (Pin)"):
            conn = db.get_connection()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO watchlist (symbol, added_at, notes) VALUES (?, datetime('now'), '')", (new_fav,))
                conn.commit()
                st.success(f"{new_fav} Watchlist'e sabitlendi!")
            except sqlite3.IntegrityError:
                st.warning(f"{new_fav} zaten izleme listesinde!")
            finally:
                conn.close()
                
    with w_col2:
        conn = db.get_connection()
        df_watch = pd.read_sql_query("SELECT symbol as Varlık, added_at as 'Eklenme Tarihi' FROM watchlist", conn)
        conn.close()
        
        if not df_watch.empty:
            st.dataframe(df_watch, hide_index=True, use_container_width=True)
            if st.button("Listeyi Temizle"):
                conn = db.get_connection()
                conn.cursor().execute("DELETE FROM watchlist")
                conn.commit()
                conn.close()
                st.rerun()
        else:
            st.info("Watchlist henüz boş. Hisseleri buraya ekleyerek takip edebilirsiniz.")

# ---------------------------------------------------------
# TAB 5: AI COMMAND CENTER
# ---------------------------------------------------------
with tab_ai:
    st.markdown("### 🧠 AI Command Center (Copilot)")
    st.caption("Piyasa, portföy ve strateji hakkında sorular sorun.")
    
    messages = st.container(height=350)
    messages.chat_message("ai").write("Merhaba, ben VarantRadar AI Danışmanı. Hangi varlık hakkında analiz veya strateji üretmemi istersiniz?")
    
    prompt = st.chat_input("Komut girin (Örn: ASELSAN için risk durumu nedir?)")
    if prompt:
        messages.chat_message("user").write(prompt)
        # Basit kural tabanlı mock AI Command Center
        prompt_lower = prompt.lower()
        if "varant" in prompt_lower:
            messages.chat_message("ai").write("Varant eşleştirmeleri için **Asset Scanner** sekmesindeki 'En İyi Fırsatlar' listesini inceleyebilirsiniz. Yüksek kaldıraç, beraberinde yüksek 'Delta' riski taşır.")
        elif "durum" in prompt_lower or "bist" in prompt_lower:
            messages.chat_message("ai").write(f"Sistem şu an {len(df_results)} adet aktif BIST varlığını taradı. Detaylı Treemap analizi için **Market Overview** sekmesine bakınız.")
        elif "risk" in prompt_lower:
            messages.chat_message("ai").write("Varlık bazlı riskler (Volatilite, Drawdown, Beta) **Asset Scanner** altındaki **Risk Center** panelinde dinamik olarak hesaplanmaktadır.")
        else:
            messages.chat_message("ai").write("Bu soruyu derinlemesine analiz edebilmem için Gemini API entegrasyonumun (Sol menüden) aktif olması gereklidir. Ancak genel analizler için Scanner'ı kullanabilirsiniz.")
# ---------------------------------------------------------
# TAB 6: QUANT RESEARCH LAB
# ---------------------------------------------------------
with tab_research:
    st.markdown("### 🧪 Quant Research Laboratory")
    st.caption("Gelişmiş backtest, strateji optimizasyonu ve Monte Carlo simülasyonları (CFG-05)")
    
    col_strat1, col_strat2 = st.columns(2)
    with col_strat1:
        selected_strategy = st.selectbox("Strateji Seçiniz", ["EMA_Crossover", "RSI_Reversal", "MACD_Trend"])
        test_symbol = st.text_input("Test Edilecek Sembol", value="ASELS.IS")
    
    with col_strat2:
        st.write("Optimizasyon Hedefi")
        target_metric = st.selectbox("Metrik", ["Sharpe_Ratio", "CAGR", "Max_Drawdown"])
        run_backtest_btn = st.button("🧪 Backtest ve Optimize Et", use_container_width=True)
        
    if run_backtest_btn:
        with st.spinner("Stratejiler test ediliyor ve Monte Carlo simülasyonları çalıştırılıyor..."):
            from engines.market_data_engine import MarketDataEngine
            from engines.strategy_engine import StrategyEngine
            from engines.optimization_engine import OptimizationEngine
            from engines.monte_carlo_engine import MonteCarloEngine
            
            md_engine = MarketDataEngine()
            df_test = md_engine.fetch_data(test_symbol, period="2y", interval="1d")
            
            if not df_test.empty:
                strategies = StrategyEngine.get_available_strategies()
                strat_func = strategies.get(selected_strategy)
                
                # Basit bir Grid
                if selected_strategy == "EMA_Crossover":
                    grid = {"fast_period": [10, 20], "slow_period": [50, 100]}
                elif selected_strategy == "RSI_Reversal":
                    grid = {"period": [14], "overbought": [70, 80], "oversold": [30, 20]}
                else:
                    grid = {"fast": [12], "slow": [26], "signal": [9]}
                    
                opt_result = OptimizationEngine.run_grid_search(df_test, strat_func, grid, target_metric=target_metric)
                best_perf = opt_result.get("Best_Metrics", {})
                
                if best_perf:
                    st.success("Optimizasyon Tamamlandı!")
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("En İyi Parametreler", str(opt_result["Best_Parameters"]))
                    m2.metric("CAGR", f"%{best_perf.get('CAGR', 0)}")
                    m3.metric("Sharpe Ratio", best_perf.get('Sharpe_Ratio', 0))
                    m4.metric("Max Drawdown", f"%{best_perf.get('Max_Drawdown', 0)}")
                    
                    st.markdown("#### 📊 Monte Carlo Simülasyonu (Gelecek 1 Yıl / 1000 Senaryo)")
                    # Monte carlo sim için en iyi parametrelere göre sinyal bulmalıyız
                    best_signals = strat_func(df_test, **opt_result["Best_Parameters"])
                    from engines.backtest_engine import BacktestEngine
                    bt = BacktestEngine()
                    bt_df = bt.run_backtest(df_test, best_signals)
                    mc_res = MonteCarloEngine.run_simulation(bt_df)
                    
                    if "error" not in mc_res:
                        sm1, sm2, sm3, sm4 = st.columns(4)
                        sm1.metric("Ortalama Beklenen Sermaye", f"{mc_res['Mean_Final_Capital']} TL")
                        sm2.metric("Kazanma Olasılığı", f"%{mc_res['Probability_of_Profit']}")
                        sm3.metric("En Kötü Senaryo (%99 VaR)", f"{mc_res['Worst_Case_1_Percent']} TL")
                        sm4.metric("En İyi Senaryo", f"{mc_res['Best_Case_1_Percent']} TL")
                        st.info("Laboratuvar aktif olarak geçmişi analiz etti ve 1000 olası geleceği simüle etti.")
                    else:
                        st.warning(mc_res["error"])
            else:
                st.error("Veri çekilemedi.")


# ---------------------------------------------------------
# TAB 5 (PORTFOLIO): PORTFOLIO INTELLIGENCE
# ---------------------------------------------------------
with tab_portfolio:
    st.markdown("### 💼 Portfolio Intelligence Center")
    st.caption("Çoklu Portföy Yönetimi, Efficient Frontier, Risk/Getiri Optimizasyonu (CFG-06)")
    
    port_col1, port_col2 = st.columns([1, 2])
    
    with port_col1:
        st.write("#### 💰 Portföy Özeti")
        from engines.portfolio_engine import PortfolioEngine
        port_engine = PortfolioEngine()
        summary = port_engine.get_portfolio_summary()
        st.metric("Toplam Sermaye", f"{summary.get('total_capital', 100000)} TL")
        st.metric("Kullanılabilir Nakit", f"{summary.get('available_balance', 100000)} TL")
        
        st.markdown("--- ")
        st.write("#### 📐 Position Sizing")
        capital_input = st.number_input("İşlem Sermayesi", value=10000)
        price_input = st.number_input("Giriş Fiyatı", value=50.0)
        stop_input = st.number_input("Stop Loss", value=48.0)
        
        from engines.position_sizing_engine import PositionSizingEngine
        if st.button("Risk Bazlı Lot Hesapla"):
            size_res = PositionSizingEngine.fixed_risk_sizing(capital_input, price_input, stop_input)
            if "error" not in size_res:
                st.success(f"Önerilen Alım: {size_res['quantity']} Lot ({size_res['investment']} TL)")
            else:
                st.error(size_res["error"])
                
    with port_col2:
        st.write("#### 🌐 Markowitz Efficient Frontier Optimizasyonu")
        st.caption("Seçili hisseler için maksimum Sharpe oranını veren optimal portföy ağırlıkları.")
        
        optimize_symbols = st.multiselect("Portföye Eklenecek Hisseler", ["ASELS.IS", "THYAO.IS", "TUPRS.IS", "GARAN.IS", "EREGL.IS", "BIMAS.IS"], default=["ASELS.IS", "THYAO.IS", "TUPRS.IS"])
        opt_capital = st.number_input("Dağıtılacak Sermaye (TL)", value=100000.0)
        
        if st.button("🤖 Portföyü Optimize Et"):
            if len(optimize_symbols) < 2:
                st.warning("Optimizasyon için en az 2 hisse seçmelisiniz.")
            else:
                with st.spinner("Efficient Frontier hesaplanıyor..."):
                    from engines.market_data_engine import MarketDataEngine
                    md = MarketDataEngine()
                    price_dict = {}
                    for sym in optimize_symbols:
                        df_s = md.fetch_data(sym, period="1y", interval="1d")
                        if not df_s.empty:
                            price_dict[sym] = df_s['close']
                    
                    if len(price_dict) >= 2:
                        import pandas as pd
                        price_df = pd.DataFrame(price_dict)
                        price_df.dropna(inplace=True)
                        
                        from engines.portfolio_optimization_engine import PortfolioOptimizationEngine
                        opt_res = PortfolioOptimizationEngine.optimize_max_sharpe(price_df, current_capital=opt_capital)
                        
                        if "error" not in opt_res:
                            st.success("Optimizasyon Başarılı!")
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Beklenen Yıllık Getiri", f"%{opt_res['expected_annual_return']}")
                            m2.metric("Yıllık Volatilite (Risk)", f"%{opt_res['annual_volatility']}")
                            m3.metric("Sharpe Oranı", opt_res['sharpe_ratio'])
                            
                            st.write("**Optimal Ağırlıklar (Target Weights):**")
                            st.json(opt_res["weights"])
                            
                            st.write("**Önerilen Lot Dağılımı (Discrete Allocation):**")
                            st.json(opt_res["allocation"])
                            st.info(f"Artan Nakit (Leftover Cash): {opt_res['leftover_cash']:.2f} TL")
                        else:
                            st.error(opt_res["error"])
                    else:
                        st.error("Yeterli geçmiş veri bulunamadı.")

    
        st.markdown("--- ")
        st.write("#### 🧠 Faktör Yatırımı (Smart Beta)")
        st.caption("Value, Momentum, Quality, Low Volatility faktör skorlarını inceleyin.")
        
        factor_symbols = st.multiselect("Faktör Analizi İçin Hisseler", ["ASELS.IS", "THYAO.IS", "TUPRS.IS", "GARAN.IS", "EREGL.IS"], default=["ASELS.IS", "THYAO.IS"])
        if st.button("📊 Faktörleri Hesapla"):
            with st.spinner("Faktör Motoru Çalışıyor..."):
                from engines.market_data_engine import MarketDataEngine
                from engines.factor_engine import FactorEngine
                md = MarketDataEngine()
                price_dict = {}
                for sym in factor_symbols:
                    df_s = md.fetch_data(sym, period="1y", interval="1d")
                    if not df_s.empty:
                        price_dict[sym] = df_s
                
                if price_dict:
                    factor_df = FactorEngine.calculate_multi_asset_factors(price_dict)
                    if not factor_df.empty:
                        st.dataframe(factor_df, use_container_width=True)
                    else:
                        st.error("Hesaplama yapılamadı.")
                else:
                    st.error("Veri çekilemedi.")

        st.markdown("--- ")
        st.write("#### 🔗 Korelasyon & Risk Dağılımı")
        st.caption("Portföydeki gizli riskleri (yüksek korelasyon) ve gerçek risk kaynaklarını (MCR) analiz edin.")
        
        corr_symbols = st.multiselect("Korelasyon & Risk Analizi İçin Hisseler", ["ASELS.IS", "THYAO.IS", "TUPRS.IS", "GARAN.IS", "EREGL.IS", "BIMAS.IS"], default=["ASELS.IS", "THYAO.IS", "TUPRS.IS"], key="corr_syms")
        
        if st.button("🔍 Korelasyon & Risk Matrisini Çıkar"):
            if len(corr_symbols) < 2:
                st.warning("Analiz için en az 2 hisse seçmelisiniz.")
            else:
                with st.spinner("Risk Matrisleri Hesaplanıyor..."):
                    from engines.market_data_engine import MarketDataEngine
                    from engines.correlation_engine import CorrelationEngine
                    from engines.attribution_engine import AttributionEngine
                    
                    md = MarketDataEngine()
                    price_dict = {}
                    for sym in corr_symbols:
                        df_s = md.fetch_data(sym, period="1y", interval="1d")
                        if not df_s.empty:
                            price_dict[sym] = df_s['close']
                    
                    if len(price_dict) >= 2:
                        import pandas as pd
                        price_df = pd.DataFrame(price_dict).dropna()
                        
                        # Korelasyon Matrisi
                        corr_matrix = CorrelationEngine.calculate_correlation_matrix(price_df)
                        st.write("**Korelasyon Matrisi (Pearson):**")
                        st.dataframe(corr_matrix.style.background_gradient(cmap='coolwarm', axis=None), use_container_width=True)
                        
                        # Uyarılar
                        alerts = CorrelationEngine.get_correlation_alerts(corr_matrix, threshold=0.80)
                        if alerts:
                            st.warning("⚠️ **Yüksek Korelasyon Uyarısı (Gizli Risk)**")
                            for alert in alerts:
                                st.write(f"- {alert['asset1']} ve {alert['asset2']} arasında %{alert['correlation']*100} korelasyon var. İkisi aynı anda düşebilir!")
                        
                        # Risk Dağılımı (MCR) - Eşit Ağırlıklı Varsayım
                        st.write("**Risk Dağılımı (Marginal Contribution to Risk - Eşit Ağırlık)**")
                        equal_weights = {sym: 1.0/len(corr_symbols) for sym in corr_symbols}
                        cov_matrix = price_df.pct_change().dropna().cov() * 252 # Yıllıklaştırılmış
                        
                        risk_contrib = AttributionEngine.calculate_risk_contribution(equal_weights, cov_matrix)
                        if risk_contrib:
                            rc_df = pd.DataFrame(risk_contrib).T
                            st.dataframe(rc_df, use_container_width=True)
                            
                            # Çeşitlendirme Skoru
                            div_score = CorrelationEngine.calculate_diversification_score(equal_weights, cov_matrix)
                            st.info(f"💡 Portföy Çeşitlendirme Skoru (PDR): {div_score} (Skor ne kadar yüksekse o kadar iyi)")
                        
                    else:
                        st.error("Yeterli veri bulunamadı.")

        st.markdown("--- ")
        st.write("#### 💧 Likidite & Gizli Maliyet Analizi")
        st.caption("Piyasa yapıcının göremediği gizli maliyetleri (Kayma, Komisyon, Süre) hesaplayın.")
        
        liq_col1, liq_col2 = st.columns(2)
        with liq_col1:
            liq_symbol = st.text_input("Likidite Test Hissesi", value="THYAO.IS")
            liq_pos_size = st.number_input("Kapatılacak Pozisyon (TL)", value=500000.0)
            
            if st.button("⏱️ Satış Süresini (Exit Time) Hesapla"):
                with st.spinner("Tahta Hacmi Analiz Ediliyor..."):
                    from engines.market_data_engine import MarketDataEngine
                    from engines.liquidity_engine import LiquidityEngine
                    md = MarketDataEngine()
                    df_liq = md.fetch_data(liq_symbol, period="3mo", interval="1d")
                    
                    if not df_liq.empty:
                        res = LiquidityEngine.calculate_liquidation_metrics(df_liq, liq_pos_size)
                        if "error" not in res:
                            st.metric("Tahmini Çıkış Süresi (Gün)", res["Days_to_Liquidate"])
                            st.metric("Beklenen Fiyat Kayması (Slippage)", f"%{res['Estimated_Slippage_Pct']}")
                            st.metric("Kayma Zararı", f"-{res['Estimated_Slippage_Cost']} TL")
                            st.info(f"Likidite Skoru: {res['Liquidity_Score']} ({res['Warning']})")
                        else:
                            st.error(res["error"])
                            
        with liq_col2:
            st.write("**Net Hedef Hesaplayıcı (Komisyon Dahil)**")
            cost_entry = st.number_input("Hisse Giriş Fiyatı", value=100.0)
            cost_target_pct = st.number_input("Net Kâr Hedefi (%)", value=10.0) / 100
            cost_comm_rate = st.number_input("Kurum Komisyonu (Örn: Binde 1 -> 0.001)", value=0.001, format="%.4f")
            
            if st.button("🎯 Gerçek Satış Fiyatını Bul"):
                from engines.cost_engine import CostEngine
                real_target = CostEngine.target_price_with_costs(cost_entry, cost_target_pct, cost_comm_rate)
                st.success(f"Net %{cost_target_pct*100} kâr için satmanız gereken fiyat: **{real_target} TL**")
                st.caption(f"(Sadece komisyonu değil, alış ve satış çift yönlü maliyeti kapatır)")

        st.markdown("--- ")
        st.write("#### 🤖 AI Yatırım Koçu (Explainable AI)")
        st.caption("Kurumsal algoritmalar tarafından hesaplanan Portföy Sağlık Skoru ve Karar Güven Endeksi (AI Confidence).")
        
        if st.button("🧠 AI Koçu'nu Çalıştır"):
            with st.spinner("Tüm veriler (Volatilite, Korelasyon, Faktörler) analiz ediliyor..."):
                from engines.ai_coach_engine import AICoachEngine
                
                # Dinamik değerler (mevcut state'den veya hesaplanan)
                div_score = st.session_state.get('diversification_score', 1.0)
                ann_vol = st.session_state.get('annual_volatility', 25.0)
                exp_ret = st.session_state.get('expected_return', 30.0)
                high_corr = st.session_state.get('high_corr_count', 0)
                liq_warn = st.session_state.get('liquidity_warnings', 0)
                
                health_report = AICoachEngine.evaluate_portfolio_health(
                    diversification_score=div_score,
                    annual_volatility=ann_vol,
                    expected_return=exp_ret,
                    high_corr_count=high_corr,
                    liquidity_warnings=liq_warn
                )
                
                st.session_state['portfolio_health_score'] = health_report['Portfolio_Health_Score']
                st.session_state['ai_confidence_score'] = health_report['AI_Confidence_Score']
                st.session_state['ai_reasons'] = health_report['Explainable_AI_Reasons']
                
                st.write(f"**Portföy Genel Durumu:** {health_report['Summary_Verdict']}")
                
                hc_col1, hc_col2 = st.columns(2)
                with hc_col1:
                    st.metric("Portföy Sağlık Skoru", f"{health_report['Portfolio_Health_Score']} / 100")
                with hc_col2:
                    st.metric("AI Güven Endeksi (Confidence)", f"%{health_report['AI_Confidence_Score']}")
                    
                st.write("**AI Açıklamaları (Explainable AI):**")
                for reason in health_report['Explainable_AI_Reasons']:
                    st.info(f"💡 {reason}")

        st.markdown("--- ")
        st.write("#### 📑 Kurumsal Raporlama (Executive Report)")
        st.caption("AI Koçunun analizlerini ve Portföy verilerini PDF formatında yazdırılabilir HTML veya Excel olarak indirin.")
        
        rep_col1, rep_col2 = st.columns(2)
        
        # Rapor için dinamik data (session state'den)
        report_portfolio_data = {
            "health_score": st.session_state.get('portfolio_health_score', 0),
            "confidence": st.session_state.get('ai_confidence_score', 0),
            "diversification": st.session_state.get('diversification_score', 0)
        }
        report_ai_reasons = st.session_state.get('ai_reasons', [
            "Henüz AI Koçu çalıştırılmadı. Lütfen önce 'AI Koçu'nu Çalıştır' butonuna tıklayın."
        ])
        
        import pandas as pd
        mock_factor_data = pd.DataFrame({"Sembol": ["ASELS.IS"], "Momentum": [80], "Quality": [90]})
        mock_corr_data = pd.DataFrame()
        
        from utils.reporting_engine import ReportingEngine
        
        with rep_col1:
            try:
                excel_bytes = ReportingEngine.generate_excel_report(report_portfolio_data, mock_factor_data, mock_corr_data)
                st.download_button(
                    label="📊 Excel Raporu İndir",
                    data=excel_bytes,
                    file_name="Portfoy_Analiz_Raporu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Excel oluşturulamadı: {e}")
                
        with rep_col2:
            try:
                html_str = ReportingEngine.generate_html_report(report_portfolio_data, report_ai_reasons)
                st.download_button(
                    label="📄 HTML/PDF Raporu İndir",
                    data=html_str,
                    file_name="Executive_Summary_Report.html",
                    mime="text/html"
                )
                st.caption("Not: İndirdiğiniz HTML dosyasını tarayıcınızda açıp (Ctrl+P) ile PDF olarak kaydedebilirsiniz.")
            except Exception as e:
                st.error(f"HTML oluşturulamadı: {e}")

    # NEW TAB: Smart Money & Institutional Flow
    with tab_smart_money:
        st.header("🐋 Smart Money & Hacim Akışı")
        st.write("Kurumsal yatırımcı ayak izlerini, para giriş/çıkışlarını ve hacim patlamalarını OHLCV üzerinden analiz edin.")
        
        sm_sym = st.text_input("Analiz Edilecek Hisse (Smart Money)", value="THYAO.IS")
        
        if st.button("🔍 Hacim ve Para Akışını Analiz Et"):
            with st.spinner("Smart Money motorları çalışıyor..."):
                from engines.market_data_engine import MarketDataEngine
                from engines.smart_money_engine import SmartMoneyEngine
                from engines.volume_analytics_engine import VolumeAnalyticsEngine
                
                md = MarketDataEngine()
                df_sm = md.fetch_data(sm_sym, period="1y", interval="1d")
                
                if not df_sm.empty:
                    sm_res = SmartMoneyEngine.analyze_smart_money(df_sm)
                    vol_res = VolumeAnalyticsEngine.analyze_volume(df_sm)
                    
                    if "error" not in sm_res and "error" not in vol_res:
                        st.subheader(f"{sm_sym} - Akıllı Para Özeti")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        # 1. Smart Money Skoru
                        with col1:
                            st.metric("Smart Money Skoru", f"{sm_res['Smart_Money_Score']}/100")
                            if sm_res['Smart_Money_Score'] >= 70:
                                st.success(f"DURUM: {sm_res['Verdict']}")
                            elif sm_res['Smart_Money_Score'] <= 30:
                                st.error(f"DURUM: {sm_res['Verdict']}")
                            else:
                                st.warning(f"DURUM: {sm_res['Verdict']}")
                                
                        # 2. Hacim Analizi (VWAP & RV)
                        with col2:
                            st.metric("Göreceli Hacim (RV)", vol_res['Relative_Volume'])
                            if vol_res['Relative_Volume'] > 1.5:
                                st.error(f"HACİM DURUMU: {vol_res['Volume_Status']}")
                            else:
                                st.info(f"HACİM DURUMU: {vol_res['Volume_Status']}")
                                
                        # 3. CMF & MFI & OBV
                        with col3:
                            st.metric("MFI (Para Akışı Endeksi)", sm_res['MFI_Value'], sm_res['MFI_Status'])
                            st.metric("Chaikin Money Flow (CMF)", sm_res['CMF_Value'], sm_res['CMF_Status'])
                            
                        st.markdown("---")
                        st.write("### 📊 VWAP ve Trend Durumu")
                        st.metric("Güncel Fiyat vs VWAP", f"{df_sm['close'].iloc[-1]} / {vol_res['VWAP_Price']}", f"{vol_res['VWAP_Distance_Pct']}%")
                        if vol_res['VWAP_Distance_Pct'] > 0:
                            st.success(f"{vol_res['VWAP_Status']} - Kurumsal ortalamanın üzerinde.")
                        else:
                            st.error(f"{vol_res['VWAP_Status']} - Kurumsal ortalamanın altında (Baskı var).")

                        st.markdown("---")
                        st.write("### 🩸 Kurumsal Tuzaklar & Emir Akışı (Order Flow)")
                        
                        from engines.order_flow_engine import OrderFlowEngine
                        of_res = OrderFlowEngine.analyze_order_flow(df_sm)
                        
                        if "error" not in of_res:
                            of_col1, of_col2 = st.columns(2)
                            
                            with of_col1:
                                st.metric("Sentetik Alıcı/Satıcı Baskısı (0-100)", f"{of_res['Order_Imbalance_Score']}")
                                if of_res['Order_Imbalance_Score'] > 65:
                                    st.success(f"BASKI: {of_res['Order_Imbalance_Status']}")
                                elif of_res['Order_Imbalance_Score'] < 35:
                                    st.error(f"BASKI: {of_res['Order_Imbalance_Status']}")
                                else:
                                    st.warning(f"BASKI: {of_res['Order_Imbalance_Status']}")
                                    
                            with of_col2:
                                st.write("**Son Likidite Avları (Stop Patlatma / Tuzak):**")
                                if not of_res['Recent_Traps']:
                                    st.info("Son 20 barda belirgin bir likidite avı (tuzak) tespit edilmedi.")
                                else:
                                    for trap in of_res['Recent_Traps']:
                                        if "BULLISH" in trap['Type']:
                                            st.success(f"🟢 {trap['Date']}: {trap['Type']} @ {trap['Price_Level']}")
                                        else:
                                            st.error(f"🔴 {trap['Date']}: {trap['Type']} @ {trap['Price_Level']}")

                        st.markdown("---")
                        st.write("### 🔄 Sektör Rotasyonu & Para Akışı (Capital Flow)")
                        st.caption("Akıllı para hangi sektörden çıkıyor, hangi sektöre giriyor?")
                        
                        rot_symbols = st.multiselect(
                            "Karşılaştırılacak Sektörler/Hisseler", 
                            ["XILTM.IS", "XBANK.IS", "XUSIN.IS", "XTICJ.IS"], 
                            default=["XILTM.IS", "XBANK.IS", "XUSIN.IS"],
                            key="rot_syms"
                        )
                        benchmark_sym = st.text_input("Benchmark Endeks", value="XU100.IS")
                        
                        if st.button("🔄 Rotasyon Haritasını Çıkar"):
                            with st.spinner("Sektörel Para Akışı Hesaplanıyor..."):
                                from engines.rotation_engine import RotationEngine
                                
                                df_bench = md.fetch_data(benchmark_sym, period="1y", interval="1d")
                                if not df_bench.empty:
                                    sector_dict = {}
                                    for sym in rot_symbols:
                                        df_s = md.fetch_data(sym, period="1y", interval="1d")
                                        if not df_s.empty:
                                            sector_dict[sym] = df_s
                                            
                                    if sector_dict:
                                        rot_df = RotationEngine.analyze_rotation(sector_dict, df_bench)
                                        if not rot_df.empty:
                                            st.dataframe(rot_df, use_container_width=True)
                                            st.info("💡 **LEADING:** Paranın girdiği, endeksi yenen liderler. **LAGGING:** Paranın çıktığı zayıflar.")
                                        else:
                                            st.error("Rotasyon hesabı yapılamadı.")
                                else:
                                    st.error("Benchmark verisi çekilemedi.")

                        st.markdown("---")
                        st.write("### 🧠 AI Smart Money & Wyckoff Döngüsü")
                        st.caption("Yapay zeka desteğiyle hissenin hangi Wyckoff evresinde (Toplama/Dağıtım) olduğunu ve Pump & Dump riskini görün.")
                        
                        if st.button("🤖 AI Manipülasyon Analizi Başlat"):
                            with st.spinner("AI Wyckoff ve Manipülasyon Risk Motoru çalışıyor..."):
                                from engines.smart_ai_engine import SmartAI_Engine
                                
                                ai_insight = SmartAI_Engine.generate_ai_insight(df_sm)
                                
                                w_col1, w_col2 = st.columns(2)
                                
                                with w_col1:
                                    st.write("**Wyckoff Piyasa Döngüsü (Faz):**")
                                    phase = ai_insight["Wyckoff_Phase"]
                                    if "ACCUMULATION" in phase or "MARKUP" in phase:
                                        st.success(f"📈 {phase}")
                                    elif "DISTRIBUTION" in phase or "MARKDOWN" in phase:
                                        st.error(f"📉 {phase}")
                                    else:
                                        st.info(f"➖ {phase}")
                                        
                                    st.caption("*Not: Kurumsallar Accumulation evresinde toplar, Distribution evresinde küçük yatırımcıya satarlar.*")
                                    
                                with w_col2:
                                    mani = ai_insight["Manipulation_Analysis"]
                                    st.metric("Pump & Dump / Manipülasyon Riski", f"{mani['Risk_Score']}/100", mani['Risk_Level'])
                                    
                                    if mani['Risk_Score'] > 0:
                                        for r in mani['Reasons']:
                                            st.warning(f"⚠️ {r}")
                                    else:
                                        st.success("✅ Temiz. Olağandışı bir fiyat/hacim manipülasyonu tespit edilmedi.")


                            
                    else:
                        st.error("Hesaplama için yeterli veri bulunamadı.")
                else:
                    st.error("Veri çekilemedi.")

    # NEW TAB: AI Intelligence Center
    with tab_ai_intel:
        st.header("🧠 AI Intelligence Center")
        st.write("Sadece sinyal üretmez; kararını açıklar, tartışır ve güven skorunu (Confidence Score) hesaplar.")
        
        ai_sym = st.text_input("Analiz Edilecek Hisse (AI Karar Merkezi)", value="ASELS.IS")
        
        if st.button("🤖 AI Karar & Güven Motorunu Çalıştır"):
            with st.spinner("AI Karar Matrisi Hesaplanıyor..."):
                from engines.market_data_engine import MarketDataEngine
                from engines.technical_engine import TechnicalEngine
                from engines.smart_money_engine import SmartMoneyEngine
                from engines.volume_analytics_engine import VolumeAnalyticsEngine
                from engines.ai_decision_engine import AIDecisionEngine
                
                md = MarketDataEngine()
                df_ai = md.fetch_data(ai_sym, period="1y", interval="1d")
                
                if not df_ai.empty:
                    # Gerekli verileri topla
                    tech = TechnicalEngine.calculate_all(df_ai)
                    sm_res = SmartMoneyEngine.analyze_smart_money(df_ai)
                    vol_res = VolumeAnalyticsEngine.analyze_volume(df_ai)
                    
                    if tech and "error" not in sm_res and "error" not in vol_res:
                        # Parametreleri çıkar
                        rsi = tech.get('RSI', pd.Series()).iloc[-1] if not tech.get('RSI', pd.Series()).empty else 50
                        macd_h = tech.get('MACD_Hist', pd.Series()).iloc[-1] if not tech.get('MACD_Hist', pd.Series()).empty else 0
                        
                        tech_dict = {'RSI': rsi, 'MACD_Hist': macd_h}
                        sm_score = sm_res.get('Smart_Money_Score', 50)
                        vwap_dist = vol_res.get('VWAP_Distance_Pct', 0)
                        
                        # AI Karar Motoru
                        decision_res = AIDecisionEngine.calculate_decision(df_ai, tech_dict, sm_score, vwap_dist)
                        
                        st.subheader(f"{ai_sym} - AI Karar & Olasılık Özeti")
                        
                        d_col1, d_col2 = st.columns(2)
                        
                        with d_col1:
                            st.write("**Nihai Yön Kararı:**")
                            dec = decision_res['Decision']
                            if "AL" in dec or "DEĞER" in dec:
                                st.success(f"🟢 {dec}")
                            elif "SAT" in dec or "DÜZELTME" in dec:
                                st.error(f"🔴 {dec}")
                            else:
                                st.warning(f"🟡 {dec}")
                                
                        with d_col2:
                            st.write("**AI Güven Skoru (Confidence):**")
                            conf = decision_res['Confidence']
                            st.metric("Olasılık", f"%{conf}")
                            st.caption(decision_res['Probability'])
                            st.progress(conf / 100)

                        st.markdown("---")
                        st.write("### 🗣️ Açıklanabilir Yapay Zeka (Explainable AI)")
                        
                        from engines.explainable_ai_engine import ExplainableAIEngine
                        
                        rv_val = vol_res.get('Relative_Volume', 1.0)
                        
                        explanations = ExplainableAIEngine.generate_explanation(decision_res['Decision'], tech_dict, sm_score, vwap_dist)
                        risks = ExplainableAIEngine.generate_counter_opinion(decision_res['Decision'], tech_dict, sm_score, vwap_dist, rv_val)
                        
                        e_col1, e_col2 = st.columns(2)
                        
                        with e_col1:
                            st.write("**✅ Neden Bu Kararı Aldım?**")
                            for exp in explanations:
                                st.info(f"💡 {exp}")
                                
                        with e_col2:
                            st.write("**⚠️ Şeytanın Avukatlığı (Karşıt Görüş)**")
                            for risk in risks:
                                st.warning(f"⚖️ {risk}")

                        st.markdown("---")
                        st.write("### 🕰️ Tarihsel Benzerlik & Senaryo Motoru")
                        st.caption("Mevcut fiyat hareketini geçmiş yıllarla kıyaslayarak benzer fraktalları bulur.")
                        
                        if st.button("🕰️ Geçmiş Benzerlikleri Ara"):
                            with st.spinner("Tüm tarihsel veriler Pearson Korelasyonu ile taranıyor..."):
                                from engines.similarity_engine import HistoricalSimilarityEngine
                                
                                sim_res = HistoricalSimilarityEngine.analyze_similarity(df_ai)
                                
                                if sim_res["Found"]:
                                    st.success(sim_res["Message"])
                                    st.write(f"**AI Projeksiyonu:** {sim_res['AI_Verdict']}")
                                    st.metric("Beklenen Ortalama Değişim (Sonraki 10 Gün)", f"%{sim_res['Avg_Expected_Change']}")
                                    
                                    st.write("**En Çok Benzeyen Geçmiş Dönemler:**")
                                    for idx, match in enumerate(sim_res["Matches"]):
                                        colA, colB, colC = st.columns(3)
                                        with colA:
                                            st.write(f"**Tarih:** {match['Date_Start']} -> {match['Date_End']}")
                                        with colB:
                                            st.write(f"**Benzerlik:** %{match['Similarity_Score']}")
                                        with colC:
                                            color = "green" if match['Future_Change_Pct'] > 0 else "red"
                                            st.markdown(f"**Sonraki 10 Gün:** <span style='color:{color}'>%{match['Future_Change_Pct']}</span>", unsafe_allow_html=True)
                                else:
                                    st.info(sim_res["Message"])

                        st.markdown("---")
                        st.write("### 💬 AI Chat Asistanı (Natural Language AI)")
                        st.caption(f"{ai_sym} hissesi hakkında yapay zekaya dilediğinizi sorun (Örn: 'Durum ne?', 'Risk var mı?', 'Yükselir mi?')")
                        
                        user_q = st.text_input("Bana bir soru sor:", key="ai_chat_input")
                        
                        if st.button("Sor"):
                            if user_q:
                                with st.spinner("Yapay Zeka yanıtlıyor..."):
                                    from engines.chat_engine import ChatEngine
                                    # Fetch Wyckoff phase to feed into the chat engine (it's part of Smart Money, but we need it here)
                                    from engines.smart_ai_engine import SmartAI_Engine
                                    ai_insight_chat = SmartAI_Engine.generate_ai_insight(df_ai)
                                    wyckoff_phase = ai_insight_chat["Wyckoff_Phase"]
                                    
                                    response = ChatEngine.process_message(user_q, ai_sym, decision_res, sm_score, wyckoff_phase)
                                    
                                    st.info(f"**Sen:** {user_q}")
                                    st.success(f"**🤖 VarantRadar AI:** {response}")
                            else:
                                st.warning("Lütfen bir soru yazın.")



                            
                    else:
                        st.error("Hesaplama için yeterli veri bulunamadı.")
                else:
                    st.error("Veri çekilemedi.")

    # NEW TAB: AI Collaboration Center (Multi-Agent)
    with tab_collaboration:
        st.header("🤖 AI Collaboration Center (Multi-Agent Toplantısı)")
        st.write("Uzman Yapay Zeka Ajanları (Trend, Hacim, Risk, Smart Money) bir araya gelerek hisseyi tartışır ve oylayarak ortak bir karar (Consensus) alırlar.")
        
        collab_sym = st.text_input("Toplantı Konusu (Hisse Sembolü):", value="TUPRS.IS")
        
        if st.button("🎙️ Ajanları Toplantıya Çağır"):
            with st.spinner("AI Ajanlar verileri analiz edip oylama yapıyor..."):
                from engines.market_data_engine import MarketDataEngine
                from engines.technical_engine import TechnicalEngine
                from engines.smart_money_engine import SmartMoneyEngine
                from engines.volume_analytics_engine import VolumeAnalyticsEngine
                from engines.smart_ai_engine import SmartAI_Engine
                from engines.multi_agent_coordinator import MultiAgentCoordinator
                
                md = MarketDataEngine()
                df_c = md.fetch_data(collab_sym, period="1y", interval="1d")
                
                if not df_c.empty:
                    # Tüm ajanların kullanacağı verileri hazırla (Context)
                    tech = TechnicalEngine.calculate_all(df_c)
                    sm_res = SmartMoneyEngine.analyze_smart_money(df_c)
                    vol_res = VolumeAnalyticsEngine.analyze_volume(df_c)
                    ai_insight = SmartAI_Engine.generate_ai_insight(df_c)
                    
                    context = {
                        "tech": tech,
                        "sm": sm_res,
                        "vol": vol_res,
                        "wyckoff": ai_insight.get("Wyckoff_Phase", "UNKNOWN"),
                        "mani_risk": ai_insight.get("Manipulation_Analysis", {}).get("Risk_Score", 0)
                    }
                    
                    coordinator = MultiAgentCoordinator()
                    debate_res = coordinator.run_debate(df_c, context)
                    
                    st.markdown("---")
                    st.subheader(f"🏆 Ortak Karar (Consensus): {debate_res['Consensus']}")
                    st.caption(f"Ajanların Oylama Skoru: {debate_res['Average_Vote_Score']} (-1 ile +1 arası)")
                    st.markdown("---")
                    
                    st.write("### 🗣️ Toplantı Tutanakları (Debate Log)")
                    for log in debate_res['Debate_Log']:
                        with st.expander(f"{log['Agent']} (Oy: {log['Vote']}) - Güven: %{log['Confidence']}", expanded=True):
                            st.caption(f"Rolü: {log['Role']}")
                            
                            if log['Vote'] == 1:
                                st.success(f"**Görüşü:** {log['Reason']}")
                            elif log['Vote'] == -1:
                                st.error(f"**Görüşü:** {log['Reason']}")
                            else:
                                st.info(f"**Görüşü:** {log['Reason']}")
                else:
                    st.error("Veri çekilemedi.")

    # NEW TAB: Autonomous AI Radar
    with tab_auto_radar:
        st.header("🛸 Autonomous AI Radar (Multi-Agent Tarayıcı)")
        st.write("Siz ekran başında yokken bile, AI ajanları tüm piyasayı (Örn: Seçili Hisseler) otonom olarak tarar, aralarında toplantı yapar ve üzerinde **Uzlaştıkları (Consensus)** fırsatları listeler.")
        
        # Basit bir BIST havuzu örneği
        default_pool = "THYAO.IS, ASELS.IS, TUPRS.IS, GARAN.IS, EREGL.IS, SISE.IS, BIMAS.IS, AKBNK.IS"
        pool_input = st.text_input("Taranacak Hisse Havuzu (Virgülle ayırın)", value=default_pool)
        
        if st.button("🛸 Otonom Taramayı Başlat"):
            symbols = [s.strip() for s in pool_input.split(",") if s.strip()]
            
            if symbols:
                with st.spinner(f"{len(symbols)} hisse için AI Ajanlar toplantıya çağrılıyor..."):
                    from engines.autonomous_radar import AutonomousRadar
                    
                    scan_results = AutonomousRadar.scan_market(symbols)
                    
                    st.success(f"Tarama Tamamlandı! Taranan: {scan_results['Total_Scanned']} | Fırsat Bulunan: {scan_results['Opportunities_Found']}")
                    
                    if scan_results['Opportunities_Found'] > 0:
                        import pandas as pd
                        df_res = pd.DataFrame(scan_results['Results'])
                        # UI için kolon isimlerini düzeltelim
                        df_res = df_res.rename(columns={
                            "Opportunity_Score": "Fırsat Skoru (0-100)",
                            "Consensus": "Ortak Karar",
                            "Wyckoff": "Piyasa Evresi",
                            "Smart_Money": "Akıllı Para Skoru"
                        })
                        st.dataframe(df_res[["Symbol", "Fırsat Skoru (0-100)", "Ortak Karar", "Piyasa Evresi", "Akıllı Para Skoru"]], use_container_width=True)
                        st.info("💡 **İpucu:** Bulunan fırsatların neden 'AL' verdiğini detaylı incelemek için bu hisseyi 'AI Collaboration' sekmesinde toplantıya sokabilirsiniz.")
                    else:
                        st.warning("Ajanlar mevcut havuzda uzlaşmaya vardıkları belirgin bir fırsat (AL yönlü) bulamadılar.")
            else:
                st.error("Lütfen taranacak hisseleri girin.")

    # NEW TAB: FinOS Kernel & Health
    with tab_finos:
        st.header("⚙️ FinOS Kernel & System Health")
        st.write("VarantRadar Pro artık basit bir uygulama değil, 'Finansal İşletim Sistemi' (FinOS) mantığıyla çalışıyor. Sistem çekirdeğini ve modüllerini buradan izleyebilirsiniz.")
        
        # Initialize Kernel in session state if not exists
        if "finos_kernel" not in st.session_state:
            from core.kernel import FinOSKernel
            st.session_state.finos_kernel = FinOSKernel()
            st.session_state.finos_boot_info = st.session_state.finos_kernel.boot()
            
        kernel = st.session_state.finos_kernel
        health = kernel.get_system_health()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            status_color = "normal" if health['Kernel_Status'] == "ONLINE" else "inverse"
            st.metric("Çekirdek (Kernel) Durumu", health['Kernel_Status'], delta_color=status_color)
        with c2:
            st.metric("Sistem Sağlık Skoru (Health)", f"%{health['System_Health_Score']}")
        with c3:
            st.metric("In-Memory Cache (Bellek Yükü)", f"{health['Memory_Usage_MB']} MB")
            
        st.markdown("---")
        st.write("### 🧩 Aktif Modüller (Service Registry)")
        
        # Modülleri yan yana kutucuklar halinde göster
        mod_cols = st.columns(len(health['Modules']))
        for i, (mod_name, mod_data) in enumerate(health['Modules'].items()):
            with mod_cols[i]:
                st.info(f"**{mod_name.replace('_', ' ')}**\nTür: {mod_data['type']}\nDurum: {mod_data['status']}")
                
        if st.button("🧹 Sistem Belleğini (Cache) Temizle"):
            kernel.data_layer.clear_cache()
            st.success("Bellek başarıyla temizlendi (Garbage Collection çalıştırıldı).")
            st.rerun()

    # NEW TAB: FinOS Automation & Events
    with tab_automation:
        st.header("⚡ FinOS Event Queue & Workflow Automation")
        st.write("İşletim sistemindeki tüm modüller Event Bus (Olay Yöneticisi) üzerinden haberleşir. Otonom zamanlanmış görevleri (Scheduler) de buradan yönetebilirsiniz.")
        
        # Initialize EventBus and Scheduler in session state
        if "finos_event_bus" not in st.session_state:
            from core.event_bus import EventBus
            from core.scheduler import Scheduler
            
            eb = EventBus()
            sc = Scheduler()
            
            # Örnek birkaç olay fırlat
            eb.publish("SYSTEM_BOOT", {"message": "FinOS Başlatıldı"})
            eb.publish("RADAR_SCAN_START", {"target": "BIST30"})
            
            # Örnek birkaç otonom görev ekle
            sc.schedule_task("Otonom BIST30 Taraması", "Her Gün 18:15", "SCAN_RADAR")
            sc.schedule_task("Portföy Risk Analizi", "Her 1 Saatte Bir", "CALC_RISK")
            
            st.session_state.finos_event_bus = eb
            st.session_state.finos_scheduler = sc
            
        eb = st.session_state.finos_event_bus
        sc = st.session_state.finos_scheduler
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("📬 Canlı Olay Akışı (Event Queue)")
            events = eb.get_recent_events()
            if events:
                for e in events:
                    st.info(f"**[{e['timestamp']}] {e['type']}**\nPayload: {e['payload']}")
            else:
                st.write("Henüz fırlatılan bir olay yok.")
                
            if st.button("🔧 Test Olayı Fırlat (Emit Event)"):
                eb.publish("TEST_EVENT", {"info": "Kullanıcı manuel olay tetikledi."})
                st.rerun()
                
        with c2:
            st.subheader("⏱️ Zamanlanmış Görevler (Scheduler)")
            tasks = sc.get_all_tasks()
            for t in tasks:
                with st.expander(f"📌 {t['name']} ({t['interval']})", expanded=True):
                    st.write(f"Durum: **{t['status']}**")
                    st.write(f"Son Çalışma: {t['last_run']}")
                    if st.button(f"Tetikle (Run Now)", key=f"btn_{t['id']}"):
                        sc.trigger_task(t['id'])
                        eb.publish("TASK_TRIGGERED", {"task_name": t['name']})
                        st.success(f"{t['name']} tamamlandı.")
                        st.rerun()

    # NEW TAB: Digital Twin & Sandbox
    with tab_digital_twin:
        st.header("🕰️ Digital Twin & Scenario Sandbox")
        st.write("VarantRadar Pro'nun 'Zaman Makinesi'. Geçmişteki bir tarihi seçin ve piyasayı o güne kadar simüle edin. AI Ajanları geleceği bilmeden o gün toplantı yapıp karar verecek. Ardından kararlarının 1 ay sonra ne kadar doğru çıktığını görebilirsiniz.")
        
        c1, c2 = st.columns(2)
        with c1:
            twin_sym = st.text_input("Simüle Edilecek Hisse:", value="TUPRS.IS")
        with c2:
            import datetime
            # Örnek geçmiş tarih
            default_date = datetime.date(2023, 5, 10)
            target_date = st.date_input("Zaman Makinesi (Hedef Tarih):", value=default_date)
            
        if st.button("🕰️ Simülasyonu Başlat (Replay)"):
            with st.spinner(f"{twin_sym} için {target_date} tarihi simüle ediliyor. Ajanlar toplantıda..."):
                from engines.digital_twin import DigitalTwinSandbox
                
                sim_res = DigitalTwinSandbox.run_simulation(twin_sym, str(target_date))
                
                if "Error" in sim_res:
                    st.error(sim_res["Error"])
                else:
                    st.success(f"Simülasyon Tamamlandı! O günkü hisse fiyatı: {sim_res['Current_Price']} TL")
                    
                    debate = sim_res["Debate_Result"]
                    st.subheader(f"🏆 Ajanların O Günkü Kararı: {debate['Consensus']}")
                    
                    with st.expander("🗣️ Toplantı Detayları (O gün ne konuştular?)"):
                        for log in debate["Debate_Log"]:
                            st.write(f"**{log['Agent']}:** {log['Reason']} (Oy: {log['Vote']})")
                            
                    st.markdown("---")
                    st.write("### 🔮 Gerçekte Ne Oldu? (1 Ay Sonra)")
                    ret = sim_res['Future_1M_Return']
                    
                    if ret > 0:
                        st.success(f"Hisse simülasyon tarihinden 1 ay sonra **%{ret}** yükseldi.")
                        if "AL" in debate['Consensus']:
                            st.balloons()
                            st.info("🎯 Ajanlar haklı çıktı! Başarılı bir tahmin.")
                    else:
                        st.error(f"Hisse simülasyon tarihinden 1 ay sonra **%{ret}** düştü.")
                        if "SAT" in debate['Consensus'] or "RİSK" in debate['Consensus']:
                            st.info("🛡️ Ajanlar düşüşü önceden sezdi ve sizi korudu!")

    # NEW TAB: Market Intelligence Hub
    with tab_market_intel:
        st.header("🏢 Institutional Market Intelligence Hub")
        st.write("Bloomberg Terminali seviyesinde Kurumsal Zeka Merkezi. Hisselerin sadece teknik grafiklerini değil; Bilançolarını (Temel Analiz), Kantitatif Skoru (Quant) ve Genel Piyasa Rejimini (Makro) tek ekranda analiz edin.")
        
        c1, c2 = st.columns(2)
        with c1:
            intel_sym = st.text_input("Analiz Edilecek Hisse (Temel Analiz):", value="TUPRS.IS")
        with c2:
            macro_index = st.text_input("Makro Rejim Endeksi (Örn: XU100.IS):", value="XU100.IS")
            
        if st.button("🏢 Kurumsal Analizi Başlat (Fundamental & Macro)"):
            with st.spinner("Piyasa Rejimi (Makro) ve Şirket Bilançosu (Fundamental) analiz ediliyor..."):
                from core.data_layer import UnifiedDataLayer
                from engines.market_regime_engine import MarketRegimeEngine
                from engines.fundamental_engine import FundamentalEngine
                
                data_layer = UnifiedDataLayer()
                
                # 1. Makro / Rejim Analizi
                df_index = data_layer.fetch_market_data(macro_index, period="1y", interval="1d")
                regime_data = MarketRegimeEngine.analyze_regime(df_index)
                
                # 2. Temel Analiz / Bilanço Analizi
                fund_data = FundamentalEngine.analyze_fundamentals(intel_sym)
                
                # --- UI RENDER ---
                
                st.markdown("---")
                st.subheader(f"🌍 {macro_index} Makro Piyasa Rejimi (Market Regime)")
                r1, r2, r3 = st.columns(3)
                
                regime_color = "normal"
                if regime_data['Regime'] == "AYI (BEAR)": regime_color = "inverse"
                elif regime_data['Regime'] == "YATAY (SIDEWAYS)": regime_color = "off"
                
                r1.metric("Piyasa Rejimi", regime_data['Regime'], delta=regime_data['Status'], delta_color=regime_color)
                r2.metric("Volatilite Durumu", regime_data['Volatility'])
                r3.metric("Kısa Vade Trend (SMA 20)", regime_data['Metrics']['SMA20'])
                
                st.markdown("---")
                st.subheader(f"🏢 {intel_sym} - Enterprise Quant & Fundamental Intelligence (Modül 76)")
                
                f1, f2, f3, f4, f5 = st.columns(5)
                f1.metric("F/K (P/E)", fund_data['P_E_Ratio'])
                f2.metric("PD/DD (P/B)", fund_data['P_B_Ratio'])
                f3.metric("Özsermaye Karlılığı (ROE)", fund_data['ROE'])
                f4.metric("Kâr Marjı", fund_data['Profit_Margin'])
                f5.metric("Borç/Özsermaye", fund_data['Debt_to_Equity'])
                
                st.write("")
                st.info(f"**💡 Temel Analiz Yorumu (AI):** {fund_data['Analysis']}")
                
                st.markdown("#### 🔬 Kantitatif Kalite Skoru (Quant Score)")
                st.progress(fund_data['Fundamental_Score'] / 100)
                st.caption(f"Fundamental Health Score: **{fund_data['Fundamental_Score']}/100** | Statü: **{fund_data['Status']}** | Piotroski Tahmini: **{fund_data['Piotroski_Estimate']}**")

    # NEW TAB: News, Sentiment & Alerts
    with tab_sentiment_alerts:
        st.header("📰 News, Sentiment & Alert Center")
        st.write("Şirket hakkındaki haberleri tarar, yatırımcıların duygu durumunu (Sentiment) NLP ile analiz eder ve kriz anlarında FinOS Event Bus üzerinden anlık acil durum alarmları fırlatır.")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("📰 Sentiment Analizi")
            news_sym = st.text_input("Haberleri Taranacak Hisse:", value="TUPRS.IS")
            if st.button("Haberleri ve Sentiment'i Analiz Et"):
                with st.spinner("İnternetten güncel haberler çekiliyor ve yapay zeka tarafından okunuyor..."):
                    from engines.sentiment_engine import SentimentEngine
                    sent_res = SentimentEngine.analyze_news(news_sym)
                    
                    st.markdown("---")
                    st.write(f"### 🧠 AI Duygu Analizi (Sentiment): {sent_res['Status']}")
                    st.progress(sent_res['Sentiment_Score'] / 100)
                    st.caption(f"Sentiment Skoru (Korku/Açgözlülük): **{sent_res['Sentiment_Score']}/100**")
                    st.info(f"**Yorum:** {sent_res['Analysis']}")
                    
                    st.write(f"#### 🗞️ Son Okunan Haberler ({sent_res['News_Count']} adet)")
                    if sent_res['News_Count'] > 0:
                        for h in sent_res['Headlines']:
                            st.write(f"- {h['title']} *(Skor: {h['sentiment']})*")
                    else:
                        st.write("Hisse hakkında güncel haber bulunamadı.")
                        
        with c2:
            st.subheader("🚨 FinOS Alert Center (Alarm Merkezi)")
            st.write("Sistemdeki tüm kritik alarmlar burada toplanır.")
            
            if st.button("Alarmları Yenile"):
                st.rerun()
                
            from engines.alert_center import AlertCenter
            ac = AlertCenter()
            alerts = ac.fetch_alerts()
            
            if alerts:
                for a in alerts:
                    st.error(f"**🚨 [{a['timestamp']}] {a['type']}**\n{a['payload']}")
            else:
                st.success("Şu an sistemde aktif bir Kriz Alarmı bulunmuyor. Her şey yolunda.")

    # NEW TAB: Digital Investment Office (Ecosystem Final)
    with tab_ecosystem:
        st.header("👑 Digital Investment Office (AI C-Suite)")
        st.write("VarantRadar Pro Enterprise Ultimate sürümünün mutlak zirvesi. Tüm yapay zeka motorları (Teknik, Bilanço, Haber, Makro, Hacim) Sanal Yönetim Kurulunda birleşir ve size ortak bir 'Executive Decision' (Yönetici Kararı) sunar.")
        
        c1, c2 = st.columns(2)
        with c1:
            eco_sym = st.text_input("Kurula Sunulacak Varlık:", value="TUPRS.IS")
        with c2:
            st.write("")
            st.write("")
            if st.button("👑 Sanal Yönetim Kurulunu Topla (Run C-Suite)"):
                with st.spinner("AI CIO, CRO ve Quant Direktörü verileri inceliyor... (Tüm motorlar eşzamanlı çalışıyor)"):
                    from engines.digital_investment_office import DigitalInvestmentOffice
                    
                    board_res = DigitalInvestmentOffice.hold_board_meeting(eco_sym)
                    exec_data = board_res["Executive_Data"]
                    minutes = board_res["Meeting_Minutes"]
                    
                    # --- NİHAİ KARAR PİRAMİDİ ---
                    st.markdown("---")
                    st.markdown(f"<h2 style='text-align: center; color: #4CAF50;'>NİHAİ AI KARARI: {exec_data['Final_Decision']}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<h4 style='text-align: center;'>Genel Güven Skoru (Confidence): %{exec_data['Confidence_Score']}</h4>", unsafe_allow_html=True)
                    st.markdown("---")
                    
                    # --- SANAL YÖNETİM KURULU GÖRÜŞLERİ ---
                    st.subheader("🗣️ Kurul Üyelerinin Görüşleri (Meeting Minutes)")
                    
                    st.info(f"**👔 AI Chief Investment Officer (CIO):**\n{minutes['AI_CIO']}")
                    st.warning(f"**🛡️ AI Chief Risk Officer (CRO):**\n{minutes['AI_CRO']}")
                    st.success(f"**📊 AI Quant Director:**\n{minutes['AI_Quant_Director']}")
                    st.write(f"**🌍 AI Chief Economist:**\n{minutes['AI_Economist']}")
                    
                    # --- SKOR TABLOSU ---
                    st.markdown("---")
                    st.subheader("🎛️ Alt Motorların Skor Dağılımı")
                    
                    s_tech = exec_data['Scores']['Technical']
                    s_fund = exec_data['Scores']['Fundamental']
                    s_sent = exec_data['Scores']['Sentiment']
                    s_sm = exec_data['Scores']['Smart_Money']
                    s_macro = exec_data['Scores']['Macro_Regime']
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Teknik Analiz", f"{s_tech['Score']}/100", delta=s_tech['Status'])
                    col2.metric("Temel Analiz", f"{s_fund['Score']}/100", delta=s_fund['Status'])
                    col3.metric("Duyarlılık", f"{s_sent['Score']}/100", delta=s_sent['Status'])
                    col4.metric("Smart Money", f"{s_sm['Score']}/100", delta=s_sm['Status'])
                    col5.metric("Makro Rejim", s_macro['Status'])
with tab_stats:
    st.markdown("### 📊 Win Rate & Historical Statistics")
    try:
        from services.tavan_tracker import TavanAuditTracker
        from services.win_rate_engine import WinRateEngine
        
        stats = WinRateEngine.get_performance_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Win Rate", f"%{stats.get('tavan_radar_win_rate', 0)}")
        col2.metric("+%5 Hit Rate", f"%{stats.get('plus5_hit_rate', 0)}")
        col3.metric("Profit Factor", str(stats.get('profit_factor', 0)))
        col4.metric("Avg Warrant Gain", f"%{stats.get('avg_ahlatci_warrant_gain', 0)}")
        
        st.markdown("#### 📅 Daily Historical Breakdown")
        history = TavanAuditTracker.get_long_term_history()
        breakdown = history.get('daily_breakdown', [])
        
        if breakdown:
            import pandas as pd
            df = pd.DataFrame(breakdown)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No historical tracking data found.")
            
    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")
