#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 0.1, 1000)
y = lambda A, f, p, c: (lambda x: A * np.cos(2 * np.pi * f * x + p) + c)

rabi = dict(
    A=0.0005359157063677955,
    f=12.804569197752492,
    p=3.0860149959473757,
    c=0.006761848591580204,
)

fig, ax = plt.subplots()
ax.plot(x, y(**rabi)(x))


def b(theta):
    global rabi
    return rabi["A"] * np.cos(theta + rabi["p"]) + rabi["c"]


for theta in np.linspace(0, np.pi, 20):
    ax.scatter(theta / (2 * np.pi * rabi["f"]), b(theta), color="red")
