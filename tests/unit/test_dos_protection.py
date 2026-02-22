from fastapi.testclient import TestClient
from api.index import app, request_counts
import time
import pytest

client = TestClient(app)

def test_rate_limiter_eviction_policy():
    """
    Test that the rate limiter evicts old entries instead of clearing everything
    when the limit (10,000 IPs) is reached.
    If clear() is used, size drops to 0 (or 1 if re-added).
    If eviction is used, size stays ~10,000.
    """
    # 1. Clear state
    request_counts.clear()

    # 2. Populate with 10,000 fake IPs
    # We simulate active users
    now = time.time()
    for i in range(10000):
        ip = f"192.168.0.{i}"
        request_counts[ip] = [now]

    assert len(request_counts) == 10000

    # 3. Add one more user (via request)
    # We use a header to simulate a new IP
    response = client.get("/api/health", headers={"X-Forwarded-For": "10.0.0.1"})
    assert response.status_code == 200

    # 4. Check size
    # If vulnerable: size == 0 (because clear() removes everything, including current user's entry)
    # If fixed: size == 10000 (1 evicted, 1 added) or close to it.

    current_size = len(request_counts)
    print(f"Size after request: {current_size}")

    # Assert that we DO NOT clear everyone.
    # We expect size to be maintained at 10000.
    # If clear() happened, size would be 0 (or 1 if logic was different).
    assert current_size >= 9999, f"Rate limiter cleared all users! Size dropped to {current_size}"


def test_rate_limit_bypass_via_spoofing():
    # Clear rate limits
    request_counts.clear()

    # Simulate a legitimate IP being rate limited
    real_ip = "203.0.113.1"

    # Fill up the rate limit for this IP
    # We use a mocked header where Vercel would append the real IP at the end
    # But the current implementation takes the FIRST IP.
    # So if we send "spoofed_ip, real_ip", it takes "spoofed_ip".

    # Let's say the attacker controls the first IP.
    # They send request 1 with "attacker_ip_1, real_ip"
    # They send request 2 with "attacker_ip_2, real_ip"
    # ...
    # This bypasses the rate limit for "real_ip" (or rather, they can make infinite requests).

    # Step 1: Prove we can bypass rate limit by changing the first IP
    # while coming from the same "real" connection (simulated by the last IP staying same).

    # Note: TestClient doesn't simulate the Vercel appending behavior automatically.
    # We must manually construct the header.

    # 105 requests with ROTATING first IP
    # The first 100 should succeed
    for i in range(100):
        spoofed_ip = f"192.168.1.{i}"
        headers = {"X-Forwarded-For": f"{spoofed_ip}, {real_ip}"}
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200, f"Request {i} failed unexpectedly"

    # The 101st request should be BLOCKED because the real IP is the same
    # regardless of the spoofed header at the start.
    spoofed_ip = "192.168.1.101"
    headers = {"X-Forwarded-For": f"{spoofed_ip}, {real_ip}"}
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 429, "Rate limit bypass via spoofing detected!"

def test_rate_limit_enforcement():
    request_counts.clear()
    ip = "10.0.0.1"
    headers = {"X-Forwarded-For": ip}

    # 100 allowed
    for _ in range(100):
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200

    # 101st blocked
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 429

def test_input_validation_velocity_limit():
    """Verify that extremely high velocities are rejected."""
    payload = {
        "velocity": 10000.0, # Too high
        "altitude": 1000.0
    }
    response = client.post("/api/trim", json=payload)
    assert response.status_code == 422 # Validation Error

    payload["velocity"] = 1000.0 # Max allowed
    # This might fail 422 if calculation fails, but Pydantic validation should pass.
    # However, TrimSolver might fail if other params are default.
    # We only care that it passed Pydantic.
    # If status code is 422 due to "calculation failed", details will be different.
    # Pydantic 422 has details about fields.

    response = client.post("/api/trim", json=payload)
    # Ideally it should be 200 or 422 with "Calculation failed" (RuntimeError)
    # But definitely NOT 422 with "Field required" or "Input should be less than..."
    if response.status_code == 422:
        error_detail = response.json()["detail"]
        # If it's a validation error, detail is a list. If Runtime error, it's a string.
        if isinstance(error_detail, list):
             # Ensure it's not about velocity being too high
             for err in error_detail:
                 if "velocity" in err["loc"]:
                     assert False, f"Velocity 1000 should be valid but got error: {err}"
