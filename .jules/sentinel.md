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

## 2026-10-29 - DoS Risk via Unbounded Numerical Inputs
**Vulnerability:** The `AnalysisRequest` API model lacked an upper bound for `velocity`, unlike the `TrimRequest` model. This allowed attackers to submit extremely large values (e.g., `1e100`), potentially causing numerical instability, infinite loops in solvers, or resource exhaustion (DoS) in the `TrimSolver`.
**Learning:** Inconsistent validation logic across similar API endpoints is a common source of security gaps. "Defense in Depth" requires that all entry points enforce the same strict constraints on domain-specific inputs.
**Prevention:** Added `le=1000` (max 1000 m/s) to the `velocity` field in `AnalysisRequest`, aligning it with `TrimRequest` and enforcing physical realism.

## 2026-11-01 - DoS Risk via Chunked Transfer Encoding Bypass
**Vulnerability:** The existing `RequestSizeLimitMiddleware` only protected against large requests by checking the `Content-Length` header. However, if an attacker uses `Transfer-Encoding: chunked`, they can bypass the `Content-Length` check entirely. Since the HTTP spec dictates `Content-Length` must be ignored when chunked encoding is present, a malicious actor can stream an unbounded amount of data (or large padding payloads) slowly over time. The application endpoints attempt to read and process the entire request body before acting, leading to resource exhaustion, memory exhaustion, or timeouts.
**Learning:** `Content-Length` size limits are ineffective on their own if `Transfer-Encoding: chunked` is supported but not constrained. When processing purely structural API inputs (like a JSON payload of numbers) that do not require continuous streaming logic, the safest defense is to reject chunked requests explicitly.
**Prevention:** Updated `RequestSizeLimitMiddleware` to explicitly reject any requests with `transfer-encoding: chunked` by returning a `411 Length Required` response. This enforces that all payloads must have a known, bounded length upfront that can be safely verified against the 1 MB limit before any body parsing occurs.

## 2026-11-02 - Missing Security Headers on Early Error Responses
**Vulnerability:** The application was not applying security headers (like `Content-Security-Policy`, `X-Frame-Options`, `Strict-Transport-Security`, etc.) to HTTP responses that were generated early by other middleware (e.g., `413 Payload Too Large` from `RequestSizeLimitMiddleware` or `429 Too Many Requests` from `RateLimitMiddleware`).
**Learning:** In FastAPI (and Starlette), `app.add_middleware()` wraps the existing application stack. This means middleware is executed in the *reverse* order of how it is added. If a security headers middleware is not added *last*, earlier middlewares can intercept the request and return a response that bypasses the security headers logic, leading to inconsistent security postures for error responses.
**Prevention:** Ensured `SecureHeadersMiddleware` is added last in `api/index.py` using `app.add_middleware(SecureHeadersMiddleware)`, making it the outermost layer that wraps all other middlewares and route handlers.

## 2026-11-03 - DoS Risk via Unbounded Aircraft Parameters
**Vulnerability:** The `AircraftParameters` Pydantic model lacked upper bounds (`le`) for core geometry and mass properties (`mass`, `S`, `b`, `c`), although it properly restricted values to be strictly positive (`gt=0`). Attackers could exploit this by submitting extremely large physical parameters (e.g., `mass=1e300`), allowing these values to bypass initial request validation and be fed into the `TrimSolver`, leading to numerical overflow (`inf`), unexpected calculation failures, and possible resource exhaustion.
**Learning:** In numerical analysis endpoints, variables must have both a lower and upper bound corresponding to realistic physical constraints to prevent solver instability. Merely checking for positiveness (`gt=0`) is insufficient. Inconsistent bounds modeling across endpoints is a recurring DoS vector.
**Prevention:** Updated `AircraftParameters` to implement sensible upper bounds (`le`) for all geometric and mass inputs (e.g., `mass <= 100000.0`, `S <= 1000.0`). Included an automated test `test_input_validation_mass_and_geometry_limits` in the test suite to ensure Pydantic actively prevents excessively large structural values from reaching downstream numerical solvers.
