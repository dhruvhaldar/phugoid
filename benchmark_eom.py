import timeit
import numpy as np
from phugoid.dynamics import equations_of_motion
from phugoid.aerodynamics import Cessna172

aircraft = Cessna172()
state = [50.0, 0.0, 2.0, 0.0, 0.05, 0.0, 0.1, 0.1, 0.0, 0.0, 0.0, -1000.0]
control = [0.05, 0.0, 0.0, 0.5]

def run_eom():
    equations_of_motion(0, state, aircraft, control)

# Warmup
run_eom()

t = timeit.timeit(run_eom, number=10000)
print(f"10k calls: {t:.4f} s")
print(f"Per call: {t/10000*1e6:.2f} us")
