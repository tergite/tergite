import typing

import numpy as np
import qiskit
import torch
import torch.nn as nn
import torch.nn.functional as F
from circuits import HybridLayerCircuit
from torch import optim
from torch.autograd import Function
from tqdm import tqdm


class HybridFunction(Function):
    """Hybrid quantum - classical function definition"""

    @staticmethod
    def forward(ctx, input, quantum_circuit, shift):
        """Forward pass computation"""
        ctx.shift = shift
        ctx.quantum_circuit = quantum_circuit

        expectation_z = ctx.quantum_circuit.run(input[0].tolist())
        result = torch.tensor([expectation_z])
        ctx.save_for_backward(input, result)

        return result

    @staticmethod
    def backward(ctx, grad_output):
        """Backward pass computation"""
        input, expectation_z = ctx.saved_tensors
        input_list = np.array(input.tolist())

        shift_right = input_list + np.ones(input_list.shape) * ctx.shift
        shift_left = input_list - np.ones(input_list.shape) * ctx.shift

        gradients = []
        for i in range(len(input_list)):
            expectation_right = ctx.quantum_circuit.run(shift_right[i])
            expectation_left = ctx.quantum_circuit.run(shift_left[i])

            gradient = torch.tensor([expectation_right]) - torch.tensor(
                [expectation_left]
            )
            gradients.append(gradient)
        # gradients = np.array([gradients]).T
        # gradients = torch.t(torch.stack(gradients))
        gradients = torch.stack(gradients)
        return gradients.double() * grad_output.double(), None, None


class Hybrid(nn.Module):
    """Hybrid quantum - classical layer definition"""

    def __init__(
        self,
        backend: qiskit.providers.Backend,
        shots: int,
        shift,
        qubits: typing.List[int] = None,
        run_id: str = "default",
    ):
        super(Hybrid, self).__init__()
        self.quantum_circuit = HybridLayerCircuit(
            backend=backend, shots=shots, qubits=qubits, run_id=run_id
        )
        self.shift = shift
        self.run_id = run_id

    def forward(self, input):
        return HybridFunction.apply(input, self.quantum_circuit, self.shift)


class Net(nn.Module):
    def __init__(
        self,
        run_id,
        n_qubits: int = 1,
        qubits: typing.List[int] = None,
        backend=qiskit.Aer.get_backend("aer_simulator"),
        shots: int = 1024,
        n_neurons: int = 16,
    ):
        super(Net, self).__init__()

        # TODO: We could fine tune here, if we want to have qubits bins and more combinations of layers
        # in_hybrid_layer = n_qubits if qubits is None else len(qubits)
        in_hybrid_layer = 1

        self.run_id = run_id

        self.fc1 = nn.Linear(2, n_neurons)
        self.fc2 = nn.Linear(n_neurons, in_hybrid_layer)

        self.hybrid = Hybrid(backend, shots, np.pi / 2, qubits=qubits, run_id=run_id)

    def forward(self, x):
        x = x.view(1, -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        x = self.hybrid(x)
        return torch.cat((x, 1 - x), -1)


def train_model(
    model: nn.Module, train_loader, epochs: int, plot: bool = False
) -> typing.Tuple["nn.Module", typing.List[float]]:
    # TODO: If one would like to write a beautiful ML framework, it might be better to pass the optimizer as a parameter
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    loss_func = nn.NLLLoss()

    loss_list = []

    model.train()
    for epoch in range(epochs):
        total_loss = []
        for batch_idx, (data, target) in tqdm(
            enumerate(train_loader), desc=f"{epoch = }", unit="samples"
        ):
            optimizer.zero_grad()
            output = model(data)
            loss = loss_func(output, target)
            loss.backward()
            optimizer.step()

            total_loss.append(loss.item())

        loss_list.append(sum(total_loss) / len(total_loss))

        print(
            "\nTraining [{:.0f}%]\tLoss: {:.4f}".format(
                100.0 * (epoch + 1) / epochs, loss_list[-1]
            )
        )

    return model, loss_list


def eval_model(model: nn.Module, eval_loader):
    model.eval()
    loss_func = nn.NLLLoss()
    total_loss = []
    with torch.no_grad():
        correct = 0
        for batch_idx, (data, target) in enumerate(eval_loader):
            output = model(data)

            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

            loss = loss_func(output, target)
            total_loss.append(loss.item())

        accuracy = sum(total_loss) / len(total_loss)
        print(
            "Performance on test data:\n\tLoss: {:.4f}\n\tAccuracy: {:.1f}%".format(
                accuracy, correct / len(eval_loader) * 100
            )
        )

    return accuracy
