from fastapi.testclient import TestClient
from api.index import app
import pytest

client = TestClient(app)

def test_negative_mass_validation():
    # Attempt to send negative mass
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "mass": -100.0
        }
    }
    response = client.post("/api/trim", json=payload)

    # Assert that the API returns 422 Unprocessable Entity
    # This confirms that validation is working
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    # Check the error message
    detail = response.json().get("detail", [])
    assert any("Input should be greater than 0" in str(d) for d in detail), "Expected validation error for negative mass"

def test_zero_mass_validation():
    # Attempt to send zero mass
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "mass": 0.0
        }
    }
    response = client.post("/api/trim", json=payload)

    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    detail = response.json().get("detail", [])
    assert any("Input should be greater than 0" in str(d) for d in detail), "Expected validation error for zero mass"

def test_negative_geometry_validation():
    # Test wing area S
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "S": -16.2
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    detail = response.json().get("detail", [])
    assert any("Input should be greater than 0" in str(d) for d in detail), "Expected validation error for negative S"

    # Test wing span b
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "b": -11.0
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any("Input should be greater than 0" in str(d) for d in detail)

    # Test chord c
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "c": -1.47
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any("Input should be greater than 0" in str(d) for d in detail)
