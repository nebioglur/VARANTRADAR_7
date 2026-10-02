import pandas as pd
import io
import datetime
from typing import Dict, Any

class ReportingEngine:
    """
    Kurumsal Portföy Raporları (Executive, Client, PDF/HTML, Excel) üretir.
    """
    
    @staticmethod
    def generate_excel_report(portfolio_data: Dict[str, Any], factor_data: pd.DataFrame, corr_matrix: pd.DataFrame) -> bytes:
        """
        Girdi: Çeşitli engine'lardan gelen analiz verileri.
        Çıktı: İndirilebilir Excel dosyasının byte dizisi.
        """
        output = io.BytesIO()
        
        # Excel writer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. Summary Sheet
            summary_df = pd.DataFrame([
                {"Metrik": "Rapor Tarihi", "Değer": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")},
                {"Metrik": "Portföy Sağlık Skoru", "Değer": portfolio_data.get('health_score', 'N/A')},
                {"Metrik": "AI Güven Endeksi", "Değer": portfolio_data.get('confidence', 'N/A')},
                {"Metrik": "Çeşitlendirme Skoru", "Değer": portfolio_data.get('diversification', 'N/A')}
            ])
            summary_df.to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # 2. Factor Analysis Sheet
            if not factor_data.empty:
                factor_data.to_excel(writer, sheet_name='Factor Analysis')
                
            # 3. Correlation Matrix Sheet
            if not corr_matrix.empty:
                corr_matrix.to_excel(writer, sheet_name='Correlation Matrix')
                
        return output.getvalue()
        
    @staticmethod
    def generate_html_report(portfolio_data: Dict[str, Any], ai_reasons: list) -> str:
        """
        Kurumsal HTML Raporu üretir. PDF olarak yazdırılabilir.
        """
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        reasons_html = "".join([f"<li>{r}</li>" for r in ai_reasons])
        
        html_template = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
                h1 {{ color: #1a4f76; border-bottom: 2px solid #1a4f76; padding-bottom: 10px; }}
                h2 {{ color: #2c3e50; margin-top: 30px; }}
                .metric-box {{ background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 5px; margin-bottom: 10px; }}
                .metric-title {{ font-size: 14px; color: #6c757d; font-weight: bold; text-transform: uppercase; }}
                .metric-value {{ font-size: 24px; color: #212529; font-weight: bold; }}
                .ai-box {{ background: #e8f4f8; border-left: 5px solid #1a4f76; padding: 15px; margin-top: 20px; }}
                .footer {{ margin-top: 50px; font-size: 12px; color: #888; text-align: center; border-top: 1px solid #ddd; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>VarantRadar Pro - Kurumsal Portföy Raporu</h1>
            <p>Tarih: {date_str}</p>
            
            <h2>Yönetici Özeti (Executive Summary)</h2>
            <div class="metric-box">
                <div class="metric-title">Portföy Sağlık Skoru</div>
                <div class="metric-value">{portfolio_data.get('health_score', 'N/A')} / 100</div>
            </div>
            <div class="metric-box">
                <div class="metric-title">AI Güven Endeksi (Confidence)</div>
                <div class="metric-value">%{portfolio_data.get('confidence', 'N/A')}</div>
            </div>
            
            <h2>🧠 AI Yatırım Koçu Görüşleri</h2>
            <div class="ai-box">
                <ul>
                    {reasons_html}
                </ul>
            </div>
            
            <div class="footer">
                Bu rapor VarantRadar Pro Enterprise Analytics (CFG-07) motoru tarafından otomatik olarak oluşturulmuştur.
                Sadece bilgi amaçlıdır, kesin yatırım tavsiyesi içermez.
            </div>
        </body>
        </html>
        """
        return html_template
