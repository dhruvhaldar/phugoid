## 2024-05-22 - Optimizing Scalar Operations in Solvers
**Learning:** The `phugoid.atmosphere` function was unnecessarily converting scalar inputs to NumPy arrays, causing ~80% overhead in hot paths (trim solver, linearization).
**Action:** Always check if a function used in inner loops handles scalar inputs efficiently without vectorization overhead.
