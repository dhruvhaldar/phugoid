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
