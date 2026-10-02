from typing import Dict, Optional

import yfinance as yf

class FundamentalEngine:
    """
    CFG-03.2 — FUNDAMENTAL DATA ENGINE
    
    Bilanço, Gelir Tablosu, Nakit Akışı, Finansal Oranlar gibi temel verileri çeker.
    """
    
    def __init__(self):
        pass
        
    def get_financial_ratios(self, symbol: str) -> Dict[str, float]:
        """Finansal oranları döner (F/K, PD/DD vs.). TradingView ve Yahoo Finance'ten canlı veriler."""
        import requests
        
        # 1. TRADINGVIEW SCANNER API (BIST Hisseleri için Mükemmel Kaynak)
        clean_sym = symbol.replace('.IS', '')
        # Varantları filtrele (genelde 5 harflidir ama BIST hisselerinde de 5 harf olabilir, yine de TV desteklerse çeker)
        tv_symbol = f"BIST:{clean_sym}"
        
        try:
            url = "https://scanner.tradingview.com/turkey/scan"
            payload = {
                "symbols": {"tickers": [tv_symbol]},
                "columns": ["price_earnings_ttm", "price_book_fq", "return_on_equity_fq", "debt_to_equity_fq", "net_margin_ttm", "sector", "industry"]
            }
            # Kapsamlı Timeout ve Header
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and len(data["data"]) > 0:
                    d = data["data"][0]["d"]
                    if d:
                        res_dict = {
                            "pe_ratio": d[0] if d[0] is not None else "N/A",
                            "pb_ratio": d[1] if d[1] is not None else "N/A",
                            "roe": (d[2] / 100.0) if d[2] is not None else "N/A", # convert to decimal
                            "debt_to_equity": d[3] if d[3] is not None else "N/A",
                            "profit_margin": (d[4] / 100.0) if d[4] is not None else "N/A",
                            "sector": d[5] if d[5] is not None else "N/A",
                            "industry": d[6] if d[6] is not None else "N/A"
                        }
                        
                        # Hybrid Fallback: Eğer Borç/Özkaynak TV'den gelmediyse yfinance'i dene (AKCNS gibi hisseler için)
                        if res_dict["debt_to_equity"] == "N/A":
                            try:
                                fallback_info = yf.Ticker(symbol).info
                                yf_debt = fallback_info.get("debtToEquity")
                                if yf_debt is not None:
                                    res_dict["debt_to_equity"] = yf_debt
                            except Exception:
                                pass
                                
                        return res_dict
        except Exception as e:
            print(f"[FundamentalEngine] TradingView API Hatası: {e}")

        # 2. YFINANCE FALLBACK (Eğer TV bulamazsa veya yurtdışı hissesi ise)
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            margin = info.get("profitMargins")
            debt = info.get("debtToEquity")
            
            return {
                "pe_ratio": pe if pe is not None else "N/A",
                "pb_ratio": pb if pb is not None else "N/A",
                "roe": roe if roe is not None else "N/A",
                "profit_margin": margin if margin is not None else "N/A",
                "debt_to_equity": debt if debt is not None else "N/A",
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A")
            }
        except Exception:
            return {
                "pe_ratio": "N/A", "pb_ratio": "N/A", "roe": "N/A", 
                "profit_margin": "N/A", "debt_to_equity": "N/A",
                "sector": "N/A", "industry": "N/A"
            }
        
    def get_balance_sheet_summary(self, symbol: str) -> Dict[str, float]:
        """Özet bilanço bilgilerini döner."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                "total_assets": info.get("totalAssets", "N/A"),
                "total_liabilities": info.get("totalDebt", "N/A"), # tam örtüşmese de yaklaşık
                "total_equity": info.get("bookValue", "N/A") # book value per share
            }
        except Exception:
            return {
                "total_assets": "N/A",
                "total_liabilities": "N/A",
                "total_equity": "N/A"
            }
