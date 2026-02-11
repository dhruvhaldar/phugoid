import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.dynamics import equations_of_motion

def simulate():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)

    velocity = 51.44
    altitude = 1524

    print("Calculating trim...")
    trim = solver.find_trim(velocity, altitude)

    # Define simulation time
    t_span = (0, 120) # 120 seconds to see Phugoid
    t_eval = np.linspace(0, 120, 1200)

    # Initial state (Trim)
    state0 = np.array([
        trim.u, 0, trim.w,
        0, 0, 0,
        0, trim.theta, 0,
        0, 0, -trim.altitude
    ])

    # Control Input (Pulse elevator input at t=5s)
    def control_input(t):
        de = trim.elevator
        da = 0
        dr = 0
        dt = trim.throttle

        if t > 5.0 and t < 7.0:
            de -= np.radians(2.0) # Pull up (negative elevator) for 2 seconds

        return np.array([de, da, dr, dt])

    def dynamics(t, state):
        ctrl = control_input(t)
        return equations_of_motion(t, state, aircraft, ctrl)

    print("Simulating...")
    sol = solve_ivp(dynamics, t_span, state0, t_eval=t_eval, method='RK45')

    if not sol.success:
        print("Simulation failed:", sol.message)
        return

    # Extract results
    u = sol.y[0]
    w = sol.y[2]
    theta = sol.y[7]
    alt = -sol.y[11]

    V = np.sqrt(u**2 + w**2)
    alpha = np.arctan2(w, u)

    # Plot
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

    axs[0].plot(sol.t, V)
    axs[0].set_ylabel('Velocity (m/s)')
    axs[0].grid(True)

    axs[1].plot(sol.t, np.degrees(alpha))
    axs[1].set_ylabel('Alpha (deg)')
    axs[1].grid(True)

    axs[2].plot(sol.t, alt)
    axs[2].set_ylabel('Altitude (m)')
    axs[2].set_xlabel('Time (s)')
    axs[2].grid(True)

    plt.suptitle('Response to Elevator Pulse (Phugoid Excitation)')
    plt.savefig('simulation.png')
    print("Saved simulation.png")

if __name__ == "__main__":
    simulate()
