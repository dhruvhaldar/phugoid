
import numpy as np
import pytest
from phugoid.dynamics import equations_of_motion
from phugoid.aerodynamics import Cessna172

def test_equations_of_motion_return_type():
    aircraft = Cessna172()
    # Test numpy array input -> numpy array output
    state_np = np.zeros(12)
    control_np = np.zeros(4)
    res_np = equations_of_motion(0, state_np, aircraft, control_np)
    assert isinstance(res_np, np.ndarray)
    assert res_np.shape == (12,)

    # Test list input -> list output
    state_list = [0.0] * 12
    control_list = [0.0] * 4
    res_list = equations_of_motion(0, state_list, aircraft, control_list)
    assert isinstance(res_list, list)
    assert len(res_list) == 12

    # Test list of numpy scalars -> list output
    state_np_list = [np.float64(0.0) for _ in range(12)]
    control_np_list = [np.float64(0.0) for _ in range(4)]
    res_np_list = equations_of_motion(0, state_np_list, aircraft, control_np_list)
    assert isinstance(res_np_list, list)
    assert len(res_np_list) == 12
    # Verify elements are floats (optimization worked and returned lists of floats)
    assert isinstance(res_np_list[0], float)

def test_equations_of_motion_correctness():
    aircraft = Cessna172()
    # Compare numpy array result with list result (should be identical)
    state_np = np.array([100.0, 0, 5.0, 0, 0.1, 0, 0, 0.05, 0, 0, 0, -1000.0])
    control_np = np.array([-0.05, 0, 0, 0.5])

    res_np = equations_of_motion(0, state_np, aircraft, control_np)

    state_list = state_np.tolist()
    control_list = control_np.tolist()
    res_list = equations_of_motion(0, state_list, aircraft, control_list)

    np.testing.assert_allclose(res_np, res_list, rtol=1e-10)
