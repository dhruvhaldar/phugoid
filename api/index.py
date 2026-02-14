from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer
from phugoid.modes import calculate_damping_ratio, calculate_natural_frequency
import os
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# Security Middleware
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Strict CSP, but allowing 'unsafe-inline' for simple frontend scripts and styles
        # Also allowing Plotly and Three.js CDNs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.plot.ly https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        return response

app.add_middleware(SecureHeadersMiddleware)

class AircraftParameters(BaseModel):
    # Core Geometry & Mass
    mass: float = 1111.0
    S: float = 16.2
    b: float = 11.0
    c: float = 1.47

    # Stability Derivatives
    CL_alpha: float = 4.58
    Cm_alpha: float = -0.9
    Cm_q: float = -12.4
    Cm_de: float = -1.28

    # Other coefficients can be added here
    CL0: float = 0.3
    CD0: float = 0.03
    Cm0: float = -0.02

class TrimRequest(BaseModel):
    velocity: float = Field(..., gt=0, description="Velocity in m/s (must be positive)")
    altitude: float = Field(..., ge=-500, le=50000, description="Altitude in meters")
    flight_path_angle: float = 0.0
    aircraft: Optional[AircraftParameters] = None

class TrimResponse(BaseModel):
    alpha_deg: float
    elevator_deg: float
    throttle: float
    theta_deg: float
    u: float
    w: float

class AnalysisRequest(BaseModel):
    velocity: float = Field(..., gt=0, description="Velocity in m/s (must be positive)")
    altitude: float = Field(..., ge=-500, le=50000, description="Altitude in meters")
    aircraft: Optional[AircraftParameters] = None

class ModeData(BaseModel):
    real: float
    imag: float
    wn: float
    zeta: float

class AnalysisResponse(BaseModel):
    longitudinal: List[ModeData]
    lateral: List[ModeData]

# Default aircraft
default_aircraft = Cessna172()

def get_aircraft(params: Optional[AircraftParameters]):
    ac = Cessna172() # Start with default
    if params:
        # Update parameters
        for k, v in params.model_dump(exclude_none=True).items():
            setattr(ac, k, v)
    return ac

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/trim", response_model=TrimResponse)
def calculate_trim(req: TrimRequest):
    try:
        ac = get_aircraft(req.aircraft)
        solver = TrimSolver(ac)
        trim = solver.find_trim(req.velocity, req.altitude, req.flight_path_angle)
        return TrimResponse(
            alpha_deg=trim.alpha_deg,
            elevator_deg=trim.elevator_deg,
            throttle=trim.throttle,
            theta_deg=np.degrees(trim.theta),
            u=trim.u,
            w=trim.w
        )
    except RuntimeError as e:
        # Expected runtime errors like convergence failure
        print(f"Trim Runtime Error: {e}")
        raise HTTPException(status_code=422, detail="Calculation failed to converge. Please check your inputs.")
    except Exception as e:
        # Unexpected errors
        print(f"Internal Error in /api/trim: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_stability(req: AnalysisRequest):
    try:
        ac = get_aircraft(req.aircraft)
        solver = TrimSolver(ac)
        trim = solver.find_trim(req.velocity, req.altitude)
        lin = Linearizer(ac, trim)

        lon_modes = lin.get_longitudinal_modes()
        lat_modes = lin.get_lateral_modes()

        def format_modes(evals):
            modes = []
            for e in evals:
                wn = calculate_natural_frequency(e)
                zeta = calculate_damping_ratio(e)
                modes.append(ModeData(
                    real=float(e.real),
                    imag=float(e.imag),
                    wn=float(wn),
                    zeta=float(zeta)
                ))
            return modes

        return AnalysisResponse(
            longitudinal=format_modes(lon_modes),
            lateral=format_modes(lat_modes)
        )

    except RuntimeError as e:
        print(f"Analysis Runtime Error: {e}")
        raise HTTPException(status_code=422, detail="Calculation failed to converge. Please check your inputs.")
    except Exception as e:
        print(f"Internal Error in /api/analyze: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

if os.path.exists("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="public")
