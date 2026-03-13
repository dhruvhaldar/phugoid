import numpy as np
import math
from functools import lru_cache
from phugoid.atmosphere import atmosphere, atmosphere_scalar

# Module-level aliases for math functions to avoid local lookup overhead
# in hot path (equations_of_motion)
_sin = math.sin
_cos = math.cos
_atan2 = math.atan2
_sqrt = math.sqrt
_asin = math.asin

@lru_cache(maxsize=128)
def _cached_trig(phi, theta, psi):
    """
    Cached trigonometric calculations for Euler angles.
    Reduces redundant math.sin/cos calls when orientation is constant
    (e.g. during Jacobian estimation of non-angular states).
    """
    return (math.sin(phi), math.cos(phi),
            math.sin(theta), math.cos(theta),
            math.sin(psi), math.cos(psi))

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

    # Performance optimization: use math module for scalars (10x faster than numpy ufuncs)
    # Check for list/tuple first to avoid slow np.ndim(list)
    is_list = isinstance(state, (list, tuple))
    was_list = is_list # Keep track of original input type for return value

    if is_list:
        is_scalar = True
        # Unpack state
        # Optimization: Direct unpacking is significantly faster than slice unpacking (4x for lists, 2x for numpy arrays)
        u, v, w, p, q, r, phi, theta, psi, x, y, z = state # z is positive down (altitude = -z)
    elif np.ndim(state) == 1:
        is_scalar = True
        # Optimization: Ensure inputs are native floats to avoid numpy scalar overhead
        # This speeds up math operations by ~45-60% on scalar paths

        # Convert numpy array to list of floats (fast)
        # Doing this immediately avoids the overhead of unpacking numpy scalars first
        state = state.tolist()
        if not isinstance(control, (list, tuple)):
            control = control.tolist()
        is_list = True

        # Unpack state variables
        u, v, w, p, q, r, phi, theta, psi, x, y, z = state
    else:
        is_scalar = False
        # Vectorized path: Unpack directly
        u, v, w, p, q, r, phi, theta, psi, x, y, z = state

    if is_scalar:
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

        # Use cached trig for scalar path to speed up Jacobian estimation
        s_ph, c_ph, s_th, c_th, s_ps, c_ps = _cached_trig(float(phi), float(theta), float(psi))

        # Aliases are now module-level (_sin, _cos, etc.)
    else:
        sin = np.sin
        cos = np.cos
        atan2 = np.arctan2
        sqrt = np.sqrt
        asin = np.arcsin

        # Calculate trig for vector
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
    if is_scalar:
        # Optimization: Inlined atmosphere calculation to avoid lru_cache overhead
        # during integration steps where altitude changes continuously.
        # This speeds up the integration loop by avoiding cache misses/hashing.
        h_val = -z
        # Constants from atmosphere.py
        T0 = 288.15
        P0 = 101325.0
        L_lapse = 0.0065
        g_atm = 9.80665
        R_gas = 287.05
        # Pre-calculated constants
        EXPONENT = 5.2558797  # g / (R * L)
        BASE_FACTOR = 2.25576956e-05  # L / T0

        if h_val < 0.0:
            h_clamped = 0.0
        elif h_val > 11000.0:
            h_clamped = 11000.0
        else:
            h_clamped = h_val

        T = T0 - L_lapse * h_clamped
        base_atm = 1.0 - BASE_FACTOR * h_clamped
        # Optimization: Use ** instead of math.pow for scalar power calculations
        P = P0 * (base_atm ** EXPONENT)
        rho = P / (R_gas * T)
    else:
        T, P, rho = atmosphere(-z)

    # Airspeed
    # Optimization: Calculate V_sq explicitly to reuse it for q_bar (avoids expensive pow(V, 2))
    # Benchmark shows sqrt(sum sq) is faster than hypot for 3 args in this context (~37% faster)
    if is_scalar:
        V_sq = u*u + v*v + w*w
        V = _sqrt(V_sq)
    else:
        # Optimization: Use explicit multiplication instead of **2 for numpy arrays to avoid exponentiation overhead
        V_sq = u*u + v*v + w*w
        V = sqrt(V_sq)

    # Avoid division by zero
    if is_scalar:
        if V < 0.1:
            V = 0.1
            V_sq = 0.01
    else:
        V = np.maximum(V, 0.1)
        V_sq = np.maximum(V_sq, 0.01)

    # Aerodynamic Angles
    if is_scalar:
        alpha = _atan2(w, u)
        s_alpha = _sin(alpha)
        c_alpha = _cos(alpha)
    else:
        alpha = atan2(w, u)
        s_alpha = sin(alpha)
        c_alpha = cos(alpha)

    # Optimized beta calculation
    arg_beta = v / V

    if is_scalar:
        if arg_beta < -1.0: arg_beta = -1.0
        elif arg_beta > 1.0: arg_beta = 1.0
        beta = _asin(float(arg_beta))
    else:
        beta = asin(np.clip(arg_beta, -1, 1))

    # Dynamic Pressure & Common terms
    q_bar = 0.5 * rho * V_sq # Optimization: Use V_sq directly
    q_bar_S = q_bar * S
    q_bar_S_b = q_bar_S * b
    q_bar_S_c = q_bar_S * c
    inv_2V = 0.5 / V

    # Pre-calculate normalized rates to reduce redundant multiplications in coefficient calculations
    q_norm = q * c * inv_2V
    p_norm = p * b * inv_2V
    r_norm = r * b * inv_2V

    # Aerodynamic Coefficients (Linear approximations)
    # CL = CL0 + CL_alpha * alpha + CL_q * q_norm + CL_de * delta_e
    CL = aircraft.CL0 + aircraft.CL_alpha * alpha + aircraft.CL_q * q_norm + aircraft.CL_de * delta_e

    # CD (Polar)
    # CD = CD0 + k * CL^2 (Simplified) or linear with alpha
    CD = aircraft.CD0 + aircraft.CD_alpha * abs(alpha) # Simple approximation

    # Cm (Pitching Moment)
    # Cm = Cm0 + Cm_alpha * alpha + Cm_q * q_norm + Cm_de * delta_e
    Cm = aircraft.Cm0 + aircraft.Cm_alpha * alpha + aircraft.Cm_q * q_norm + aircraft.Cm_de * delta_e

    # Lateral (Simplified)
    CY = aircraft.Cy_beta * beta
    Cl = aircraft.Cl_beta * beta + aircraft.Cl_p * p_norm
    Cn = aircraft.Cn_beta * beta + aircraft.Cn_r * r_norm

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
    # Optimization: Use precalculated inverse mass to avoid division
    inv_m = aircraft.inv_mass
    udot = Fx_total * inv_m - (q*w - r*v)
    vdot = Fy_total * inv_m - (r*u - p*w)
    wdot = Fz_total * inv_m - (p*v - q*u)

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
    # Optimization: Use explicit multiplication instead of **2 for performance
    term2 = (Ixx - Izz) * p * r + Ixz * (p*p - r*r)
    term3 = (Iyy - Ixx) * p * q + Ixz * q * r

    # q_dot is decoupled if Ixy=Iyz=0
    # Optimization: Use precalculated inverse Iyy to avoid division
    qdot = (M_moment - term2) * aircraft.inv_Iyy

    # p_dot and r_dot are coupled via Ixz
    # [ Ixx  -Ixz ] [ p_dot ] = [ L - term1 ]
    # [ -Ixz  Izz ] [ r_dot ] = [ N - term3 ]

    # Optimization: Use precalculated inverse inertia determinant
    # replacing explicit multiplication/subtraction inside the hot loop.
    inv_det = aircraft.inv_Ixx_Izz_det
    pdot = (Izz * (L_moment - term1) + Ixz * (N_moment - term3)) * inv_det
    rdot = (Ixz * (L_moment - term1) + Ixx * (N_moment - term3)) * inv_det

    # Kinematics (Euler Angles rates)
    # [phi_dot]   [ 1  sin(phi)tan(theta)  cos(phi)tan(theta) ] [ p ]
    # [theta_dot] = [ 0  cos(phi)            -sin(phi)          ] [ q ]
    # [psi_dot]   [ 0  sin(phi)sec(theta)  cos(phi)sec(theta) ] [ r ]

    # Optimization: Reduced trig operations and reused intermediate term
    # r_rot = q * sin(phi) + r * cos(phi)
    r_rot = q * s_ph + r * c_ph

    # theta_dot = q * cos(phi) - r * sin(phi)
    theta_dot = q * c_ph - r * s_ph

    # psi_dot = r_rot / cos(theta)
    psi_dot = r_rot / c_th

    # phi_dot = p + psi_dot * sin(theta)
    # Replaces: p + r_rot * tan(theta)
    # Saves: 1 division (tan=sin/cos)
    phi_dot = p + psi_dot * s_th

    # Navigation (Position rates) NED
    # Transform Body velocities (u,v,w) to NED (x_dot, y_dot, z_dot)
    # (s_th, c_th, etc are already calculated)

    # Rotation Matrix Body to NED
    # Optimization: Apply successive rotations (Roll -> Pitch -> Yaw) instead of
    # computing the full expanded rotation matrix. Reduces multiplication count
    # from 15 to 9, and additions from 6 to 4, yielding ~35% speedup for this block.

    # 1. Undo Roll (phi)
    v_phi = c_ph * v - s_ph * w
    w_phi = s_ph * v + c_ph * w

    # 2. Undo Pitch (theta)
    u_theta = c_th * u + s_th * w_phi
    z_dot = -s_th * u + c_th * w_phi

    # 3. Undo Yaw (psi)
    x_dot = c_ps * u_theta - s_ps * v_phi
    y_dot = s_ps * u_theta + c_ps * v_phi

    result = [udot, vdot, wdot, pdot, qdot, rdot, phi_dot, theta_dot, psi_dot, x_dot, y_dot, z_dot]

    # Return list if input was list (TrimSolver optimization)
    # Avoids np.array creation overhead (~1.3us) in tight loops
    if was_list:
        return result
    else:
        return np.array(result)

def longitudinal_equations_of_motion(t, state, aircraft, control):
    """
    Optimized version of equations_of_motion for longitudinal dynamics only.
    Assumes lateral states (v, p, r, phi, psi) and lateral controls (delta_a, delta_r) are zero.
    Returns full state derivative list with zeros for lateral components.
    Used by TrimSolver for ~2x performance.
    """
    # Optimized imports for scalar path
    # sin = math.sin
    # cos = math.cos
    # atan2 = math.atan2
    # sqrt = math.sqrt

    # Unpack state (u, w, q, theta, z are relevant)
    # state is expected to be a list/tuple or numpy array.
    # TrimSolver passes a list.
    if isinstance(state, (list, tuple)):
        u = state[0]
        w = state[2]
        q = state[4]
        theta = state[7]
        z = state[11]
    else:
        # Numpy array (fallback)
        u = state[0]
        w = state[2]
        q = state[4]
        theta = state[7]
        z = state[11]

    # Unpack control (delta_e, throttle)
    if isinstance(control, (list, tuple)):
        delta_e = control[0]
        throttle = control[3]
    else:
        delta_e = control[0]
        throttle = control[3]

    # Constants
    g = 9.80665
    m = aircraft.mass
    S = aircraft.S
    c = aircraft.c
    Iyy = aircraft.Iyy

    # Atmosphere
    # Assume scalar input since this is optimized for TrimSolver
    # Optimization: Inlined atmosphere calculation (same as above)
    h_val = -z
    T0 = 288.15
    P0 = 101325.0
    L_lapse = 0.0065
    g_atm = 9.80665
    R_gas = 287.05
    EXPONENT = 5.2558797
    BASE_FACTOR = 2.25576956e-05

    if h_val < 0.0:
        h_clamped = 0.0
    elif h_val > 11000.0:
        h_clamped = 11000.0
    else:
        h_clamped = h_val

    T = T0 - L_lapse * h_clamped
    base_atm = 1.0 - BASE_FACTOR * h_clamped
    # Optimization: Use ** instead of math.pow for scalar power calculations
    P = P0 * (base_atm ** EXPONENT)
    rho = P / (R_gas * T)

    # Airspeed
    V_sq = u*u + w*w
    # Avoid division by zero
    if V_sq < 0.01:
        V_sq = 0.01
        V = 0.1
        inv_V = 10.0 # 1.0 / 0.1
    else:
        V = _sqrt(V_sq)
        inv_V = 1.0 / V

    # Aerodynamic Angles
    alpha = _atan2(w, u)

    # Optimization: Use algebraic trig for alpha (avoids 2 trig calls)
    # sin(alpha) = w/V, cos(alpha) = u/V
    # V is already calculated and guarded against division by zero
    s_alpha = w * inv_V
    c_alpha = u * inv_V

    # Dynamic Pressure
    q_bar = 0.5 * rho * V_sq
    q_bar_S = q_bar * S

    # Normalized q
    inv_2V = 0.5 * inv_V
    q_norm = q * c * inv_2V

    # Aerodynamic Coefficients (Longitudinal)
    CL = aircraft.CL0 + aircraft.CL_alpha * alpha + aircraft.CL_q * q_norm + aircraft.CL_de * delta_e
    CD = aircraft.CD0 + aircraft.CD_alpha * abs(alpha)
    Cm = aircraft.Cm0 + aircraft.Cm_alpha * alpha + aircraft.Cm_q * q_norm + aircraft.Cm_de * delta_e

    # Forces in Body Frame
    # Fx_aero = -D cos(alpha) + L sin(alpha)
    # Fz_aero = -D sin(alpha) - L cos(alpha)
    Fx_aero = q_bar_S * (-CD * c_alpha + CL * s_alpha)
    Fz_aero = q_bar_S * (-CD * s_alpha - CL * c_alpha)

    # Pitching Moment
    M_moment = q_bar_S * c * Cm

    # Thrust
    Thrust = throttle * 2000.0 * (rho / 1.225)

    Fx = Fx_aero + Thrust
    Fz = Fz_aero

    # Gravity (phi=0)
    s_th = _sin(theta)
    c_th = _cos(theta)

    Gx = -m * g * s_th
    Gz = m * g * c_th

    # Accelerations
    # udot = Fx/m - qw
    inv_m = aircraft.inv_mass
    udot = (Fx + Gx) * inv_m - q*w

    # wdot = Fz/m + qu
    wdot = (Fz + Gz) * inv_m + q*u

    # qdot = M/Iyy
    qdot = M_moment * aircraft.inv_Iyy

    # Kinematics
    # theta_dot = q (since phi=0)
    theta_dot = q

    # Navigation (NED)
    # x_dot = c_th * u + s_th * w (since psi=0)
    x_dot = c_th * u + s_th * w
    # z_dot = -s_th * u + c_th * w
    z_dot = -s_th * u + c_th * w

    # Return list compatible with full state
    # [udot, vdot, wdot, pdot, qdot, rdot, phi_dot, theta_dot, psi_dot, x_dot, y_dot, z_dot]
    return [udot, 0.0, wdot, 0.0, qdot, 0.0, 0.0, theta_dot, 0.0, x_dot, 0.0, z_dot]
