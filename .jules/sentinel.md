## 2026-10-25 - [Security Enhancement] Strengthen CORS and Security Headers
**Vulnerability:** The application had an overly permissive CORS configuration (`allow_headers=["*"]`) and was missing strict HTTPS enforcement directives (`upgrade-insecure-requests` in CSP and `preload` in HSTS).
**Learning:** Even when core application security (rate limiting, validation) is robust, outer-layer HTTP security middleware must be strictly configured according to the Principle of Least Privilege. Allowing wildcard CORS headers introduces unnecessary attack surfaces.
**Prevention:** Always restrict `allow_headers` in `CORSMiddleware` to the minimum necessary set (e.g., `["Content-Type"]`), and ensure robust HTTPS mechanisms (`HSTS preload` and `CSP upgrade-insecure-requests`) are present in `SecureHeadersMiddleware`.

## 2026-10-25 - [Security Enhancement] Add Security Event Logging to API Middlewares
**Vulnerability:** The API middlewares (RateLimiting, RequestSizeLimiting) were silently rejecting malicious or malformed requests (e.g., DoS attempts via chunked encoding or oversized payloads, rate limit violations) without logging the events, leading to a lack of observability for security monitoring and attack detection.
**Learning:** Silently failing on security boundaries prevents administrators from detecting active attacks or misconfigured clients. Security controls like rate limiters and payload size limits should always log when they trigger, including relevant context like the client IP and requested path.
**Prevention:** Always include logging statements (e.g., `logger.warning`) in middleware exception paths or early return blocks that handle security violations or input rejections.

## 2026-10-25 - [High] Prevent DOM XSS via InnerHTML
**Vulnerability:** The vanilla JavaScript frontend (`public/main.js`) used `.innerHTML` with string concatenation to render lists of dynamically fetched stability modes.
**Learning:** Using `.innerHTML` when handling API responses (even numbers that appear safe) violates defense-in-depth and establishes dangerous patterns that can lead to Cross-Site Scripting (XSS).
**Prevention:** Always use safe DOM manipulation methods (`document.createElement()`, `textContent`, and `.appendChild()`) for dynamically updating the DOM to eliminate arbitrary HTML injection vectors.

## 2026-10-25 - [Security Enhancement] Enforce Cross-Origin Isolation via COEP
**Vulnerability:** The application partially implemented Cross-Origin Isolation by setting `Cross-Origin-Opener-Policy: same-origin` but missed the `Cross-Origin-Embedder-Policy: require-corp` header. This left the application partially exposed to side-channel attacks (like Spectre) since the browser requires both headers to enable full cross-origin isolation.
**Learning:** Full cross-origin isolation (which enables features like `SharedArrayBuffer` and mitigates side-channel attacks) requires a pair of headers: COOP and COEP. Implementing only one is insufficient.
**Prevention:** When implementing security headers for cross-origin boundaries, ensure both COOP and COEP are verified together as part of the security header suite.

## 2026-10-26 - [High] Fix Rate Limiting Bypass via Payload Size Rejection
**Vulnerability:** The order of middlewares in `api/index.py` caused `RequestSizeLimitMiddleware` to run *before* `RateLimitMiddleware`. Consequently, if an attacker sent requests with oversized payloads (triggering a 413 response) or chunked transfer encoding (triggering a 411 response), the request was rejected early and never reached the rate limiter. This allowed an attacker to infinitely spam the server with oversized requests without being rate limited, causing excessive CPU usage and Disk Exhaustion (DoS via log forging).
**Learning:** In FastAPI, `app.add_middleware()` executes custom middlewares in reverse order of addition. Security controls must be layered such that defensive mechanisms like rate limiters run as early as possible in the request pipeline.
**Prevention:** Always order `app.add_middleware()` calls so that `RateLimitMiddleware` wraps inner size/content limiters, ensuring early rejections are still counted against an IP's rate limit.

## 2026-10-26 - [Medium] Fix Log Forging vulnerability
**Vulnerability:** The API middlewares (`RequestSizeLimitMiddleware` and `RateLimitMiddleware`) logged the requested path (`request.url.path`) directly into the logs without escaping newline characters when rejecting bad payloads or rate limiting requests.
**Learning:** An attacker can send malicious requests containing CRLF characters in the path, allowing them to forge fake log entries (Log Forging / CRLF Injection).
**Prevention:** Always sanitize user-controlled data before logging it. Wrapping the variable in `repr(str(...))` effectively escapes control characters (like `\n` and `\r`) before they are written to the log.

## 2026-10-26 - [Medium] Fix incomplete Log Forging prevention
**Vulnerability:** While `request.url.path` was previously sanitized with `repr(str())` to prevent CRLF injection, other user-controlled data such as `request.headers.get("content-length")` and `client_ip` (extracted from `X-Forwarded-For`) were still being logged directly via f-strings.
**Learning:** Any data extracted from HTTP requests (headers, query parameters, IP addresses) can be spoofed or manipulated by an attacker to include control characters like `\n` or `\r`. Fixing one log variable is insufficient if others remain unprotected.
**Prevention:** Always apply consistent sanitization (e.g., `repr(str(...))`) to ALL variables containing client-provided data before passing them to logging functions.

## 2026-10-26 - [Medium] Missing Logging for Validation Errors
**Vulnerability:** The application was not logging `RequestValidationError` exceptions, silently dropping invalid payloads and malformed data without creating an audit trail.
**Learning:** Request validation errors are often the first sign of an attacker probing the API surface, fuzzing endpoints, or attempting payload-based attacks. Silently dropping these requests without logging creates a lack of observability and prevents security monitoring tools from detecting malicious activity.
**Prevention:** Always log request validation failures (e.g., using `logger.warning`) as Security Events, ensuring that relevant context like the client IP and requested path are included and properly sanitized to prevent log forging.

## 2026-10-26 - [Medium] Centralize True Client IP Extraction
**Vulnerability:** The `RequestSizeLimitMiddleware` logged `request.client.host` directly instead of correctly extracting the true client IP from `X-Forwarded-For` proxy headers like Vercel, reducing observability. Other middlewares handled this manually, leading to duplicated and inconsistent security logic.
**Learning:** Security mechanisms relying on client context (like IP addresses for logging or rate limiting) must extract that context uniformly. Scattered, manual extraction often leads to oversights in some middlewares, blinding security monitoring when behind proxies.
**Prevention:** Implement and use a centralized utility function (e.g., `get_client_ip`) for extracting client context across all middlewares and exception handlers to ensure consistency and correctness.

## 2026-10-26 - [Security Enhancement] Prevent Rate Limit Time Skew Bypass
**Vulnerability:** The `RateLimitMiddleware` used `time.time()` to calculate rolling window expiration (e.g., `now - t < 60`). `time.time()` relies on the system clock, which can jump forwards or backwards due to NTP synchronization, leap seconds, or manual changes, potentially allowing an attacker to bypass rate limits or accidentally locking out legitimate users.
**Learning:** Security mechanisms relying on time intervals (like rate limiters or session timeouts) must be resilient to system clock variations.
**Prevention:** In security-sensitive time calculations, always use `time.monotonic()` instead of `time.time()` to guarantee a strictly increasing clock, preventing bypasses caused by system time adjustments.
