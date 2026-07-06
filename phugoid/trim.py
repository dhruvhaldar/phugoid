import numpy as np
import math
from phugoid.dynamics import equations_of_motion, longitudinal_equations_of_motion
from phugoid.atmosphere import atmosphere_scalar

_sin = math.sin
_cos = math.cos
_sqrt = math.sqrt

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
    a00, a01, a02, a10, a11, a12, a20, a21, a22 = A

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

    return x0, x1, x2

class TrimSolver:
    def __init__(self, aircraft):
        self.aircraft = aircraft

    def find_trim(self, velocity, altitude, flight_path_angle=0.0):
        """
        Finds the trim state for steady level flight (or steady climb/descent)
        using a custom Newton-Raphson solver to avoid SciPy dependency.
        """
        # Calculate atmosphere once, as altitude is constant during root-finding
        _, _, rho_val = atmosphere_scalar(altitude)

        # Pull these constants out to avoid lookups in the hot loop
        _ac = self.aircraft
        _leom = longitudinal_equations_of_motion

        def objective(alpha, elevator, throttle):
            theta = alpha + flight_path_angle
            u = velocity * _cos(alpha)
            w = velocity * _sin(alpha)

            # Optimization: Pass tuple directly to avoid list instantiation/mutation overhead
            state_tup = (u, 0.0, w, 0.0, 0.0, 0.0, 0.0, theta, 0.0, 0.0, 0.0, -altitude)
            control_tup = (elevator, 0.0, 0.0, throttle)

            derivs = _leom(0, state_tup, _ac, control_tup, rho=rho_val)
            return derivs[0], derivs[2], derivs[4], state_tup

        def jacobian(alpha, elevator, throttle, f0_0, f0_1, f0_2, state_tup0, eps=1e-5):
            inv_eps = 1.0 / eps

            # Inlined objective(alpha+eps)
            alpha_eps = alpha + eps
            theta_eps = alpha_eps + flight_path_angle
            u_eps = velocity * _cos(alpha_eps)
            w_eps = velocity * _sin(alpha_eps)
            state_tup_alpha = (u_eps, 0.0, w_eps, 0.0, 0.0, 0.0, 0.0, theta_eps, 0.0, 0.0, 0.0, -altitude)
            control_tup_alpha = (elevator, 0.0, 0.0, throttle)
            derivs0 = _leom(0, state_tup_alpha, _ac, control_tup_alpha, rho=rho_val)
            fp0_0, fp0_1, fp0_2 = derivs0[0], derivs0[2], derivs0[4]

            # Optimization: Use analytical derivatives for elevator and throttle
            # Both are linear in the longitudinal equations of motion.
            # This avoids 2 expensive calls to _leom per jacobian evaluation.

            # Elevator analytical derivatives
            V_sq = state_tup0[0]*state_tup0[0] + state_tup0[2]*state_tup0[2]
            if V_sq < 0.01:
                V_sq = 0.01
                inv_V = 10.0
            else:
                inv_V = 1.0 / _sqrt(V_sq)

            s_alpha = state_tup0[2] * inv_V
            c_alpha = state_tup0[0] * inv_V

            q_bar_S = 0.5 * rho_val * V_sq * _ac.S
            inv_m = _ac.inv_mass

            # Analytical partial derivatives with respect to elevator deflection (delta_e):
            # d(udot)/de = q_bar_S / m * (CL_de * sin(alpha) - CD_de * cos(alpha))
            # d(wdot)/de = q_bar_S / m * (-CL_de * cos(alpha) - CD_de * sin(alpha))
            # d(qdot)/de = q_bar_S * c * Cm_de / Iyy
            # Note: For this aerodynamic model, CD_alpha exists but CD_de is not explicitly modeled (CD_de = 0).
            # The simplified equations in longitudinal_equations_of_motion use CD = CD0 + CD_alpha * abs(alpha),
            # so CD does not change with delta_e.

            j_elev_0 = q_bar_S * _ac.CL_de * s_alpha * inv_m
            j_elev_1 = -q_bar_S * _ac.CL_de * c_alpha * inv_m
            j_elev_2 = q_bar_S * _ac.c * _ac.Cm_de * _ac.inv_Iyy

            # Throttle analytical derivatives
            # d(udot)/dth = 2000.0 * (rho / 1.225) / m
            j_throt_0 = 2000.0 * (rho_val / 1.225) * inv_m
            j_throt_1 = 0.0
            j_throt_2 = 0.0

            # Pack fast tuple directly
            J = (
                (fp0_0 - f0_0) * inv_eps, j_elev_0, j_throt_0,
                (fp0_1 - f0_1) * inv_eps, j_elev_1, j_throt_1,
                (fp0_2 - f0_2) * inv_eps, j_elev_2, j_throt_2
            )

            return J

        # Custom Newton-Raphson solver
        alpha, elevator, throttle = 0.05, -0.05, 0.5
        max_iter = 100
        tol = 1e-8
        success = False

        tol_sq = tol * tol
        for i in range(max_iter):
            f0_0, f0_1, f0_2, state_tup0 = objective(alpha, elevator, throttle)
            # Optimization: avoid _sqrt during error check for speed
            # error = _sqrt(f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2)
            if (f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2) < tol_sq:
                success = True
                break
                
            J = jacobian(alpha, elevator, throttle, f0_0, f0_1, f0_2, state_tup0)
            try:
                # Solve J * dx = -f0
                dx0, dx1, dx2 = solve_3x3(J, (-f0_0, -f0_1, -f0_2))
                # Damping factor to prevent divergence
                alpha += 0.5 * dx0
                elevator += 0.5 * dx1
                throttle += 0.5 * dx2
                
                # Constrain throttle between 0 and 1
                if throttle < 0.0: throttle = 0.0
                elif throttle > 1.0: throttle = 1.0
            except SingularMatrixError:
                break

        if not success:
            # Try alternate guess
            alpha, elevator, throttle = 0.1, -0.1, 0.8
            for i in range(max_iter):
                f0_0, f0_1, f0_2, state_tup0 = objective(alpha, elevator, throttle)
                # Optimization: avoid _sqrt during error check for speed
                if (f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2) < tol_sq:
                    success = True
                    break
                    
                J = jacobian(alpha, elevator, throttle, f0_0, f0_1, f0_2, state_tup0)
                try:
                    dx0, dx1, dx2 = solve_3x3(J, (-f0_0, -f0_1, -f0_2))
                    alpha += 0.5 * dx0
                    elevator += 0.5 * dx1
                    throttle += 0.5 * dx2

                    if throttle < 0.0: throttle = 0.0
                    elif throttle > 1.0: throttle = 1.0
                except SingularMatrixError:
                    break

                    
            if not success:
                error = _sqrt(f0_0*f0_0 + f0_1*f0_1 + f0_2*f0_2)
                raise RuntimeError(f"Trim solver failed to converge. Final error: {error}")

        alpha_trim, elevator_trim, throttle_trim = alpha, elevator, throttle
        theta_trim = alpha_trim + flight_path_angle
        u_trim = velocity * np.cos(alpha_trim)
        w_trim = velocity * np.sin(alpha_trim)

        return TrimState(alpha_trim, elevator_trim, throttle_trim, u_trim, w_trim, theta_trim, velocity, altitude)
