"""
Snake - Kivy edition
--------------------
Home screen has a Game Type dropdown: Classic, Tunnel, Box.
Pick a type, press "Start New Game", and that mode opens.

Desktop: arrow keys / WASD or the on-screen D-pad.
Phone:   on-screen D-pad.
"""

import os
import random
import json
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle, Triangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
LOGO = os.path.join(HERE, "logo.png")

# ----------------------------------------------------------------- settings
CELL_PX = 20                              # size of one grid cell in pixels
MOVE_INTERVAL = 0.15                      # seconds per snake step (lower = faster)
GRID_COLOR = (0.20, 0.45, 0.95, 0.35)     # blue grid lines
WALL_COLOR = (0.72, 0.72, 0.95, 1)        # light lavender walls
DECOR_DENSITY = 0.03                      # clusters per cell; 0 turns the pattern off
DECOR_BLUE = [(0.13, 0.28, 0.80), (0.16, 0.33, 0.88), (0.10, 0.22, 0.70)]
DECOR_PURPLE = [(0.40, 0.22, 0.78), (0.46, 0.27, 0.85)]
BONUS_POINTS = 10
BONUS_MIN_WAIT = 30                       # fewest steps before a bonus appears
BONUS_MAX_WAIT = 80                       # most steps before a bonus appears
BONUS_LIFETIME = 50                       # steps a bonus stays before vanishing
BONUS_COLOR = (1.0, 0.85, 0.20, 1)        # gold

# Dropdown entries -> wall layout. Add a new mode by adding a line here
# (and a matching branch in make_walls if it needs walls).
GAME_TYPES = {
    "Classic": None,
    "Tunnel": "tunnel",
    "Box": "box",
    "Apartment": "apartment",
}

UP, DOWN, LEFT, RIGHT = (0, 1), (0, -1), (-1, 0), (1, 0)

class HighScores:
    """Best score for each game type, saved in a small JSON file."""

    def __init__(self, path=None):
        self.path = path
        self.best = {name: 0 for name in GAME_TYPES}
        self._load()

    def _load(self):
        if not self.path:
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            for name in self.best:
                self.best[name] = int(data.get(name, 0))
        except (OSError, ValueError, TypeError, AttributeError):
            pass                          # no file yet, or unreadable: start at zero

    def get(self, game_type):
        return self.best.get(game_type, 0)

    def submit(self, game_type, score):
        """Record a score. Returns True if it is a new high score."""
        if score > self.get(game_type):
            self.best[game_type] = score
            self._save()
            return True
        return False

    def _save(self):
        if not self.path:
            return
        try:
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.best, f)
        except OSError:
            pass

# ------------------------------------------------------------------- walls
def make_walls(kind, cols, rows):
    """Return the set of (col, row) cells that are walls for a game type.
    Sizes scale with the grid, so it looks right on any screen."""
    walls = set()
    if kind == "tunnel":
        # three horizontal bars: top edge, bottom edge, and one in the middle
        width = max(4, round(cols * 0.36))
        thick = max(1, round(rows / 17))
        c0 = cols // 2 - width // 2
        mid = rows // 2
        for c in range(c0, c0 + width):
            for k in range(thick):
                walls.add((c, rows - 1 - k))      # top bar
                walls.add((c, k))                 # bottom bar
                walls.add((c, mid - 2 - k))       # middle bar, below the start row
    elif kind == "box":
        # an L-shaped block in each of the four corners
        arm_x = max(2, round(cols * 0.15))
        arm_y = max(2, round(rows * 0.15))
        corners = ((0, 0, 1, 1), (cols - 1, 0, -1, 1),
                   (0, rows, 1, -1), (cols - 1, rows, -1, -1))
        for cx, cy, sx, sy in corners:
            for i in range(arm_x):
                walls.add((cx + sx * i, cy))
            for i in range(arm_y):
                walls.add((cx, cy + sy * i))
    elif kind == "apartment":
        # Two L-shaped walls make "rooms": one hangs from the top edge and runs
        # to the right edge, the other rises from the bottom edge and runs to
        # the left edge. The corridor between them is where the snake starts.
        t = max(1, round(rows / 17))                  # wall thickness
        q = max(2, round(rows * 0.25))                # distance of each arm from its edge
        a_c = max(1, round(cols * 0.31))              # column of the top wall's upright
        b_c = min(max(a_c + t + 1, round(cols * 0.54)), cols - t - 1)  # bottom wall's upright
        top_arm = rows - 1 - q                   # highest row of the top wall's arm
        for k in range(t):
            for x in range(a_c, cols):                # top arm, to the right edge
                walls.add((x, top_arm - k))
            for x in range(0, b_c + t):               # bottom arm, from the left edge
                walls.add((x, q + k))
        for y in range(top_arm - t + 1, rows):       # top upright, down from the top edge
            for k in range(t):
                walls.add((a_c + k, y))
        for y in range(0, q + t):                     # bottom upright, up from the bottom edge
            for k in range(t):
                walls.add((b_c + k, y))
    return walls

# ------------------------------------------------------------ decoration
def make_decor(cols, rows):
    """Random clusters of filled cells, like the Nokia board.
    Returns {colour: [(col, row), ...]}. Purely cosmetic: it never affects the game."""
    if DECOR_DENSITY <= 0:
        return {}
    cells = {}
    for _ in range(max(3, round(cols * rows * DECOR_DENSITY))):
        w, h = random.randint(2, 4), random.randint(2, 3)
        x0 = random.randint(0, max(0, cols - w))
        y0 = random.randint(0, max(0, rows - h))
        main, other = ((DECOR_PURPLE, DECOR_BLUE) if random.random() < 0.25
                       else (DECOR_BLUE, DECOR_PURPLE))
        for x in range(x0, min(cols, x0 + w)):
            for y in range(y0, min(rows, y0 + h)):
                if random.random() < 0.8:                  # leave some holes
                    palette = other if random.random() < 0.15 else main
                    cells[(x, y)] = random.choice(palette)
    groups = {}
    for cell, colour in cells.items():
        groups.setdefault(colour, []).append(cell)
    return groups

# -------------------------------------------------------------- game board
class GameBoard(Widget):
    score = NumericProperty(0)
    game_over = BooleanProperty(False)

    def __init__(self, wall_kind=None, **kwargs):
        super().__init__(**kwargs)
        self.wall_kind = wall_kind
        self.cell_size = CELL_PX
        self.cols = 0
        self.rows = 0
        self.walls = set()
        self.decor = {}
        self.snake = []
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.food = (0, 0)
        self.bonus = None
        self.bonus_ttl = 0
        self.bonus_timer = 0
        self.bind(size=self._on_resize, pos=self._on_resize)

    def _on_resize(self, *args):
        # Fit as many whole cells as possible so the grid reaches every edge.
        cols = max(1, int(self.width // CELL_PX))
        rows = max(1, int(self.height // CELL_PX))
        if (cols, rows) != (self.cols, self.rows):
            self.cols, self.rows = cols, rows
            self.reset_game()          # grid size known/changed: rebuild and restart
        else:
            self.redraw()

    def reset_game(self):
        mid_x, mid_y = max(self.cols // 2, 3), self.rows // 2
        self.snake = [(mid_x - 1, mid_y), (mid_x - 2, mid_y), (mid_x - 3, mid_y)]
        self.walls = make_walls(self.wall_kind, self.cols, self.rows)
        self.walls.difference_update(self.snake)
        self.decor = make_decor(self.cols, self.rows)  # a new random pattern
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.score = 0
        self.game_over = False
        self._reset_bonus()
        self.spawn_food()
        self.redraw()

    # ---- food and bonus
    def spawn_food(self):
        free = [(x, y) for x in range(self.cols) for y in range(self.rows)
                if (x, y) not in self.snake and (x, y) not in self.walls]
        if not free:
            self.game_over = True
            return
        self.food = random.choice(free)

    def _reset_bonus(self):
        self.bonus = None
        self.bonus_ttl = 0
        self.bonus_timer = random.randint(BONUS_MIN_WAIT, BONUS_MAX_WAIT)

    def spawn_bonus(self):
        free = [(x, y) for x in range(self.cols) for y in range(self.rows)
                if (x, y) not in self.snake and (x, y) != self.food
                and (x, y) not in self.walls]
        if free:
            self.bonus = random.choice(free)
            self.bonus_ttl = BONUS_LIFETIME

    # ---- movement
    def set_direction(self, new_dir):
        opposite = (-self.direction[0], -self.direction[1])
        if new_dir != opposite:
            self.next_direction = new_dir

    def update(self, dt):
        if self.game_over or not self.snake:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        # wrap around the edges instead of dying on them
        new_head = ((head_x + dx) % self.cols, (head_y + dy) % self.rows)

        if new_head in self.snake or new_head in self.walls:
            self.end_game()
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self.spawn_food()
        else:
            self.snake.pop()

        # bonus item: eat it for points, or it vanishes after a while
        if self.bonus is not None:
            if new_head == self.bonus:
                self.score += BONUS_POINTS
                self._reset_bonus()
            else:
                self.bonus_ttl -= 1
                if self.bonus_ttl <= 0:
                    self._reset_bonus()
        else:
            self.bonus_timer -= 1
            if self.bonus_timer <= 0:
                self.spawn_bonus()

        self.redraw()

    def end_game(self):
        self.game_over = True

    # ---- drawing
    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.09, 0.09, 0.11, 1)
            Rectangle(pos=self.pos, size=self.size)
            if not self.snake:
                return

            cs = self.cell_size

            # grid lines, edge to edge
            Color(*GRID_COLOR)
            for col in range(self.cols + 1):
                Rectangle(pos=(self.x + col * cs, self.y), size=(1, self.height))
            for row in range(self.rows + 1):
                Rectangle(pos=(self.x, self.y + row * cs), size=(self.width, 1))




            # walls (Tunnel / Box)
            Color(*WALL_COLOR)
            for wx, wy in self.walls:
                Rectangle(pos=(self.x + wx * cs, self.y + wy * cs), size=(cs, cs))

            # food
            Color(0.90, 0.25, 0.25, 1)
            fx, fy = self.food
            Rectangle(pos=(self.x + fx * cs, self.y + fy * cs), size=(cs, cs))

            # bonus (gold circle) - blinks when about to disappear
            if self.bonus and not (self.bonus_ttl <= 15 and self.bonus_ttl % 4 < 2):
                bx, by = self.bonus
                Color(*BONUS_COLOR)
                Ellipse(pos=(self.x + bx * cs, self.y + by * cs), size=(cs, cs))

            # snake body
            Color(0.30, 0.85, 0.40, 1)
            for sx, sy in self.snake[1:]:
                Rectangle(pos=(self.x + sx * cs, self.y + sy * cs),
                          size=(cs - 1, cs - 1))

            self._draw_head()

    def _draw_head(self):
        hx, hy = self.snake[0]
        cs = self.cell_size
        base_x = self.x + hx * cs
        base_y = self.y + hy * cs
        dx, dy = self.direction

        Color(0.45, 0.95, 0.55, 1)
        Rectangle(pos=(base_x, base_y), size=(cs - 1, cs - 1))

        # eyes sit toward the front of the head, so the snake "looks" ahead
        perp = (-dy, dx)
        forward = 0.20 * cs
        side = 0.22 * cs
        cx, cy = base_x + cs / 2, base_y + cs / 2
        eye_c = (cx + dx * forward, cy + dy * forward)
        eyes = ((eye_c[0] + perp[0] * side, eye_c[1] + perp[1] * side),
                (eye_c[0] - perp[0] * side, eye_c[1] - perp[1] * side))
        eye_r = max(2, cs * 0.14)
        pupil_r = max(1, cs * 0.07)
        for ex, ey in eyes:
            Color(1, 1, 1, 1)
            Ellipse(pos=(ex - eye_r, ey - eye_r), size=(eye_r * 2, eye_r * 2))
            Color(0.05, 0.05, 0.05, 1)
            px, py = dx * pupil_r * 0.6, dy * pupil_r * 0.6
            Ellipse(pos=(ex + px - pupil_r, ey + py - pupil_r),
                    size=(pupil_r * 2, pupil_r * 2))

    # ---- keyboard (desktop testing)
    def on_key_down(self, key):
        mapping = {'up': UP, 'w': UP, 'down': DOWN, 's': DOWN,
                   'left': LEFT, 'a': LEFT, 'right': RIGHT, 'd': RIGHT}
        if key in mapping:
            self.set_direction(mapping[key])


# ------------------------------------------------------------------- D-pad
class DPadButton(Button):
    def __init__(self, symbol, **kwargs):
        super().__init__(
            text=symbol, font_size=26, bold=True,
            background_normal='', background_down='',
            background_color=(0.20, 0.22, 0.26, 1),
            color=(0.95, 0.95, 0.95, 1), **kwargs)


class DPad(GridLayout):
    """Cross-shaped arrow pad: up / left / right / down around an empty centre."""

    def __init__(self, on_up, on_down, on_left, on_right, **kwargs):
        super().__init__(cols=3, rows=3, spacing=6, **kwargs)
        cells = (
            Widget(), DPadButton("\u25B2", on_press=lambda *_: on_up()), Widget(),
            DPadButton("\u25C0", on_press=lambda *_: on_left()), Widget(),
            DPadButton("\u25B6", on_press=lambda *_: on_right()),
            Widget(), DPadButton("\u25BC", on_press=lambda *_: on_down()), Widget(),
        )
        for w in cells:
            self.add_widget(w)


# ------------------------------------------------------------- game screen
class RootLayout(BoxLayout):
    """The game: info bar, score bar, board and D-pad."""

    def __init__(self, game_type, on_menu, scores, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self._tick = None
        self.game_type = game_type
        self.scores = scores

        info_bar = BoxLayout(size_hint=(1, 0.05), padding=(10, 0))
        info_bar.add_widget(Label(text=f"Type: {game_type}", font_size=16))
        self.high_label = Label(text=f"High Score: {scores.get(game_type)}", font_size=16)
        info_bar.add_widget(self.high_label)
        self.add_widget(info_bar)

        top_bar = BoxLayout(size_hint=(1, 0.08), padding=(10, 0), spacing=6)
        self.score_label = Label(text="Score: 0", font_size=20)
        top_bar.add_widget(self.score_label)
        top_bar.add_widget(Button(
            text="Menu", size_hint=(0.25, 1), on_press=lambda *_: on_menu()))
        top_bar.add_widget(Button(
            text="Restart", size_hint=(0.3, 1),
            on_press=lambda *_: self.board.reset_game()))
        self.add_widget(top_bar)

        self.board = GameBoard(wall_kind=GAME_TYPES[game_type], size_hint=(1, 0.63))
        self.add_widget(self.board)
        self.board.bind(score=self._refresh_label, game_over=self._refresh_label)

        wrapper = BoxLayout(size_hint=(1, 0.24), padding=10)
        wrapper.add_widget(DPad(
            on_up=lambda: self.board.set_direction(UP),
            on_down=lambda: self.board.set_direction(DOWN),
            on_left=lambda: self.board.set_direction(LEFT),
            on_right=lambda: self.board.set_direction(RIGHT),
        ))
        self.add_widget(wrapper)

        self._tick = Clock.schedule_interval(self.board.update, MOVE_INTERVAL)
        Window.bind(on_key_down=self._on_window_key_down)

    def stop(self):
        """Call when leaving the game screen."""
        self.scores.submit(self.game_type, self.board.score)
        if self._tick:
            self._tick.cancel()
            self._tick = None
        Window.unbind(on_key_down=self._on_window_key_down)

    def _on_window_key_down(self, window, key, scancode, codepoint, modifiers):
        name = {273: 'up', 274: 'down', 276: 'left', 275: 'right'}.get(key, codepoint)
        if name:
            self.board.on_key_down(name)

    def _refresh_label(self, *args):
        b = self.board
        if b.game_over:
            if self.scores.submit(self.game_type, b.score):
                self.score_label.text = f"Game Over! New High Score: {b.score}"
            else:
                self.score_label.text = f"Game Over! Score: {b.score}"
        else:
            self.score_label.text = f"Score: {b.score}"
        # shown live: the saved best, or the current score if it is higher
        self.high_label.text = f"High Score: {max(self.scores.get(self.game_type), b.score)}"


# --------------------------------------------------------------- home screen
class MenuButton(Button):
    """Flat button used on the home screen; gets lighter while pressed."""

    def __init__(self, **kwargs):
        opts = dict(
            font_size=22,
            background_normal='', background_down='', background_disabled_normal='',
            background_color=(0.20, 0.22, 0.26, 1),
            color=(0.95, 0.95, 0.95, 1), disabled_color=(1, 1, 1, 0.3),
            size_hint=(1, None), height=dp(54),
        )
        opts.update(kwargs)
        super().__init__(**opts)
        self._base = tuple(opts['background_color'])
        self.bind(state=self._on_state)

    def _on_state(self, button, state):
        r, g, b, a = self._base
        self.background_color = ((min(r + 0.12, 1), min(g + 0.12, 1), min(b + 0.12, 1), a)
                                 if state == 'down' else self._base)


class DropButton(MenuButton):
    """A MenuButton with a blue outline and a small down-arrow, for dropdowns."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.after:
            Color(0.20, 0.45, 0.95, 1)
            self._outline = Line(rectangle=(0, 0, 0, 0), width=1.5)
            Color(0.95, 0.95, 0.95, 1)
            self._arrow = Triangle(points=[0, 0, 0, 0, 0, 0])
        self.bind(pos=self._place, size=self._place)

    def _place(self, *args):
        self._outline.rectangle = (self.x, self.y, self.width, self.height)
        cx, cy, s = self.right - dp(26), self.center_y, dp(7)
        self._arrow.points = [cx - s, cy + s * 0.5, cx + s, cy + s * 0.5, cx, cy - s * 0.7]


class MenuLayout(BoxLayout):
    def __init__(self, on_start, on_scores, selected=None, **kwargs):
        super().__init__(orientation='vertical', padding=dp(24), spacing=dp(10), **kwargs)
        self.selected = selected          # None until the player picks a type

        if os.path.exists(LOGO):
            self.add_widget(Image(source=LOGO))
        else:
            self.add_widget(Widget())
        self.add_widget(Label(
            text="SNAKE", font_size=44, bold=True, color=(0.45, 0.95, 0.55, 1),
            size_hint=(1, None), height=dp(56)))

        self.dropdown = DropDown()
        for name in GAME_TYPES:
            option = MenuButton(text=name, height=dp(48),
                                background_color=(0.16, 0.18, 0.22, 1))
            option.bind(on_release=lambda btn: self.dropdown.select(btn.text))
            self.dropdown.add_widget(option)
        self.dropdown.bind(on_select=self._on_pick)

        self.type_btn = DropButton(text="Game Type")
        self.type_btn.bind(on_release=self.dropdown.open)
        self.add_widget(self.type_btn)
        self._refresh_type_btn()

        self.add_widget(MenuButton(
            text="Start New Game", font_size=24, height=dp(60),
            background_color=(0.30, 0.85, 0.40, 1), color=(0.05, 0.05, 0.05, 1),
            on_release=lambda *_: on_start(self.selected)))
        self.add_widget(MenuButton(
            text="High Score", on_release=lambda *_: on_scores()))

    def _refresh_type_btn(self):
        if self.selected:
            self.type_btn.text = self.selected
            self.type_btn.color = (1, 1, 1, 1)
        else:
            self.type_btn.text = "Game Type"
            self.type_btn.color = (0.70, 0.72, 0.78, 1)

    def _on_pick(self, dropdown, name):
        self.selected = name
        self._refresh_type_btn()

class Separator(Widget):
    """A thin horizontal line."""

    def __init__(self, **kwargs):
        super().__init__(size_hint=(1, None), height=dp(1), **kwargs)
        with self.canvas:
            Color(0.20, 0.45, 0.95, 0.6)
            self._line = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self._line.pos = self.pos
        self._line.size = self.size


class HighScoreLayout(BoxLayout):
    """High scores page: one row per game type, with a line between the rows."""

    def __init__(self, scores, on_back, **kwargs):
        super().__init__(orientation='vertical', padding=dp(24), spacing=dp(10), **kwargs)
        self.add_widget(Label(
            text="HIGH SCORES", font_size=36, bold=True, color=(1.0, 0.85, 0.20, 1),
            size_hint=(1, None), height=dp(70)))
        self.add_widget(Separator())

        names = list(GAME_TYPES)
        for i, name in enumerate(names):
            row = BoxLayout(size_hint=(1, None), height=dp(56), padding=(dp(12), 0))
            row.add_widget(self._cell(name, 'left', 0.6, (0.95, 0.95, 0.95, 1)))
            row.add_widget(self._cell(str(scores.get(name)), 'right', 0.4,
                                      (1.0, 0.85, 0.20, 1)))
            self.add_widget(row)
            if i < len(names) - 1:
                self.add_widget(Separator())      # line between game types

        self.add_widget(Widget())                 # pushes Back to the bottom
        self.add_widget(MenuButton(text="Back", on_release=lambda *_: on_back()))

    @staticmethod
    def _cell(text, halign, hint_x, color):
        label = Label(text=text, font_size=24, halign=halign, valign='middle',
                      color=color, size_hint=(hint_x, 1))
        label.bind(size=lambda lbl, size: setattr(lbl, 'text_size', size))
        return label


# ----------------------------------------------------------------------- app
class SnakeApp(App):
    def build(self):
        self.title = "Snake"
        self.scores = HighScores(os.path.join(self.user_data_dir, "highscores.json"))
        self.selected_type = None
        self.in_scores = False
        self.game = None
        self.container = BoxLayout()
        self.show_menu()
        Window.bind(on_keyboard=self._on_back)
        return self.container

    def show_menu(self):
        self._stop_game()
        self.in_scores = False
        self.container.clear_widgets()
        self.container.add_widget(
            MenuLayout(on_start=self.start_game, on_scores=self.show_high_scores,
                       selected=self.selected_type))

    def show_high_scores(self):
        self.in_scores = True
        self.container.clear_widgets()
        self.container.add_widget(
            HighScoreLayout(scores=self.scores, on_back=self.show_menu))

    def start_game(self, choice):
        self.selected_type = choice
        game_type = choice or "Classic"
        self.in_scores = False
        self._stop_game()
        self.container.clear_widgets()
        self.game = RootLayout(game_type=game_type, on_menu=self.show_menu,scores=self.scores)
        self.container.add_widget(self.game)

    def on_pause(self):
        if self.game:
            self.scores.submit(self.game.game_type, self.game.board.score)
        return True

    def on_stop(self):
        self._stop_game()

    def _stop_game(self):
        if self.game:
            self.game.stop()
            self.game = None

    def _on_back(self, window, key, *args):
        # Android back button / Esc: leave the game for the menu
        if key == 27 and (self.game or self.in_scores):
            self.show_menu()
            return True
        return False


if __name__ == "__main__":
    SnakeApp().run()
