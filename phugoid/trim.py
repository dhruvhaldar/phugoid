import numpy as np
from scipy.optimize import root
from phugoid.dynamics import equations_of_motion

class TrimState:
    def __init__(self, alpha, elevator, throttle, u, w, theta, velocity, altitude):
        self.alpha = alpha
        self.elevator = elevator
        self.throttle = throttle
        self.u = u
        self.w = w
        self.theta = theta
        self.velocity = velocity
        self.altitude = altitude

        self.alpha_deg = np.degrees(alpha)
        self.elevator_deg = np.degrees(elevator)

class TrimSolver:
    def __init__(self, aircraft):
        self.aircraft = aircraft

    def find_trim(self, velocity, altitude, flight_path_angle=0.0):
        """
        Finds the trim state for steady level flight (or steady climb/descent).

        Args:
            velocity (float): True Airspeed [m/s]
            altitude (float): Altitude [m]
            flight_path_angle (float): Gamma [rad] (default 0 for level flight)

        Returns:
            TrimState: Object containing trim values.
        """

        # Unknowns: x = [alpha, elevator, throttle]

        def objective(x):
            alpha, elevator, throttle = x

            theta = alpha + flight_path_angle
            u = velocity * np.cos(alpha)
            w = velocity * np.sin(alpha)

            # State: [u, v, w, p, q, r, phi, theta, psi, x, y, z]
            # Optimization: Use list instead of np.array to avoid creation overhead
            # equations_of_motion handles lists efficiently now
            state = [u, 0, w, 0, 0, 0, 0, theta, 0, 0, 0, -altitude]
            # Control: [de, da, dr, dt]
            control = [elevator, 0, 0, throttle]

            derivs = equations_of_motion(0, state, self.aircraft, control)

            # We want udot, wdot, qdot to be zero (Longitudinal trim)
            return [derivs[0], derivs[2], derivs[4]]

        # Initial guess
        # Alpha usually small positive
        # Elevator usually small negative (to pitch up/balance nose heavy) or positive depending on sign convention.
        # Here elevator positive is usually TE down -> pitch down. C172 usually needs pitch up (negative elevator) if CG is fwd of AC.
        # Throttle 0.5
        x0 = [0.05, -0.05, 0.5]

        sol = root(objective, x0, method='hybr')

        if not sol.success:
             # Try another guess if first fails
            x0 = [0.1, -0.1, 0.8]
            sol = root(objective, x0, method='hybr')
            if not sol.success:
                raise RuntimeError("Trim solver failed to converge: " + sol.message)

        alpha_trim, elevator_trim, throttle_trim = sol.x
        theta_trim = alpha_trim + flight_path_angle
        u_trim = velocity * np.cos(alpha_trim)
        w_trim = velocity * np.sin(alpha_trim)

        return TrimState(alpha_trim, elevator_trim, throttle_trim, u_trim, w_trim, theta_trim, velocity, altitude)
