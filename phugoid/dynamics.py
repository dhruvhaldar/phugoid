import numpy as np
import math
from phugoid.atmosphere import atmosphere

def equations_of_motion(t, state, aircraft, control):
    """
    Computes the time derivative of the state vector for a 6-DOF rigid body aircraft.

    Args:
        t (float): Time [s]
        state (np.ndarray): State vector [u, v, w, p, q, r, phi, theta, psi, x, y, z]
                            u, v, w: Body velocities [m/s]
                            p, q, r: Body angular rates [rad/s]
                            phi, theta, psi: Euler angles [rad]
                            x, y, z: Position (NED) [m]
        aircraft (Aircraft): Aircraft object with parameters
        control (np.ndarray): Control inputs [delta_e, delta_a, delta_r, throttle] [rad, 0-1]

    Returns:
        np.ndarray or list: State derivative [du/dt, ..., dz/dt].
                            Returns list if input state is list/tuple (for performance),
                            otherwise returns np.ndarray.
    """

    # Unpack state
    # Optimization: Direct unpacking is significantly faster than slice unpacking (4x for lists, 2x for numpy arrays)
    u, v, w, p, q, r, phi, theta, psi, x, y, z = state # z is positive down (altitude = -z)

    # Performance optimization: use math module for scalars (10x faster than numpy ufuncs)
    # Check for list/tuple first to avoid slow np.ndim(list)
    is_list = isinstance(state, (list, tuple))
    was_list = is_list # Keep track of original input type for return value
    is_scalar = is_list or np.ndim(state) == 1

    if is_scalar:
        # Optimization: Ensure inputs are native floats to avoid numpy scalar overhead
        # This speeds up math operations by ~45-60% on scalar paths
        if not is_list:
            # Convert numpy array to list of floats (fast)
            state = state.tolist()
            if not isinstance(control, (list, tuple)):
                control = control.tolist()
            is_list = True

            # Re-unpack state variables (they were numpy scalars)
            u, v, w, p, q, r, phi, theta, psi, x, y, z = state

        # Check heuristic for numpy scalars (which are slow for math module)
        # We check the first element (u) as a proxy for the whole state vector
        u_val = state[0]
        if type(u_val) is not float and type(u_val) is not int:
            state = [float(x) for x in state]
            # Re-unpack state variables to use native floats
            u, v, w, p, q, r, phi, theta, psi, x, y, z = state

        # Check control vector as well (elevator usually)
        de_val = control[0]
        if type(de_val) is not float and type(de_val) is not int:
            control = [float(x) for x in control]

        sin = math.sin
        cos = math.cos
        atan2 = math.atan2
        sqrt = math.sqrt
        asin = math.asin
    else:
        sin = np.sin
        cos = np.cos
        atan2 = np.arctan2
        sqrt = np.sqrt
        asin = np.arcsin

    # Pre-calculate trigonometric functions
    c_th = cos(theta)
    s_th = sin(theta)
    c_ph = cos(phi)
    s_ph = sin(phi)
    c_ps = cos(psi)
    s_ps = sin(psi)

    # Unpack control
    delta_e, delta_a, delta_r, throttle = control

    # Constants
    g = 9.80665
    m = aircraft.mass
    S = aircraft.S
    c = aircraft.c
    b = aircraft.b

    # Inertia tensor (simplified diagonal + Ixz)
    Ixx = aircraft.Ixx
    Iyy = aircraft.Iyy
    Izz = aircraft.Izz
    Ixz = aircraft.Ixz

    # Atmosphere
    T, P, rho = atmosphere(-z)

    # Airspeed
    V = sqrt(u**2 + v**2 + w**2)

    # Avoid division by zero
    if is_scalar:
        if V < 0.1: V = 0.1
    else:
        V = np.maximum(V, 0.1)

    # Aerodynamic Angles
    alpha = atan2(w, u)
    s_alpha = sin(alpha)
    c_alpha = cos(alpha)

    # Optimized beta calculation
    arg_beta = v / V

    if is_scalar:
        if arg_beta < -1.0: arg_beta = -1.0
        elif arg_beta > 1.0: arg_beta = 1.0
        beta = asin(float(arg_beta))
    else:
        beta = asin(np.clip(arg_beta, -1, 1))

    # Dynamic Pressure & Common terms
    q_bar = 0.5 * rho * V**2
    q_bar_S = q_bar * S
    q_bar_S_b = q_bar_S * b
    q_bar_S_c = q_bar_S * c
    inv_2V = 0.5 / V

    # Aerodynamic Coefficients (Linear approximations)
    # CL = CL0 + CL_alpha * alpha + CL_q * (c/(2V)) * q + CL_de * delta_e
    CL = aircraft.CL0 + aircraft.CL_alpha * alpha + aircraft.CL_q * (c * inv_2V) * q + aircraft.CL_de * delta_e

    # CD (Polar)
    # CD = CD0 + k * CL^2 (Simplified) or linear with alpha
    CD = aircraft.CD0 + aircraft.CD_alpha * abs(alpha) # Simple approximation

    # Cm (Pitching Moment)
    # Cm = Cm0 + Cm_alpha * alpha + Cm_q * (c/(2V)) * q + Cm_de * delta_e
    Cm = aircraft.Cm0 + aircraft.Cm_alpha * alpha + aircraft.Cm_q * (c * inv_2V) * q + aircraft.Cm_de * delta_e

    # Lateral (Simplified)
    CY = aircraft.Cy_beta * beta
    Cl = aircraft.Cl_beta * beta + aircraft.Cl_p * (b * inv_2V) * p
    Cn = aircraft.Cn_beta * beta + aircraft.Cn_r * (b * inv_2V) * r

    # Forces in Stability/Wind Axes -> Body Axes
    # Lift (L) acts perpendicular to V in plane of symmetry
    # Drag (D) acts opposite to V
    # Sideforce (Y) acts perpendicular to plane of symmetry

    # Rotate Lift and Drag to Body Frame (approx for small beta)
    # Fx_aero = -D cos(alpha) + L sin(alpha)
    # Fz_aero = -D sin(alpha) - L cos(alpha)
    # Fy_aero = Y

    Fx_aero = q_bar_S * (-CD * c_alpha + CL * s_alpha)
    Fz_aero = q_bar_S * (-CD * s_alpha - CL * c_alpha)
    Fy_aero = q_bar_S * CY

    # Moments
    L_moment = q_bar_S_b * Cl
    M_moment = q_bar_S_c * Cm
    N_moment = q_bar_S_b * Cn

    # Thrust (Assumed aligned with x-body axis for simplicity)
    # Simple model: Thrust proportional to throttle * density ratio
    Thrust = throttle * 2000.0 * (rho / 1.225) # Max thrust 2000N at SL

    Fx = Fx_aero + Thrust
    Fy = Fy_aero
    Fz = Fz_aero

    # Gravity in Body Frame
    Gx = -m * g * s_th
    Gy = m * g * c_th * s_ph
    Gz = m * g * c_th * c_ph

    # Total Forces
    Fx_total = Fx + Gx
    Fy_total = Fy + Gy
    Fz_total = Fz + Gz

    # Equations of Motion

    # Linear Acceleration
    # m(u_dot + qw - rv) = Fx
    udot = Fx_total/m - (q*w - r*v)
    vdot = Fy_total/m - (r*u - p*w)
    wdot = Fz_total/m - (p*v - q*u)

    # Angular Acceleration
    # I * omega_dot + omega x (I * omega) = Moments
    # Solving for p_dot, q_dot, r_dot
    # Assuming Ixz is small but present, Ixy=Iyz=0

    # Simplified Euler equations with Ixz
    # Ixx*p_dot - Ixz*r_dot + (Izz-Iyy)*q*r - Ixz*p*q = L
    # Iyy*q_dot + (Ixx-Izz)*p*r + Ixz*(p^2 - r^2) = M
    # Izz*r_dot - Ixz*p_dot + (Iyy-Ixx)*p*q + Ixz*q*r = N

    # M_total = [L_moment, M_moment, N_moment]

    term1 = (Izz - Iyy) * q * r - Ixz * p * q
    term2 = (Ixx - Izz) * p * r + Ixz * (p**2 - r**2)
    term3 = (Iyy - Ixx) * p * q + Ixz * q * r

    # q_dot is decoupled if Ixy=Iyz=0
    qdot = (M_moment - term2) / Iyy

    # p_dot and r_dot are coupled via Ixz
    # [ Ixx  -Ixz ] [ p_dot ] = [ L - term1 ]
    # [ -Ixz  Izz ] [ r_dot ] = [ N - term3 ]

    det = Ixx * Izz - Ixz**2
    pdot = (Izz * (L_moment - term1) + Ixz * (N_moment - term3)) / det
    rdot = (Ixz * (L_moment - term1) + Ixx * (N_moment - term3)) / det

    # Kinematics (Euler Angles rates)
    # [phi_dot]   [ 1  sin(phi)tan(theta)  cos(phi)tan(theta) ] [ p ]
    # [theta_dot] = [ 0  cos(phi)            -sin(phi)          ] [ q ]
    # [psi_dot]   [ 0  sin(phi)sec(theta)  cos(phi)sec(theta) ] [ r ]

    # tan(theta) = s_th / c_th
    t_th = s_th / c_th

    phi_dot = p + (q * s_ph + r * c_ph) * t_th
    theta_dot = q * c_ph - r * s_ph
    psi_dot = (q * s_ph + r * c_ph) / c_th

    # Navigation (Position rates) NED
    # Transform Body velocities (u,v,w) to NED (x_dot, y_dot, z_dot)
    # (s_th, c_th, etc are already calculated)

    # Rotation Matrix Body to NED
    # R11 = c_th*c_ps
    # R12 = s_ph*s_th*c_ps - c_ph*s_ps
    # R13 = c_ph*s_th*c_ps + s_ph*s_ps
    # ...

    x_dot = (c_th*c_ps)*u + (s_ph*s_th*c_ps - c_ph*s_ps)*v + (c_ph*s_th*c_ps + s_ph*s_ps)*w
    y_dot = (c_th*s_ps)*u + (s_ph*s_th*s_ps + c_ph*c_ps)*v + (c_ph*s_th*s_ps - s_ph*c_ps)*w
    z_dot = (-s_th)*u + (s_ph*c_th)*v + (c_ph*c_th)*w

    result = [udot, vdot, wdot, pdot, qdot, rdot, phi_dot, theta_dot, psi_dot, x_dot, y_dot, z_dot]

    # Return list if input was list (TrimSolver optimization)
    # Avoids np.array creation overhead (~1.3us) in tight loops
    if was_list:
        return result
    else:
        return np.array(result)
