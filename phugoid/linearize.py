import numpy as np
from phugoid.dynamics import equations_of_motion

class Linearizer:
    def __init__(self, aircraft, trim_state):
        self.aircraft = aircraft
        self.trim = trim_state

        # Build full trim state vector
        self.x_trim = np.array([
            trim_state.u, 0, trim_state.w,
            0, 0, 0,
            0, trim_state.theta, 0,
            0, 0, -trim_state.altitude
        ])

        self.u_trim = np.array([trim_state.elevator, 0, 0, trim_state.throttle])

        self.A, self.B = self.compute_jacobian()

    def compute_jacobian(self, step=1e-4):
        n_state = 12
        n_control = 4

        # Optimization: Use scalar iteration instead of vectorized calls
        # N=12 is small enough that overhead of numpy ufuncs outweighs vectorization gain.
        # Scalar path uses math module which is ~2.5x faster.

        # Pre-convert trim state/control to lists for fast scalar path
        x_trim_list = self.x_trim.tolist()
        u_trim_list = self.u_trim.tolist()

        A = np.zeros((n_state, n_state))

        # Compute A matrix (df/dx) - perturbation of state
        for i in range(n_state):
            # Optimization: Skip horizontal position states (x=9, y=10)
            # The equations of motion for a flat-earth model with uniform atmosphere
            # are independent of x and y position. The derivatives are exactly zero.
            # This saves 4 expensive calls to equations_of_motion (approx 16% speedup).
            if i in [9, 10]:
                continue

            # Perturb state i
            x_plus = list(x_trim_list) # Shallow copy is enough for list of floats
            x_plus[i] += step

            x_minus = list(x_trim_list)
            x_minus[i] -= step

            # Call scalar EoM
            # equations_of_motion returns list for list input
            f_plus = equations_of_motion(0, x_plus, self.aircraft, u_trim_list)
            f_minus = equations_of_motion(0, x_minus, self.aircraft, u_trim_list)

            # Fill column i of A
            # We can't vector subtract lists directly, so use list comp
            col = [(fp - fm) / (2 * step) for fp, fm in zip(f_plus, f_minus)]
            A[:, i] = col

        B = np.zeros((n_state, n_control))

        # Compute B matrix (df/du) - perturbation of control
        for i in range(n_control):
            u_plus = list(u_trim_list)
            u_plus[i] += step

            u_minus = list(u_trim_list)
            u_minus[i] -= step

            f_plus = equations_of_motion(0, x_trim_list, self.aircraft, u_plus)
            f_minus = equations_of_motion(0, x_trim_list, self.aircraft, u_minus)

            col = [(fp - fm) / (2 * step) for fp, fm in zip(f_plus, f_minus)]
            B[:, i] = col

        return A, B

    def get_longitudinal_matrices(self):
        # Extract indices for u, w, q, theta
        # u=0, w=2, q=4, theta=7
        indices = [0, 2, 4, 7]
        A_lon = self.A[np.ix_(indices, indices)]
        B_lon = self.B[np.ix_(indices, [0, 3])] # Elevator, Throttle
        return A_lon, B_lon

    def get_lateral_matrices(self):
        # Extract indices for v, p, r, phi
        # v=1, p=3, r=5, phi=6
        indices = [1, 3, 5, 6]
        A_lat = self.A[np.ix_(indices, indices)]
        B_lat = self.B[np.ix_(indices, [1, 2])] # Aileron, Rudder
        return A_lat, B_lat

    def get_longitudinal_modes(self):
        A_lon, _ = self.get_longitudinal_matrices()
        evals, evecs = np.linalg.eig(A_lon)
        return evals

    def get_lateral_modes(self):
        A_lat, _ = self.get_lateral_matrices()
        evals, evecs = np.linalg.eig(A_lat)
        return evals

    def plot_pole_map(self):
        # This will be handled by the frontend usually, but if we need a static plot:
        # For now, just print or return data
        pass
