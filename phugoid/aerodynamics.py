
class Aircraft:
    def __init__(self, name="Generic"):
        self.name = name

        # Geometry
        self.S = 16.2  # Wing Area [m^2] (C172)
        self.b = 11.0  # Wing Span [m]
        self.c = 1.47  # Mean Aerodynamic Chord [m]
        self.mass = 1111.0 # Mass [kg] (Max Gross)

        # Inertia [kg*m^2]
        self.Ixx = 1285.3
        self.Iyy = 1824.9
        self.Izz = 2666.9
        self.Ixz = 0.0

        # Aerodynamic Coefficients (Longitudinal)
        # Non-dimensional
        self.CL0 = 0.3
        self.CD0 = 0.03
        self.Cm0 = -0.02

        # Stability Derivatives (per radian)
        self.CL_alpha = 4.58
        self.CL_q = 3.8
        self.CL_de = 0.35 # Elevator effectiveness

        self.CD_alpha = 0.1 # Induced drag factor approx
        self.CD_q = 0.0
        self.CD_de = 0.0

        self.Cm_alpha = -0.9
        self.Cm_q = -12.4
        self.Cm_de = -1.28
        self.Cm_alphadot = -2.5 # Downwash lag

        # Lateral Derivatives (Simplified)
        self.Cy_beta = -0.3
        self.Cl_beta = -0.1
        self.Cn_beta = 0.1

        self.Cl_p = -0.5
        self.Cn_r = -0.15

class Cessna172(Aircraft):
    def __init__(self):
        super().__init__("Cessna 172")
