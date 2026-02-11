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

        A = np.zeros((n_state, n_state))
        B = np.zeros((n_state, n_control))

        # Compute A matrix (df/dx)
        for i in range(n_state):
            x_plus = self.x_trim.copy()
            x_minus = self.x_trim.copy()
            x_plus[i] += step
            x_minus[i] -= step

            f_plus = equations_of_motion(0, x_plus, self.aircraft, self.u_trim)
            f_minus = equations_of_motion(0, x_minus, self.aircraft, self.u_trim)

            A[:, i] = (f_plus - f_minus) / (2 * step)

        # Compute B matrix (df/du)
        for i in range(n_control):
            u_plus = self.u_trim.copy()
            u_minus = self.u_trim.copy()
            u_plus[i] += step
            u_minus[i] -= step

            f_plus = equations_of_motion(0, self.x_trim, self.aircraft, u_plus)
            f_minus = equations_of_motion(0, self.x_trim, self.aircraft, u_minus)

            B[:, i] = (f_plus - f_minus) / (2 * step)

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
