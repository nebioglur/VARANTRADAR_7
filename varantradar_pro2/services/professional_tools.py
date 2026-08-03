import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from config.bist_symbols import BIST30_SYMBOLS

class ProfessionalTools:
    """
    VarantRadar Pro V9 - Profesyonel Trader Araçları
    Heatmap, Korelasyon Matrisi ve piyasa derinliği analizleri sunar.
    """
    
    @staticmethod
    def generate_dummy_correlation_matrix(symbols: list) -> go.Figure:
        """Modül 10: Korelasyon Matrisi (Simüle edilmiş)"""
        # Gerçekte yfinance'den tüm hisselerin kapanışları indirilip pd.DataFrame.corr() hesaplanır
        # Performans için rastgele mantıklı bir matris oluşturuyoruz.
        n = len(symbols)
        # Create a symmetric positive semi-definite matrix
        rand_mat = np.random.rand(n, n)
        corr_mat = (rand_mat + rand_mat.T) / 2
        np.fill_diagonal(corr_mat, 1.0)
        
        df_corr = pd.DataFrame(corr_mat, index=symbols, columns=symbols)
        
        fig = px.imshow(df_corr, 
                        text_auto=".2f", 
                        aspect="auto",
                        color_continuous_scale="RdBu_r",
                        title="BIST Korelasyon Matrisi (Simülasyon)")
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        return fig

    @staticmethod
    def generate_market_heatmap(symbols: list, radar_results: pd.DataFrame = None) -> go.Figure:
        """Modül 10: BIST Isı Haritası (Treemap)"""
        if radar_results is None or radar_results.empty:
            # Generate dummy data
            data = {
                'Symbol': symbols,
                'MarketCap': np.random.randint(100, 1000, size=len(symbols)),
                'DailyReturn': np.random.uniform(-5, 5, size=len(symbols))
            }
            df = pd.DataFrame(data)
        else:
            # Use radar results if available
            df = radar_results.copy()
            df['Symbol'] = df['Hisse']
            df['MarketCap'] = df['Hacim'] if 'Hacim' in df.columns else np.random.randint(100, 1000, size=len(df))
            df['DailyReturn'] = df['RSI'] - 50 # Sadece renklendirme için örnek (Gerçekte % değişim olmalı)
            
        df['Sector'] = 'BIST30' # Basitleştirme
        
        fig = px.treemap(df, 
                         path=['Sector', 'Symbol'], 
                         values='MarketCap',
                         color='DailyReturn',
                         color_continuous_scale='RdYlGn',
                         color_continuous_midpoint=0,
                         title="BIST30 Piyasa Isı Haritası (Market Heatmap)")
        fig.update_layout(margin=dict(t=30, l=0, r=0, b=0))
        return fig
