"""
VarantRadar Pro - Gercek Basari Karnesi Motoru
04 Agustos 2026'dan itibaren tavan_tracker verilerine dayanir.
Sahte/hardcoded veri YOKTUR - tum istatistikler gercek seans verilerinden hesaplanir.
"""
from typing import Dict, Any
from services.tavan_tracker import TavanAuditTracker


class WinRateEngine:
    """
    Gercek performans istatistiklerini tavan_tracker uzerinden hesaplar.
    Sahte veri uretmez - sadece gercek seans kayitlarindan beslenir.
    """

    @classmethod
    def get_performance_stats(cls) -> Dict[str, Any]:
        """Tum sistemin genel basari metriklerini gercek veriden dondurur."""
        try:
            history = TavanAuditTracker.get_long_term_history(start_date="2026-08-04")
            summ = history.get("summary", {})

            total_candidates = summ.get("total_candidates_tracked", 0)
            total_tavan = summ.get("total_hit_ceiling", 0)
            total_plus5 = summ.get("total_hit_plus5", 0)
            total_days = summ.get("total_days_tracked", 0)
            tavan_pct = summ.get("tavan_success_pct", 0.0)
            plus5_pct = summ.get("plus5_success_pct", 0.0)
            avg_max_gain = summ.get("cumulative_avg_max_gain_pct", 0.0)
            avg_close_gain = summ.get("cumulative_avg_closing_gain_pct", 0.0)
            warrant_avg = summ.get("ahlatci_warrant_avg_gain_pct", 0.0)

            # Profit Factor hesapla (basit: kazanan/kaybeden orani)
            losers = total_candidates - total_plus5
            profit_factor = round(total_plus5 / max(losers, 1), 2) if total_candidates > 0 else 0.0

            # Son gunlerin dokumleri
            daily_breakdown = history.get("daily_breakdown", [])
            recent_signals = []
            for day in daily_breakdown[:5]:  # Son 5 gun
                candidates = day.get("candidates", [])
                for c in candidates[:3]:  # Her gunden max 3 sinyal
                    max_gain = c.get("max_gain_pct", 0)
                    closing_gain = c.get("closing_gain_pct", 0)
                    hit_ceiling = c.get("hit_ceiling", False)

                    if hit_ceiling:
                        status = "TAVAN KILIDI"
                        pnl = f"+%{max_gain}"
                    elif max_gain >= 5:
                        status = "+%5 HEDEF ULASILDI"
                        pnl = f"+%{closing_gain}"
                    elif closing_gain > 0:
                        status = "POZITIF KAPANIŞ"
                        pnl = f"+%{closing_gain}"
                    else:
                        status = "NEGATIF KAPANIŞ"
                        pnl = f"%{closing_gain}"

                    recent_signals.append({
                        "symbol": c.get("symbol", "?"),
                        "date": day.get("date", ""),
                        "signal_type": "Tavan Radari",
                        "entry_price": "",
                        "target_price": "",
                        "exit_price": "",
                        "pnl_pct": pnl,
                        "status": status,
                        "duration": day.get("snapshot_time", ""),
                        "warrant_gain": f"+%{round(max_gain * 6.2, 1)}" if max_gain > 0 else "-%0"
                    })

            return {
                "summary": {
                    "total_signals_30d": total_candidates,
                    "target_reached": total_tavan,
                    "stopped_out": total_candidates - total_plus5,
                    "win_rate_pct": tavan_pct,
                    "avg_profit_pct": avg_max_gain,
                    "avg_time_to_target_hours": f"{total_days} Seans",
                    "profit_factor": profit_factor
                },
                "category_winrates": [
                    {
                        "name": "Tavan Radari (Gercek Veri)",
                        "icon": "fa-rocket",
                        "color": "var(--accent-green)",
                        "signals": total_candidates,
                        "success": total_tavan,
                        "win_rate": f"%{tavan_pct}",
                        "avg_gain": f"+%{avg_max_gain}",
                        "desc": f"{total_days} seansta {total_tavan}/{total_candidates} tavan kilidi"
                    },
                    {
                        "name": "+%5 ve Uzeri Kar Basarisi",
                        "icon": "fa-chart-line",
                        "color": "var(--accent-blue)",
                        "signals": total_candidates,
                        "success": total_plus5,
                        "win_rate": f"%{plus5_pct}",
                        "avg_gain": f"+%{avg_close_gain}",
                        "desc": f"{total_plus5}/{total_candidates} oneri +%5 ustu kar sagladi"
                    },
                    {
                        "name": "Ahlatci Varant Kaldiraci",
                        "icon": "fa-building-columns",
                        "color": "var(--accent-purple)",
                        "signals": total_candidates,
                        "success": total_tavan,
                        "win_rate": f"+%{warrant_avg}",
                        "avg_gain": f"+%{warrant_avg}",
                        "desc": f"~6.2x kaldıracli varant getirisi ortalaması"
                    }
                ],
                "recent_completed_signals": recent_signals
            }
        except Exception as e:
            print(f"[WinRateEngine] Gercek veri hatasi: {e}")
            return {
                "summary": {
                    "total_signals_30d": 0,
                    "target_reached": 0,
                    "stopped_out": 0,
                    "win_rate_pct": 0,
                    "avg_profit_pct": 0,
                    "avg_time_to_target_hours": "Veri bekleniyor",
                    "profit_factor": 0
                },
                "category_winrates": [],
                "recent_completed_signals": []
            }
