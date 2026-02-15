import pytest
import numpy as np
from phugoid.atmosphere import atmosphere

def test_atmosphere_scalar():
    h = 1000.0
    T, P, rho = atmosphere(h)
    assert isinstance(T, float)
    assert isinstance(P, float)
    assert isinstance(rho, float)
    assert T > 0
    assert P > 0
    assert rho > 0

def test_atmosphere_scalar_vs_array():
    h_scalar = 2500.0
    h_array = np.array([2500.0])

    T_s, P_s, rho_s = atmosphere(h_scalar)
    T_a, P_a, rho_a = atmosphere(h_array)

    assert np.isclose(T_s, T_a)
    assert np.isclose(P_s, P_a)
    assert np.isclose(rho_s, rho_a)

def test_atmosphere_clamping_scalar():
    # Test below 0
    T_low, P_low, rho_low = atmosphere(-500.0)
    T_0, P_0, rho_0 = atmosphere(0.0)
    assert T_low == T_0
    assert P_low == P_0
    assert rho_low == rho_0

    # Test above 11000
    T_high, P_high, rho_high = atmosphere(15000.0)
    T_11k, P_11k, rho_11k = atmosphere(11000.0)
    assert T_high == T_11k
    assert P_high == P_11k
    assert rho_high == rho_11k
