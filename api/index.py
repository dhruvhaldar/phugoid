from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import time
from collections import defaultdict
import numpy as np
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer
from phugoid.modes import calculate_damping_ratio, calculate_natural_frequency
import os
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# Global storage for rate limiting (IP -> list of timestamps)
request_counts = defaultdict(list)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        # Handle X-Forwarded-For for proxies (like Vercel)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_ip = forwarded.split(",")[0]
        else:
            client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        # Clean up old timestamps (older than 60s)
        # We only keep timestamps within the last 60 seconds
        request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < 60]

        # Check limit (100 requests per minute)
        if len(request_counts[client_ip]) >= 100:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})

        request_counts[client_ip].append(now)

        # Basic cleanup to prevent memory exhaustion from IP spoofing
        if len(request_counts) > 10000:
            request_counts.clear()

        return await call_next(request)

# Security Middleware
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Strict CSP, but allowing 'unsafe-inline' for simple frontend scripts and styles
        # Also allowing Plotly and Three.js CDNs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.plot.ly https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        return response

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecureHeadersMiddleware)

class AircraftParameters(BaseModel):
    # Core Geometry & Mass
    mass: float = Field(1111.0, gt=0, description="Mass in kg (must be positive)")
    S: float = Field(16.2, gt=0, description="Wing Area in m^2 (must be positive)")
    b: float = Field(11.0, gt=0, description="Wing Span in m (must be positive)")
    c: float = Field(1.47, gt=0, description="Mean Aerodynamic Chord in m (must be positive)")

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
