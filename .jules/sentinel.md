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
