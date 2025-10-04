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