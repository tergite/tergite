import numpy as np
import qiskit
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Function

from circuits import HybridLayerCircuit
from utils import append_thetas


class HybridFunction(Function):
    """ Hybrid quantum - classical function definition """

    @staticmethod
    def forward(ctx, input, quantum_circuit, shift):
        """ Forward pass computation """
        ctx.shift = shift
        ctx.quantum_circuit = quantum_circuit

        expectation_z = ctx.quantum_circuit.run(input[0].tolist())
        result = torch.tensor([expectation_z])
        ctx.save_for_backward(input, result)

        return result

    @staticmethod
    def backward(ctx, grad_output):
        """ Backward pass computation """
        input, expectation_z = ctx.saved_tensors
        input_list = np.array(input.tolist())

        shift_right = input_list + np.ones(input_list.shape) * ctx.shift
        shift_left = input_list - np.ones(input_list.shape) * ctx.shift

        gradients = []
        for i in range(len(input_list)):
            expectation_right = ctx.quantum_circuit.run(shift_right[i])
            expectation_left = ctx.quantum_circuit.run(shift_left[i])

            gradient = torch.tensor([expectation_right]) - torch.tensor([expectation_left])
            gradients.append(gradient)
        # gradients = np.array([gradients]).T
        # gradients = torch.t(torch.stack(gradients))
        gradients = torch.stack(gradients)
        return gradients.double() * grad_output.double(), None, None


class Hybrid(nn.Module):
    """ Hybrid quantum - classical layer definition """

    def __init__(self, backend: qiskit.providers.Backend, shots, shift, run_id: str = 'default'):
        super(Hybrid, self).__init__()
        self.quantum_circuit = HybridLayerCircuit(backend=backend, shots=shots, run_id=run_id)
        self.shift = shift
        self.run_id = run_id

    def forward(self, input):
        return HybridFunction.apply(input, self.quantum_circuit, self.shift)


class Net(nn.Module):
    def __init__(self, run_id,
                 n_qubits: int = 1,
                 backend=qiskit.Aer.get_backend('aer_simulator')):
        super(Net, self).__init__()

        self.run_id = run_id

        self.fc1 = nn.Linear(2, 128)
        self.fc2 = nn.Linear(128, n_qubits)

        self.hybrid = Hybrid(backend, 100, np.pi / 2, run_id=run_id)

    def forward(self, x):
        x = x.view(1, -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        x = self.hybrid(x)
        return torch.cat((x, 1 - x), -1)
