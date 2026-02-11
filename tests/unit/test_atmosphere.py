import numpy as np
import pytest
from phugoid.atmosphere import atmosphere

def test_sea_level():
    h = 0.0
    T, P, rho = atmosphere(h)

    assert np.isclose(T, 288.15)
    assert np.isclose(P, 101325.0)
    assert np.isclose(rho, 1.225, atol=1e-3)

def test_troposphere():
    h = 5000.0
    T, P, rho = atmosphere(h)

    # Expected values roughly
    # T = 288.15 - 0.0065 * 5000 = 255.65
    assert np.isclose(T, 255.65)

    # P check
    # P = 101325 * (1 - 0.0065*5000/288.15)^(9.80665/(287.05*0.0065))
    # P approx 54019
    assert 54000 < P < 54100

    # rho check
    # rho = P / (R*T) = 54019 / (287.05 * 255.65) = 0.736
    assert 0.73 < rho < 0.74

def test_array_input():
    h = np.array([0, 5000])
    T, P, rho = atmosphere(h)

    assert len(T) == 2
    assert np.isclose(T[0], 288.15)
    assert np.isclose(T[1], 255.65)
