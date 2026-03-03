import time
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer

ac = Cessna172()
solver = TrimSolver(ac)

start = time.perf_counter()
for _ in range(1000):
    trim = solver.find_trim(velocity=50.0, altitude=1000.0)
end = time.perf_counter()
print(f"TrimSolver 1000 runs: {end - start:.4f} seconds")

start = time.perf_counter()
for _ in range(1000):
    lin = Linearizer(ac, trim)
end = time.perf_counter()
print(f"Linearizer 1000 runs: {end - start:.4f} seconds")
