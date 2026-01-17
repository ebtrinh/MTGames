from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Ellipse, Rectangle, Triangle, PushMatrix, PopMatrix, Rotate
from kivy.clock import Clock
from kivy.config import Config
import random
import math
import ctypes

# WM_TOUCH Configuration - same as other touchscreen games
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('input', 'wm_touch', 'wm_touch')
Config.set('input', 'wm_pen', 'wm_pen')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1100')
Config.set('graphics', 'height', '850')

# Disable Windows touch gestures to prevent interference
def disable_windows_touch_gestures():
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
    (0.9, 0.2, 0.2, 1),   # Red
    (0.2, 0.7, 0.2, 1),   # Green
    (0.2, 0.4, 0.9, 1),   # Blue
    (0.9, 0.7, 0.1, 1),   # Yellow
]

PLAYER_NAMES = ["Red", "Green", "Blue", "Yellow"]


class Ball(Widget):
    """A marble ball that bounces around the play area"""

    def __init__(self, x, y, radius=15, is_golden=False, **kwargs):
        super(Ball, self).__init__(**kwargs)
        self.base_radius = radius  # Base radius for scaling
        self.radius = radius
        self.size = (radius * 2, radius * 2)
        self.center = (x, y)

        # Random velocity - FAST and violent
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(300, 500)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.active = True

        # Golden balls are worth 3 points
        self.is_golden = is_golden
        if is_golden:
            self.color = (1, 0.85, 0, 1)  # Golden yellow
            self.points = 3
        else:
            self.color = (1, 1, 1, 1)  # White marble
            self.points = 1

    def update_size(self, scale):
        """Update ball size based on scale factor"""
        self.radius = self.base_radius * scale
        self.size = (self.radius * 2, self.radius * 2)

    def update(self, dt, circle_center, circle_radius):
        """Update ball position and handle circular boundary bounces"""
        if not self.active:
            return

        # Move ball
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Get ball center
        bx, by = self.center
        cx, cy = circle_center

        # Distance from ball center to circle center
        dx = bx - cx
        dy = by - cy
        distance = math.sqrt(dx**2 + dy**2)

        # Bounce off circular boundary (accounting for ball radius and hippo space)
        boundary_radius = circle_radius - self.radius - 20
        if distance > boundary_radius:
            # Normalize the direction vector
            if distance > 0:
                nx = dx / distance
                ny = dy / distance
            else:
                nx, ny = 0, 1

            # Push ball back inside
            self.center = (
                cx + nx * boundary_radius,
                cy + ny * boundary_radius
            )

            # Reflect velocity off the circular boundary - NO damping for violent bounces
            dot = self.vx * nx + self.vy * ny
            self.vx = (self.vx - 2 * dot * nx) * 1.02  # Slight boost on bounce!
            self.vy = (self.vy - 2 * dot * ny) * 1.02

        # Add violent random movement to keep balls chaotic
        self.vx += random.uniform(-50, 50)
        self.vy += random.uniform(-50, 50)

        # Clamp velocity - high speeds allowed
        max_speed = 600
        min_speed = 200
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > max_speed:
            self.vx = (self.vx / speed) * max_speed
            self.vy = (self.vy / speed) * max_speed
        elif speed < min_speed:
            # Keep high minimum speed
            if speed > 0:
                self.vx = (self.vx / speed) * min_speed
                self.vy = (self.vy / speed) * min_speed


class Hippo(Widget):
    """A hippo that can chomp to collect balls"""

    def __init__(self, player_id, angle, game, **kwargs):
        super(Hippo, self).__init__(**kwargs)
        self.player_id = player_id
        self.angle = angle  # Angle in degrees around the circle (0 = bottom)
        self.game = game
        self.color = PLAYER_COLORS[player_id]
        self.score = 0

        # Chomp state - simplified
        self.is_active = False  # Is the hippo being pressed?
        self.extend_progress = 0  # 0 to 1, how far head is extended out
        self.head_scale = 1.0  # 1.0 = normal (down), 1.5 = enlarged (up/open)
        self.has_chomped = False  # Has this press already done its chomp?

        # Animation speeds
        self.extend_speed = 8  # How fast head extends/retracts
        self.shrink_speed = 20  # How fast head snaps down - very fast!

        # Base sizes (will be scaled)
        self.base_body_size = 120  # Made bigger
        self.base_mouth_extend = 80  # Made bigger

        # Current sizes (updated on resize)
        self.body_size = self.base_body_size
        self.mouth_extend = self.base_mouth_extend
        self.scale = 1.0

        # Touch tracking - store all touches on this hippo
        self.active_touches = set()

    def update_size(self, scale):
        """Update hippo size based on scale factor"""
        self.scale = scale
        self.body_size = self.base_body_size * scale
        self.mouth_extend = self.base_mouth_extend * scale
        self.size = (self.body_size * 2.5, self.body_size * 2.5)

    def get_rotation(self):
        """Get rotation angle - hippos face inward toward center"""
        return self.angle  # Face toward center

    def get_head_center_and_radius(self):
        """Get the current head position and radius for collision detection"""
        cx, cy = self.center
        extend = self.mouth_extend * self.extend_progress

        # Calculate direction toward center (inward)
        angle_rad = math.radians(self.angle + 90)
        dir_x = math.cos(angle_rad)
        dir_y = math.sin(angle_rad)

        # Head position extends inward from hippo body
        head_cx = cx + dir_x * extend * 0.6
        head_cy = cy + dir_y * extend * 0.6

        # Head radius based on current scale
        head_radius = self.body_size * 0.45 * self.head_scale

        return head_cx, head_cy, head_radius

    def get_body_center_and_radius(self):
        """Get the hippo body position and radius for collision detection"""
        cx, cy = self.center
        body_radius = self.body_size * 0.5
        return cx, cy, body_radius

    def is_head_up(self):
        """Returns True if the head is enlarged (up position) - can eat balls"""
        return self.head_scale > 1.25 and self.extend_progress > 0.5

    def check_ball_collision(self, ball):
        """Check if head or body collides with a ball. Returns 'eat', 'bounce', or None"""
        bx, by = ball.center
        br = ball.radius

        # Check head collision if extended
        if self.extend_progress > 0.3:
            head_cx, head_cy, head_radius = self.get_head_center_and_radius()
            dx = bx - head_cx
            dy = by - head_cy
            distance = math.sqrt(dx**2 + dy**2)

            if distance < head_radius + br:
                if self.is_head_up():
                    return 'eat'  # Head is up/enlarged - eat the ball
                else:
                    return 'bounce'  # Head is down/normal - bounce the ball

        # Always check body collision (even when not extended)
        body_cx, body_cy, body_radius = self.get_body_center_and_radius()
        dx = bx - body_cx
        dy = by - body_cy
        distance = math.sqrt(dx**2 + dy**2)

        if distance < body_radius + br:
            return 'bounce'  # Always bounce off body

        return None

    def bounce_ball(self, ball):
        """Bounce a ball away from the hippo"""
        bx, by = ball.center

        # Determine what to bounce off of - head if extended, otherwise body
        if self.extend_progress > 0.3:
            center_x, center_y, radius = self.get_head_center_and_radius()
        else:
            center_x, center_y, radius = self.get_body_center_and_radius()

        # Calculate direction from hippo to ball
        dx = bx - center_x
        dy = by - center_y
        distance = math.sqrt(dx**2 + dy**2)

        if distance > 0:
            # Normalize direction
            nx = dx / distance
            ny = dy / distance

            # Push ball out
            push_dist = radius + ball.radius + 5
            ball.center = (center_x + nx * push_dist, center_y + ny * push_dist)

            # Reflect and boost velocity away
            speed = math.sqrt(ball.vx**2 + ball.vy**2)
            ball.vx = nx * max(speed, 200)
            ball.vy = ny * max(speed, 200)

    def start_chomp(self):
        """Start the chomp action"""
        self.is_active = True
        self.has_chomped = False  # New press, ready to chomp

    def stop_chomp(self):
        """Stop chomping - head will retract"""
        self.is_active = False

    def update(self, dt):
        """Update chomp animation"""
        if self.is_active:
            if not self.has_chomped:
                # Extending out AND enlarging at the same time
                self.extend_progress = min(1, self.extend_progress + self.extend_speed * dt)
                # Head enlarges proportionally as it extends
                self.head_scale = 1.0 + (self.extend_progress * 0.5)  # 1.0 to 1.5

                # Once fully extended, snap down
                if self.extend_progress >= 1:
                    self.has_chomped = True  # Mark that we've done the chomp
            else:
                # Already extended - snap head down to normal size
                if self.head_scale > 1.0:
                    self.head_scale = max(1.0, self.head_scale - self.shrink_speed * dt)
                # Stay extended at normal size while held (do nothing else)
        else:
            # Released: retract head back into body
            # First shrink head to normal if needed
            if self.head_scale > 1.0:
                self.head_scale = max(1.0, self.head_scale - self.shrink_speed * dt)
            else:
                # Then retract
                self.extend_progress = max(0, self.extend_progress - self.extend_speed * dt)
                if self.extend_progress <= 0:
                    # Fully retracted, reset state
                    self.head_scale = 1.0
                    self.has_chomped = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.active_touches.add(touch.uid)
            touch.ud['hippo'] = self
            self.start_chomp()
            return True
        return False

    def on_touch_up(self, touch):
        if touch.uid in self.active_touches:
            self.active_touches.discard(touch.uid)
            # Only stop chomping if all touches are released
            if len(self.active_touches) == 0:
                self.stop_chomp()
            return True
        return False


class HungryHipposGame(Widget):
    """Main game widget"""

    def __init__(self, **kwargs):
        super(HungryHipposGame, self).__init__(**kwargs)
        self.hippos = []
        self.balls = []
        self.game_active = False
        self.total_balls = 20
        self.balls_remaining = 0
        self.update_timer = None

        # Circle properties (calculated on resize)
        self.circle_center = (0, 0)
        self.circle_radius = 100
        self.scale = 1.0

        self.bind(size=self.on_size_change, pos=self.on_size_change)

    def get_scale(self):
        """Get scale factor based on window size"""
        base_size = 800  # Base window size for scale=1
        current_size = min(self.width, self.height)
        return current_size / base_size

    def on_size_change(self, *args):
        # Update circle dimensions
        self.circle_center = (self.width / 2, self.height / 2)
        self.circle_radius = min(self.width, self.height) / 2 - 20
        self.scale = self.get_scale()

        # Update all object sizes
        for ball in self.balls:
            ball.update_size(self.scale)

        if self.hippos:
            self.position_hippos()

        self.update_canvas()

    def position_hippos(self):
        """Position hippos around the circle edge"""
        cx, cy = self.circle_center
        # Place hippos slightly outside the circle
        hippo_distance = self.circle_radius - 30 * self.scale

        for hippo in self.hippos:
            hippo.update_size(self.scale)

            # Convert angle to radians (0 = right, 90 = up, etc.)
            # Subtract 90 to make 0 = bottom
            angle_rad = math.radians(hippo.angle - 90)
            hx = cx + math.cos(angle_rad) * hippo_distance
            hy = cy + math.sin(angle_rad) * hippo_distance

            hippo.center = (hx, hy)

    def start_game(self, num_players=4):
        """Start a new game"""
        self.hippos = []
        self.balls = []

        # Recalculate circle
        self.circle_center = (self.width / 2, self.height / 2)
        self.circle_radius = min(self.width, self.height) / 2 - 20
        self.scale = self.get_scale()

        # Create hippos at equal angles around circle
        # Angles: 0 (bottom), 90 (right), 180 (top), 270 (left)
        angles = [0, 90, 180, 270]
        for i in range(num_players):
            hippo = Hippo(i, angles[i], self)
            self.hippos.append(hippo)

        self.position_hippos()

        # Create balls in center
        cx, cy = self.circle_center
        num_golden = 3  # 3 special golden balls worth 3 points each
        for i in range(self.total_balls):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, 50 * self.scale)
            x = cx + math.cos(angle) * dist
            y = cy + math.sin(angle) * dist
            is_golden = i < num_golden  # First 3 balls are golden
            ball = Ball(x, y, radius=18 if not is_golden else 22, is_golden=is_golden)
            ball.update_size(self.scale)
            self.balls.append(ball)

        self.balls_remaining = self.total_balls
        self.game_active = True

        # Start update loop
        if self.update_timer:
            self.update_timer.cancel()
        self.update_timer = Clock.schedule_interval(self.update_game, 1/60.0)

        self.update_canvas()

    def update_game(self, dt):
        """Main game update loop"""
        if not self.game_active:
            return

        # Update balls with circular boundary
        for ball in self.balls:
            ball.update(dt, self.circle_center, self.circle_radius)

        # Update hippos and check collisions
        for hippo in self.hippos:
            hippo.update(dt)

            # Check ball collisions
            for ball in self.balls:
                if ball.active:
                    result = hippo.check_ball_collision(ball)
                    if result == 'eat':
                        ball.active = False
                        hippo.score += ball.points  # Golden balls worth 3!
                        self.balls_remaining -= 1
                    elif result == 'bounce':
                        hippo.bounce_ball(ball)

        # Check win condition
        if self.balls_remaining <= 0:
            self.end_game()

        self.update_canvas()

    def end_game(self):
        """End the game and show winner"""
        self.game_active = False
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    def get_winner(self):
        """Get the winning player(s)"""
        if not self.hippos:
            return None
        max_score = max(h.score for h in self.hippos)
        winners = [h for h in self.hippos if h.score == max_score]
        return winners

    def update_canvas(self):
        """Draw all game elements"""
        self.canvas.clear()

        cx, cy = self.circle_center

        with self.canvas:
            # Background
            Color(0.15, 0.15, 0.2, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Play area circle (outer ring)
            Color(0.3, 0.4, 0.3, 1)
            Ellipse(
                pos=(cx - self.circle_radius, cy - self.circle_radius),
                size=(self.circle_radius * 2, self.circle_radius * 2)
            )

            # Inner play area
            inner_radius = self.circle_radius - 15 * self.scale
            Color(0.2, 0.3, 0.2, 1)
            Ellipse(
                pos=(cx - inner_radius, cy - inner_radius),
                size=(inner_radius * 2, inner_radius * 2)
            )

            # Draw hippos
            for hippo in self.hippos:
                self.draw_hippo(hippo)

            # Draw balls
            for ball in self.balls:
                if ball.active:
                    # Golden ball glow effect
                    if ball.is_golden:
                        Color(1, 0.9, 0, 0.3)
                        glow_size = ball.radius * 3
                        Ellipse(
                            pos=(ball.center_x - glow_size/2, ball.center_y - glow_size/2),
                            size=(glow_size, glow_size)
                        )
                    # Ball shadow
                    Color(0, 0, 0, 0.3)
                    shadow_offset = 3 * self.scale
                    Ellipse(
                        pos=(ball.x + shadow_offset, ball.y - shadow_offset),
                        size=ball.size
                    )
                    # Ball
                    Color(*ball.color)
                    Ellipse(pos=ball.pos, size=ball.size)
                    # Ball shine
                    Color(1, 1, 1, 0.5 if ball.is_golden else 0.4)
                    shine_size = ball.radius * 0.6
                    Ellipse(
                        pos=(ball.x + ball.radius * 0.3, ball.y + ball.radius * 0.8),
                        size=(shine_size, shine_size)
                    )

    def draw_hippo(self, hippo):
        """Draw a single hippo - head scales up/down for chomp animation"""
        cx, cy = hippo.center
        color = hippo.color
        scale = hippo.scale

        # Calculate animations
        extend = hippo.mouth_extend * hippo.extend_progress  # How far out the head is
        head_scale_factor = hippo.head_scale  # How big the head is (1.0 = normal, 1.5 = enlarged/up)

        with self.canvas:
            PushMatrix()
            Rotate(angle=hippo.get_rotation(), origin=(cx, cy))

            # Hippo body (back part) - stays fixed
            Color(color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, 1)
            body_size = hippo.body_size
            body_offset = 25 * scale
            Ellipse(
                pos=(cx - body_size/2, cy - body_size/2 - body_offset),
                size=(body_size, body_size)
            )

            # Neck/connector when extended
            if hippo.extend_progress > 0.1:
                Color(color[0] * 0.8, color[1] * 0.8, color[2] * 0.8, 1)
                neck_width = body_size * 0.5
                neck_height = extend * 0.8
                Ellipse(
                    pos=(cx - neck_width/2, cy - neck_width/4),
                    size=(neck_width, neck_height)
                )

            # Hippo head - extends out and scales up/down
            Color(*color)
            base_head_size = body_size * 0.9
            head_size = base_head_size * head_scale_factor
            head_y = cy + extend * 0.6

            # Main head ellipse
            Ellipse(
                pos=(cx - head_size/2, head_y - head_size/3),
                size=(head_size, head_size * 0.85)
            )

            # Snout (top of head) - also scales
            snout_width = head_size * 0.75
            snout_height = head_size * 0.45
            snout_y = head_y + head_size * 0.25
            Color(color[0] * 1.1, color[1] * 1.1, color[2] * 1.1, 1)
            Ellipse(
                pos=(cx - snout_width/2, snout_y),
                size=(snout_width, snout_height)
            )

            # Eyes - scale with head
            eye_offset = head_size * 0.22
            eye_size = 18 * scale * head_scale_factor
            Color(1, 1, 1, 1)
            Ellipse(
                pos=(cx - eye_offset - eye_size/2, head_y + head_size * 0.05),
                size=(eye_size, eye_size)
            )
            Ellipse(
                pos=(cx + eye_offset - eye_size/2, head_y + head_size * 0.05),
                size=(eye_size, eye_size)
            )

            # Pupils
            pupil_size = 10 * scale * head_scale_factor
            Color(0, 0, 0, 1)
            Ellipse(
                pos=(cx - eye_offset - pupil_size/2, head_y + head_size * 0.03),
                size=(pupil_size, pupil_size)
            )
            Ellipse(
                pos=(cx + eye_offset - pupil_size/2, head_y + head_size * 0.03),
                size=(pupil_size, pupil_size)
            )

            # Nostrils - scale with head
            nostril_size = 8 * scale * head_scale_factor
            nostril_offset = 12 * scale * head_scale_factor
            Color(0.2, 0.1, 0.1, 1)
            Ellipse(
                pos=(cx - nostril_offset - nostril_size/2, snout_y + snout_height * 0.55),
                size=(nostril_size, nostril_size)
            )
            Ellipse(
                pos=(cx + nostril_offset - nostril_size/2, snout_y + snout_height * 0.55),
                size=(nostril_size, nostril_size)
            )

            PopMatrix()

    def on_touch_down(self, touch):
        for hippo in self.hippos:
            if hippo.on_touch_down(touch):
                return True
        return super(HungryHipposGame, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        for hippo in self.hippos:
            hippo.on_touch_up(touch)
        return super(HungryHipposGame, self).on_touch_up(touch)


class HungryHipposApp(FloatLayout):
    """Main app layout with UI elements"""

    def __init__(self, **kwargs):
        super(HungryHipposApp, self).__init__(**kwargs)

        # Game widget
        self.game = HungryHipposGame(size_hint=(1, 1))
        self.add_widget(self.game)

        # Score labels for each player
        self.score_labels = []

        for i in range(4):
            label = Label(
                text=f"{PLAYER_NAMES[i]}: 0",
                font_size='24sp',
                color=PLAYER_COLORS[i],
                size_hint=(None, None),
                size=(150, 50),
                bold=True
            )
            self.score_labels.append(label)
            self.add_widget(label)

        # Title box background
        self.title_box = Widget(
            size_hint=(None, None),
            size=(500, 80),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        with self.title_box.canvas:
            Color(0, 0, 0, 0.7)
            self.title_box_rect = Rectangle(pos=self.title_box.pos, size=self.title_box.size)
        self.title_box.bind(pos=self._update_title_box, size=self._update_title_box)
        self.add_widget(self.title_box)

        # Title
        self.title_label = Label(
            text="HUNGRY HUNGRY HIPPOS",
            font_size='36sp',
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(500, 80),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True
        )
        self.add_widget(self.title_label)

        # Start button
        self.start_button = Button(
            text="START GAME",
            font_size='28sp',
            size_hint=(None, None),
            size=(250, 70),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
            background_color=(0.2, 0.7, 0.3, 1)
        )
        self.start_button.bind(on_press=self.on_start_press)
        self.add_widget(self.start_button)

        # Winner box background (hidden initially)
        self.winner_box = Widget(
            size_hint=(None, None),
            size=(500, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        with self.winner_box.canvas:
            Color(0, 0, 0, 0.8)
            self.winner_box_rect = Rectangle(pos=self.winner_box.pos, size=self.winner_box.size)
        self.winner_box.bind(pos=self._update_winner_box, size=self._update_winner_box)
        self.add_widget(self.winner_box)
        self.winner_box.opacity = 0

        # Winner label (hidden initially)
        self.winner_label = Label(
            text="",
            font_size='48sp',
            color=(1, 1, 0, 1),
            size_hint=(None, None),
            size=(500, 100),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            bold=True
        )
        self.add_widget(self.winner_label)
        self.winner_label.opacity = 0

        # Balls remaining label
        self.balls_label = Label(
            text="",
            font_size='20sp',
            color=(1, 1, 1, 0.8),
            size_hint=(None, None),
            size=(200, 40),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.balls_label)

        # Update positions and scores
        self.bind(size=self.update_ui_positions)
        Clock.schedule_interval(self.update_scores, 1/30.0)

        # Disable Windows gestures after a short delay
        Clock.schedule_once(lambda dt: disable_windows_touch_gestures(), 0.5)

    def _update_title_box(self, *args):
        """Update title box rectangle position"""
        self.title_box_rect.pos = self.title_box.pos
        self.title_box_rect.size = self.title_box.size

    def _update_winner_box(self, *args):
        """Update winner box rectangle position"""
        self.winner_box_rect.pos = self.winner_box.pos
        self.winner_box_rect.size = self.winner_box.size

    def update_ui_positions(self, *args):
        """Position score labels inside the circle between center and hippos"""
        # Calculate circle properties directly from current window size
        # to avoid timing issues with game's on_size_change
        cx = self.width / 2
        cy = self.height / 2
        circle_radius = min(self.width, self.height) / 2 - 20
        base_size = 800
        scale = min(self.width, self.height) / base_size

        # Scale all text
        score_font_size = int(24 * scale)
        title_font_size = int(36 * scale)
        button_font_size = int(28 * scale)
        winner_font_size = int(48 * scale)
        balls_font_size = int(20 * scale)

        for label in self.score_labels:
            label.font_size = f'{score_font_size}sp'
        self.title_label.font_size = f'{title_font_size}sp'
        self.start_button.font_size = f'{button_font_size}sp'
        self.winner_label.font_size = f'{winner_font_size}sp'
        self.balls_label.font_size = f'{balls_font_size}sp'

        # Scale button and box sizes
        self.start_button.size = (250 * scale, 70 * scale)
        self.title_box.size = (500 * scale, 80 * scale)
        self.title_label.size = (500 * scale, 80 * scale)
        self.winner_box.size = (500 * scale, 100 * scale)
        self.winner_label.size = (500 * scale, 100 * scale)

        if len(self.score_labels) >= 4 and circle_radius > 0:
            # Position labels inside the circle, halfway between center and hippo
            label_distance = circle_radius * 0.55

            # Position labels around the circle matching hippo positions
            # Angles: 0 (bottom), 90 (right), 180 (top), 270 (left)
            angles = [0, 90, 180, 270]
            for i, angle in enumerate(angles):
                angle_rad = math.radians(angle - 90)
                lx = cx + math.cos(angle_rad) * label_distance
                ly = cy + math.sin(angle_rad) * label_distance
                self.score_labels[i].center = (lx, ly)

    def update_scores(self, dt):
        """Update score display"""
        for i, hippo in enumerate(self.game.hippos):
            if i < len(self.score_labels):
                self.score_labels[i].text = f"{PLAYER_NAMES[i]}: {hippo.score}"

        # Update balls remaining
        if self.game.game_active:
            self.balls_label.text = f"Balls: {self.game.balls_remaining}"

        # Check for game end
        if not self.game.game_active and self.game.hippos and self.game.balls_remaining <= 0:
            winners = self.game.get_winner()
            if winners and self.winner_label.opacity == 0:
                if len(winners) == 1:
                    self.winner_label.text = f"{PLAYER_NAMES[winners[0].player_id]} WINS!"
                    self.winner_label.color = winners[0].color
                else:
                    names = " & ".join(PLAYER_NAMES[w.player_id] for w in winners)
                    self.winner_label.text = f"TIE: {names}!"
                    self.winner_label.color = (1, 1, 0, 1)
                self.winner_label.opacity = 1
                self.winner_box.opacity = 1
                self.start_button.text = "PLAY AGAIN"
                self.start_button.opacity = 1

    def on_start_press(self, instance):
        """Start a new game"""
        self.title_label.opacity = 0
        self.title_box.opacity = 0
        self.winner_label.opacity = 0
        self.winner_box.opacity = 0
        self.start_button.opacity = 0

        # Show all score labels
        for label in self.score_labels:
            label.opacity = 1

        self.game.start_game(num_players=4)


class HungryHippos(App):
    def build(self):
        return HungryHipposApp()


if __name__ == '__main__':
    HungryHippos().run()
