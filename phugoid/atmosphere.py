import numpy as np
from functools import lru_cache

# Constants
T0 = 288.15     # Sea level temperature [K]
P0 = 101325.0   # Sea level pressure [Pa]
L = 0.0065      # Temperature lapse rate [K/m]
g = 9.80665     # Gravity [m/s^2]
R = 287.05      # Gas constant for dry air [J/(kg*K)]

# Pre-calculated constants for optimization
EXPONENT = g / (R * L)
BASE_FACTOR = L / T0

@lru_cache(maxsize=128)
def _atmosphere_scalar(altitude_val):
    """
    Optimized scalar implementation of ISA Atmosphere Model with caching.

    Args:
        altitude_val (float): Altitude in meters (MSL).

    Returns:
        tuple: (Temperature [K], Pressure [Pa], Density [kg/m^3])
    """
    h_clamped = altitude_val
    if h_clamped < 0:
        h_clamped = 0.0
    elif h_clamped > 11000:
        h_clamped = 11000.0

    T = T0 - L * h_clamped

    # Optimized power calculation
    # P = P0 * (1 - L * h_clamped / T0) ** (g / (R * L))
    base = 1.0 - BASE_FACTOR * h_clamped
    P = P0 * (base ** EXPONENT)

    rho = P / (R * T)
    return float(T), float(P), float(rho)

def atmosphere(altitude):
    """
    ISA Atmosphere Model (Troposphere).

    Args:
        altitude (float or np.ndarray): Altitude in meters (MSL).

    Returns:
        tuple: (Temperature [K], Pressure [Pa], Density [kg/m^3])
    """

    # Cap at Tropopause (11km) for simplicity of this project scope
    # or handle it if needed. For flight mechanics of typical GA aircraft,
    # troposphere is sufficient.

    if isinstance(altitude, (int, float)):
        # Scalar optimization: caching and pre-calc constants
        # Convert to float to ensure cache consistency (e.g. 1000 vs 1000.0)
        return _atmosphere_scalar(float(altitude))
    else:
        # Vectorized implementation for arrays
        h = np.array(altitude, dtype=float)
        h_clamped = np.clip(h, 0, 11000) # Troposphere only implementation

        T = T0 - L * h_clamped

        # P = P0 * (1 - L * h_clamped / T0) ** (g / (R * L))
        # Vectorized optimization
        base = 1.0 - BASE_FACTOR * h_clamped
        P = P0 * (base ** EXPONENT)

        rho = P / (R * T)

        if np.ndim(altitude) == 0:
            return float(T), float(P), float(rho)
        return T, P, rho
