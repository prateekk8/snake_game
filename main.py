"""
Classic Snake Game - Kivy Edition
----------------------------------
Runs on desktop (PyCharm, with arrow-key controls) and on mobile
(Android/iOS, with swipe controls) from the same codebase.

Run locally with:  python main.py
"""

import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import NumericProperty, ListProperty, BooleanProperty

GRID_SIZE = 20          # kept for backward reference; actual cols/rows are computed from CELL_PX
CELL_PX = 20             # fixed pixel size of each grid cell - grid now fills the whole board
MOVE_INTERVAL = 0.15    # seconds between snake moves (lower = faster)
GRID_COLOR = (0.20, 0.45, 0.95, 0.35)   # blue - most popular favourite colour worldwide, higher opacity

UP, DOWN, LEFT, RIGHT = (0, 1), (0, -1), (-1, 0), (1, 0)


class GameBoard(Widget):
    score = NumericProperty(0)
    game_over = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cell_size = CELL_PX
        self.cols = 1
        self.rows = 1
        self.snake = []
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.food = (0, 0)
        self.bind(size=self._on_resize, pos=self._on_resize)
        self.reset_game()

    def _on_resize(self, *args):
        # Fixed pixel cell size - fit as many whole cells as possible into
        # the widget so the grid always reaches every edge with no leftover gap.
        self.cell_size = CELL_PX
        self.cols = max(1, int(self.width // self.cell_size))
        self.rows = max(1, int(self.height // self.cell_size))
        self.redraw()

    def reset_game(self):
        mid_x, mid_y = self.cols // 2, self.rows // 2
        self.snake = [(mid_x - 1, mid_y), (mid_x - 2, mid_y), (mid_x - 3, mid_y)]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.score = 0
        self.game_over = False
        self.spawn_food()
        self.redraw()

    def spawn_food(self):
        while True:
            pos = (random.randint(0, self.cols - 1), random.randint(0, self.rows - 1))
            if pos not in self.snake:
                self.food = pos
                return

    def set_direction(self, new_dir):
        # Prevent the snake from reversing directly into itself
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    def update(self, dt):
        if self.game_over:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        # Wrap around the edges instead of dying on wall contact
        new_head = ((head_x + dx) % self.cols, (head_y + dy) % self.rows)

        # Self collision
        if new_head in self.snake:
            self.end_game()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.spawn_food()
        else:
            self.snake.pop()

        self.redraw()

    def end_game(self):
        self.game_over = True

    def redraw(self):
        self.canvas.clear()
        if not self.snake:
            with self.canvas:
                Color(0.09, 0.09, 0.11, 1)
                Rectangle(pos=self.pos, size=self.size)
            return
        with self.canvas:
            # Background
            Color(0.09, 0.09, 0.11, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Grid lines - fill the entire board edge-to-edge
            Color(*GRID_COLOR)
            for col in range(self.cols + 1):
                x = self.x + col * self.cell_size
                Rectangle(pos=(x, self.y), size=(1, self.height))
            for row in range(self.rows + 1):
                y = self.y + row * self.cell_size
                Rectangle(pos=(self.x, y), size=(self.width, 1))

            # Food
            Color(0.90, 0.25, 0.25, 1)
            fx, fy = self.food
            Rectangle(
                pos=(self.x + fx * self.cell_size, self.y + fy * self.cell_size),
                size=(self.cell_size, self.cell_size),
            )

            # Snake body (everything except the head)
            Color(0.30, 0.85, 0.40, 1)
            for (sx, sy) in self.snake[1:]:
                Rectangle(
                    pos=(self.x + sx * self.cell_size, self.y + sy * self.cell_size),
                    size=(self.cell_size - 1, self.cell_size - 1),
                )

            # Head, with a face looking in the direction of travel
            self._draw_head()

    def _draw_head(self):
        hx, hy = self.snake[0]
        cs = self.cell_size
        base_x = self.x + hx * cs
        base_y = self.y + hy * cs
        dx, dy = self.direction

        Color(0.45, 0.95, 0.55, 1)
        Rectangle(pos=(base_x, base_y), size=(cs - 1, cs - 1))

        # Eye placement: perpendicular offset from the direction of travel,
        # pushed toward the front of the head.
        perp = (-dy, dx)
        forward = 0.20 * cs
        side = 0.22 * cs
        cx, cy = base_x + cs / 2, base_y + cs / 2
        eye_center = (cx + dx * forward, cy + dy * forward)
        eye1 = (eye_center[0] + perp[0] * side, eye_center[1] + perp[1] * side)
        eye2 = (eye_center[0] - perp[0] * side, eye_center[1] - perp[1] * side)

        eye_r = max(2, cs * 0.14)
        pupil_r = max(1, cs * 0.07)

        for ex, ey in (eye1, eye2):
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, ey - eye_r), size=(eye_r * 2, eye_r * 2))
            Color(0.05, 0.05, 0.05, 1)
            pdx, pdy = dx * pupil_r * 0.6, dy * pupil_r * 0.6
            Ellipse(pos=(ex + pdx - pupil_r, ey + pdy - pupil_r), size=(pupil_r * 2, pupil_r * 2))

    # --- Keyboard controls (desktop testing in PyCharm) ---
    def on_key_down(self, key):
        mapping = {
            'up': UP, 'w': UP,
            'down': DOWN, 's': DOWN,
            'left': LEFT, 'a': LEFT,
            'right': RIGHT, 'd': RIGHT,
        }
        if key in mapping:
            self.set_direction(mapping[key])


class DPadButton(Button):
    """A round arrow button used inside the D-pad."""

    def __init__(self, symbol, **kwargs):
        super().__init__(
            text=symbol,
            font_size=26,
            bold=True,
            background_normal='',
            background_down='',
            background_color=(0.20, 0.22, 0.26, 1),
            color=(0.95, 0.95, 0.95, 1),
            **kwargs,
        )
        with self.canvas.before:
            Color(0.20, 0.22, 0.26, 1)
            self._circle = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_circle, size=self._sync_circle)

    def _sync_circle(self, *args):
        self._circle.pos = self.pos
        self._circle.size = self.size


class DPad(GridLayout):
    """A classic cross-shaped directional pad: up / left / right / down,
    laid out around an empty center, like an old game-console arrow knob."""

    def __init__(self, on_up, on_down, on_left, on_right, **kwargs):
        super().__init__(cols=3, rows=3, spacing=6, **kwargs)

        blank_tl = Widget()
        self.up_btn = DPadButton("\u25B2", on_press=lambda *_: on_up())
        blank_tr = Widget()

        self.left_btn = DPadButton("\u25C0", on_press=lambda *_: on_left())
        center = Widget()
        self.right_btn = DPadButton("\u25B6", on_press=lambda *_: on_right())

        blank_bl = Widget()
        self.down_btn = DPadButton("\u25BC", on_press=lambda *_: on_down())
        blank_br = Widget()

        for w in (blank_tl, self.up_btn, blank_tr,
                  self.left_btn, center, self.right_btn,
                  blank_bl, self.down_btn, blank_br):
            self.add_widget(w)


class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        top_bar = BoxLayout(size_hint=(1, 0.08), padding=(10, 0))
        self.score_label = Label(text="Score: 0", font_size=20)
        top_bar.add_widget(self.score_label)
        self.restart_btn = Button(
            text="Restart", size_hint=(0.35, 1),
            on_press=lambda *_: self.board.reset_game(),
        )
        top_bar.add_widget(self.restart_btn)
        self.add_widget(top_bar)

        self.board = GameBoard(size_hint=(1, 0.68))
        self.add_widget(self.board)
        self.board.bind(score=self._update_score, game_over=self._on_game_over)

        # On-screen D-pad ("arrow knob") for mobile and desktop
        dpad_wrapper = BoxLayout(size_hint=(1, 0.24), padding=10)
        self.dpad = DPad(
            on_up=lambda: self.board.set_direction(UP),
            on_down=lambda: self.board.set_direction(DOWN),
            on_left=lambda: self.board.set_direction(LEFT),
            on_right=lambda: self.board.set_direction(RIGHT),
        )
        dpad_wrapper.add_widget(self.dpad)
        self.add_widget(dpad_wrapper)

        Clock.schedule_interval(self.board.update, MOVE_INTERVAL)

        Window.bind(on_key_down=self._on_window_key_down)

    def _on_window_key_down(self, window, key, scancode, codepoint, modifiers):
        key_name = {
            273: 'up', 274: 'down', 276: 'left', 275: 'right',
        }.get(key, codepoint)
        if key_name:
            self.board.on_key_down(key_name)

    def _update_score(self, instance, value):
        self.score_label.text = f"Score: {value}"

    def _on_game_over(self, instance, value):
        if value:
            self.score_label.text = f"Game Over! Score: {self.board.score} - tap Restart"


class SnakeApp(App):
    def build(self):
        self.title = "Snake"
        return RootLayout()


if __name__ == "__main__":
    SnakeApp().run()
