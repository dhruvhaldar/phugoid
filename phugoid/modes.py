import numpy as np

class Mode:
    def __init__(self, eigenvalue, name="Unknown"):
        self.eigenvalue = eigenvalue
        self.name = name
        self.wn, self.zeta = self._analyze()

    def _analyze(self):
        n = self.eigenvalue.real
        omega = self.eigenvalue.imag

        wn = np.sqrt(n**2 + omega**2)

        if wn == 0:
            zeta = 0
        else:
            zeta = -n / wn

        return wn, zeta

    def __repr__(self):
        return f"{self.name}: Eval={self.eigenvalue:.4f}, Wn={self.wn:.4f}, Zeta={self.zeta:.4f}"

def calculate_damping_ratio(eigenvalue):
    n = eigenvalue.real
    omega = eigenvalue.imag
    wn = np.sqrt(n**2 + omega**2)
    if wn == 0:
        return 0.0
    return -n / wn

def calculate_natural_frequency(eigenvalue):
    n = eigenvalue.real
    omega = eigenvalue.imag
    return np.sqrt(n**2 + omega**2)
