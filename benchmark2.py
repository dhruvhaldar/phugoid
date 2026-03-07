import time
from phugoid.trim import TrimSolver
from phugoid.aerodynamics import Cessna172

aircraft = Cessna172()
solver = TrimSolver(aircraft)

start = time.time()
for _ in range(1000):
    solver.find_trim(velocity=51.44, altitude=1524, flight_path_angle=0)
end = time.time()
print(f"TrimSolver 1000 runs: {end - start:.4f} seconds")
