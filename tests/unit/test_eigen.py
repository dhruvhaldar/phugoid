import pytest
import numpy as np
from phugoid.aerodynamics import Cessna172
from phugoid.trim import TrimSolver
from phugoid.linearize import Linearizer
from phugoid.modes import calculate_damping_ratio, calculate_natural_frequency

def test_longitudinal_modes():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)
    trim = solver.find_trim(velocity=51.44, altitude=1524)

    lin = Linearizer(aircraft, trim)

    evals = lin.get_longitudinal_modes()

    # Expect 4 eigenvalues
    assert len(evals) == 4

    wns = np.array([calculate_natural_frequency(e) for e in evals])
    zetas = np.array([calculate_damping_ratio(e) for e in evals])

    # Sort by frequency
    idx = np.argsort(wns)
    wns = wns[idx]
    zetas = zetas[idx]

    # Phugoid is the slower mode (first 2, if conjugate pair)
    # Short Period is the faster mode (last 2)

    wn_ph = wns[0] # Should be same for pair
    zeta_ph = zetas[0]

    wn_sp = wns[2]
    zeta_sp = zetas[2]

    print(f"Phugoid: wn={wn_ph:.3f}, zeta={zeta_ph:.3f}")
    print(f"Short Period: wn={wn_sp:.3f}, zeta={zeta_sp:.3f}")

    # Check general characteristics for C172-like aircraft
    # Phugoid: Low frequency, low damping
    assert 0.01 < wn_ph < 1.0
    # Phugoid damping is usually low positive
    assert -0.1 < zeta_ph < 0.5

    # Short Period: Higher frequency, higher damping
    assert 1.0 < wn_sp < 15.0
    assert 0.1 < zeta_sp < 1.5

def test_lateral_modes():
    aircraft = Cessna172()
    solver = TrimSolver(aircraft)
    trim = solver.find_trim(velocity=51.44, altitude=1524)

    lin = Linearizer(aircraft, trim)
    evals = lin.get_lateral_modes()

    assert len(evals) == 4

    # Lateral modes: Dutch Roll (pair), Spiral (real), Roll (real)
    # Spiral usually slow (small eigenvalue)
    # Roll usually fast (large real eigenvalue)
    # Dutch Roll complex pair

    real_parts = np.array([e.real for e in evals])
    imag_parts = np.array([e.imag for e in evals])

    # Check stability (all real parts should be roughly negative)
    # Spiral might be slightly unstable (positive real part) for some aircraft
    # But generally stable or close to 0

    # Count complex pairs (Dutch Roll)
    complex_mask = np.abs(imag_parts) > 1e-4
    n_complex = np.sum(complex_mask)

    # Usually 2 complex poles for Dutch Roll
    assert n_complex == 2

    # Remaining 2 are real (Spiral, Roll)
    real_indices = np.where(~complex_mask)[0]
    assert len(real_indices) == 2

    real_poles = real_parts[real_indices]
    real_poles.sort() # sort ascending (most negative first)

    roll_pole = real_poles[0] # Very negative (fast)
    spiral_pole = real_poles[1] # Close to zero (slow)

    print(f"Roll Pole: {roll_pole:.3f}")
    print(f"Spiral Pole: {spiral_pole:.3f}")

    assert roll_pole < -1.0 # Fast convergence
    assert abs(spiral_pole) < 0.5 # Slow dynamics

if __name__ == "__main__":
    test_longitudinal_modes()
    test_lateral_modes()
