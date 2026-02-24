from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_cache_control_header():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "Cache-Control" in response.headers
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert "Pragma" in response.headers
    assert response.headers["Pragma"] == "no-cache"

def test_inf_params_rejected():
    # Aircraft with inf mass
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "mass": "inf"
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "finite_number"

def test_nan_params_rejected():
    # Aircraft with nan CL_alpha
    payload = {
        "velocity": 100,
        "altitude": 1000,
        "aircraft": {
            "CL_alpha": "nan"
        }
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "finite_number"
