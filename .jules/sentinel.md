## 2026-05-20 - Information Disclosure via Unhandled Exceptions
**Vulnerability:** API endpoints were catching generic `Exception` and returning `str(e)` in the HTTP 400 response. This exposed internal error details (e.g., from SciPy solvers) to the client.
**Learning:** In scientific applications using complex libraries (like SciPy/NumPy), internal errors can be verbose and reveal implementation details or stack traces if not sanitized.
**Prevention:** Catch specific exceptions (e.g., `ValueError`, `RuntimeError`) for expected failures and return sanitized messages. For unexpected exceptions, log the error and return a generic 500 'Internal Server Error'.

## 2024-05-23 - Missing Validation on Physical Model Parameters
**Vulnerability:** The `AircraftParameters` model allowed physically impossible values (e.g., negative mass, negative wing area) to be passed to the backend. This could cause the numerical solvers (`scipy.optimize.root`) to fail in unpredictable ways, potentially leading to resource exhaustion or undefined behavior.
**Learning:** Scientific code often assumes "sane" inputs, but when exposed via an API, these assumptions become attack vectors. Pydantic models with default values are easy to leave unvalidated.
**Prevention:** Explicitly define physical constraints (e.g., `gt=0` for mass/lengths) using `Field` in Pydantic models. Treat physical constants as user input when they can be overridden via the API.
