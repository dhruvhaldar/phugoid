## 2024-05-22 - [Optimizing Scalar Paths in Scientific Python]
**Learning:** High-frequency physics functions (like atmosphere models) called within solvers often receive scalar inputs. Defaulting to NumPy array conversion for "vectorization" adds massive overhead (10-50x) for these scalar calls.
**Action:** Always check `isinstance(x, (int, float))` and implement a pure Python path for scalars in core physics functions.

## 2024-05-23 - [Redundant Physics Calculations in Solvers]
**Learning:** Numerical solvers (like `scipy.optimize.root` or custom Jacobian estimators) often call physics functions repeatedly with partially identical inputs (e.g., varying state but keeping altitude constant). Stateless physics functions re-calculate expensive environment data (atmosphere) unnecessarily.
**Action:** Use `@lru_cache` on pure functions that depend on environment variables (like altitude) to memoize results across solver iterations, especially for finite difference calculations.

## 2026-XX-XX - [Numpy Overhead on Scalar Math]
**Learning:** `np.clip` and `np.arcsin` (and other ufuncs) carry significant overhead (10-20x) when applied to scalar inputs compared to Python built-ins or `math` module functions. This is critical in tight loops like `equations_of_motion`.
**Action:** For scalar-heavy paths, explicitly check for scalar types and use `math` module functions or Python logic instead of numpy ufuncs.

## 2026-XX-XX - [Optimizing equations_of_motion]
**Learning:** `equations_of_motion` is a hotspot called thousands of times. Replacing `numpy` ufuncs with `math` module functions for scalar inputs (detected via `np.ndim(state) == 1`) improved performance by ~28% (35us -> 25us per call).
**Action:** Use conditional dispatch based on `np.ndim` to support both scalar (fast) and vector (compatible) paths in core physics functions.

## 2026-XX-XX - [Avoiding Array Creation in Solvers]
**Learning:** Creating `np.array` from scalar values in a tight loop (like in `TrimSolver` objective function) has noticeable overhead (~1.3us). Passing Python lists instead avoids this.
Additionally, `np.ndim(list)` is significantly slower (~7us) than `np.ndim(array)` (~0.1us).
By constructing lists in the solver and avoiding `np.ndim` checks on lists (via `isinstance`), we can achieve ~4x speedup in dynamics calls within the solver.
**Action:** In iterative solvers, construct and pass Python lists for state/control vectors if the underlying physics function supports list inputs efficiently. Optimize physics functions to check `isinstance(x, (list, tuple))` before calling `np.ndim`.

## 2026-XX-XX - [Return Type Optimization in Scalar Paths]
**Learning:** In tight loops (like TrimSolver), avoiding the conversion of result lists back to `np.ndarray` saves ~1.5us per call (~18% speedup). However, this changes the return type based on input type (List -> List, Array -> Array), which is a potential API hazard.
**Action:** When implementing this optimization, ensure the caller (e.g. Solver) handles the list return type (e.g. via unpacking) and explicitly document the behavior in the function docstring.

## 2026-XX-XX - [Numpy Scalar Overhead in Core Physics Loop]
**Learning:** Lists containing Numpy scalars (e.g. `[np.float64(0.0), ...]`) passed to physics functions defeat `math` module optimizations because `type(np.float64) is not float` (though `isinstance` passes). Explicitly converting these to native `float` using list comprehension yields ~30-40% speedup in `equations_of_motion`.
**Action:** In core physics loops, add a fast check (e.g. `type(state[0]) is not float`) and convert inputs to native floats immediately if detected. Ensure return type semantics (Array vs List) are preserved to avoid breaking callers.
