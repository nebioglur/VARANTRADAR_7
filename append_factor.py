import io

content = '''
    
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
'''

with io.open("c:/Users/nebio/Desktop/VarantRadarPro/app.py", "r", encoding="utf-8") as f:
    text = f.read()

# Insert the factor logic at the end of tab_portfolio (we can just append it to the end of the file since tab_portfolio is at the end)
with io.open("c:/Users/nebio/Desktop/VarantRadarPro/app.py", "a", encoding="utf-8") as f:
    f.write(content)
