import enum

import numpy as np
from numpy.random import normal
from pydantic import Field
from scipy import special

from quantflow.utils.types import Vector

from .base import Im, IntensityProcess, StochasticProcess1DMarginal


class SamplingAlgorithm(str, enum.Enum):
    euler = "euler"
    milstein = "milstein"
    implicit = "implicit"


class CIR(IntensityProcess):
    r"""The Cox–Ingersoll–Ross (CIR) model is a mean-reverting square-root diffusion
    process.

    The process :math:`x_t` that satisfies the following stochastic
    differential equation with Wiener process :math:`w_t`:

    .. math::
        dx_t = \kappa (\theta - x_t) dt + \sigma \sqrt{x_t}dw_t

    This process is guaranteed to be positive if

    .. math::
        2 \kappa \theta >= \sigma^2

    :param rate: The initial value of the process :math:`x_0`
    :param kappa: Mean reversion speed :math:`\kappa`
    :param sigma: Volatility parameter :math:`\sigma`
    :param theta: Long term mean rate :math:`\theta`
    """
    sigma: float = Field(default=1.0, gt=0, description="Volatility")
    theta: float = Field(default=1.0, gt=0, description="Mean rate")
    sample_algo: SamplingAlgorithm = Field(
        default=SamplingAlgorithm.implicit, description="Sampling algorithm"
    )

    @property
    def is_positive(self) -> bool:
        return self.kappa * self.theta >= 0.5 * self.sigma2

    @property
    def sigma2(self) -> float:
        return self.sigma * self.sigma

    def marginal(self, t: float, N: int = 128) -> StochasticProcess1DMarginal:
        return CIRMarginal(self, t, N)

    def sample(self, n: int, t: float = 1, steps: int = 0) -> np.ndarray:
        match self.sample_algo:
            case SamplingAlgorithm.euler:
                return self.sample_euler(n, t, steps)
            case SamplingAlgorithm.milstein:
                return self.sample_euler(n, t, steps, 0.25)
            case SamplingAlgorithm.implicit:
                return self.sample_implicit(n, t, steps)

    def sample_euler(
        self, n: int, t: float = 1, steps: int = 0, ic: float = 0
    ) -> np.ndarray:
        """Use an Euler scheme to sample the process.

        The implementation preserve the positivity of the process even if the
        Feller condition is not satisfied.
        """
        time_steps, dt = self.sample_dt(t, steps)
        kappa = self.kappa
        theta = self.theta
        sdt = self.sigma * np.sqrt(dt)
        sdt2 = sdt * sdt
        paths = np.zeros((time_steps + 1, n))
        paths[0, :] = self.rate
        for t in range(time_steps):
            w = normal(scale=sdt, size=n)
            x = paths[t, :]
            xplus = np.clip(x, 0, None)
            dx = kappa * (theta - xplus) * dt + np.sqrt(xplus) * w + ic * (w * w - sdt2)
            paths[t + 1, :] = x + dx
        return paths

    def sample_implicit(self, n: int, t: float = 1, steps: int = 0) -> np.ndarray:
        """Use an implicit scheme to preserve positivity of the process."""
        time_steps, dt = self.sample_dt(t, steps)
        kappa = self.kappa
        theta = self.theta
        kdt2 = 2 * (1 + kappa * dt)
        kts = (kappa * theta - 0.5 * self.sigma2) * dt
        sdt = self.sigma * np.sqrt(dt)
        paths = np.zeros((time_steps + 1, n))
        paths[0, :] = self.rate
        for t in range(time_steps):
            w = normal(scale=sdt, size=n)
            x = paths[t, :]
            w2p = np.clip(w * w + 2 * (x + kts) * kdt2, 0, None)
            xs = (w + np.sqrt(w2p)) / kdt2
            paths[t + 1, :] = xs * xs
        return paths

    def characteristic(self, t: float, u: Vector) -> Vector:
        iu = Im * u
        sigma = self.sigma
        kappa = self.kappa
        kt = kappa * t
        ekt = np.exp(kt)
        sigma2 = sigma * sigma
        s2u = iu * sigma2
        c = s2u + (2 * kappa - s2u) * ekt
        b = 2 * kappa * iu / c
        a = 2 * kappa * self.theta * (kt + np.log(2 * kappa / c)) / sigma2
        return np.exp(a + b * self.rate)

    def cumulative_characteristic(self, t: float, u: Vector) -> Vector:
        iu = Im * u
        sigma = self.sigma
        kappa = self.kappa
        sigma2 = sigma * sigma
        gamma = np.sqrt(kappa * kappa - 2 * iu * sigma2)
        egt = np.exp(gamma * t)
        c = (gamma + kappa) * (1 - egt) - 2 * gamma
        d = 2 * gamma * np.exp(0.5 * (gamma + kappa) * t)
        a = 2 * self.theta * kappa * np.log(-d / c) / sigma2
        b = 2 * iu * (1 - egt) / c
        return np.exp(a + b * self.rate)


class CIRMarginal(StochasticProcess1DMarginal[CIR]):
    def mean(self) -> float:
        ekt = np.exp(-self.process.kappa * self.t)
        return self.process.rate * ekt + self.process.theta * (1 - ekt)

    def std(self) -> float:
        kappa = self.process.kappa
        ekt = np.exp(-kappa * self.t)
        return np.sqrt(
            self.process.sigma2
            * (1 - ekt)
            * (self.process.rate * ekt + 0.5 * self.process.theta * (1 - ekt))
            / kappa
        )

    def pdf(self, x: Vector) -> Vector:
        k = self.process.kappa
        s2 = self.process.sigma2
        ekt = np.exp(-k * self.t)
        c = 2 * k / (1 - ekt) / s2
        q = 2 * k * self.process.theta / s2 - 1
        u = c * ekt * self.process.rate
        v = c * x
        return (
            c
            * np.exp(-v - u)
            * np.power(v / u, 0.5 * q)
            * special.iv(q, 2 * np.sqrt(u * v))
        )
