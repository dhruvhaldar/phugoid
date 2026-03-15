import time
from phugoid.linearize import Linearizer
from phugoid.trim import TrimSolver
from phugoid.aerodynamics import Cessna172

ac = Cessna172()
solver = TrimSolver(ac)
trim = solver.find_trim(velocity=51.44, altitude=1524, flight_path_angle=0)

class FastLinearizer2(Linearizer):
    def compute_jacobian(self, step=1e-4):
        from phugoid.dynamics import equations_of_motion
        import numpy as np

        n_state = 12
        n_control = 4

        x_trim_list = self.x_trim.tolist()
        u_trim_list = self.u_trim.tolist()

        f_nominal = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)

        inv_step = 1.0 / step
        A_cols = [None] * n_state

        for i in range(n_state):
            if i in [9, 10]:
                continue
            old_val = x_trim_list[i]
            x_trim_list[i] = old_val + step
            f_plus = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)
            x_trim_list[i] = old_val

            A_cols[i] = [
                (f_plus[0] - f_nominal[0]) * inv_step,
                (f_plus[1] - f_nominal[1]) * inv_step,
                (f_plus[2] - f_nominal[2]) * inv_step,
                (f_plus[3] - f_nominal[3]) * inv_step,
                (f_plus[4] - f_nominal[4]) * inv_step,
                (f_plus[5] - f_nominal[5]) * inv_step,
                (f_plus[6] - f_nominal[6]) * inv_step,
                (f_plus[7] - f_nominal[7]) * inv_step,
                (f_plus[8] - f_nominal[8]) * inv_step,
                (f_plus[9] - f_nominal[9]) * inv_step,
                (f_plus[10] - f_nominal[10]) * inv_step,
                (f_plus[11] - f_nominal[11]) * inv_step
            ]

        B_cols = [None] * n_control
        for i in range(n_control):
            old_val = u_trim_list[i]
            u_trim_list[i] = old_val + step
            f_plus = equations_of_motion(0, x_trim_list, self.aircraft, u_trim_list)
            u_trim_list[i] = old_val

            B_cols[i] = [
                (f_plus[0] - f_nominal[0]) * inv_step,
                (f_plus[1] - f_nominal[1]) * inv_step,
                (f_plus[2] - f_nominal[2]) * inv_step,
                (f_plus[3] - f_nominal[3]) * inv_step,
                (f_plus[4] - f_nominal[4]) * inv_step,
                (f_plus[5] - f_nominal[5]) * inv_step,
                (f_plus[6] - f_nominal[6]) * inv_step,
                (f_plus[7] - f_nominal[7]) * inv_step,
                (f_plus[8] - f_nominal[8]) * inv_step,
                (f_plus[9] - f_nominal[9]) * inv_step,
                (f_plus[10] - f_nominal[10]) * inv_step,
                (f_plus[11] - f_nominal[11]) * inv_step
            ]

        for i in [9, 10]:
            A_cols[i] = [0.0] * n_state

        return np.array(A_cols).T, np.array(B_cols).T

start = time.perf_counter()
for _ in range(1000):
    lin = FastLinearizer2(ac, trim)
end = time.perf_counter()
print(f"Fast Linearizer 2 1000 runs: {end - start:.4f} seconds")
