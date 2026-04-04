from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import time
import hashlib
import secrets
from collections import defaultdict
import numpy as np
import os
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer
from phugoid.modes import calculate_damping_ratio, calculate_natural_frequency

app = FastAPI()

# Global storage for rate limiting (IP -> list of timestamps)
request_counts = defaultdict(list)

# Generate a random salt on startup for IP hashing to prevent rainbow table attacks
IP_HASH_SALT = secrets.token_hex(16)

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1 MB limit (1 * 1024 * 1024 bytes)
        if "chunked" in request.headers.get("transfer-encoding", "").lower():
            # If chunked encoding, we cannot determine content length beforehand,
            # so we reject it to avoid memory exhaustion DOS.
            return JSONResponse(status_code=411, content={"detail": "Length Required"})

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > 1048576:
                    return JSONResponse(status_code=413, content={"detail": "Payload Too Large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        # Handle X-Forwarded-For for proxies (like Vercel)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Vercel appends the client IP to the end of the list.
            # We take the last IP to prevent spoofing by clients adding their own headers.
            client_ip = forwarded.split(",")[-1].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Hash the client IP with a salt to prevent storing PII in memory and thwart rainbow table attacks
        salted_ip = f"{client_ip}:{IP_HASH_SALT}"
        client_ip_hash = hashlib.sha256(salted_ip.encode("utf-8")).hexdigest()

        now = time.time()
        # Clean up old timestamps (older than 60s)
        # Handle LRU: Remove from dict to re-insert at end if exists
        if client_ip_hash in request_counts:
            timestamps = request_counts.pop(client_ip_hash)
        else:
            timestamps = []

        # Filter timestamps
        timestamps = [t for t in timestamps if now - t < 60]

        # Check limit (100 requests per minute)
        if len(timestamps) >= 100:
            # Re-insert before returning
            request_counts[client_ip_hash] = timestamps
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": "60"}
            )

        timestamps.append(now)
        request_counts[client_ip_hash] = timestamps

        # Basic cleanup to prevent memory exhaustion from IP spoofing
        # Evict oldest entries (LRU) instead of clearing all
        while len(request_counts) > 10000:
            try:
                # Remove the first item (oldest insertion)
                request_counts.pop(next(iter(request_counts)))
            except StopIteration:
                break

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
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

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

        # Prevent caching of sensitive calculation results
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"

        return response

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecureHeadersMiddleware)

# Security Enhancement: CORSMiddleware is added LAST so it becomes the outermost
# middleware (wrapping all others). This ensures CORS headers are correctly applied
# even to early error responses (e.g., 429 Too Many Requests, 413 Payload Too Large)
# generated by the inner middlewares, preventing the browser from hiding the true status code.
# It also allows preflight OPTIONS requests to be intercepted immediately, preventing
# them from inadvertently exhausting user rate limits.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class AircraftParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Core Geometry & Mass
    mass: float = Field(1111.0, gt=0, le=100000.0, description="Mass in kg (must be positive)", allow_inf_nan=False)
    S: float = Field(16.2, gt=0, le=1000.0, description="Wing Area in m^2 (must be positive)", allow_inf_nan=False)
    b: float = Field(11.0, gt=0, le=100.0, description="Wing Span in m (must be positive)", allow_inf_nan=False)
    c: float = Field(1.47, gt=0, le=50.0, description="Mean Aerodynamic Chord in m (must be positive)", allow_inf_nan=False)

    # Stability Derivatives
    CL_alpha: float = Field(4.58, ge=-1000.0, le=1000.0, allow_inf_nan=False)
    Cm_alpha: float = Field(-0.9, ge=-1000.0, le=1000.0, allow_inf_nan=False)
    Cm_q: float = Field(-12.4, ge=-1000.0, le=1000.0, allow_inf_nan=False)
    Cm_de: float = Field(-1.28, ge=-1000.0, le=1000.0, allow_inf_nan=False)

    # Other coefficients can be added here
    CL0: float = Field(0.3, ge=-1000.0, le=1000.0, allow_inf_nan=False)
    CD0: float = Field(0.03, ge=-1000.0, le=1000.0, allow_inf_nan=False)
    Cm0: float = Field(-0.02, ge=-1000.0, le=1000.0, allow_inf_nan=False)

class TrimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    velocity: float = Field(..., gt=0, le=1000, description="Velocity in m/s (must be positive, max 1000)", allow_inf_nan=False)
    altitude: float = Field(..., ge=-500, le=50000, description="Altitude in meters", allow_inf_nan=False)
    flight_path_angle: float = Field(0.0, ge=-90.0, le=90.0, allow_inf_nan=False)
    aircraft: Optional[AircraftParameters] = None

class TrimResponse(BaseModel):
    alpha_deg: float
    elevator_deg: float
    throttle: float
    theta_deg: float
    u: float
    w: float

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    velocity: float = Field(..., gt=0, le=1000, description="Velocity in m/s (must be positive, max 1000)", allow_inf_nan=False)
    altitude: float = Field(..., ge=-500, le=50000, description="Altitude in meters", allow_inf_nan=False)
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
    except ValueError as e:
        # Handle ValueError, e.g. for invalid arguments to math functions internally
        print(f"Trim Value Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid mathematical operation during calculation.")
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
    except ValueError as e:
        print(f"Analysis Value Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid mathematical operation during analysis.")
    except Exception as e:
        print(f"Internal Error in /api/analyze: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")

if os.path.exists("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="public")
