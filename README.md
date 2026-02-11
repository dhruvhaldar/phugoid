# Phugoid

**Phugoid** is a Python-based flight dynamics engine designed for **SD2805 Flight Mechanics**. It serves as a modern replacement for the traditional Matlab toolboxes used in aeronautical engineering.

The tool provides a complete pipeline for analyzing aircraft stability: from defining aerodynamic coefficients and finding the **Trim State** (Equilibrium), to linearizing the equations of motion and visualizing the resulting **Eigenmodes** (dynamic stability).

## 📚 Syllabus Mapping (SD2805)

This project strictly adheres to the course learning outcomes:

| Module | Syllabus Topic | Implemented Features |
| --- | --- | --- |
| **Equations of Motion** | *Formulate EoM for atmospheric flight* | Full 6-DOF non-linear rigid body dynamics (). |
| **Equilibrium** | *Analyze equilibrium (Trim)* | Numerical solver to find control surface deflections () for steady-level flight. |
| **Stability** | *Analyze stability & modes* | Linearization routine to extract **Longitudinal** (Phugoid, Short Period) and **Lateral** (Dutch Roll, Spiral) modes. |
| **Control** | *Design a basic control system* | State-space feedback control (LQR/PID) for Stability Augmentation Systems (SAS). |
| **Simulation** | *Integrate equations in time* | RK45 integrator for trajectory analysis (e.g., response to a step elevator input). |

## 🚀 Deployment (Vercel)

Phugoid is designed to run as a serverless analysis tool.

1. **Fork** this repository.
2. Deploy to **Vercel** (Python runtime is auto-detected).
3. Access the **Stability Analyzer** at `https://your-phugoid.vercel.app`.

## 📊 Artifacts & Dynamics Analysis

### 1. Trim Analysis (Equilibrium)

*Calculates the angle of attack () and elevator deflection () required to maintain a specific velocity and altitude.*

**Code:**

```python
from phugoid.trim import TrimSolver
from phugoid.aircraft import Cessna172

# Initialize Aircraft Model
aircraft = Cessna172()

# Find Trim for Level Flight at 100 knots, 5000 ft
solver = TrimSolver(aircraft)
state = solver.find_trim(velocity=51.44, altitude=1524, flight_path_angle=0)

print(f"Trim Alpha: {state.alpha_deg:.2f} deg")
print(f"Trim Elevator: {state.elevator_deg:.2f} deg")

```

**Artifact Output:**

> *Figure 1: Trim Diagram. The visual shows the balance of forces (Lift = Weight, Thrust = Drag) and moments (Pitching Moment = 0) at the trim point. The elevator deflection generates the necessary tail down-force to balance the center of gravity.*

### 2. Eigenmode Visualization (Pole-Zero Map)

*Linearizes the system around the trim point to identify natural modes of motion.*

**Code:**

```python
from phugoid.linearize import Linearizer

# Get State Space Matrices (A, B)
lin = Linearizer(aircraft, trim_state=state)
longitudinal_modes = lin.get_longitudinal_modes()

lin.plot_pole_map()

```

**Artifact Output:**

> *Figure 2: The S-Plane (Pole-Zero Map).
> * **Short Period Mode:** Two complex conjugate poles far to the left (high damping, fast frequency).
> * **Phugoid Mode:** Two complex conjugate poles near the imaginary axis (low damping, slow frequency).
> * Stability is confirmed if all poles lie in the left half-plane (Re < 0).*
>
>

### 3. Dynamic Response (The Phugoid Mode)

*Simulates the time history of the aircraft after a perturbation, showing the exchange between kinetic and potential energy.*

**Artifact Output:**

> *Figure 3: Phugoid Oscillation. The graph plots Velocity vs. Altitude over time. As the aircraft pitches up, it gains altitude but loses speed (Simulated). When it stalls/slows, it noses down to regain speed, losing altitude. This long-period exchange of energy is a classic flight mechanics ILO.*

## 🧪 Testing Strategy

### Unit Tests (Aerodynamics)

Located in `tests/unit/`.

*Example: `tests/unit/test_eigen.py*`

```python
def test_short_period_approximation():
    """
    Verifies that the full matrix eigenvalue matches the
    Short Period approximation formula: wn approx sqrt(Z_alpha * M_q / U0)
    """
    aircraft = GenericTransport()
    full_eigen = aircraft.get_eigenvalue('short_period')
    approx_wn = aircraft.approximate_short_period_freq()

    # Approx should be within 10% for conventional aircraft
    assert abs(full_eigen.imag - approx_wn) / approx_wn < 0.10

```

### E2E Tests (Simulation)

Located in `tests/e2e/`.

*Example: `tests/e2e/test_trim.py*`

```python
def test_trim_convergence():
    """
    E2E Test: Does the non-linear simulation stay stable at the calculated trim?
    Integration over 10 seconds should result in near-zero acceleration.
    """
    trim_state = solver.find_trim(velocity=100)
    sim = Simulation(aircraft, initial_state=trim_state)
    final_state = sim.run(duration=10.0)

    assert abs(final_state.q) < 1e-4 # Pitch rate should remain zero
    assert abs(final_state.az) < 1e-2 # Vertical accel should remain zero

```

## ⚖️ License

**MIT License**

Copyright (c) 2026 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files... [Standard MIT Text]