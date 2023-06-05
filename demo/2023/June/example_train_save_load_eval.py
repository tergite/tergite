from datetime import datetime

import torch
import torch.nn as nn
from torch import optim
from torch.utils.data import DataLoader

from conf import Backends
from data_handling import IQDataGenerator
from learning import Net
from utils import load_thetas

RUN_ID = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
N_QUBITS = 2
TRAIN_EPOCHS = 5

N_TRAIN_SAMPLES = 30
N_EVAL_SAMPLES = 10

BACKEND = Backends.Simulator

# generate data
train_loader = DataLoader(IQDataGenerator.get_2d_binary_class(n_samples=N_TRAIN_SAMPLES),
                          batch_size=1,
                          shuffle=True)
eval_loader = DataLoader(IQDataGenerator.get_2d_binary_class(n_samples=N_EVAL_SAMPLES),
                         batch_size=1,
                         shuffle=True)

# init model
model = Net(RUN_ID, n_qubits=N_QUBITS)
optimizer = optim.Adam(model.parameters(),
                       lr=0.001)
loss_func = nn.NLLLoss()

loss_list = []

# train
model.train()
for epoch in range(TRAIN_EPOCHS):
    total_loss = []
    for batch_idx, (data, target) in enumerate(train_loader):

        print(f'--- Training {batch_idx + 1} of {2 * N_TRAIN_SAMPLES} samples in batch {epoch + 1} of {TRAIN_EPOCHS} ---')

        optimizer.zero_grad()
        output = model(data)
        loss = loss_func(output, target)
        loss.backward()
        optimizer.step()

        total_loss.append(loss.item())

    loss_list.append(sum(total_loss) / len(total_loss))

    print('Training [{:.0f}%]\tLoss: {:.4f}'.format(
        100. * (epoch + 1) / TRAIN_EPOCHS, loss_list[-1]))

# save
torch.save(model, f'{RUN_ID}_example.model')

# load
loaded_model = torch.load(f'{RUN_ID}_example.model')

# eval
loaded_model.eval()
with torch.no_grad():
    correct = 0
    for batch_idx, (data, target) in enumerate(eval_loader):
        output = loaded_model(data)

        pred = output.argmax(dim=1, keepdim=True)
        correct += pred.eq(target.view_as(pred)).sum().item()

        loss = loss_func(output, target)
        total_loss.append(loss.item())

    print('Performance on test data:\n\tLoss: {:.4f}\n\tAccuracy: {:.1f}%'.format(
        sum(total_loss) / len(total_loss),
        correct / len(eval_loader) * 100)
    )

thetas = load_thetas(RUN_ID)
