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

## 2026-11-04 - HTTP Request Smuggling DoS Bypass via Transfer-Encoding and Content-Length
**Vulnerability:** The `RequestSizeLimitMiddleware` checked `Content-Length` before `Transfer-Encoding: chunked`. By sending both headers (with a small, valid `Content-Length`), an attacker could bypass the chunked check entirely. The server would read the message as chunked, allowing unbounded payloads and causing resource exhaustion (DoS).
**Learning:** In HTTP/1.1, `Transfer-Encoding: chunked` overrides `Content-Length` (RFC 7230). Middleware MUST check `Transfer-Encoding` independently and preferably first to prevent smuggling bypasses.
**Prevention:** Modified `RequestSizeLimitMiddleware` to check for `chunked` in `Transfer-Encoding` first and immediately reject it, before parsing or considering `Content-Length`. Added a test to verify requests containing both headers are still rejected.

## 2026-11-05 - Missing Cross-Origin Resource Sharing (CORS) Policy
**Vulnerability:** The FastAPI application lacked an explicitly defined CORS policy, leading to default browser restrictions that block external web applications from invoking the API, or potentially allowing overly permissive default behavior depending on the framework's fallback.
**Learning:** Public or semi-public API endpoints require an explicit `CORSMiddleware` configuration to explicitly declare allowed origins, methods, and headers, preventing unauthorized cross-origin access and mitigating potential CSRF/XSS exploitation vectors if authentication were added.
**Prevention:** Added `CORSMiddleware` explicitly configured to allow local frontend origins (`allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"]`), ensuring maximum compatibility while maintaining strict control over allowed HTTP methods and headers.

## 2026-11-06 - Information Disclosure via Unhandled ValueError
**Vulnerability:** The `/api/trim` and `/api/analyze` endpoints were missing explicit exception handling for `ValueError` which can occur internally during mathematical operations (e.g. invalid arguments to math functions in downstream solvers). Previously, these would be caught by the generic `Exception` handler, which logged the error and returned a generic 500 'Internal Server Error', or worse, potentially expose error details.
**Learning:** Mathematical applications relying heavily on NumPy/SciPy or complex numerical solvers should explicitly handle `ValueError` and other domain-specific exceptions, distinguishing them from unexpected internal 500 errors to provide sanitized, context-appropriate 400 Bad Request responses.
**Prevention:** Added explicit `except ValueError as e:` blocks to both `/api/trim` and `/api/analyze` endpoints. This ensures numerical evaluation errors return a sanitized 400 "Invalid mathematical operation during calculation/analysis." message, preventing generic 500 failures and ensuring graceful error handling.

## 2026-11-07 - Missing CORS Headers on Early Error Responses and Preflight Rate Limiting
**Vulnerability:** `CORSMiddleware` was added first, making it the innermost middleware. This caused early error responses (429 Too Many Requests, 413 Payload Too Large) to lack CORS headers, breaking client-side error handling by hiding the true HTTP status code behind a generic CORS error. Furthermore, preflight `OPTIONS` requests were being inappropriately processed by the `RateLimitMiddleware`, counting towards user rate limits and opening a minor DoS vector.
**Learning:** In FastAPI/Starlette, `app.add_middleware()` adds middlewares in reverse execution order (last added = outermost). `CORSMiddleware` must be added *last* so it acts as the outermost middleware, enabling it to handle preflight requests immediately and ensure CORS headers are correctly applied to all responses, including errors generated by other nested security middlewares.
**Prevention:** Moved `CORSMiddleware` to be the last middleware added, ensuring it wraps the entire application stack including security, rate limiting, and size limit middlewares.
