import sys
import os

# Add parent directory to path to import phugoid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer
from phugoid.modes import calculate_natural_frequency, calculate_damping_ratio

def analyze():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)

    velocity = 51.44 # 100 kts
    altitude = 1524 # 5000 ft

    print(f"Analyzing {aircraft.name} at V={velocity:.1f} m/s, h={altitude} m")

    try:
        trim = solver.find_trim(velocity, altitude)
    except Exception as e:
        print(f"Failed to trim: {e}")
        return

    print("-" * 40)
    print(f"Trim Alpha:    {trim.alpha_deg:.2f} deg")
    print(f"Trim Elevator: {trim.elevator_deg:.2f} deg")
    print(f"Trim Throttle: {trim.throttle:.2f}")
    print("-" * 40)

    lin = Linearizer(aircraft, trim)

    print("\nLongitudinal Modes:")
    evals = lin.get_longitudinal_modes()
    for i, e in enumerate(evals):
        wn = calculate_natural_frequency(e)
        zeta = calculate_damping_ratio(e)
        print(f"Mode {i+1}: {e.real:.4f} ± {abs(e.imag):.4f}j | Wn={wn:.4f}, Zeta={zeta:.4f}")

    print("\nLateral Modes:")
    evals = lin.get_lateral_modes()
    for i, e in enumerate(evals):
        wn = calculate_natural_frequency(e)
        zeta = calculate_damping_ratio(e)
        print(f"Mode {i+1}: {e.real:.4f} ± {abs(e.imag):.4f}j | Wn={wn:.4f}, Zeta={zeta:.4f}")

if __name__ == "__main__":
    analyze()
