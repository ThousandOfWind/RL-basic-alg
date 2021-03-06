import copy
import torch as th
from torch.optim import Adam
from torch.distributions import Categorical
import torch.nn.functional as F

import os
from .model.base import DNNAgent
from .model.critic import DNN


class ACLearner:
    """
    1. DQN- RNNAgent
    2. train
    """

    def __init__(self, param_set, writer):
        self.obs_shape = param_set['obs_shape'][0]
        self.gamma = param_set['gamma']
        self.learning_rate = param_set['learning_rate']

        self.pi = DNNAgent(param_set)
        self.V = DNN(param_set)

        self.params = [
                        {'params': self.pi.parameters()},
                        {'params': self.V.parameters()}
                    ]
        self.optimiser = Adam(self.params, lr=self.learning_rate)

        self.writer = writer
        self._episode = 0

        self.log_pi_batch = []
        self.value_batch = []


    def new_trajectory(self):
        self.log_pi_batch = []
        self.value_batch = []


    def get_action(self, observation, *arg):
        obs = th.FloatTensor(observation)
        pi= self.pi(obs=obs)
        m = Categorical(pi)
        action_index = int(m.sample())

        self.log_pi_batch.append(pi)
        self.value_batch.append(self.V(obs=obs))
        return action_index, pi

    def learn(self, memory):
        batch = memory.get_last_trajectory()

        reward = th.FloatTensor(batch['reward'][0])
        log_pi = th.stack(self.log_pi_batch)

        # build I
        I = [1, ]
        for index in range(1, len(batch['reward'][0])):
            I.append(I[index - 1] * self.gamma)
        I = th.FloatTensor(I)

        value = th.stack(self.value_batch)
        mask = th.ones_like(value)
        mask[-1] = 0
        next_value = th.cat([value[1:], value[0:1]],dim=-1) * mask

        td_error = reward + self.gamma * next_value.detach() - value

        J = - ((I * td_error).detach() * log_pi).mean()
        value_loss = (td_error ** 2).mean()
        loss = J + value_loss

        self.writer.add_scalar('Loss/J', J.item(), self._episode)
        self.writer.add_scalar('Loss/B', value_loss.item(), self._episode)
        self.writer.add_scalar('Loss/loss', loss.item(), self._episode)


        self.optimiser.zero_grad()
        loss.backward()
        grad_norm = th.nn.utils.clip_grad_norm_(self.pi.parameters(), 10)
        grad_norm = th.nn.utils.clip_grad_norm_(self.V.parameters(), 10)
        self.optimiser.step()

        self._episode += 1




