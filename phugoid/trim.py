import numpy as np
import math
from phugoid.dynamics import equations_of_motion, longitudinal_equations_of_motion

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

class SingularMatrixError(Exception):
    pass

def solve_3x3(A, b):
    # Optimization: Explicitly solve 3x3 system without np.linalg.solve
    # np.linalg.solve adds significant overhead (~40-50%) in this tight loop
    # due to numpy array instantiation. Explicit calculation is ~6x faster.
    det = (A[0][0] * (A[1][1] * A[2][2] - A[1][2] * A[2][1]) -
           A[0][1] * (A[1][0] * A[2][2] - A[1][2] * A[2][0]) +
           A[0][2] * (A[1][0] * A[2][1] - A[1][1] * A[2][0]))

    if abs(det) < 1e-15:
        raise SingularMatrixError("Singular matrix")

    inv_det = 1.0 / det

    x0 = ((A[1][1] * A[2][2] - A[1][2] * A[2][1]) * b[0] +
          (A[0][2] * A[2][1] - A[0][1] * A[2][2]) * b[1] +
          (A[0][1] * A[1][2] - A[0][2] * A[1][1]) * b[2]) * inv_det

    x1 = ((A[1][2] * A[2][0] - A[1][0] * A[2][2]) * b[0] +
          (A[0][0] * A[2][2] - A[0][2] * A[2][0]) * b[1] +
          (A[0][2] * A[1][0] - A[0][0] * A[1][2]) * b[2]) * inv_det

    x2 = ((A[1][0] * A[2][1] - A[1][1] * A[2][0]) * b[0] +
          (A[0][1] * A[2][0] - A[0][0] * A[2][1]) * b[1] +
          (A[0][0] * A[1][1] - A[0][1] * A[1][0]) * b[2]) * inv_det

    return [x0, x1, x2]

class TrimSolver:
    def __init__(self, aircraft):
        self.aircraft = aircraft

    def find_trim(self, velocity, altitude, flight_path_angle=0.0):
        """
        Finds the trim state for steady level flight (or steady climb/descent)
        using a custom Newton-Raphson solver to avoid SciPy dependency.
        """
        def objective(x):
            alpha = float(x[0])
            elevator = float(x[1])
            throttle = float(x[2])

            theta = alpha + flight_path_angle
            u = velocity * math.cos(alpha)
            w = velocity * math.sin(alpha)

            # Optimization: pass lists of floats to avoid np.array overhead in tight loops
            state = [u, 0.0, w, 0.0, 0.0, 0.0, 0.0, theta, 0.0, 0.0, 0.0, -altitude]
            control = [elevator, 0.0, 0.0, throttle]

            derivs = longitudinal_equations_of_motion(0, state, self.aircraft, control)
            return [derivs[0], derivs[2], derivs[4]]

        def jacobian(x, eps=1e-5):
            f0 = objective(x)

            # Optimization: Use lists entirely instead of numpy arrays to avoid
            # constant-time instantiation overhead in this tight inner loop.
            x_plus0 = [x[0] + eps, x[1], x[2]]
            f_plus0 = objective(x_plus0)

            x_plus1 = [x[0], x[1] + eps, x[2]]
            f_plus1 = objective(x_plus1)

            x_plus2 = [x[0], x[1], x[2] + eps]
            f_plus2 = objective(x_plus2)

            # Construct row-major J for numpy solve
            J = [
                [(f_plus0[0] - f0[0]) / eps, (f_plus1[0] - f0[0]) / eps, (f_plus2[0] - f0[0]) / eps],
                [(f_plus0[1] - f0[1]) / eps, (f_plus1[1] - f0[1]) / eps, (f_plus2[1] - f0[1]) / eps],
                [(f_plus0[2] - f0[2]) / eps, (f_plus1[2] - f0[2]) / eps, (f_plus2[2] - f0[2]) / eps]
            ]

            return J, f0

        # Custom Newton-Raphson solver
        x = [0.05, -0.05, 0.5]
        max_iter = 100
        tol = 1e-8
        success = False

        for i in range(max_iter):
            J, f0 = jacobian(x)
            # Optimization: Use explicit multiplication instead of **2 for performance
            error = math.sqrt(f0[0]*f0[0] + f0[1]*f0[1] + f0[2]*f0[2])
            
            if error < tol:
                success = True
                break
                
            try:
                # Solve J * dx = -f0
                dx = solve_3x3(J, [-f0[0], -f0[1], -f0[2]])
                # Damping factor to prevent divergence
                x[0] += 0.5 * dx[0]
                x[1] += 0.5 * dx[1]
                x[2] += 0.5 * dx[2]
                
                # Constrain throttle between 0 and 1
                if x[2] < 0.0: x[2] = 0.0
                elif x[2] > 1.0: x[2] = 1.0
            except SingularMatrixError:
                break

        if not success:
            # Try alternate guess
            x = [0.1, -0.1, 0.8]
            for i in range(max_iter):
                J, f0 = jacobian(x)
                # Optimization: Use explicit multiplication instead of **2 for performance
                error = math.sqrt(f0[0]*f0[0] + f0[1]*f0[1] + f0[2]*f0[2])
                
                if error < tol:
                    success = True
                    break
                    
                try:
                    dx = solve_3x3(J, [-f0[0], -f0[1], -f0[2]])
                    x[0] += 0.5 * dx[0]
                    x[1] += 0.5 * dx[1]
                    x[2] += 0.5 * dx[2]

                    if x[2] < 0.0: x[2] = 0.0
                    elif x[2] > 1.0: x[2] = 1.0
                except SingularMatrixError:
                    break
                    
            if not success:
                raise RuntimeError(f"Trim solver failed to converge. Final error: {error}")

        alpha_trim, elevator_trim, throttle_trim = x[0], x[1], x[2]
        theta_trim = alpha_trim + flight_path_angle
        u_trim = velocity * np.cos(alpha_trim)
        w_trim = velocity * np.sin(alpha_trim)

        return TrimState(alpha_trim, elevator_trim, throttle_trim, u_trim, w_trim, theta_trim, velocity, altitude)
