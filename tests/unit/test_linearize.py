import pytest
import numpy as np
from phugoid.linearize import Linearizer
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimState

class TestLinearizer:
    def test_jacobian_horizontal_position_independence(self):
        """
        Verify that the state derivatives are independent of horizontal position (x, y).
        This test ensures that columns 9 and 10 of the A matrix are zero,
        validating the optimization to skip their computation.
        """
        # Create a dummy trim state
        trim = TrimState(
            alpha=0.1,
            elevator=-0.05,
            throttle=0.6,
            u=50.0,
            w=5.0,
            theta=0.1,
            velocity=np.sqrt(50**2 + 5**2),
            altitude=1000.0
        )
        aircraft = Cessna172()

        lin = Linearizer(aircraft, trim)
        A, B = lin.compute_jacobian()

        # Check column 9 (x position)
        np.testing.assert_allclose(A[:, 9], 0, atol=1e-10, err_msg="Column 9 (x) of Jacobian A must be zero")

        # Check column 10 (y position)
        np.testing.assert_allclose(A[:, 10], 0, atol=1e-10, err_msg="Column 10 (y) of Jacobian A must be zero")

    def test_jacobian_structure(self):
        """
        Verify that the Jacobian matrix has the expected shape and contains non-zero elements
        where expected (e.g. diagonal, cross-coupling).
        """
        trim = TrimState(
            alpha=0.05,
            elevator=-0.02,
            throttle=0.5,
            u=40.0,
            w=2.0,
            theta=0.05,
            velocity=np.sqrt(40**2 + 2**2),
            altitude=500.0
        )
        aircraft = Cessna172()
        lin = Linearizer(aircraft, trim)
        A, B = lin.compute_jacobian()

        assert A.shape == (12, 12)
        assert B.shape == (12, 4)

        # Check that some key elements are non-zero
        # u_dot depends on u (A[0,0])
        assert abs(A[0, 0]) > 1e-5
        # w_dot depends on w (A[2,2])
        assert abs(A[2, 2]) > 1e-5
        # q_dot depends on q (A[4,4])
        assert abs(A[4, 4]) > 1e-5
