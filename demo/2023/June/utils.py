import pickle
import os

import numpy as np


def append_thetas(run_id: str, thetas: np.ndarray):
    filename = f'{run_id}.thetas'
    stored_thetas = np.array([])
    if filename in os.listdir():
        stored_thetas = pickle.load(open(filename, 'rb'))
    stored_thetas = np.concatenate((stored_thetas, np.array(thetas)))
    pickle.dump(stored_thetas, open(filename, 'wb'))


def load_thetas(run_id: str):
    filename = f'{run_id}.thetas'
    return pickle.load(open(filename, 'rb'))
