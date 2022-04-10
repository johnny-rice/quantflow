# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.8
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # From Characteristic Function to PDF
#
# * [Fourier Transfrom and Characteristic Functions](https://faculty.baruch.cuny.edu/lwu/890/ADP_Transform.pdf)
# * [Option Pricing using the Fractional FFT](https://faculty.baruch.cuny.edu/lwu/890/ChourdakisFRFT_JCF2005.pdf)
# * [Fourier Transforms Methods](https://www.uv.es/bfc/TFM2014/008-014.pdf)

# %% [markdown]
# To obtain the PDF from a characteristic function one uses the inverse Fourier transfrom formula
#
# \begin{equation}
#   f(x) = \frac{1}{2\pi}\int_{-\infty}^\infty e^{-iux} \Phi_x\left(u\right) du = \frac{1}{\pi} {\mathcal R} \int_0^\infty e^{-iux} \Phi_u du
# \end{equation}
#
# The last equivalence is due to the fact that the PDF is a real valued.

# %% [markdown] tags=[]
# ## FFT Integration
#
# FFT is an efficient algorithm for computing discrete Fourier coefficients $d$ from $f$. Gievn an event number $N=2^n$, these are given by
#
# \begin{equation}
# d_j = \frac{1}{N}\sum_{m=0}^{N-1} f_m e^{-jm\frac{2\pi}{N} i}\ \ j=0, 1, \dots, N-1
# \end{equation}
#
# The PDF integration can be approximated using the trapezoidal rule:
#
# \begin{align}
# u_m &= \delta_u m \\ 
# f(x) &\approx \frac{1}{\pi}\sum_{m=0}^{N-1} h_m e^{-i u_m x} \Phi_x\left(u_m\right) \delta_u
# \end{align}
#
# Where $h_m$ is given by the integration methodology, either trapezoidal or simpson rule.
# The approximation can be rewritten as
#
# \begin{align}
# x_j &= -b + \delta_x j \\
# \zeta &= \delta_u \delta_x \\
# f_m &= h_m \frac{N}{\pi} e^{i u_m b} \Phi_x\left(u_m\right) \delta_u\\
# f(x_j) &\approx \frac{1}{N} \sum_{m=0}^{N-1} f_m e^{-j m \zeta i}
# \end{align}
#
# The parameter $b$ controls the range of the random variable $x$, while $\delta_u$ is the discretization in the frequency domain and must be small enough to provide good accuracy of the integral. Finally $N$ must be large enough that the characteristic function is virtually 0 for $u_{N-1}=\delta_u N$.
#
# The FFT requires
#
# \begin{equation}
# \zeta = \frac{2\pi}{N}
# \end{equation}
#
# which means $\delta_u$ and $\delta_x$ cannot be chosen indipendently.

# %%
from quantflow.sp.weiner import Weiner
p = Weiner(0.5)
m = p.marginal(1)
m.std()

# %%
import plotly.express as px
import pandas as pd
N = 128*2*2
M = 50
freq = m.frequency_space(N, M)
df = pd.DataFrame(dict(frequency=freq, psi=m.characteristic(freq)))
fig = px.line(df, x="frequency", y="psi", markers=True)
fig.show()

# %%
import plotly.graph_objects as go
from scipy.stats import norm
r = m.pdf_from_characteristic(N, M)
n = norm.pdf(r["x"], scale=m.std())
fig = px.line(r, x="x", y="y", markers=True)
fig.add_trace(go.Scatter(x=r["x"], y=n, name="analytical", line=dict()))
fig.show()

# %% [markdown]
# ## FRFT
# Compared to the FFT, this method relaxes the constraint $\zeta=2\pi/N$ so that frequency domain and strike domains can be discretized independently.
#
# \begin{align}
# y &= \left(\left[e^{-i j^2 \zeta/2}\right]_{j=0}^{N-1}, \left[0\right]_{j=0}^{N-1}\right) \\
# z &= \left(\left[e^{i j^2 \zeta/2}\right]_{j=0}^{N-1}, \left[e^{i\left(N-j\right)^2 \zeta/2}\right]_{j=0}^{N-1}\right)
# \end{align}
#
# We can now reduce the number of points needed for the discretization and achieve higher accuracy by properly selecting the domain discretization independently.

# %%
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import norm
import numpy as np

N = 64
M = 8
dx = 4/N
r = m.pdf_from_characteristic(N, M, dx)
n = norm.pdf(r["x"], scale=m.std())
fig = px.line(r, x="x", y="y", markers=True)
fig.add_trace(go.Scatter(x=r["x"], y=n, name="analytical", line=dict()))
fig.show()

# %%
