import numpy as np

def atmosphere(altitude):
    """
    ISA Atmosphere Model (Troposphere).

    Args:
        altitude (float or np.ndarray): Altitude in meters (MSL).

    Returns:
        tuple: (Temperature [K], Pressure [Pa], Density [kg/m^3])
    """
    # Constants
    T0 = 288.15     # Sea level temperature [K]
    P0 = 101325.0   # Sea level pressure [Pa]
    L = 0.0065      # Temperature lapse rate [K/m]
    g = 9.80665     # Gravity [m/s^2]
    R = 287.05      # Gas constant for dry air [J/(kg*K)]

    # Cap at Tropopause (11km) for simplicity of this project scope
    # or handle it if needed. For flight mechanics of typical GA aircraft,
    # troposphere is sufficient.

    # Optimized for scalar input (hot path in solvers)
    if np.ndim(altitude) == 0:
        h = float(altitude)
        if h < 0: h = 0.0
        elif h > 11000: h = 11000.0

        T = T0 - L * h
        P = P0 * (1 - L * h / T0) ** (g / (R * L))
        rho = P / (R * T)
        return T, P, rho

    h = np.array(altitude, dtype=float)
    h_clamped = np.clip(h, 0, 11000) # Troposphere only implementation

    T = T0 - L * h_clamped
    P = P0 * (1 - L * h_clamped / T0) ** (g / (R * L))
    rho = P / (R * T)

    return T, P, rho
