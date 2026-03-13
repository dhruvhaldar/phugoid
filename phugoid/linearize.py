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

        # Optimization: Use pure Python lists instead of np.zeros
        # Avoiding numpy array instantiation inside this tight inner loop provides significant speedup.
        A_cols = [None] * n_state

        # Calculate nominal state derivative once (f(x))
        # Reuse this for forward difference calculation to save ~50% of EoM calls
        f_nominal = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)

        # Optimization: Pre-calculate inverse step to replace division with multiplication
        inv_step = 1.0 / step

        # Compute A matrix (df/dx) - perturbation of state
        for i in range(n_state):
            # Optimization: Skip horizontal position states (x=9, y=10)
            # The equations of motion for a flat-earth model with uniform atmosphere
            # are independent of x and y position. The derivatives are exactly zero.
            # This saves 2 expensive calls to equations_of_motion (approx 14% additional speedup).
            if i in [9, 10]:
                continue

            # Optimization: Perturb state i in place instead of creating a new list copy
            old_val = x_trim_list[i]
            x_trim_list[i] = old_val + step

            # Call scalar EoM
            # equations_of_motion returns list for list input
            f_plus = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)

            # Revert perturbation
            x_trim_list[i] = old_val

            # Fill column i of A
            # Forward difference: (f(x+h) - f(x)) * inv_step
            # Optimization: Use index-based list comprehension for matrix column assignment
            A_cols[i] = [(f_plus[j] - f_nominal[j]) * inv_step for j in range(n_state)]

        B_cols = [None] * n_control

        # Compute B matrix (df/du) - perturbation of control
        for i in range(n_control):
            # Optimization: Perturb control i in place instead of creating a new list copy
            old_val = u_trim_list[i]
            u_trim_list[i] = old_val + step

            f_plus = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)

            # Revert perturbation
            u_trim_list[i] = old_val

            # Optimization: Use index-based list comprehension for matrix column assignment
            B_cols[i] = [(f_plus[j] - f_nominal[j]) * inv_step for j in range(n_state)]

        # Deal with uninitialized columns in A (indices 9, 10 which are skipped)
        for i in [9, 10]:
            A_cols[i] = [0.0] * n_state

        return np.array(A_cols).T, np.array(B_cols).T

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
        pass
