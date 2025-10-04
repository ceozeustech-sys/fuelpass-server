import os
import datetime
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
REVOKED_KEYS = set()

api_key_header = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key in REVOKED_KEYS or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Access revoked or invalid API key")

# 🚦 Rate limiting setup
limiter = Limiter(key_func=get_remote_address)

# ✅ Create the FastAPI app
app = FastAPI(title="FuelPass Demo Estimator")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="."), name="static")

# Request and Response Models
class EstimateRequest(BaseModel):
    make: str = None
    year: int = None
    engine_l: float = None
    distance_km: float
    fuel_price: float
    body_type: str = "sedan"
    route: str = "mixed"
    driving_style: str = "normal"

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
def estimate(request: Request, req: EstimateRequest, api_key: str = Security(verify_api_key)):
    logging.info(f"Estimate request: {req.distance_km} km, body={req.body_type}, engine={req.engine_l}, fuel_price={req.fuel_price}")
    
    try:
        # Use defaults if optional fields are missing
        year = req.year
        engine_l = req.engine_l
        distance_km = float(req.distance_km)
        fuel_price = float(req.fuel_price)
        body_type = req.body_type or "sedan"
        route = req.route or "mixed"
        driving_style = req.driving_style or "normal"

        # 1) Base consumption
        if engine_l is None:
            base = 8.5
        else:
            if engine_l <= 1.2:
                base = 5.5
            elif engine_l <= 1.6:
                base = 6.5
            elif engine_l <= 2.0:
                base = 8.0
            elif engine_l <= 3.0:
                base = 10.0
            else:
                base = 13.0

        # 2) Age adjustment
        current_year = datetime.datetime.now().year
        extra = 0.0
        if year is not None:
            age = current_year - int(year)
            if age > 10:
                extra = 1.0 + min((age - 10) * 0.1, 1.5)
        consumption = base + extra

        # 3) Body type
        if body_type.lower() in ("suv", "pickup", "truck"):
            consumption += 1.8
        elif body_type.lower() in ("van",):
            consumption += 1.2

        # 4) Route adjustments
        if route.lower() in ("highway", "hwy", "motorway"):
            consumption *= 0.85
        elif route.lower() in ("city", "urban"):
            consumption *= 1.12

        # 5) Driving style
        if driving_style.lower() in ("aggressive", "fast"):
            consumption *= 1.15
        elif driving_style.lower() in ("eco", "gentle", "calm"):
            consumption *= 0.95

        l_per_100km = round(consumption, 2)
        best = distance_km * l_per_100km / 100.0
        min_l = best * 0.88
        max_l = best * 1.12

        deposit_best = round(best * fuel_price, 2)
        deposit_min = round(min_l * fuel_price, 2)
        deposit_max = round(max_l * fuel_price, 2)

        notes = "Heuristic demo estimator. For licensing, production rules may differ."

        return EstimateResponse(
            best_liters=round(best, 2),
            min_liters=round(min_l, 2),
            max_liters=round(max_l, 2),
            l_per_100km=l_per_100km,
            deposit_best=deposit_best,
            deposit_min=deposit_min,
            deposit_max=deposit_max,
            notes=notes
        )

    except Exception as e:
        logging.error(f"Estimate error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Invalid input: {str(e)}")

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