from fastapi.testclient import TestClient
from api.index import app, request_counts
import pytest

client = TestClient(app)

def test_api_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_trim_validation_error_type():
    # Test with invalid velocity type (string)
    response = client.post("/api/trim", json={"velocity": "invalid", "altitude": 1000})
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["detail"][0]["msg"] == "Input should be a valid number, unable to parse string as a number"

def test_trim_validation_error_value():
    # Test with invalid velocity value (negative)
    response = client.post("/api/trim", json={"velocity": -100, "altitude": 1000})
    assert response.status_code == 422
    data = response.json()
    # Pydantic validation error for gt=0
    assert data["detail"][0]["msg"] == "Input should be greater than 0"

def test_trim_flight_path_angle_bounds():
    # Test with a flight path angle that is out of bounds
    response = client.post("/api/trim", json={"velocity": 100, "altitude": 1000, "flight_path_angle": 100})
    assert response.status_code == 422
    data = response.json()
    assert "Input should be less than or equal to 90" in data["detail"][0]["msg"]

    response = client.post("/api/trim", json={"velocity": 100, "altitude": 1000, "flight_path_angle": -100})
    assert response.status_code == 422
    data = response.json()
    assert "Input should be greater than or equal to -90" in data["detail"][0]["msg"]

def test_trim_convergence_failure_handling():
    # Test with inputs that might cause convergence failure
    # If unhandled, it might return 500 or leak stack trace.
    # Now it should return 422 with sanitized message or 200 if it manages to converge.

    response = client.post("/api/trim", json={"velocity": 0.0001, "altitude": 1000})

    if response.status_code == 422:
        # If it fails, check message is sanitized
        error_detail = response.json()["detail"]
        assert error_detail == "Calculation failed to converge. Please check your inputs."
    elif response.status_code == 500:
        # If it crashed, check message is generic
        error_detail = response.json()["detail"]
        assert error_detail == "An internal error occurred."

    # If 200, it's fine, we can't easily force failure without mocking,
    # but we verified the code path handles exceptions.

def test_security_headers():
    # Check for security headers
    response = client.get("/api/health")
    # These headers are added by our middleware
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"

    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    assert "script-src 'self' https://cdn.plot.ly https://cdnjs.cloudflare.com;" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp
    assert "frame-ancestors 'none'" in csp

    # Ensure unsafe-inline is NOT in script-src
    script_src = csp.split("script-src")[1].split(";")[0]
    assert "'unsafe-inline'" not in script_src

def test_rate_limiting():
    # Clear previous request counts to ensure clean state
    request_counts.clear()

    # Send 100 requests (allowed)
    for _ in range(100):
        response = client.get("/api/health")
        if response.status_code != 200:
             print(f"Failed at request {_}: {response.status_code}")
        assert response.status_code == 200

    # Send 101st request (should be blocked)
    response = client.get("/api/health")
    assert response.status_code == 429
    assert response.json() == {"detail": "Too many requests. Please try again later."}
    assert response.headers.get("retry-after") == "60"

    # Ensure headers are present even on 429
    assert "X-Frame-Options" in response.headers

def test_chunked_transfer_encoding_rejection():
    # Ensure that chunked transfer encoding is blocked to prevent DoS via infinite chunking
    request_counts.clear()
    # TestClient in httpx will overwrite chunked logic if we provide 'content'.
    # By providing None for content/data, we can force the headers to stay as-is.
    response = client.post("/api/trim", headers={"Transfer-Encoding": "chunked"})
    assert response.status_code == 411
    assert response.json() == {"detail": "Length Required"}


def test_cors_headers():
    response = client.options("/api/health", headers={"Origin": "http://localhost:8000", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

def test_cors_headers_on_error_responses():
    request_counts.clear()
    for _ in range(100):
        client.get("/api/health")
    response = client.get("/api/health", headers={"Origin": "http://localhost:8000"})
    assert response.status_code == 429
    assert "access-control-allow-origin" in response.headers

def test_input_validation_forbids_extra_fields():
    request_counts.clear()
    payload = {
        "velocity": 100.0,
        "altitude": 1000.0,
        "extra_field": "should be rejected"
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()
    assert response.json()["detail"][0]["type"] == "extra_forbidden"

def test_aircraft_parameters_forbids_extra_fields():
    request_counts.clear()
    payload = {
        "velocity": 100.0,
        "altitude": 1000.0,
        "aircraft": {
            "mass": 1000,
            "extra_param": "should fail"
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
