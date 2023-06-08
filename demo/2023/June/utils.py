import os
import pickle

import numpy as np
import qiskit

try:
    from qiskit.providers.tergite import Tergite
except:
    print('Could not import Tergite!')


class Utils:

    @staticmethod
    def get_backend(name: str):
        if name == 'AerSimulator':
            return qiskit.Aer.get_backend('aer_simulator')
        elif name is None:
            raise RuntimeError('Calling backend without providing name')
        else:
            tergite_provider = Tergite.get_provider()
            backend = tergite_provider.get_backend(name)
            backend.set_options(shots=1024)
            return backend

    @staticmethod
    def append_thetas(run_id: str, thetas: np.ndarray):
        filename = f'{run_id}.thetas'
        stored_thetas = np.array([])
        if filename in os.listdir():
            stored_thetas = pickle.load(open(filename, 'rb'))
        stored_thetas = np.concatenate((stored_thetas, np.array(thetas)))
        pickle.dump(stored_thetas, open(filename, 'wb'))

    @staticmethod
    def load_thetas(run_id: str):
        filename = f'{run_id}.thetas'
        return pickle.load(open(filename, 'rb'))
