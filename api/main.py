from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import logging
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

# Fail closed: the API token must be supplied by the deployment secret store.
_bearer = HTTPBearer(auto_error=True)
_allowed_origins = [origin.strip() for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
    from api.auth import is_valid_api_token
    if not is_valid_api_token(credentials.credentials):
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
def analyze_stock(request: AnalysisRequest, authorized: bool = Depends(verify_token)):
    """
    Belirtilen hisseyi/varlığı VarantRadar AI motoru ile analiz eder.
    Mobil ve Web App için uç noktadır.
    """
    try:
        if request.interval not in {"1m", "2m", "5m", "15m", "30m", "60m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}:
            raise HTTPException(status_code=422, detail="Unsupported interval")
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
    except HTTPException:
        raise
    except Exception:
        logging.exception("Analysis request failed")
        raise HTTPException(status_code=500, detail="Analysis request failed")

@app.get("/api/v1/health")
def health_check():
    """Modül 11: Sistem Sağlığı / Kubernetes Liveness Probe"""
    return {"status": "UP", "database": "not_checked", "ai_engine": "not_checked"}
