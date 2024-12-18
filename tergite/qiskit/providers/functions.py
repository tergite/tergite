# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import numpy as np
from sympy import And, Piecewise, S, cos, pi, symbols


def delta_t_function(t, args):
    """
    Vectorized envelope function δ(t) as a function of time.

    Returns:
    - delta_t: the value of δ(t) (same shape as t)
    """
    t_w = args["t_w"]
    t_rf = args["t_rf"]
    t_p = args["t_p"]
    delta_0 = args["delta_0"]

    condlist = [
        t <= t_w,
        (t > t_w) & (t <= t_w + t_rf / 2),
        (t > t_w + t_rf / 2) & (t < t_w + t_rf / 2 + t_p),
        (t >= t_w + t_rf / 2 + t_p) & (t < t_w + t_rf + t_p),
        t >= t_w + t_rf + t_p,
    ]
    choicelist = [
        0,
        delta_0 / 2 * (1 - np.cos(2 * np.pi * (t - t_w) / t_rf)),
        delta_0,
        delta_0 / 2 * (1 - np.cos(2 * np.pi * (t - t_w - t_p) / t_rf)),
        0,
    ]
    return np.select(condlist, choicelist)


def delta_t_function_sympy(t, symbolic_args):
    """
    Symbolic envelope function δ(t) as a function of time using SymPy.

    Parameters:
    - t: SymPy symbol representing time.
    - symbolic_args: dictionary containing SymPy symbols for parameters.

    Returns:
    - delta_t: SymPy expression representing δ(t).
    """
    # Unpack symbolic variables, use symbols if not provided
    t_w = symbolic_args.get("t_w", symbols("t_w", real=True))
    t_rf = symbolic_args.get("t_rf", symbols("t_rf", real=True))
    t_p = symbolic_args.get("t_p", symbols("t_p", real=True))
    delta_0 = symbolic_args.get("delta_0", symbols("delta_0", real=True))

    # Define conditions using SymPy relational operators
    cond1 = t <= t_w
    cond2 = And(t > t_w, t <= t_w + t_rf / 2)
    cond3 = And(t > t_w + t_rf / 2, t < t_w + t_rf / 2 + t_p)
    cond4 = And(t >= t_w + t_rf / 2 + t_p, t < t_w + t_rf + t_p)
    cond5 = t >= t_w + t_rf + t_p

    # Define expressions using SymPy functions
    expr1 = S.Zero
    expr2 = delta_0 / 2 * (1 - cos(2 * pi * (t - t_w) / t_rf))
    expr3 = delta_0
    expr4 = delta_0 / 2 * (1 - cos(2 * pi * (t - t_w - t_p) / t_rf))
    expr5 = S.Zero

    # Create the Piecewise function
    delta_t = Piecewise(
        (expr1, cond1),
        (expr2, cond2),
        (expr3, cond3),
        (expr4, cond4),
        (expr5, cond5),
    )
    return delta_t
