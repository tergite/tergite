from enum import Enum

import qiskit
try:
    from qiskit.providers.tergite import Tergite
except:
    print('Could not import Tergite!')

class BackendSwitch:
    @staticmethod
    def get(name:str):
        if name == 'simulator':
            return qiskit.Aer
        elif name == 'LokeAB_TEST':
            tergite_provider = Tergite.get_provider()
            return tergite_provider.get_backend('LokeAB_TEST')

class Backends(Enum):

    Simulator = BackendSwitch.get('simulator')
    QAL9000 = BackendSwitch.get('Nov_rain')
