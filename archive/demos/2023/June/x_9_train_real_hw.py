from datetime import datetime

import torch
from data_handling import IQDataGenerator
from learning import Net, eval_model, train_model
from torch.utils.data import DataLoader
from utils import Utils

# Set this global ID to some value or the model value that you want to learn
RUN_ID = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

# TODO: how many qubits do we wanna use?
QUBITS = [i for i in range(9)]
N_QUBITS = len(QUBITS)
SHOTS = 1024

TRAIN_EPOCHS = 10

N_TRAIN_SAMPLES = 100
N_EVAL_SAMPLES = 20

# TODO: which backend do we wanna use?
BACKEND = Utils.get_backend("new_nine_qubits", shots=SHOTS)

# generate data
train_loader = DataLoader(
    IQDataGenerator.get_2d_binary_class(n_samples=N_TRAIN_SAMPLES),
    batch_size=1,
    shuffle=True,
)
eval_loader = DataLoader(
    IQDataGenerator.get_2d_binary_class(n_samples=N_EVAL_SAMPLES),
    batch_size=1,
    shuffle=True,
)

# init model
model = Net(RUN_ID, n_qubits=N_QUBITS, qubits=QUBITS, backend=BACKEND, shots=SHOTS)

# train model
trained_model, losses = train_model(model, train_loader, TRAIN_EPOCHS)

# save
torch.save(trained_model, f"temp/{RUN_ID}.model")

accuracy = eval_model(trained_model, eval_loader)
