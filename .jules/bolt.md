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

## 2026-XX-XX - [Unpacking Numpy Arrays for Scalar Math]
**Learning:** Directly unpacking a 1D NumPy array into variables (e.g., `u, v, w = state`) creates NumPy scalars, which are significantly slower in subsequent math operations than native Python floats. Converting the array to a list first (`state = state.tolist()`) before unpacking ensures that the variables are native floats, avoiding this overhead and improving performance by ~25% in hot paths like `equations_of_motion`.
**Action:** When optimizing scalar paths for functions that accept NumPy arrays, convert 1D arrays to lists using `.tolist()` immediately before unpacking and processing.

## 2026-XX-XX - [Optimizing Kinematic Equations]
**Learning:** Kinematic equations involving Euler angles often contain redundant trigonometric terms. By pre-calculating common terms (e.g., `r_rotated = q * sin(phi) + r * cos(phi)`) and using algebraic substitutions (e.g., deriving `phi_dot` from `psi_dot`), we can reduce the number of expensive multiplications and divisions, yielding measurable performance improvements.
**Action:** Analyze mathematical equations for common sub-expressions and algebraic simplifications, especially in high-frequency physics loops.

## 2026-02-17 - [Optimizing Euclidean Norm in Python]
**Learning:** In Python 3.12+, `math.hypot(x, y, z)` is slightly slower (~37%) than `math.sqrt(x*x + y*y + z*z)` for scalar inputs, likely due to internal overflow checks. Additionally, calculating `V**2` using `pow(V, 2)` is significantly slower (~2x) than simple multiplication `V*V` or reusing the squared sum from the norm calculation.
**Action:** When computing magnitude and its square (e.g., for dynamic pressure `0.5 * rho * V**2`), calculate `V_sq = sum(x**2)` first, then `V = sqrt(V_sq)`, and use `V_sq` directly to avoid the expensive `pow` call.

## 2026-02-17 - [Avoiding NumPy Array Construction in Tight Numerical Solver Loops]
**Learning:** Inside numerical solvers like a Newton-Raphson scheme in `TrimSolver`, constructing and returning intermediate `numpy.ndarray` vectors (like state vectors and derivative arrays) on every iteration carries significant constant-time instantiation overhead. This overhead adds up when solving small state dimensions ($N=3$). Returning raw Python `list`s out of the objective function and explicitly assigning elements into Jacobian matrix columns bypasses this instantiation overhead.
**Action:** For $N \le 3$ inner loops of a numerical solver, return and pass around Python `list` objects instead of `np.array` across boundaries when vectorization gains are outweighed by instantiation costs. Cast back to `np.array` *only* before calling `np.linalg.solve`.
## 2026-02-28 - [Optimizing Body-to-NED Position Rate Translations]
**Learning:** The calculation of NED position rates (`x_dot`, `y_dot`, `z_dot`) in `equations_of_motion` involves a large sequence of multiplications computing the full 3D rotation matrix natively. Translating velocities by undoing Roll, Pitch, and Yaw via chained 2D-like transformations successively reduces the math operations from 15 multiplications / 6 additions to 9 multiplications / 4 additions, yielding an isolated ~35% performance uplift without changing output values.
**Action:** When rotating vectors across 3D coordinate frames inside hot paths, prefer applying chained sequential single-axis transformations mathematically over building/multiplying through fully unrolled multi-axis 3x3 rotation matrices.

## 2026-03-10 - [Avoiding NumPy Array Construction in Small Objective Function Jacobians]
**Learning:** Returning scalar NumPy arrays or allocating zeros arrays (`np.zeros((3, 3))`) to build Jacobians inside tight inner-loops (like `TrimSolver`'s Newton-Raphson $N \le 3$ loop) adds roughly 40-50% constant-time overhead. By changing the loop logic to use pure Python nested lists and explicitly updating `x` dynamically without NumPy operations (e.g., `x[0] += dx[0]`), performance dramatically improves because it bypasses the object instantiation.
**Action:** When working on numerical solvers iterating over very small dimensions (e.g., $N \le 3$), avoid allocating NumPy arrays inside the objective or Jacobian function calculations; formulate everything around standard Python lists, calling `np.linalg.solve` explicitly with lists.

## 2026-03-22 - [Optimizing Explicit Matrix Inverse Calculations in Python]
**Learning:** Inside small pure-Python solver loops (like Cramer's rule for `solve_3x3`), repeated multi-dimensional array access (e.g., `A[1][2]`) and recalculating identical 2x2 determinant blocks incurs high constant-time overhead.
**Action:** Unpack elements into flat local variables (e.g., `a10, a11, a12 = A[1]`) immediately, and pre-calculate any repeated intermediate mathematical expressions (like `m11_22 = a11 * a22 - a12 * a21`). This avoids repeated index lookups and redundant floating-point math, leading to almost a ~1.75x speedup for the explicit solver function itself.

## 2026-03-25 - [Optimizing Python Exponentiation]
**Learning:** In Python, the built-in exponentiation operator `**` carries significant overhead compared to `math.pow()` for non-integer powers, likely due to additional checks and dynamic type handling. Benchmarks show `math.pow(base, exp)` is roughly 40% faster than `base ** exp` for floating-point calculations.
**Action:** In core physics loops (like atmosphere models or equations of motion), use `math.pow()` instead of `**` when calculating powers with float exponents, ensuring to alias the function (e.g., `_pow = math.pow`) at the module level for maximum performance.
## 2026-03-04 - [Avoiding Redundant Jacobian Calculations in Custom Solvers]
**Learning:** In custom Newton-Raphson solvers (like `TrimSolver`), evaluating the base objective function (`f0`) inside the Jacobian calculation function means that the Jacobian and its expensive finite difference perturbations (e.g., `f_plus0`, `f_plus1`) will be evaluated even on the final, converged iteration where the error is below tolerance and the loop will immediately break.
**Action:** Extract the base objective function evaluation (`f0`) to the main solver loop, evaluate convergence, and only pass `f0` into the Jacobian function if a new iteration is actually required. This skips the final unnecessary Jacobian calculation, saving multiple objective function calls.
