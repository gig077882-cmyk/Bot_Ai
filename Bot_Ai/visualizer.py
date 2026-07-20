import cv2
import numpy as np


class AIVisualizer:
    def __init__(self, window_name="GD AI Vision"):
        self.window_name = window_name
        self.q_values = [0.0, 0.0]
        self.current_action = 0
        self.info_lines = []
        self.show_grid = True
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 800, 560)

    def update_q_values(self, q_values, action=None):
        self.q_values = q_values
        if action is not None:
            self.current_action = action

    def set_info(self, lines):
        self.info_lines = lines

    def render(self, state, raw_frame=None):
        canvas_h, canvas_w = 560, 800
        canvas = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 36

        game_x, game_y = 10, 10
        ai_x, ai_y = 430, 10

        if raw_frame is not None and raw_frame.size > 0:
            h, w = raw_frame.shape[:2]
            scale = min(400 / h, 360 / w)
            disp = (int(w * scale), int(h * scale))
            frame = cv2.resize(raw_frame, disp)
            canvas[game_y : game_y + disp[1], game_x : game_x + disp[0]] = frame
            cv2.putText(canvas, "Game", (game_x, game_y + disp[1] + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        else:
            cv2.putText(canvas, "No frame", (game_x, game_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

        if state is not None and len(state.shape) == 3:
            c, h, w = state.shape
            recent = state[-1]
            frame_norm = (recent * 255).astype(np.uint8)

            scale_factor = 3
            size = w * scale_factor
            ai = cv2.resize(frame_norm, (size, size), interpolation=cv2.INTER_NEAREST)
            ai_color = cv2.cvtColor(ai, cv2.COLOR_GRAY2BGR)

            if self.show_grid:
                gray_val = 50
                for i in range(1, w):
                    cv2.line(ai_color, (i * scale_factor, 0), (i * scale_factor, size - 1),
                             (gray_val, gray_val, gray_val), 1)
                for j in range(1, h):
                    cv2.line(ai_color, (0, j * scale_factor), (size - 1, j * scale_factor),
                             (gray_val, gray_val, gray_val), 1)
                cv2.rectangle(ai_color, (0, 0), (size - 1, size - 1),
                              (120, 120, 120), 1)

            canvas[ai_y : ai_y + size, ai_x : ai_x + size] = ai_color
            label = f"AI Input 84x84"

            stack_x = ai_x + size + 15
            for i in range(min(c, 4)):
                frame = state[i]
                fn = (frame * 255).astype(np.uint8)
                f = cv2.cvtColor(fn, cv2.COLOR_GRAY2BGR)
                f = cv2.resize(f, (60, 60))
                canvas[ai_y + i * 70 : ai_y + i * 70 + 60, stack_x : stack_x + 60] = f
                cv2.putText(canvas, f"t-{c - i - 1}", (stack_x, ai_y + i * 70 + 73),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)

            cv2.putText(canvas, label, (ai_x, ai_y + size + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
            cv2.putText(canvas, "Stack", (stack_x, ai_y - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

        bar_y = 440
        bar_x = 10
        bar_w = 500
        bar_h = 18
        for i, q in enumerate(self.q_values):
            y = bar_y + i * 28
            label = ["NO JUMP", "JUMP"][i]
            active = i == self.current_action
            c = (0, 220, 0) if active else (200, 200, 200)
            cv2.putText(canvas, label, (bar_x, y + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1)
            cv2.rectangle(canvas, (bar_x + 80, y - 5), (bar_x + 80 + bar_w, y + 12),
                          (50, 50, 50), 1)
            fill = max(0, min(int((q + 5) / 10 * bar_w), bar_w))
            if fill > 0:
                cv2.rectangle(canvas, (bar_x + 80, y - 5), (bar_x + 80 + fill, y + 12),
                              (0, 220, 0) if active else (0, 140, 255), -1)
            cv2.putText(canvas, f"{q:.3f}", (bar_x + 80 + bar_w + 8, y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        info_y = 510
        for line in self.info_lines:
            cv2.putText(canvas, line, (10, info_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 255), 1)
            info_y += 18

        cv2.imshow(self.window_name, canvas)
        key = cv2.waitKey(1) & 0xFF
        return key

    def close(self):
        cv2.destroyWindow(self.window_name)
