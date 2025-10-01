from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="FuelPass Demo Estimator")

# serve templates from templates/
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="."), name="static")

class EstimateRequest(BaseModel):
    year: int
    engine_l: float
    distance_km: float
    body_type: str
    route: str
    driving_style: str

@app.post("/estimate")
async def estimate(req: EstimateRequest):
    # simple heuristic demo calculation
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

    return {
        "best_liters": round(best, 2),
        "min_liters": round(mn, 2),
        "max_liters": round(mx, 2),
        "l_per_100km": round(l_per_100, 2),
        "deposit_best": deposit_best,
        "deposit_min": deposit_min,
        "deposit_max": deposit_max,
        "notes": notes
    }

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
