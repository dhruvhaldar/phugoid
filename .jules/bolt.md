## 2026-04-05 - Direct Array Indexing over Sequence Unpacking
**Learning:** In tight numerical loops like `equations_of_motion`, duck-typed sequence unpacking (`try...except` combined with `type()` checks) introduces constant overhead on every call. For highly optimized paths, direct index access combined with explicit `float()` casting is faster, forces fast C-level scalar math operations, and natively supports both native Python lists and NumPy arrays without instantiation overhead.
**Action:** Use direct indexing and explicit casting (e.g., `float(state[0])`) over sequence unpacking or dynamic type checking in hot loops to improve performance.

## 2026-04-09 - Flat Tuples over Nested Lists for Matrix Solvers
**Learning:** In highly repetitive custom numerical solver loops (like `TrimSolver`'s Newton-Raphson `solve_3x3` and `jacobian`), allocating, returning, and accessing nested lists (e.g., `[[a, b, c], [d, e, f]]`) adds measurable memory allocation overhead and repeated index lookup overhead. Returning and accepting flat tuples (e.g., `(a, b, c, d, e, f)`) avoids this instantiation penalty completely and enables extremely fast flat unpacking (`a, b, c, d, e, f = A`) in hot paths.
**Action:** Use flat tuples and flat index-unpacking instead of nested lists for small fixed-size data structures (like 3x3 matrices) inside tight numerical loops.
