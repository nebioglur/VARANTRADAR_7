import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

class ChartEngine:
    @staticmethod
    def create_advanced_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
        """
        Gelişmiş teknik analiz grafiği (Modül 4)
        """
        if df.empty:
            return go.Figure()

        # Alt grafikler oluştur (3 satır: 1. Fiyat+Hacim+Göstergeler, 2. MACD, 3. RSI)
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f"{symbol} Fiyat Grafiği", "MACD", "RSI")
        )

        # 4.1 Mum Grafik
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], 
            low=df['low'], close=df['close'], name='Fiyat'
        ), row=1, col=1)

        # 4.2 Hacim (Fiyat grafiğinin altına yerleştirilir, y2 ekseni kullanılır)
        colors = ['red' if row['open'] - row['close'] >= 0 else 'green' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(
            x=df.index, y=df['volume'], name='Hacim', marker_color=colors, opacity=0.3
        ), row=1, col=1)

        # 4.3 EMA & 4.4 VWAP
        if 'ema_20' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['ema_20'], line=dict(color='orange', width=1), name='EMA 20'), row=1, col=1)
        if 'vwap' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['vwap'], line=dict(color='blue', width=1, dash='dot'), name='VWAP'), row=1, col=1)
            
        # SuperTrend
        if 'SUPERTREND' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['SUPERTREND'], line=dict(color='rgba(255, 0, 0, 0.5)', width=1, dash='dot'), name='SuperTrend'), row=1, col=1)

        # 4.5 & 4.6 Destek ve Direnç (Otomatik S/R Seviyeleri)
        sr_cols = [c for c in df.columns if 'AUTO_SR' in c]
        for col in sr_cols:
            level = df[col].iloc[-1]
            fig.add_hline(y=level, line_dash="dash", line_color="rgba(0, 255, 255, 0.5)", annotation_text="D/D", row=1, col=1)
            
        # MACD Alt Grafiği
        if 'macd' in df.columns and 'macd_signal' in df.columns and 'macd_hist' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['macd'], line=dict(color='blue', width=1), name='MACD'), row=2, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['macd_signal'], line=dict(color='orange', width=1), name='Signal'), row=2, col=1)
            # Histogram
            macd_colors = ['green' if val >= 0 else 'red' for val in df['macd_hist']]
            fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], marker_color=macd_colors, name='Histogram'), row=2, col=1)

        # RSI Alt Grafiği
        if 'rsi' in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='purple', width=1), name='RSI'), row=3, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        # Rangebreaks for excluding weekends and holidays
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        
        # 4.8, 4.9, 4.10 Plotly default config settings (Applied in frontend, but we format the layout here)
        # V9 UPDATE: Profesyonel Çizim Araçları (DrawTools) Eklendi
        fig.update_layout(
            template='plotly_dark',
            height=800,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode='drawline',
            newshape=dict(line_color='yellow', line_width=2),
            modebar_add=['drawline', 'drawopenpath', 'drawcircle', 'drawrect', 'eraseshape']
        )
        
        return fig
