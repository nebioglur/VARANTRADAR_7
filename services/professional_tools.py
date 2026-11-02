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
        n = len(symbols)
        # No observed return history was provided; do not invent correlations.
        df_corr = pd.DataFrame(np.full((n, n), np.nan), index=symbols, columns=symbols)

        fig = px.imshow(df_corr, 
                        text_auto=".2f", 
                        aspect="auto",
                        color_continuous_scale="RdBu_r",
                        title="BIST Korelasyon Matrisi (Geçmiş fiyat verisi gerekli)")
        fig.update_layout(margin=dict(l=0, r=0, t=30, b=0))
        return fig

    @staticmethod
    def generate_market_heatmap(symbols: list, radar_results: pd.DataFrame = None) -> go.Figure:
        """Modül 10: BIST Isı Haritası (Treemap)"""
        if radar_results is None or radar_results.empty:
            return go.Figure().update_layout(title="Isı haritası için doğrulanmış piyasa verisi gerekli")
        else:
            # Use radar results if available
            df = radar_results.copy()
            df['Symbol'] = df['Hisse']
            df['MarketCap'] = df['Hacim'] if 'Hacim' in df.columns else df.get('Volume', 0)
            df['DailyReturn'] = df['Change_Pct'] if 'Change_Pct' in df.columns else df.get('Daily_Change_Pct', 0)
            
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
