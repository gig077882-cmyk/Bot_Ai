import random
import numpy as np
import torch
import torch.nn.functional as F
from collections import deque

from model import create_model


class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states))
        actions = torch.LongTensor(np.array(actions)).unsqueeze(1)
        rewards = torch.FloatTensor(np.array(rewards))
        next_states = torch.FloatTensor(np.array(next_states))
        dones = torch.FloatTensor(np.array(dones))

        return states, actions, rewards, next_states, dones

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    def __init__(self, input_shape, n_actions, config, device="cuda"):
        self.device = device
        self.input_shape = input_shape
        self.n_actions = n_actions

        self.model = create_model(input_shape, n_actions, device)
        self.target_model = create_model(input_shape, n_actions, device)
        self.target_model.load_state_dict(self.model.state_dict())
        self.target_model.eval()

        self.lr = config["training"]["learning_rate"]
        self.gamma = config["training"]["gamma"]
        self.batch_size = config["training"]["batch_size"]
        self.target_update_freq = config["training"]["target_update_freq"]

        self.epsilon = config["training"]["epsilon_start"]
        self.epsilon_end = config["training"]["epsilon_end"]
        self.epsilon_decay = config["training"]["epsilon_decay"]

        buffer_size = config["training"]["replay_buffer_size"]
        self.replay_buffer = ReplayBuffer(buffer_size)

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        self.steps = 0

    def act(self, state, eval_mode=False):
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.model(state_t)
        if not eval_mode and random.random() < self.epsilon:
            return random.randrange(self.n_actions)
        return q_values.argmax().item()

    def get_q_values(self, state):
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        with torch.no_grad():
            q_values = self.model(state_t)
        return q_values.cpu().numpy()[0]

    def update(self):
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.batch_size
        )
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        with torch.no_grad():
            next_q = self.target_model(next_states)
            max_next_q = next_q.max(dim=1, keepdim=True)[0]
            target_q = rewards.unsqueeze(1) + self.gamma * max_next_q * (
                1 - dones.unsqueeze(1)
            )

        current_q = self.model(states).gather(1, actions)
        loss = F.mse_loss(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
        self.optimizer.step()

        self.steps += 1

        if self.steps % self.target_update_freq == 0:
            self.target_model.load_state_dict(self.model.state_dict())

        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        return loss.item()

    def save(self, path):
        from model import save_model
        save_model(self.model, path)
        torch.save(
            {
                "target_state_dict": self.target_model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "epsilon": self.epsilon,
                "steps": self.steps,
            },
            path.replace(".pth", "_agent.pth"),
        )

    def load(self, path):
        from model import load_model
        self.model = load_model(path, self.device)
        self.model.to(self.device)
        agent_data = torch.load(
            path.replace(".pth", "_agent.pth"), map_location=self.device
        )
        self.target_model = create_model(self.input_shape, self.n_actions, self.device)
        self.target_model.load_state_dict(agent_data["target_state_dict"])
        self.target_model.eval()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        self.optimizer.load_state_dict(agent_data["optimizer_state_dict"])
        self.epsilon = agent_data["epsilon"]
        self.steps = agent_data["steps"]
