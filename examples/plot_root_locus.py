import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer

def plot_root_locus():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)

    velocities = np.linspace(40, 70, 10) # 40 m/s to 70 m/s
    altitude = 1524

    lon_roots = []
    lat_roots = []

    print("Calculating trim points...")
    for v in velocities:
        try:
            trim = solver.find_trim(v, altitude)
            lin = Linearizer(aircraft, trim)
            lon_roots.append(lin.get_longitudinal_modes())
            lat_roots.append(lin.get_lateral_modes())
        except Exception as e:
            print(f"Trim failed at {v} m/s: {e}")
            continue

    if not lon_roots:
        print("No valid trim points found.")
        return

    lon_roots = np.array(lon_roots)
    lat_roots = np.array(lat_roots)

    plt.figure(figsize=(10, 8))

    # Plot Longitudinal
    for i in range(4):
        plt.scatter(lon_roots[:, i].real, lon_roots[:, i].imag, label='Longitudinal' if i==0 else "", color='blue')

    # Plot Lateral
    for i in range(4):
        plt.scatter(lat_roots[:, i].real, lat_roots[:, i].imag, label='Lateral' if i==0 else "", color='red', marker='x')

    plt.axvline(0, color='k', linestyle='--')
    plt.axhline(0, color='k', linestyle='--')
    plt.xlabel('Real Axis (Sigma)')
    plt.ylabel('Imag Axis (j Omega)')
    plt.title(f'Root Locus vs Velocity ({velocities[0]:.1f}-{velocities[-1]:.1f} m/s)')
    plt.legend()
    plt.grid(True)
    plt.savefig('root_locus.png')
    print("Saved root_locus.png")

if __name__ == "__main__":
    plot_root_locus()
