
import pytest
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_aircraft_mass_validation():
    # Test mass <= 0
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {"mass": 0}
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert "Input should be greater than 0" in response.text

    payload["aircraft"]["mass"] = -10
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422

def test_aircraft_geometry_validation():
    # Test S, b, c <= 0
    base_payload = {"velocity": 100, "altitude": 1000}

    # Wing Area S
    payload = base_payload.copy()
    payload["aircraft"] = {"S": 0}
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert "Input should be greater than 0" in response.text

    # Span b
    payload = base_payload.copy()
    payload["aircraft"] = {"b": -1}
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422

    # Chord c
    payload = base_payload.copy()
    payload["aircraft"] = {"c": 0}
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422

def test_drag_coefficient_validation():
    # Test CD0 < 0 (0 is allowed)
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {"CD0": -0.01}
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert "Input should be greater than or equal to 0" in response.text

    # Test CD0 = 0 (valid theoretical limit)
    payload["aircraft"]["CD0"] = 0
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 200

def test_analyze_endpoint_validation():
    # Ensure /api/analyze also validates aircraft parameters
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {"mass": -500}
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 422
