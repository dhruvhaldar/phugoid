import pytest
import numpy as np
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.dynamics import equations_of_motion

def test_trim_convergence():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)

    velocity = 51.44 # 100 knots
    altitude = 1524.0 # 5000 ft

    trim = solver.find_trim(velocity=velocity, altitude=altitude)

    # Check that derivatives are close to zero
    u = trim.u
    w = trim.w
    theta = trim.theta

    state = np.array([u, 0, w, 0, 0, 0, 0, theta, 0, 0, 0, -altitude])
    control = np.array([trim.elevator, 0, 0, trim.throttle])

    derivs = equations_of_motion(0, state, aircraft, control)

    udot, vdot, wdot, pdot, qdot, rdot = derivs[0:6]

    # Verify longitudinal equilibrium
    assert abs(udot) < 1e-3
    assert abs(wdot) < 1e-3
    assert abs(qdot) < 1e-3

    # Check lateral is zero too (should be by symmetry)
    assert abs(vdot) < 1e-4
    assert abs(pdot) < 1e-4
    assert abs(rdot) < 1e-4

    # Check reasonable values
    # Alpha should be small positive (cruise)
    assert 0 < trim.alpha_deg < 10
    # Elevator usually negative for stability (tail down force)
    # But depends on Cm0 vs CG.
    # C172: Cm0 is negative, so needs negative elevator (pitch up) to balance?
    # Actually if Cm0 < 0, nose down pitching moment. We need nose up moment.
    # Elevator at tail. Positive elevator (down) creates lift up -> nose down moment.
    # So we need negative elevator (up) -> force down -> nose up moment.
    # So elevator should be negative.

    # With my code:
    # Cm = Cm0 + Cm_alpha * alpha + Cm_de * de
    # Cm0 = -0.02
    # Cm_alpha = -0.9 (stable)
    # Cm_de = -1.28

    # 0 = -0.02 + -0.9*alpha + -1.28*de
    # If alpha is positive, term2 is negative.
    # So -0.02 - 0.9*alpha - 1.28*de = 0
    # de = (-0.02 - 0.9*alpha)/1.28
    # Both terms negative => de is negative.

    assert trim.elevator < 0

    # Throttle positive
    assert 0 < trim.throttle < 1.0

if __name__ == "__main__":
    test_trim_convergence()
