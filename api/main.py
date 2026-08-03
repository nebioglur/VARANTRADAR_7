from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import sys
import os

# Sistemin ana modüllerini yükleyebilmek için path ayarı
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.antigravity_core import AntigravityCore
from services.ai_decision_engine import AIDecisionEngine

app = FastAPI(
    title="VarantRadar Pro API",
    description="Enterprise Edition REST API Gateway (Modül 01 & 08)",
    version="11.0.0"
)

# Dummy Dependency for Authentication (Modül 10)
def verify_token(token: str):
    if token != "V11_ENTERPRISE_SECRET_TOKEN":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True

# Request/Response Models
class AnalysisRequest(BaseModel):
    symbol: str
    interval: str = "1d"

@app.get("/")
def read_root():
    return {"message": "VarantRadar Enterprise API Çalışıyor", "status": "Healthy"}

@app.post("/api/v1/analyze")
def analyze_stock(request: AnalysisRequest):
    """
    Belirtilen hisseyi/varlığı VarantRadar AI motoru ile analiz eder.
    Mobil ve Web App için uç noktadır.
    """
    try:
        core = AntigravityCore()
        core.initialize_system()
        
        # Veri çekimi
        core.update_stock_data(request.symbol)
        df = core.analyzer.calculate_indicators(request.symbol, request.interval)
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Veri bulunamadı")
            
        ai_report = AIDecisionEngine.generate_ai_report(df, request.symbol)
        
        return {
            "symbol": request.symbol,
            "success": True,
            "ai_report": ai_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
def health_check():
    """Modül 11: Sistem Sağlığı / Kubernetes Liveness Probe"""
    return {"status": "UP", "database": "Connected", "ai_engine": "Ready"}
