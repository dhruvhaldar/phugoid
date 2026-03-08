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

    # Optimization: Flatten array access to avoid repeated nested indexing overhead
    a00, a01, a02 = A[0]
    a10, a11, a12 = A[1]
    a20, a21, a22 = A[2]

    # Pre-calculate common 2x2 determinants
    m11_22 = a11 * a22 - a12 * a21
    m10_22 = a10 * a22 - a12 * a20
    m10_21 = a10 * a21 - a11 * a20

    det = a00 * m11_22 - a01 * m10_22 + a02 * m10_21

    if abs(det) < 1e-15:
        raise SingularMatrixError("Singular matrix")

    inv_det = 1.0 / det

    b0, b1, b2 = b

    x0 = (m11_22 * b0 + (a02 * a21 - a01 * a22) * b1 + (a01 * a12 - a02 * a11) * b2) * inv_det
    x1 = (-m10_22 * b0 + (a00 * a22 - a02 * a20) * b1 + (a02 * a10 - a00 * a12) * b2) * inv_det
    x2 = (m10_21 * b0 + (a01 * a20 - a00 * a21) * b1 + (a00 * a11 - a01 * a10) * b2) * inv_det

    return [x0, x1, x2]

class TrimSolver:
    def __init__(self, aircraft):
        self.aircraft = aircraft

    def find_trim(self, velocity, altitude, flight_path_angle=0.0):
        """
        Finds the trim state for steady level flight (or steady climb/descent)
        using a custom Newton-Raphson solver to avoid SciPy dependency.
        """
        # Optimization: Pre-allocate state and control lists outside the hot objective loop
        # to avoid constant-time instantiation overhead on every function call.
        state = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -altitude]
        control = [0.0, 0.0, 0.0, 0.0]

        def objective(x):
            alpha = x[0]
            elevator = x[1]
            throttle = x[2]

            theta = alpha + flight_path_angle
            u = velocity * math.cos(alpha)
            w = velocity * math.sin(alpha)

            # Mutate pre-allocated lists instead of creating new ones
            state[0] = u
            state[2] = w
            state[7] = theta

            control[0] = elevator
            control[3] = throttle

            derivs = longitudinal_equations_of_motion(0, state, self.aircraft, control)
            return [derivs[0], derivs[2], derivs[4]]

        def jacobian(x, f0, eps=1e-5):
            # Optimization: Use lists entirely instead of numpy arrays to avoid
            # constant-time instantiation overhead in this tight inner loop.
            # Mutate state lists in-place for the perturbation to avoid array/list allocations.
            inv_eps = 1.0 / eps

            old_val = x[0]
            x[0] = old_val + eps
            f_plus0 = objective(x)
            x[0] = old_val

            old_val = x[1]
            x[1] = old_val + eps
            f_plus1 = objective(x)
            x[1] = old_val

            old_val = x[2]
            x[2] = old_val + eps
            f_plus2 = objective(x)
            x[2] = old_val

            # Optimization: Unpack f0 to avoid repeated index lookups
            f0_0, f0_1, f0_2 = f0[0], f0[1], f0[2]

            # Construct row-major J for numpy solve
            J = [
                [(f_plus0[0] - f0_0) * inv_eps, (f_plus1[0] - f0_0) * inv_eps, (f_plus2[0] - f0_0) * inv_eps],
                [(f_plus0[1] - f0_1) * inv_eps, (f_plus1[1] - f0_1) * inv_eps, (f_plus2[1] - f0_1) * inv_eps],
                [(f_plus0[2] - f0_2) * inv_eps, (f_plus1[2] - f0_2) * inv_eps, (f_plus2[2] - f0_2) * inv_eps]
            ]

            return J

        # Custom Newton-Raphson solver
        x = [0.05, -0.05, 0.5]
        max_iter = 100
        tol = 1e-8
        success = False

        for i in range(max_iter):
            f0 = objective(x)
            # Optimization: Use explicit multiplication instead of **2 for performance
            # Unpack to avoid multiple list lookups
            f0_0, f0_1, f0_2 = f0[0], f0[1], f0[2]
            error = math.sqrt(f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2)
            
            if error < tol:
                success = True
                break
                
            J = jacobian(x, f0)
            try:
                # Solve J * dx = -f0
                dx = solve_3x3(J, [-f0_0, -f0_1, -f0_2])
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
                f0 = objective(x)
                # Optimization: Use explicit multiplication instead of **2 for performance
                f0_0, f0_1, f0_2 = f0[0], f0[1], f0[2]
                error = math.sqrt(f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2)
                
                if error < tol:
                    success = True
                    break
                    
                J = jacobian(x, f0)
                try:
                    dx = solve_3x3(J, [-f0_0, -f0_1, -f0_2])
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
