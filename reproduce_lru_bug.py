import time
from collections import defaultdict

# Mock the logic from RateLimitMiddleware
request_counts = defaultdict(list)
MAX_ENTRIES = 5  # Small number for testing

def access(ip):
    now = time.time()
    # Logic from RateLimitMiddleware (Simulated)

    # Clean up (pop and re-insert?) - The original code pops!
    if ip in request_counts:
        timestamps = request_counts.pop(ip)
    else:
        timestamps = []

    timestamps = [t for t in timestamps if now - t < 60]

    if len(timestamps) >= 100:
        # Re-insert
        request_counts[ip] = timestamps
        return "429"

    timestamps.append(now)
    request_counts[ip] = timestamps

    # Eviction logic
    while len(request_counts) > MAX_ENTRIES:
        try:
            popped = next(iter(request_counts))
            request_counts.pop(popped)
            print(f"Evicted: {popped}")
        except StopIteration:
            break
    return "200"

print("--- Testing Current Implementation ---")
# Fill cache
for i in range(MAX_ENTRIES):
    access(f"ip_{i}")

print(f"Cache keys: {list(request_counts.keys())}")

# Access ip_0 again (should make it MRU)
print("Accessing ip_0 again...")
access("ip_0")
print(f"Cache keys: {list(request_counts.keys())}")

# Add new entry (should trigger eviction)
print("Adding ip_new...")
access("ip_new")
print(f"Cache keys: {list(request_counts.keys())}")

# Check if ip_0 is still there
if "ip_0" in request_counts:
    print("PASS: ip_0 was NOT evicted (LRU works)")
else:
    print("FAIL: ip_0 was evicted (FIFO behavior)")
