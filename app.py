import os
import logging
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 🔒 Logging setup
logging.basicConfig(level=logging.INFO)

# 🔑 API Key Configuration
API_KEY = "fp_live_zeustech_fuelpass_2025"
REVOKED_KEYS = set()  # Add keys here to instantly block them

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in REVOKED_KEYS or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Access revoked or invalid API key")

# 🚦 Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="FuelPass Demo Estimator")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="."), name="static")

# Request and Response Models
class EstimateRequest(BaseModel):
    year: int
    engine_l: float
    distance_km: float
    body_type: str
    route: str
    driving_style: str

class EstimateResponse(BaseModel):
    best_liters: float
    min_liters: float
    max_liters: float
    l_per_100km: float
    deposit_best: float
    deposit_min: float
    deposit_max: float
    notes: str

@app.post("/estimate", response_model=EstimateResponse)
@limiter.limit("100/minute")
def estimate(req: EstimateRequest, api_key: str = Security(verify_api_key)):
    logging.info(f"Estimate request: {req.distance_km} km, body={req.body_type}, engine={req.engine_l}")
    
    # Simple heuristic demo calculation
    base = req.engine_l * req.distance_km * 0.07
    best = base
    mn = base * 0.9
    mx = base * 1.1
    l_per_100 = (base / req.distance_km) * 100

    fuel_price = 25.0  # placeholder price per liter
    deposit_best = round(best * fuel_price, 2)
    deposit_min = round(mn * fuel_price, 2)
    deposit_max = round(mx * fuel_price, 2)

    notes = "Heuristic demo estimator. For licensing, production rules may differ."

    return EstimateResponse(
        best_liters=round(best, 2),
        min_liters=round(mn, 2),
        max_liters=round(mx, 2),
        l_per_100km=round(l_per_100, 2),
        deposit_best=deposit_best,
        deposit_min=deposit_min,
        deposit_max=deposit_max,
        notes=notes
    )

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/terms", response_class=HTMLResponse)
async def terms():
    return """
    <html>
    <head><title>FuelPass API Terms</title></head>
    <body style="font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px;">
        <h1>FuelPass API Terms of Use</h1>
        <p>By using the FuelPass Estimator API, you agree to the following:</p>
        <ul>
            <li><strong>No reverse engineering:</strong> You may not attempt to copy, replicate, or derive the estimation logic.</li>
            <li><strong>No resale or sublicensing:</strong> API access is for your internal use only.</li>
            <li><strong>Payment:</strong> You agree to pay either:
                <ul>
                    <li>R10.00 per active user per month, OR</li>
                    <li>An upfront license fee of R500M–R1B as negotiated.</li>
                </ul>
            </li>
            <li><strong>Penalty for breach:</strong> Violation of these terms incurs a R1 billion penalty (per FuelPass Financial Gospel).</li>
        </ul>
        <p>This service is provided by ZeusTech (Pty) Ltd (CIPC Reg: 9444644352).</p>
    </body>
    </html>
    """

# For Render.com
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
