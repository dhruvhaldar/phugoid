import numpy as np
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
        np.ndarray: State derivative [du/dt, ..., dz/dt]
    """

    # Unpack state
    u, v, w = state[0:3]
    p, q, r = state[3:6]
    phi, theta, psi = state[6:9]
    x, y, z = state[9:12] # z is positive down (altitude = -z)

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
    V = np.sqrt(u**2 + v**2 + w**2)
    if V < 0.1: V = 0.1 # Avoid division by zero

    # Aerodynamic Angles
    alpha = np.arctan2(w, u)
    beta = np.arcsin(np.clip(v/V, -1, 1))

    # Dynamic Pressure
    q_bar = 0.5 * rho * V**2

    # Aerodynamic Coefficients (Linear approximations)
    # CL = CL0 + CL_alpha * alpha + CL_q * (c/(2V)) * q + CL_de * delta_e
    CL = aircraft.CL0 + aircraft.CL_alpha * alpha + aircraft.CL_q * (c/(2*V)) * q + aircraft.CL_de * delta_e

    # CD (Polar)
    # CD = CD0 + k * CL^2 (Simplified) or linear with alpha
    CD = aircraft.CD0 + aircraft.CD_alpha * abs(alpha) # Simple approximation

    # Cm (Pitching Moment)
    # Cm = Cm0 + Cm_alpha * alpha + Cm_q * (c/(2V)) * q + Cm_de * delta_e
    Cm = aircraft.Cm0 + aircraft.Cm_alpha * alpha + aircraft.Cm_q * (c/(2*V)) * q + aircraft.Cm_de * delta_e

    # Lateral (Simplified)
    CY = aircraft.Cy_beta * beta
    Cl = aircraft.Cl_beta * beta + aircraft.Cl_p * (b/(2*V)) * p
    Cn = aircraft.Cn_beta * beta + aircraft.Cn_r * (b/(2*V)) * r

    # Forces in Stability/Wind Axes -> Body Axes
    # Lift (L) acts perpendicular to V in plane of symmetry
    # Drag (D) acts opposite to V
    # Sideforce (Y) acts perpendicular to plane of symmetry

    # Rotate Lift and Drag to Body Frame (approx for small beta)
    # Fx_aero = -D cos(alpha) + L sin(alpha)
    # Fz_aero = -D sin(alpha) - L cos(alpha)
    # Fy_aero = Y

    Fx_aero = q_bar * S * (-CD * np.cos(alpha) + CL * np.sin(alpha))
    Fz_aero = q_bar * S * (-CD * np.sin(alpha) - CL * np.cos(alpha))
    Fy_aero = q_bar * S * CY

    # Moments
    L_moment = q_bar * S * b * Cl
    M_moment = q_bar * S * c * Cm
    N_moment = q_bar * S * b * Cn

    # Thrust (Assumed aligned with x-body axis for simplicity)
    # Simple model: Thrust proportional to throttle * density ratio
    Thrust = throttle * 2000.0 * (rho / 1.225) # Max thrust 2000N at SL

    Fx = Fx_aero + Thrust
    Fy = Fy_aero
    Fz = Fz_aero

    # Gravity in Body Frame
    Gx = -m * g * np.sin(theta)
    Gy = m * g * np.cos(theta) * np.sin(phi)
    Gz = m * g * np.cos(theta) * np.cos(phi)

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

    phi_dot = p + (q * np.sin(phi) + r * np.cos(phi)) * np.tan(theta)
    theta_dot = q * np.cos(phi) - r * np.sin(phi)
    psi_dot = (q * np.sin(phi) + r * np.cos(phi)) / np.cos(theta)

    # Navigation (Position rates) NED
    # Transform Body velocities (u,v,w) to NED (x_dot, y_dot, z_dot)
    c_th = np.cos(theta)
    s_th = np.sin(theta)
    c_ph = np.cos(phi)
    s_ph = np.sin(phi)
    c_ps = np.cos(psi)
    s_ps = np.sin(psi)

    # Rotation Matrix Body to NED
    # R11 = c_th*c_ps
    # R12 = s_ph*s_th*c_ps - c_ph*s_ps
    # R13 = c_ph*s_th*c_ps + s_ph*s_ps
    # ...

    x_dot = (c_th*c_ps)*u + (s_ph*s_th*c_ps - c_ph*s_ps)*v + (c_ph*s_th*c_ps + s_ph*s_ps)*w
    y_dot = (c_th*s_ps)*u + (s_ph*s_th*s_ps + c_ph*c_ps)*v + (c_ph*s_th*s_ps - s_ph*c_ps)*w
    z_dot = (-s_th)*u + (s_ph*c_th)*v + (c_ph*c_th)*w

    return np.array([udot, vdot, wdot, pdot, qdot, rdot, phi_dot, theta_dot, psi_dot, x_dot, y_dot, z_dot])
