import numpy as np
import torch
from torch.utils.data import Dataset


class IQDataset(Dataset):
    def __init__(self, data, targets):
        self.data = data
        self.targets = targets

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.data[index], self.targets[index]


class IQDataGenerator:
    @staticmethod
    def get_2d_binary_class(
        n_samples=100,
        mean_zeros=np.array([1, 1]),
        mean_ones=np.array([-1, -2]),
        cov_zeros=np.array([[0.3, 0.6], [0.8, -0.4]]),
        cov_ones=np.array([[-0.4, 0.4], [0.7, 0.6]]),
    ):
        zeros = np.random.multivariate_normal(mean_zeros, cov_zeros, n_samples)
        ones = np.random.multivariate_normal(mean_ones, cov_ones, n_samples)

        datapoints = np.append(zeros, ones).reshape((n_samples * 2, 2))
        targets = np.append(
            [0 for _ in range(n_samples)], [1 for _ in range(n_samples)]
        )

        datapoints_tensor = torch.from_numpy(datapoints).float()
        targets_tensor = torch.from_numpy(targets).long()

        return IQDataset(datapoints_tensor, targets_tensor)
