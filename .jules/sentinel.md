## 2026-05-20 - Information Disclosure via Unhandled Exceptions
**Vulnerability:** API endpoints were catching generic `Exception` and returning `str(e)` in the HTTP 400 response. This exposed internal error details (e.g., from SciPy solvers) to the client.
**Learning:** In scientific applications using complex libraries (like SciPy/NumPy), internal errors can be verbose and reveal implementation details or stack traces if not sanitized.
**Prevention:** Catch specific exceptions (e.g., `ValueError`, `RuntimeError`) for expected failures and return sanitized messages. For unexpected exceptions, log the error and return a generic 500 'Internal Server Error'.

## 2026-06-19 - Incomplete Security Headers
**Vulnerability:** HTTP security headers were manually implemented and incomplete, leaving gaps (HSTS, Referrer-Policy, object-src).
**Learning:** The project relies on a custom `SecureHeadersMiddleware` in `api/index.py` which requires manual updates for new headers.
**Prevention:** Maintain a comprehensive list of headers in this middleware or migrate to a dedicated library.
