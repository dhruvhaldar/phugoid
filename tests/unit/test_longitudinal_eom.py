import numpy as np
import pytest
from phugoid.dynamics import equations_of_motion, longitudinal_equations_of_motion
from phugoid.aerodynamics import Cessna172

def test_longitudinal_eom_correctness():
    """
    Verify that longitudinal_equations_of_motion produces identical results to equations_of_motion
    when lateral states and controls are zero.
    """
    aircraft = Cessna172()

    # Test case 1: Steady level flight approx
    # u, v, w, p, q, r, phi, theta, psi, x, y, z
    state = [50.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, -1000.0]
    # delta_e, delta_a, delta_r, throttle
    control = [-0.05, 0.0, 0.0, 0.6]

    # Full equations
    full_derivs = equations_of_motion(0, state, aircraft, control)

    # Longitudinal optimized equations
    long_derivs = longitudinal_equations_of_motion(0, state, aircraft, control)

    # Check that outputs match
    # Only check u, w, q, theta, x, z (indices 0, 2, 4, 7, 9, 11)
    # Also check that lateral outputs (1, 3, 5, 6, 8, 10) are zero in long_derivs (implied)

    np.testing.assert_allclose(full_derivs, long_derivs, rtol=1e-10, err_msg="Longitudinal equations mismatch")

def test_longitudinal_eom_with_pitch_rate():
    """
    Verify correctness when q is non-zero (dynamic maneuver).
    """
    aircraft = Cessna172()
    state = [45.0, 0.0, 5.0, 0.0, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, -500.0]
    control = [-0.1, 0.0, 0.0, 0.8]

    full_derivs = equations_of_motion(0, state, aircraft, control)
    long_derivs = longitudinal_equations_of_motion(0, state, aircraft, control)

    np.testing.assert_allclose(full_derivs, long_derivs, rtol=1e-10, err_msg="Dynamic maneuver mismatch")

def test_longitudinal_eom_lateral_zero():
    """
    Verify that lateral derivatives are explicitly zero.
    """
    aircraft = Cessna172()
    state = [50.0, 0.0, 2.0, 0.0, 0.05, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, -1000.0]
    control = [-0.05, 0.0, 0.0, 0.6]

    res = longitudinal_equations_of_motion(0, state, aircraft, control)

    # Lateral indices: 1 (v), 3 (p), 5 (r), 6 (phi), 8 (psi), 10 (y)
    lateral_indices = [1, 3, 5, 6, 8, 10]
    for i in lateral_indices:
        assert res[i] == 0.0, f"Index {i} should be zero"
