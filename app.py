import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import datetime

app = FastAPI(title="FuelPass Estimator")
templates = Jinja2Templates(directory="templates")

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
    estimated_cost_zar: float
    notes: str = ""

def estimate_fuel_liters_internal(year, engine_l, distance_km, body_type, route, driving_style):
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

    current_year = datetime.datetime.now().year
    extra = 0.0
    if year is not None:
        age = current_year - int(year)
        if age > 10:
            extra = 1.0 + min((age - 10) * 0.1, 1.5)
    consumption = base + extra

    if body_type and body_type.lower() in ("suv","pickup","truck"):
        consumption += 1.8
    elif body_type and body_type.lower() in ("van",):
        consumption += 1.2

    if route and route.lower() in ("highway","hwy","motorway"):
        consumption *= 0.85
    elif route and route.lower() in ("city","urban"):
        consumption *= 1.12

    if driving_style and driving_style.lower() in ("aggressive","fast"):
        consumption *= 1.15
    elif driving_style and driving_style.lower() in ("eco","gentle","calm"):
        consumption *= 0.95

    l_per_100km = round(consumption, 2)
    best = distance_km * l_per_100km / 100.0
    min_l = best * 0.88
    max_l = best * 1.12
    return round(best,2), round(min_l,2), round(max_l,2), l_per_100km

@app.post("/estimate", response_model=EstimateResponse)
def estimate(req: EstimateRequest):
    best, mn, mx, l_per_100 = estimate_fuel_liters_internal(
        year=req.year,
        engine_l=req.engine_l,
        distance_km=req.distance_km,
        body_type=req.body_type,
        route=req.route,
        driving_style=req.driving_style
    )
    estimated_cost = best * req.fuel_price
    notes = "Heuristic demo estimator. For licensing, production rules may differ."
    return EstimateResponse(
        best_liters=best,
        min_liters=mn,
        max_liters=mx,
        l_per_100km=l_per_100,
        estimated_cost_zar=round(estimated_cost, 2),
        notes=notes
    )

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
