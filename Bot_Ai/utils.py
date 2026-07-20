import os
import yaml


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


class ProgressTracker:
    def __init__(self, window=100):
        self.window = window
        self.rewards = []
        self.lengths = []
        self.losses = []
        self.epsilons = []

    def log_episode(self, reward, length, loss=None, epsilon=None):
        self.rewards.append(reward)
        self.lengths.append(length)
        if loss is not None:
            self.losses.append(loss)
        if epsilon is not None:
            self.epsilons.append(epsilon)

    def avg_reward(self):
        if not self.rewards:
            return 0.0
        return sum(self.rewards[-self.window:]) / len(self.rewards[-self.window:])

    def avg_length(self):
        if not self.lengths:
            return 0.0
        return sum(self.lengths[-self.window:]) / len(self.lengths[-self.window:])

    def avg_loss(self):
        if not self.losses:
            return 0.0
        return sum(self.losses[-self.window:]) / len(self.losses[-self.window:])

    def current_epsilon(self):
        return self.epsilons[-1] if self.epsilons else 1.0

    def summary(self):
        return (
            f"Reward: {self.avg_reward():.2f} | "
            f"Length: {self.avg_length():.1f} | "
            f"Loss: {self.avg_loss():.4f} | "
            f"Eps: {self.current_epsilon():.3f}"
        )
