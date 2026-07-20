import time
import numpy as np
import torch
from gd_env import GeometryDashEnv
from agent import DQNAgent
from utils import load_config, ensure_dir, ProgressTracker
from visualizer import AIVisualizer


def train():
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

    save_path = config["training"]["model_save_path"]
    ensure_dir(save_path)

    env = GeometryDashEnv(config)
    vis = AIVisualizer()
    tracker = ProgressTracker(window=100)
    best_reward = float("-inf")
    episode = 0

    print(f"Episodes: {config['training']['total_episodes']}")
    print(f"Batch size: {config['training']['batch_size']}")
    print(f"Buffer size: {config['training']['replay_buffer_size']}")
    print("Starting training... Press 'Q' in visualizer window or Ctrl+C to stop.\n")

    try:
        for episode in range(1, config["training"]["total_episodes"] + 1):
            state = env.reset()
            episode_reward = 0.0
            episode_loss = 0.0
            loss_count = 0
            start_time = time.time()

            for step in range(config["training"]["max_steps_per_episode"]):
                action = agent.act(state)
                next_state, reward, done, _ = env.step(action)
                agent.replay_buffer.push(state, action, reward, next_state, done)

                state = next_state
                episode_reward += reward

                loss = agent.update()
                if loss > 0:
                    episode_loss += loss
                    loss_count += 1

                if step % 4 == 0:
                    q_vals = agent.get_q_values(state)
                    raw = env.get_last_raw_frame()
                    if raw is None:
                        raw = np.zeros((84, 84, 3), dtype=np.uint8)
                    info = [
                        f"Episode: {episode}/{config['training']['total_episodes']}",
                        f"Step: {step} | Reward: {episode_reward:.2f}",
                        f"Epsilon: {agent.epsilon:.3f} | Buffer: {len(agent.replay_buffer)}",
                        f"Action: {'JUMP' if action == 1 else 'NO JUMP'}",
                        f"Q: no={q_vals[0]:.2f} jump={q_vals[1]:.2f}",
                        f"Avg Reward(100): {tracker.avg_reward():.2f}",
                    ]
                    vis.update_q_values(q_vals, action)
                    vis.set_info(info)
                    key = vis.render(state, raw)
                    if key == ord("q") or key == ord("Q"):
                        print("\nVisualizer closed by user")
                        raise KeyboardInterrupt

                if done:
                    break

            duration = time.time() - start_time

            avg_loss = episode_loss / max(loss_count, 1)
            tracker.log_episode(episode_reward, step + 1, avg_loss, agent.epsilon)

            if episode % config["training"]["log_freq"] == 0:
                print(
                    f"Ep {episode:5d} | "
                    f"{tracker.summary()} | "
                    f"Time: {duration:.1f}s | "
                    f"Buffer: {len(agent.replay_buffer)}"
                )

            if episode % config["training"]["save_freq"] == 0:
                agent.save(save_path)
                print(f"Saved: {save_path} (reward: {episode_reward:.2f})")

            if episode_reward > best_reward:
                best_reward = episode_reward
                best_path = save_path.replace(".pth", "_best.pth")
                agent.save(best_path)
                print(f"New best! Reward: {best_reward:.2f}")

    except KeyboardInterrupt:
        print("\nTraining interrupted")

    finally:
        agent.save(save_path)
        print(f"\nFinal model: {save_path}")
        print(f"Best reward: {best_reward:.2f}")
        print(f"Episodes: {episode}")
        vis.close()
        env.close()


if __name__ == "__main__":
    train()
