from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

import numpy as np
import numpy.typing as npt
from scipy.optimize import Bounds

from .types import FloatArray


class TransformError(RuntimeError):
    pass


class TransformResult(NamedTuple):
    """Result of a transform"""

    x: FloatArray
    y: np.ndarray


def grid(n: int) -> npt.NDArray[np.int_]:
    return np.arange(0, n, 1)


def trapezoid(n: int) -> FloatArray:
    h = np.ones(n)
    h[0] = 0.5
    return h


def simpson(n: int) -> FloatArray:
    h = np.ones(n)
    h[1::2] = 4
    h[2::2] = 2
    return h / 3


def default_bounds() -> Bounds:
    return Bounds(-np.inf, np.inf)


def lower_bound(b: Any, value: float) -> float:
    try:
        v = float(b[0])
        return value if np.isinf(v) else v
    except TypeError:
        return value


def upper_bound(b: Any, value: float) -> float:
    try:
        v = float(b[0])
        return value if np.isinf(v) else v
    except TypeError:
        return value


class Transform:
    """Transforms for option pricing"""

    def __init__(
        self,
        n: int | None = None,
        max_frequency: float | None = None,
        domain_range: Bounds | None = None,
        simpson_rule: bool = False,
    ) -> None:
        n = n or 128
        max_frequency = max_frequency or 20.0
        self.delta_f = max_frequency / n
        self.frequency_domain = self.delta_f * grid(n)
        self.domain_range = domain_range or default_bounds()
        self.h = simpson(n) if simpson_rule else trapezoid(n)

    @property
    def n(self) -> int:
        """Number of discretization points in the frequency and space domain"""
        return self.frequency_domain.shape[0]

    @property
    def fft_zeta(self) -> float:
        return 2 * np.pi / self.n

    @property
    def fft_delta_x(self) -> float:
        return self.fft_zeta / self.delta_f

    def space_domain(self, delta_x: float) -> FloatArray:
        """Return the space domain discretization points"""
        b0 = lower_bound(self.domain_range.lb, -0.5 * delta_x * self.n)
        b1 = upper_bound(self.domain_range.ub, delta_x * self.n + b0)
        if not np.isclose((b1 - b0) / self.n, delta_x):
            raise TransformError("Incompatible delta_x with domain bounds")
        return delta_x * grid(self.n) + b0

    def __call__(self, y: np.ndarray, delta_x: float | None = None) -> TransformResult:
        return self.fft(y) if delta_x is None else self.frft(y, delta_x)

    def fft(self, y: np.ndarray) -> TransformResult:
        """Transform using the Fast Fourier Transform"""
        x, f = self.transform(y, self.fft_delta_x)
        return TransformResult(x=x, y=np.fft.fft(f).real / self.n)

    def frft(self, y: np.ndarray, delta_x: float) -> TransformResult:
        """Transform using the Fractional Fourier Transform"""
        x, f = self.transform(y, delta_x)
        r = FrFT.calculate(f, delta_x * self.delta_f)
        return TransformResult(x=x, y=r.result.real)

    def transform(self, y: np.ndarray, delta_x: float) -> TransformResult:
        if y.shape != self.frequency_domain.shape:
            raise TransformError("shapes not compatible")
        x = self.space_domain(delta_x)
        b = -x[0]
        t = (
            self.h
            * self.n
            * np.exp(1j * self.frequency_domain * b)
            * y
            * self.delta_f
            / np.pi
        )
        return TransformResult(x=x, y=t)


@dataclass
class FrFT:
    """Fractional Fourier Transfrom"""

    result: np.ndarray
    zeta: float
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    fft_y: np.ndarray
    fft_z: np.ndarray
    y_z: np.ndarray

    @property
    def n(self) -> int:
        return self.result.shape[0]

    @classmethod
    def calculate(cls, x: np.ndarray, zeta: float) -> FrFT:
        n = x.shape[0]
        g = grid(n)
        ez = coef(g, zeta)
        # ez2 = np.flip(ez)
        ez2 = coef(n - g, zeta)
        ezi = 1 / ez
        y = np.concatenate((x * ezi, np.zeros(n)))
        z = np.concatenate((ez, ez2))
        fft_y = np.fft.fft(y)
        fft_z = np.fft.fft(z)
        y_z = np.fft.ifft(fft_y * fft_z) / n
        result = ezi * y_z[:n]
        return cls(
            result=result,
            x=x,
            zeta=zeta,
            y=y,
            z=z,
            fft_y=fft_y,
            fft_z=fft_z,
            y_z=y_z,
        )


def coef(g: np.ndarray, zeta: float) -> np.ndarray:
    return np.exp(0.5 * 1j * g * g * zeta)
