with open("api/index.py", "r") as f:
    content = f.read()

# FastAPI adds middleware in reverse order (Last added = Outermost).
# So the execution flow goes from bottom to top of the add_middleware calls.
# Currently:
# 4. RateLimitMiddleware (added 1st = Innermost)
# 3. RequestSizeLimitMiddleware (added 2nd)
# 2. SecureHeadersMiddleware (added 3rd)
# 1. CORSMiddleware (added 4th = Outermost)

# To make RateLimitMiddleware OUTERMOST (after CORS), we need to add it LAST.
# Or, if we want RateLimit to run BEFORE RequestSizeLimit, we need to add RateLimit AFTER RequestSizeLimit.

# We want:
# 1. CORS
# 2. SecureHeaders
# 3. RateLimit
# 4. RequestSizeLimit (Innermost)

# So the order of addition should be:
# 1. RequestSizeLimit (added first = innermost)
# 2. RateLimit
# 3. SecureHeaders
# 4. CORS

old = """
# RateLimitMiddleware is added outermost (before SecureHeaders) to wrap inner middlewares
# ensuring early rejections (like 413 Payload Too Large) are still rate-limited.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(SecureHeadersMiddleware)
"""

new = """
# RequestSizeLimitMiddleware is the innermost custom middleware
app.add_middleware(RequestSizeLimitMiddleware)

# RateLimitMiddleware wraps RequestSizeLimitMiddleware so that if a payload
# is rejected early (e.g. 413 or 411), the request still counts towards the IP's rate limit.
app.add_middleware(RateLimitMiddleware)

# SecureHeadersMiddleware wraps both, ensuring security headers are set on all responses,
# including 429 Too Many Requests and 413 Payload Too Large.
app.add_middleware(SecureHeadersMiddleware)
"""

if old in content:
    content = content.replace(old, new)
    with open("api/index.py", "w") as f:
        f.write(content)
    print("Fixed order.")
else:
    print("Old string not found.")
