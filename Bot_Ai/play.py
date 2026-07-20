import time
import numpy as np
import torch
from gd_env import GeometryDashEnv
from agent import DQNAgent
from utils import load_config
from visualizer import AIVisualizer


def play():
    config = load_config()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    n_actions = 2
    input_shape = (
        config["preprocessing"]["frame_stack"],
        config["preprocessing"]["resize_width"],
        config["preprocessing"]["resize_height"],
    )

    agent = DQNAgent(input_shape, n_actions, config, device=device)
    vis = AIVisualizer("GD AI - Playing")

    model_path = config["training"]["model_save_path"]
    try:
        agent.load(model_path)
        print(f"Loaded model: {model_path}")
        print(f"Epsilon: {agent.epsilon:.3f} | Steps trained: {agent.steps}")
    except (FileNotFoundError, RuntimeError) as e:
        print(f"No trained model found ({e}). Running randomly.")

    env = GeometryDashEnv(config)
    print("\nPlaying... Press 'Q' in visualizer or Ctrl+C to stop.\n")

    try:
        episode = 0
        while True:
            episode += 1
            state = env.reset()
            total_reward = 0.0
            step = 0

            for step in range(config["training"]["max_steps_per_episode"]):
                action = agent.act(state, eval_mode=True)
                next_state, reward, done, _ = env.step(action)

                state = next_state
                total_reward += reward

                if step % 4 == 0:
                    q_vals = agent.get_q_values(state)
                    raw = env.get_last_raw_frame()
                    if raw is None:
                        raw = np.zeros((84, 84, 3), dtype=np.uint8)
                    info = [
                        f"Episode: {episode} | Step: {step}",
                        f"Reward: {total_reward:.2f}",
                        f"Action: {'JUMP' if action == 1 else 'NO JUMP'}",
                        f"Q: no={q_vals[0]:.2f} jump={q_vals[1]:.2f}",
                    ]
                    vis.update_q_values(q_vals, action)
                    vis.set_info(info)
                    key = vis.render(state, raw)
                    if key == ord("q") or key == ord("Q"):
                        raise KeyboardInterrupt
                    time.sleep(0.01)

                if done:
                    break

            print(f"Ep {episode:4d} | Reward: {total_reward:+7.2f} | Steps: {step+1:5d}")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        vis.close()
        env.close()


if __name__ == "__main__":
    play()
