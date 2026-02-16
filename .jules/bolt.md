## 2024-05-22 - [Optimizing Scalar Paths in Scientific Python]
**Learning:** High-frequency physics functions (like atmosphere models) called within solvers often receive scalar inputs. Defaulting to NumPy array conversion for "vectorization" adds massive overhead (10-50x) for these scalar calls.
**Action:** Always check `isinstance(x, (int, float))` and implement a pure Python path for scalars in core physics functions.

## 2024-05-23 - [Redundant Physics Calculations in Solvers]
**Learning:** Numerical solvers (like `scipy.optimize.root` or custom Jacobian estimators) often call physics functions repeatedly with partially identical inputs (e.g., varying state but keeping altitude constant). Stateless physics functions re-calculate expensive environment data (atmosphere) unnecessarily.
**Action:** Use `@lru_cache` on pure functions that depend on environment variables (like altitude) to memoize results across solver iterations, especially for finite difference calculations.

## 2026-XX-XX - [Numpy Overhead on Scalar Math]
**Learning:** `np.clip` and `np.arcsin` (and other ufuncs) carry significant overhead (10-20x) when applied to scalar inputs compared to Python built-ins or `math` module functions. This is critical in tight loops like `equations_of_motion`.
**Action:** For scalar-heavy paths, explicitly check for scalar types and use `math` module functions or Python logic instead of numpy ufuncs.
