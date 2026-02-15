## 2024-05-22 - [Optimizing Scalar Paths in Scientific Python]
**Learning:** High-frequency physics functions (like atmosphere models) called within solvers often receive scalar inputs. Defaulting to NumPy array conversion for "vectorization" adds massive overhead (10-50x) for these scalar calls.
**Action:** Always check `isinstance(x, (int, float))` and implement a pure Python path for scalars in core physics functions.
