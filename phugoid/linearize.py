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

    def _compute_perturbations(self, X_batch, U_batch):
        """
        Computes f(x, u) for each column in X_batch and U_batch.
        Optimized to use the scalar path of equations_of_motion by converting columns to Python lists.
        This avoids NumPy broadcasting overhead for small matrices (N=12) and leverages faster math module operations.
        """
        # Convert to list of lists (transposed so we iterate over columns)
        # Passing lists to equations_of_motion triggers the optimized scalar path (using math module)
        X_list = X_batch.T.tolist()
        U_list = U_batch.T.tolist()

        f_list = [
            equations_of_motion(0, x, self.aircraft, u)
            for x, u in zip(X_list, U_list)
        ]

        # Convert back to (12, N) array
        # f_list is a list of N result vectors (each length 12)
        # np.array(f_list) -> shape (N, 12). We need (12, N), so transpose.
        return np.array(f_list).T

    def compute_jacobian(self, step=1e-4):
        n_state = 12
        n_control = 4

        # Compute A matrix (df/dx)
        # Vectorized perturbation of state
        # Create (12, 12) matrix where each column is x_trim with perturbation on diagonal
        eye_step = np.eye(n_state) * step
        X_plus = self.x_trim[:, None] + eye_step
        X_minus = self.x_trim[:, None] - eye_step

        # Broadcast control (must be broadcasted to (4, 12) to match state batch size)
        U_broadcast = self.u_trim[:, None] + np.zeros((1, n_state))

        # Call equations of motion (optimized)
        f_plus = self._compute_perturbations(X_plus, U_broadcast)
        f_minus = self._compute_perturbations(X_minus, U_broadcast)

        # f_plus is (12, 12) matrix where column i is f(x + dx_i)
        A = (f_plus - f_minus) / (2 * step)

        # Compute B matrix (df/du)
        # Vectorized perturbation of control
        eye_step_u = np.eye(n_control) * step
        U_plus = self.u_trim[:, None] + eye_step_u
        U_minus = self.u_trim[:, None] - eye_step_u

        # Broadcast state (must be broadcasted to (12, 4) to match control batch size)
        X_broadcast = self.x_trim[:, None] + np.zeros((1, n_control))

        f_plus = self._compute_perturbations(X_broadcast, U_plus)
        f_minus = self._compute_perturbations(X_broadcast, U_minus)

        B = (f_plus - f_minus) / (2 * step)

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
