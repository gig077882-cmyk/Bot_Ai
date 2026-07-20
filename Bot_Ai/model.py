import torch
import torch.nn as nn
import json


class DuelingDQN(nn.Module):
    def __init__(self, input_shape, n_actions):
        super().__init__()
        self.input_shape = input_shape
        self.n_actions = n_actions
        c, h, w = input_shape

        self.conv = nn.Sequential(
            nn.Conv2d(c, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
        )

        with torch.no_grad():
            dummy = torch.zeros(1, c, h, w)
            conv_out = self.conv(dummy)
            conv_flat_size = conv_out.view(1, -1).size(1)

        self.fc_value = nn.Sequential(
            nn.Linear(conv_flat_size, 512), nn.ReLU(), nn.Linear(512, 1)
        )

        self.fc_advantage = nn.Sequential(
            nn.Linear(conv_flat_size, 512), nn.ReLU(), nn.Linear(512, n_actions)
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Conv2d)):
                nn.init.kaiming_uniform_(m.weight, mode="fan_in", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        value = self.fc_value(x)
        advantage = self.fc_advantage(x)
        return value + advantage - advantage.mean(dim=1, keepdim=True)

    def get_config(self):
        return {"input_shape": list(self.input_shape), "n_actions": self.n_actions}


def create_model(input_shape, n_actions, device="cpu"):
    model = DuelingDQN(input_shape, n_actions)
    return model.to(device)


def load_model(path, device="cpu"):
    with open(path.replace(".pth", "_cfg.json"), "r") as f:
        cfg = json.load(f)
    model = DuelingDQN(tuple(cfg["input_shape"]), cfg["n_actions"])
    model.load_state_dict(torch.load(path, map_location=device, weights_only=True))
    return model.to(device)


def save_model(model, path):
    torch.save(model.state_dict(), path)
    cfg_path = path.replace(".pth", "_cfg.json")
    with open(cfg_path, "w") as f:
        json.dump(model.get_config(), f)
