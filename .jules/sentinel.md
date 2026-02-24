## 2026-05-20 - Information Disclosure via Unhandled Exceptions
**Vulnerability:** API endpoints were catching generic `Exception` and returning `str(e)` in the HTTP 400 response. This exposed internal error details (e.g., from SciPy solvers) to the client.
**Learning:** In scientific applications using complex libraries (like SciPy/NumPy), internal errors can be verbose and reveal implementation details or stack traces if not sanitized.
**Prevention:** Catch specific exceptions (e.g., `ValueError`, `RuntimeError`) for expected failures and return sanitized messages. For unexpected exceptions, log the error and return a generic 500 'Internal Server Error'.

## 2026-06-19 - Incomplete Security Headers
**Vulnerability:** HTTP security headers were manually implemented and incomplete, leaving gaps (HSTS, Referrer-Policy, object-src).
**Learning:** The project relies on a custom `SecureHeadersMiddleware` in `api/index.py` which requires manual updates for new headers.
**Prevention:** Maintain a comprehensive list of headers in this middleware or migrate to a dedicated library.

## 2026-07-15 - DoS Risk via Unprotected Computation Endpoints
**Vulnerability:** The `/api/trim` and `/api/analyze` endpoints perform computationally expensive operations (e.g., `TrimSolver`, `Linearizer`) without rate limiting, allowing trivial DoS attacks.
**Learning:** In-memory rate limiting using Python's `BaseHTTPMiddleware` and `defaultdict` is a viable, dependency-free stopgap, but it scales poorly (per-instance state) and has potential memory leak risks (unbounded IP keys).
**Prevention:** Implemented `RateLimitMiddleware` with periodic size-based cleanup. Future scaling should move state to Redis. Middleware ordering is critical: rate limiting must happen *before* heavy processing but should still allow security headers on 429 responses.

## 2026-08-27 - Rate Limit Bypass via Memory Clearing
**Vulnerability:** The in-memory rate limiter's cleanup strategy (`request_counts.clear()` when size > 10000) allowed attackers to reset all rate limits by flooding the system with spoofed IPs, enabling a complete bypass of protection or DoS.
**Learning:** Naive "flush all" cache eviction strategies in security controls create critical bypass vectors. Rate limiters must degrade gracefully (e.g., LRU eviction) rather than failing open or resetting state globally.
**Prevention:** Replaced `clear()` with an iterative LRU eviction policy that removes only the oldest entries while preserving active user history.

## 2026-10-26 - Rate Limit Bypass via IP Spoofing
**Vulnerability:** The rate limiter extracted the client IP using `forwarded.split(",")[0]`, which takes the *first* IP in the `X-Forwarded-For` header. This allowed attackers to bypass rate limits by injecting a fake IP at the start of the header (e.g., `X-Forwarded-For: <fake>, <real>`).
**Learning:** Naive parsing of `X-Forwarded-For` is a common pitfall. Trusting the first IP assumes the client is honest or the header was stripped by a trusted perimeter. In cloud environments like Vercel, the real client IP (or the last trusted proxy) is appended to the *end* of the list.
**Prevention:** Changed extraction logic to use the *last* IP (`forwarded.split(",")[-1].strip()`) which represents the immediate connection to the trusted proxy/edge, preventing client-side spoofing.

## 2026-10-27 - Subresource Integrity (SRI) for CDN Assets
**Vulnerability:** CDN-hosted scripts (`plotly.min.js`, `three.min.js`) were included without integrity checks, allowing potential XSS if the CDN provider is compromised or a man-in-the-middle attack modifies the response.
**Learning:** Trusting third-party CDNs blindly violates "Defense in Depth". Even reputable CDNs can serve malicious content if their infrastructure is breached.
**Prevention:** Added `integrity` (SRI hash) and `crossorigin="anonymous"` attributes to all external script tags to ensure browsers verify the file content matches the expected hash before execution.

## 2026-10-28 - DoS and Undefined Behavior via Non-Finite Floating Point Inputs
**Vulnerability:** The API accepted `Infinity` and `NaN` values for floating-point fields (e.g., `flight_path_angle`, `CL_alpha`) in Pydantic models. These values propagated to the backend physics engine (`phugoid.dynamics`), causing unhandled exceptions (500 Internal Server Error) or `NaN` poisoning of calculation results.
**Learning:** Python's `float` type includes `inf` and `nan`, and Pydantic V2 allows them by default unless explicitly restricted. Mathematical applications must rigorously sanitize numerical inputs to ensure finiteness.
**Prevention:** Updated all critical Pydantic fields to use `Field(..., allow_inf_nan=False)` and added comprehensive unit tests to reject non-finite inputs with a 422 Unprocessable Entity error.
