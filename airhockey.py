from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock
from kivy.config import Config
import math
import ctypes

# WM_TOUCH Configuration - same as other touchscreen games
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('input', 'wm_touch', 'wm_touch')
Config.set('input', 'wm_pen', 'wm_pen')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1100')
Config.set('graphics', 'height', '800')


def disable_windows_touch_gestures():
    """Disable Windows touch gestures to prevent interference with IR frame"""
    try:
        from kivy.core.window import Window
        hwnd = ctypes.windll.user32.GetActiveWindow()

        class GESTURECONFIG(ctypes.Structure):
            _fields_ = [
                ("dwID", ctypes.c_uint),
                ("dwWant", ctypes.c_uint),
                ("dwBlock", ctypes.c_uint),
            ]

        GC_ALLGESTURES = 0x00000001
        config = GESTURECONFIG(0, 0, GC_ALLGESTURES)
        ctypes.windll.user32.SetGestureConfig(
            hwnd, 0, 1, ctypes.byref(config), ctypes.sizeof(GESTURECONFIG)
        )
    except Exception as e:
        print(f"Could not disable gestures: {e}")


# Player colors
PLAYER_COLORS = [
    (0.2, 0.5, 0.9, 1),   # Blue (left player)
    (0.9, 0.3, 0.2, 1),   # Red (right player)
]

PLAYER_NAMES = ["Blue", "Red"]
WINNING_SCORE = 7


class Puck(Widget):
    """The air hockey puck with physics"""

    def __init__(self, x, y, **kwargs):
        super(Puck, self).__init__(**kwargs)
        self.base_radius = 25
        self.radius = self.base_radius
        self.size = (self.radius * 2, self.radius * 2)
        self.center = (x, y)

        self.vx = 0
        self.vy = 0
        self.friction = 0.995  # Slight friction
        self.max_speed = 1500
        self.min_speed = 50  # Below this, puck stops

    def update_size(self, scale):
        """Update puck size based on scale factor"""
        self.radius = self.base_radius * scale
        self.size = (self.radius * 2, self.radius * 2)

    def reset(self, x, y):
        """Reset puck to center with no velocity"""
        self.center = (x, y)
        self.vx = 0
        self.vy = 0

    def update(self, dt, table_bounds, goal_height):
        """Update puck position and handle wall bounces"""
        left, bottom, right, top = table_bounds

        # Move puck
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Apply friction
        self.vx *= self.friction
        self.vy *= self.friction

        # Stop if too slow
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        if speed < self.min_speed:
            self.vx = 0
            self.vy = 0

        # Clamp to max speed
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed

        # Wall collisions
        cx, cy = self.center
        table_center_y = (bottom + top) / 2
        goal_half = goal_height / 2

        # Top wall (solid)
        if cy + self.radius > top:
            self.center = (cx, top - self.radius)
            self.vy = -abs(self.vy) * 0.9

        # Bottom wall (solid)
        cx, cy = self.center
        if cy - self.radius < bottom:
            self.center = (cx, bottom + self.radius)
            self.vy = abs(self.vy) * 0.9

        # Left wall (with goal opening)
        cx, cy = self.center
        in_left_goal = abs(cy - table_center_y) < goal_half
        if cx - self.radius < left and not in_left_goal:
            self.center = (left + self.radius, cy)
            self.vx = abs(self.vx) * 0.9

        # Right wall (with goal opening)
        in_right_goal = abs(cy - table_center_y) < goal_half
        if cx + self.radius > right and not in_right_goal:
            self.center = (right - self.radius, cy)
            self.vx = -abs(self.vx) * 0.9

        # Check for goals
        cx, cy = self.center
        if cx - self.radius < left - 20 and in_left_goal:
            return 1  # Player 1 (red/right) scores
        if cx + self.radius > right + 20 and in_right_goal:
            return 0  # Player 0 (blue/left) scores

        return None  # No goal


class Paddle(Widget):
    """A player's paddle that follows touch input"""

    def __init__(self, player_id, game, **kwargs):
        super(Paddle, self).__init__(**kwargs)
        self.player_id = player_id
        self.game = game
        self.color = PLAYER_COLORS[player_id]

        self.base_radius = 45
        self.radius = self.base_radius
        self.size = (self.radius * 2, self.radius * 2)

        # Velocity for puck collision
        self.vx = 0
        self.vy = 0
        self.last_x = 0
        self.last_y = 0

        # Touch tracking
        self.active_touch = None

    def update_size(self, scale):
        """Update paddle size based on scale factor"""
        self.radius = self.base_radius * scale
        self.size = (self.radius * 2, self.radius * 2)

    def get_bounds(self):
        """Get the area this paddle is allowed to move in"""
        table_bounds = self.game.get_table_bounds()
        left, bottom, right, top = table_bounds
        center_x = (left + right) / 2

        if self.player_id == 0:  # Left player (blue)
            return (left + self.radius, bottom + self.radius,
                    center_x - self.radius, top - self.radius)
        else:  # Right player (red)
            return (center_x + self.radius, bottom + self.radius,
                    right - self.radius, top - self.radius)

    def constrain_position(self, x, y):
        """Constrain position to paddle's allowed area"""
        min_x, min_y, max_x, max_y = self.get_bounds()
        x = max(min_x, min(max_x, x))
        y = max(min_y, min(max_y, y))
        return x, y

    def move_to(self, x, y):
        """Move paddle to position, constrained to bounds"""
        x, y = self.constrain_position(x, y)
        self.center = (x, y)

    def update_velocity(self, dt):
        """Calculate velocity from position change"""
        if dt > 0:
            self.vx = (self.center_x - self.last_x) / dt
            self.vy = (self.center_y - self.last_y) / dt
        self.last_x = self.center_x
        self.last_y = self.center_y

    def is_in_zone(self, touch_x):
        """Check if a touch x-position is in this paddle's zone"""
        table_bounds = self.game.get_table_bounds()
        left, bottom, right, top = table_bounds
        center_x = (left + right) / 2

        if self.player_id == 0:  # Left player (blue)
            return touch_x < center_x
        else:  # Right player (red)
            return touch_x >= center_x

    def on_touch_down(self, touch):
        if self.active_touch is None and self.is_in_zone(touch.x):
            self.active_touch = touch.uid
            touch.ud['paddle'] = self
            self.move_to(touch.x, touch.y)
            return True
        return False

    def on_touch_move(self, touch):
        if touch.uid == self.active_touch:
            self.move_to(touch.x, touch.y)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.uid == self.active_touch:
            self.active_touch = None
            return True
        return False


class AirHockeyGame(Widget):
    """Main game widget with physics and rendering"""

    def __init__(self, **kwargs):
        super(AirHockeyGame, self).__init__(**kwargs)
        self.puck = None
        self.paddles = []
        self.scores = [0, 0]
        self.game_active = False
        self.update_timer = None
        self.goal_pause = False
        self.goal_pause_timer = None

        # Table dimensions (calculated on resize)
        self.table_margin = 40
        self.goal_width_ratio = 0.35
        self.scale = 1.0

        self.bind(size=self.on_size_change, pos=self.on_size_change)

    def get_scale(self):
        """Get scale factor based on window size"""
        base_width = 1100
        return self.width / base_width

    def get_table_bounds(self):
        """Get table boundaries (left, bottom, right, top)"""
        margin = self.table_margin * self.scale
        return (
            self.x + margin,
            self.y + margin,
            self.x + self.width - margin,
            self.y + self.height - margin
        )

    def get_goal_height(self):
        """Get the height of the goal opening"""
        left, bottom, right, top = self.get_table_bounds()
        table_height = top - bottom
        return table_height * self.goal_width_ratio

    def on_size_change(self, *args):
        self.scale = self.get_scale()

        if self.puck:
            self.puck.update_size(self.scale)

        for paddle in self.paddles:
            paddle.update_size(self.scale)

        self.update_canvas()

    def start_game(self):
        """Start a new game"""
        self.scores = [0, 0]
        self.scale = self.get_scale()

        # Create puck at center
        table_bounds = self.get_table_bounds()
        center_x = (table_bounds[0] + table_bounds[2]) / 2
        center_y = (table_bounds[1] + table_bounds[3]) / 2

        self.puck = Puck(center_x, center_y)
        self.puck.update_size(self.scale)

        # Create paddles
        self.paddles = []
        for i in range(2):
            paddle = Paddle(i, self)
            paddle.update_size(self.scale)
            self.paddles.append(paddle)

        # Position paddles at starting positions
        self.reset_positions()

        self.game_active = True
        self.goal_pause = False

        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = Clock.schedule_interval(self.update_game, 1 / 60.0)

        self.update_canvas()

    def reset_positions(self):
        """Reset puck and paddles to starting positions"""
        table_bounds = self.get_table_bounds()
        left, bottom, right, top = table_bounds
        center_x = (left + right) / 2
        center_y = (bottom + top) / 2

        # Puck at center
        if self.puck:
            self.puck.reset(center_x, center_y)

        # Paddles at their sides (left and right)
        if len(self.paddles) >= 2:
            self.paddles[0].center = (left + (center_x - left) * 0.3, center_y)  # Blue on left
            self.paddles[1].center = (right - (right - center_x) * 0.3, center_y)  # Red on right

            for paddle in self.paddles:
                paddle.last_x = paddle.center_x
                paddle.last_y = paddle.center_y
                paddle.vx = 0
                paddle.vy = 0

    def update_game(self, dt):
        """Main game update loop"""
        if not self.game_active or self.goal_pause:
            self.update_canvas()
            return

        # Update paddle velocities
        for paddle in self.paddles:
            paddle.update_velocity(dt)

        # Update puck
        table_bounds = self.get_table_bounds()
        goal_height = self.get_goal_height()
        goal_result = self.puck.update(dt, table_bounds, goal_height)

        # Check paddle-puck collisions
        for paddle in self.paddles:
            self.check_paddle_collision(paddle)

        # Check for goal
        if goal_result is not None:
            self.on_goal(goal_result)

        self.update_canvas()

    def check_paddle_collision(self, paddle):
        """Check and handle collision between paddle and puck"""
        px, py = self.puck.center
        mx, my = paddle.center

        dx = px - mx
        dy = py - my
        distance = math.sqrt(dx ** 2 + dy ** 2)
        min_dist = self.puck.radius + paddle.radius

        if distance < min_dist and distance > 0:
            # Normalize collision vector (points from paddle to puck)
            nx = dx / distance
            ny = dy / distance

            # Push puck out of paddle with extra margin to prevent re-collision
            separation = min_dist - distance + 5
            self.puck.center = (px + nx * separation, py + ny * separation)

            # Calculate new puck velocity based on paddle velocity
            # The puck should move in the direction the paddle was moving, plus some reflection
            paddle_speed = math.sqrt(paddle.vx ** 2 + paddle.vy ** 2)

            if paddle_speed > 50:
                # Fast hit - puck goes in paddle's direction
                self.puck.vx = paddle.vx * 1.2
                self.puck.vy = paddle.vy * 1.2
            else:
                # Slow/stationary paddle - reflect puck velocity
                dot = self.puck.vx * nx + self.puck.vy * ny
                self.puck.vx -= 2 * dot * nx
                self.puck.vy -= 2 * dot * ny
                # Add small paddle velocity contribution
                self.puck.vx += paddle.vx * 0.5
                self.puck.vy += paddle.vy * 0.5

            # Ensure puck is moving AWAY from paddle (minimum escape velocity)
            escape_dot = self.puck.vx * nx + self.puck.vy * ny
            min_escape_speed = 250
            if escape_dot < min_escape_speed:
                # Add velocity in the escape direction
                self.puck.vx += nx * (min_escape_speed - escape_dot)
                self.puck.vy += ny * (min_escape_speed - escape_dot)

            # Clamp to reasonable speed
            speed = math.sqrt(self.puck.vx ** 2 + self.puck.vy ** 2)
            if speed > self.puck.max_speed:
                self.puck.vx = (self.puck.vx / speed) * self.puck.max_speed
                self.puck.vy = (self.puck.vy / speed) * self.puck.max_speed

    def on_goal(self, scorer):
        """Handle goal scored"""
        self.scores[scorer] += 1
        self.goal_pause = True

        # Check for winner
        if self.scores[scorer] >= WINNING_SCORE:
            self.end_game(scorer)
            return

        # Brief pause then reset
        def resume(dt):
            self.goal_pause = False
            self.reset_positions()

        if self.goal_pause_timer:
            self.goal_pause_timer.cancel()
        self.goal_pause_timer = Clock.schedule_once(resume, 1.0)

    def end_game(self, winner):
        """End the game"""
        self.game_active = False
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    def get_winner(self):
        """Get the winning player index, or None if game not over"""
        for i, score in enumerate(self.scores):
            if score >= WINNING_SCORE:
                return i
        return None

    def update_canvas(self):
        """Draw all game elements"""
        self.canvas.clear()

        table_bounds = self.get_table_bounds()
        left, bottom, right, top = table_bounds
        table_width = right - left
        table_height = top - bottom
        center_x = (left + right) / 2
        center_y = (bottom + top) / 2
        goal_height = self.get_goal_height()
        goal_half = goal_height / 2

        with self.canvas:
            # Background
            Color(0.1, 0.1, 0.15, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Table surface
            Color(0.15, 0.25, 0.4, 1)
            Rectangle(pos=(left, bottom), size=(table_width, table_height))

            # Table border
            border_width = 4 * self.scale
            Color(0.4, 0.35, 0.3, 1)

            # Top border (solid)
            Rectangle(pos=(left - border_width, top),
                      size=(table_width + border_width * 2, border_width))

            # Bottom border (solid)
            Rectangle(pos=(left - border_width, bottom - border_width),
                      size=(table_width + border_width * 2, border_width))

            # Left border (with goal gap)
            Rectangle(pos=(left - border_width, bottom),
                      size=(border_width, center_y - goal_half - bottom))
            Rectangle(pos=(left - border_width, center_y + goal_half),
                      size=(border_width, top - center_y - goal_half))

            # Right border (with goal gap)
            Rectangle(pos=(right, bottom),
                      size=(border_width, center_y - goal_half - bottom))
            Rectangle(pos=(right, center_y + goal_half),
                      size=(border_width, top - center_y - goal_half))

            # Goal areas
            goal_depth = 30 * self.scale
            Color(0.1, 0.1, 0.1, 1)
            # Left goal (blue's goal - red scores here)
            Rectangle(pos=(left - goal_depth, center_y - goal_half),
                      size=(goal_depth, goal_height))
            # Right goal (red's goal - blue scores here)
            Rectangle(pos=(right, center_y - goal_half),
                      size=(goal_depth, goal_height))

            # Goal outlines
            Color(PLAYER_COLORS[0][0], PLAYER_COLORS[0][1], PLAYER_COLORS[0][2], 0.8)
            Line(rectangle=(left - goal_depth, center_y - goal_half,
                            goal_depth, goal_height), width=2)
            Color(PLAYER_COLORS[1][0], PLAYER_COLORS[1][1], PLAYER_COLORS[1][2], 0.8)
            Line(rectangle=(right, center_y - goal_half,
                            goal_depth, goal_height), width=2)

            # Center line (vertical)
            Color(0.3, 0.4, 0.5, 1)
            line_width = 3 * self.scale
            Rectangle(pos=(center_x - line_width / 2, bottom),
                      size=(line_width, table_height))

            # Center circle
            circle_radius = min(table_width, table_height) * 0.15
            Color(0.3, 0.4, 0.5, 1)
            Line(circle=(center_x, center_y, circle_radius), width=2 * self.scale)

            # Center dot
            dot_radius = 8 * self.scale
            Color(0.3, 0.4, 0.5, 1)
            Ellipse(pos=(center_x - dot_radius, center_y - dot_radius),
                    size=(dot_radius * 2, dot_radius * 2))

            # Draw paddles
            for paddle in self.paddles:
                self.draw_paddle(paddle)

            # Draw puck
            if self.puck:
                self.draw_puck()

    def draw_paddle(self, paddle):
        """Draw a paddle"""
        cx, cy = paddle.center
        r = paddle.radius

        with self.canvas:
            # Outer ring (darker)
            Color(paddle.color[0] * 0.6, paddle.color[1] * 0.6,
                  paddle.color[2] * 0.6, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # Inner circle
            inner_r = r * 0.7
            Color(*paddle.color)
            Ellipse(pos=(cx - inner_r, cy - inner_r),
                    size=(inner_r * 2, inner_r * 2))

            # Center grip
            grip_r = r * 0.3
            Color(paddle.color[0] * 0.4, paddle.color[1] * 0.4,
                  paddle.color[2] * 0.4, 1)
            Ellipse(pos=(cx - grip_r, cy - grip_r),
                    size=(grip_r * 2, grip_r * 2))

    def draw_puck(self):
        """Draw the puck"""
        cx, cy = self.puck.center
        r = self.puck.radius

        with self.canvas:
            # Shadow
            shadow_offset = 3 * self.scale
            Color(0, 0, 0, 0.4)
            Ellipse(pos=(cx - r + shadow_offset, cy - r - shadow_offset),
                    size=(r * 2, r * 2))

            # Puck body
            Color(0.1, 0.1, 0.1, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

            # Puck edge highlight
            Color(0.3, 0.3, 0.3, 1)
            Line(circle=(cx, cy, r), width=2 * self.scale)

            # Center circle
            inner_r = r * 0.4
            Color(0.2, 0.2, 0.2, 1)
            Ellipse(pos=(cx - inner_r, cy - inner_r),
                    size=(inner_r * 2, inner_r * 2))

    def on_touch_down(self, touch):
        for paddle in self.paddles:
            if paddle.on_touch_down(touch):
                return True
        return super(AirHockeyGame, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        for paddle in self.paddles:
            if paddle.on_touch_move(touch):
                return True
        return super(AirHockeyGame, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        for paddle in self.paddles:
            paddle.on_touch_up(touch)
        return super(AirHockeyGame, self).on_touch_up(touch)


class AirHockeyAppLayout(FloatLayout):
    """Main app layout with UI elements"""

    def __init__(self, **kwargs):
        super(AirHockeyAppLayout, self).__init__(**kwargs)

        # Game widget
        self.game = AirHockeyGame(size_hint=(1, 1))
        self.add_widget(self.game)

        # Score labels
        self.score_labels = []
        for i in range(2):
            label = Label(
                text="0",
                font_size='72sp',
                color=PLAYER_COLORS[i],
                size_hint=(None, None),
                size=(100, 100),
                bold=True
            )
            self.score_labels.append(label)
            self.add_widget(label)

        # Title
        self.title_label = Label(
            text="AIR HOCKEY",
            font_size='48sp',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(400, 80),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True
        )
        self.add_widget(self.title_label)

        # Subtitle
        self.subtitle_label = Label(
            text=f"First to {WINNING_SCORE} wins!",
            font_size='24sp',
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(None, None),
            size=(300, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.42}
        )
        self.add_widget(self.subtitle_label)

        # Start button
        self.start_button = Button(
            text="START GAME",
            font_size='32sp',
            size_hint=(None, None),
            size=(280, 80),
            pos_hint={'center_x': 0.5, 'center_y': 0.33},
            background_color=(0.2, 0.6, 0.3, 1)
        )
        self.start_button.bind(on_press=self.on_start_press)
        self.add_widget(self.start_button)

        # Winner label (hidden initially)
        self.winner_label = Label(
            text="",
            font_size='56sp',
            color=(1, 1, 0, 1),
            size_hint=(None, None),
            size=(500, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True
        )
        self.add_widget(self.winner_label)
        self.winner_label.opacity = 0

        # Goal notification label
        self.goal_label = Label(
            text="GOAL!",
            font_size='64sp',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(300, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True
        )
        self.add_widget(self.goal_label)
        self.goal_label.opacity = 0

        # Update positions and scores
        self.bind(size=self.update_ui_positions)
        Clock.schedule_interval(self.update_ui, 1 / 30.0)

        # Disable Windows gestures
        Clock.schedule_once(lambda dt: disable_windows_touch_gestures(), 0.5)

    def update_ui_positions(self, *args):
        """Position UI elements"""
        scale = min(self.width / 1100, self.height / 800)

        # Scale fonts
        score_font = int(72 * scale)
        title_font = int(48 * scale)
        subtitle_font = int(24 * scale)
        button_font = int(32 * scale)
        winner_font = int(56 * scale)
        goal_font = int(64 * scale)

        for label in self.score_labels:
            label.font_size = f'{score_font}sp'
        self.title_label.font_size = f'{title_font}sp'
        self.subtitle_label.font_size = f'{subtitle_font}sp'
        self.start_button.font_size = f'{button_font}sp'
        self.winner_label.font_size = f'{winner_font}sp'
        self.goal_label.font_size = f'{goal_font}sp'

        # Scale button
        self.start_button.size = (280 * scale, 80 * scale)

        # Position score labels on sides
        margin = 80 * scale
        if len(self.score_labels) >= 2:
            # Blue player score (left side)
            self.score_labels[0].center = (self.width * 0.25, self.height - margin)
            # Red player score (right side)
            self.score_labels[1].center = (self.width * 0.75, self.height - margin)

    def update_ui(self, dt):
        """Update UI state"""
        # Update scores
        for i, score in enumerate(self.game.scores):
            if i < len(self.score_labels):
                self.score_labels[i].text = str(score)

        # Show goal notification
        if self.game.goal_pause and not self.game.get_winner():
            self.goal_label.opacity = 1
        else:
            self.goal_label.opacity = 0

        # Check for winner
        winner = self.game.get_winner()
        if winner is not None and self.winner_label.opacity == 0:
            self.winner_label.text = f"{PLAYER_NAMES[winner]} WINS!"
            self.winner_label.color = PLAYER_COLORS[winner]
            self.winner_label.opacity = 1
            self.start_button.text = "PLAY AGAIN"
            self.start_button.opacity = 1

    def on_start_press(self, instance):
        """Start a new game"""
        self.title_label.opacity = 0
        self.subtitle_label.opacity = 0
        self.winner_label.opacity = 0
        self.start_button.opacity = 0

        for label in self.score_labels:
            label.opacity = 1

        self.game.start_game()


class AirHockey(App):
    def build(self):
        return AirHockeyAppLayout()


if __name__ == '__main__':
    AirHockey().run()
