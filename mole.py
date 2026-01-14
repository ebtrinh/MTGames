from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, Rectangle, Line as GLine
from math import cos, sin, radians
from kivy.clock import Clock
from kivy.config import Config
import random

# Configure for touchscreen
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1100')
Config.set('graphics', 'height', '850')

# Ensure Windows touch input is enabled
Config.set('input', 'wm_touch', 'wm_touch')
Config.set('input', 'wm_pen', 'wm_pen')


class Mole(Widget):
    def __init__(self, hole_index, on_whack_callback, **kwargs):
        super(Mole, self).__init__(**kwargs)
        self.hole_index = hole_index
        self.on_whack_callback = on_whack_callback
        self.is_up = False
        self.mole_type = 'normal'  # 'normal' or 'bomb'
        self.is_hit = False  # Track if mole has been hit
        self.bind(size=self.update_canvas, pos=self.update_canvas)
        self.update_canvas()
    
    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            if self.is_up:
                if self.mole_type == 'bomb':
                    # Draw bomb (black/red circle with fuse)
                    Color(0.8, 0, 0, 1)  # Red
                    Ellipse(pos=self.pos, size=self.size)
                    
                    # Draw black circle inside
                    Color(0, 0, 0, 1)  # Black
                    inner_margin = self.width * 0.15
                    Ellipse(pos=(self.x + inner_margin, self.y + inner_margin), 
                           size=(self.width - inner_margin * 2, self.height - inner_margin * 2))
                    
                    # Draw fuse (yellow/orange - simple rectangle)
                    Color(1, 0.6, 0, 1)  # Orange/Yellow
                    fuse_width = self.width * 0.15
                    fuse_height = self.height * 0.2
                    Rectangle(pos=(self.x + (self.width - fuse_width) / 2, self.y + self.height * 0.8),
                             size=(fuse_width, fuse_height))
                    
                    # Draw skull symbol (X shape)
                    Color(1, 1, 1, 1)  # White
                    center_x = self.x + self.width / 2
                    center_y = self.y + self.height / 2
                    half_size = self.width * 0.15
                    # Top-left to bottom-right
                    GLine(points=[center_x - half_size, center_y + half_size, 
                                 center_x + half_size, center_y - half_size],
                         width=max(3, self.width * 0.08))
                    # Top-right to bottom-left
                    GLine(points=[center_x + half_size, center_y + half_size,
                                 center_x - half_size, center_y - half_size],
                         width=max(3, self.width * 0.08))
                else:
                    # Draw mole (brown circle with face)
                    Color(0.4, 0.2, 0.1, 1)  # Brown
                    Ellipse(pos=self.pos, size=self.size)
                    
                    # Draw eyes
                    eye_size = self.width * 0.15
                    eye_offset_x = self.width * 0.25
                    eye_offset_y = self.height * 0.35
                    
                    if self.is_hit:
                        # Draw X eyes for dead mole
                        Color(1, 0, 0, 1)  # Red X
                        center_x_left = self.x + eye_offset_x + eye_size / 2
                        center_x_right = self.x + self.width - eye_offset_x - eye_size / 2
                        center_y = self.y + eye_offset_y + eye_size / 2
                        half_eye = eye_size * 0.35
                        # Left eye X
                        GLine(points=[center_x_left - half_eye, center_y + half_eye,
                                     center_x_left + half_eye, center_y - half_eye],
                             width=max(2, self.width * 0.06))
                        GLine(points=[center_x_left + half_eye, center_y + half_eye,
                                     center_x_left - half_eye, center_y - half_eye],
                             width=max(2, self.width * 0.06))
                        # Right eye X
                        GLine(points=[center_x_right - half_eye, center_y + half_eye,
                                     center_x_right + half_eye, center_y - half_eye],
                             width=max(2, self.width * 0.06))
                        GLine(points=[center_x_right + half_eye, center_y + half_eye,
                                     center_x_right - half_eye, center_y - half_eye],
                             width=max(2, self.width * 0.06))
                    else:
                        # Draw normal eyes
                        Color(1, 1, 1, 1)  # White
                        Ellipse(pos=(self.x + eye_offset_x, self.y + eye_offset_y), size=(eye_size, eye_size))
                        Ellipse(pos=(self.x + self.width - eye_offset_x - eye_size, self.y + eye_offset_y), size=(eye_size, eye_size))
                        
                        # Draw pupils
                        Color(0, 0, 0, 1)  # Black
                        pupil_size = eye_size * 0.5
                        pupil_offset = (eye_size - pupil_size) / 2
                        Ellipse(pos=(self.x + eye_offset_x + pupil_offset, self.y + eye_offset_y + pupil_offset), size=(pupil_size, pupil_size))
                        Ellipse(pos=(self.x + self.width - eye_offset_x - eye_size + pupil_offset, self.y + eye_offset_y + pupil_offset), size=(pupil_size, pupil_size))
                    
                    # Draw nose
                    Color(1, 0.5, 0, 1)  # Orange
                    nose_size = self.width * 0.2
                    Ellipse(pos=(self.x + (self.width - nose_size) / 2, self.y + self.height * 0.15), size=(nose_size, nose_size))
            else:
                # Draw empty hole (dark gray)
                Color(0.3, 0.3, 0.3, 1)  # Dark gray
                Ellipse(pos=self.pos, size=self.size)
    
    def pop_up(self, mole_type='normal'):
        self.mole_type = mole_type
        self.is_up = True
        self.is_hit = False
        self.update_canvas()
    
    def pop_down(self):
        self.is_up = False
        self.is_hit = False
        self.update_canvas()
    
    def mark_hit(self):
        """Mark the mole as hit (for visual feedback)"""
        self.is_hit = True
        self.update_canvas()
    
    def on_touch_down(self, touch):
        if self.is_up and self.collide_point(*touch.pos):
            if self.mole_type == 'bomb':
                # For bombs, trigger explosion callback immediately
                self.on_whack_callback(self.mole_type, self)
            else:
                # For normal moles, show X eyes briefly before disappearing
                self.mark_hit()
                self.on_whack_callback(self.mole_type, self)
            return True
        return False


class Explosion(Widget):
    """Explosion animation widget"""
    def __init__(self, center_x, center_y, base_size, parent_widget, **kwargs):
        super(Explosion, self).__init__(**kwargs)
        # Store absolute coordinates (relative to parent/game widget)
        self.center_x = center_x
        self.center_y = center_y
        self.base_size = base_size
        self.parent_widget = parent_widget  # Reference to game widget for coordinate conversion
        self.radius = base_size * 0.2
        self.max_radius = base_size * 2.0
        self.alpha = 1.0
        self.particles = []
        self.animation_clock = None
        self.init_particles()
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.update_canvas()
    
    def init_particles(self):
        """Create particle positions for explosion"""
        num_particles = 16
        for i in range(num_particles):
            angle = radians(i * (360 / num_particles))
            self.particles.append({
                'angle': angle,
                'distance': self.radius * 0.3,
                'size': self.base_size * 0.12,
                'color_idx': i % 3
            })
    
    def update_canvas(self, *args):
        self.canvas.clear()
        # Convert absolute coordinates to relative coordinates (relative to this widget's position)
        rel_x = self.center_x - self.x
        rel_y = self.center_y - self.y
        
        with self.canvas:
            # Draw explosion particles
            for particle in self.particles:
                # Use bright colors (red, orange, yellow)
                if particle['color_idx'] == 0:
                    Color(1, 0.2, 0, self.alpha)  # Red
                elif particle['color_idx'] == 1:
                    Color(1, 0.6, 0, self.alpha)  # Orange
                else:
                    Color(1, 1, 0, self.alpha)  # Yellow
                
                # Calculate particle position relative to explosion center (which is relative to this widget)
                x = rel_x + cos(particle['angle']) * particle['distance'] - particle['size']/2
                y = rel_y + sin(particle['angle']) * particle['distance'] - particle['size']/2
                
                # Draw particle
                Ellipse(pos=(x, y), size=(particle['size'], particle['size']))
            
            # Draw central burst circle
            if self.alpha > 0.5:
                Color(1, 1, 0.5, self.alpha * 0.8)  # Bright yellow/white center
                Ellipse(pos=(rel_x - self.radius * 0.3, rel_y - self.radius * 0.3),
                       size=(self.radius * 0.6, self.radius * 0.6))
    
    def animate(self, dt):
        """Animate explosion expanding"""
        expand_speed = self.max_radius * 0.25
        still_expanding = False
        
        for particle in self.particles:
            if particle['distance'] < self.max_radius:
                particle['distance'] += expand_speed * dt * 60
                particle['size'] *= (1 + dt * 0.5)
                still_expanding = True
        
        self.alpha -= dt * 2.0  # Fade out
        
        if self.alpha <= 0 or not still_expanding:
            # Clean up
            if self.animation_clock:
                self.animation_clock.cancel()
            if self.parent:
                self.parent.remove_widget(self)
            return False
        
        self.update_canvas()
        return True


class WhackAMoleGame(Widget):
    def __init__(self, **kwargs):
        super(WhackAMoleGame, self).__init__(**kwargs)
        self.score = 0
        self.moles = []
        self.game_active = False
        self.mole_schedule = None
        self.game_timer = None
        self.time_remaining = 60  # 60 second game
        self.start_time = 0  # Track game start time for speed increase
        
        # Adaptive grid - will be calculated based on window size
        self.grid_rows = 4
        self.grid_cols = 5
        self.mole_size = 80
        self.spacing = 60  # Much more spacing between cells
        
        # Speed control
        self.base_speed = 1.5  # Base time between moles (seconds)
        self.min_speed = 0.2  # Minimum time (maximum speed)
        self.speed_factor = 1.0  # Current speed multiplier
        
        # Explosions list
        self.explosions = []
        
        # Bind size to update layout and recalculate grid
        self.bind(size=self.calculate_grid_and_layout)
        self.bind(pos=self.update_layout)
    
    def calculate_grid_and_layout(self, *args):
        """Calculate optimal grid size based on window dimensions"""
        if self.width <= 0 or self.height <= 0:
            return
        
        # Reserve space for UI (top and bottom)
        usable_width = self.width - 40  # 20px margin on each side
        usable_height = self.height - 150  # Space for UI elements
        
        # Calculate how many cells can fit with desired spacing
        # Try different mole sizes to find optimal fit
        target_mole_size = 75
        target_spacing = 60
        
        # Calculate max cells that fit
        max_cols = int((usable_width + target_spacing) / (target_mole_size + target_spacing))
        max_rows = int((usable_height + target_spacing) / (target_mole_size + target_spacing))
        
        # Limit grid size (reasonable bounds)
        max_cols = min(max_cols, 8)
        max_rows = min(max_rows, 7)
        max_cols = max(max_cols, 3)
        max_rows = max(max_rows, 3)
        
        # Adjust mole size to fit nicely
        available_width = usable_width - (max_cols - 1) * target_spacing
        available_height = usable_height - (max_rows - 1) * target_spacing
        self.mole_size = min(available_width / max_cols, available_height / max_rows)
        self.mole_size = max(60, min(120, self.mole_size))  # Clamp between 60-120
        
        self.grid_cols = max_cols
        self.grid_rows = max_rows
        self.spacing = target_spacing
        
        # Only update positions here, don't recreate moles
        # Mole recreation is handled in start_game() or when size changes during non-active game
        if len(self.moles) > 0:
            old_num_moles = len(self.moles)
            new_num_moles = self.grid_rows * self.grid_cols
            # If grid size changed and game is not active, recreate moles
            if not self.game_active and old_num_moles != new_num_moles:
                self.create_moles()
            else:
                # Just update positions (or skip if game active to avoid mid-game disruption)
                if not self.game_active:
                    self.update_layout()
        else:
            # No moles yet, just update layout (moles will be created when game starts)
            self.update_layout()
    
    def update_layout(self, *args):
        """Update positions of existing moles"""
        if len(self.moles) == 0:
            return
        
        # Calculate grid layout
        total_width = (self.grid_cols * self.mole_size) + ((self.grid_cols - 1) * self.spacing)
        total_height = (self.grid_rows * self.mole_size) + ((self.grid_rows - 1) * self.spacing)
        
        start_x = self.x + (self.width - total_width) / 2
        start_y = self.y + (self.height - total_height) / 2 + 50  # Offset for UI
        
        for i, mole in enumerate(self.moles):
            if i >= self.grid_rows * self.grid_cols:
                break
            row = i // self.grid_cols
            col = i % self.grid_cols
            
            mole_x = start_x + col * (self.mole_size + self.spacing)
            mole_y = start_y + row * (self.mole_size + self.spacing)
            mole.pos = (mole_x, mole_y)
            mole.size = (self.mole_size, self.mole_size)
    
    def create_moles(self):
        # Clear existing moles
        for mole in self.moles:
            self.remove_widget(mole)
        self.moles = []
        
        # Create moles
        for i in range(self.grid_rows * self.grid_cols):
            mole = Mole(i, self.on_mole_whacked)
            mole.size = (self.mole_size, self.mole_size)
            self.moles.append(mole)
            self.add_widget(mole)
        
        self.update_layout()
    
    def on_mole_whacked(self, mole_type, mole_widget):
        if mole_type == 'bomb':
            # Create explosion at bomb location
            # Coordinates are relative to this game widget (self)
            center_x = mole_widget.x + mole_widget.width / 2
            center_y = mole_widget.y + mole_widget.height / 2
            
            explosion = Explosion(center_x, center_y, mole_widget.width, self)
            # Make explosion widget cover the entire game area (so it can draw anywhere)
            explosion.size = self.size
            explosion.pos = self.pos
            self.add_widget(explosion)
            
            # Animate explosion (60 FPS)
            explosion.animation_clock = Clock.schedule_interval(explosion.animate, 1/60.0)
            
            # Hit a bomb - lose points and time penalty
            self.score -= 25
            if self.score < 0:
                self.score = 0
            # Also lose some time as penalty
            self.time_remaining = max(0, self.time_remaining - 3)
            
            # Remove bomb immediately
            mole_widget.pop_down()
        else:
            # Hit a normal mole - show X eyes briefly, then remove
            # mole_widget already has is_hit set, just delay removal
            def remove_mole(dt):
                if mole_widget.is_up:
                    mole_widget.pop_down()
            Clock.schedule_once(remove_mole, 0.3)  # Show X eyes for 0.3 seconds
            
            # Hit a normal mole - gain points
            self.score += 10
    
    def start_game(self):
        # Calculate optimal grid size based on CURRENT window size first (before setting game_active)
        # This ensures we use the window size at game start, not at app creation
        def setup_game(dt=None):
            if self.width <= 0 or self.height <= 0:
                # If size not set yet, retry
                Clock.schedule_once(setup_game, 0.1)
                return
            
            # Temporarily disable game_active so calculate_grid_and_layout knows we're initializing
            was_active = self.game_active
            self.game_active = False
            
            # Calculate grid with current window size (this will update grid_rows/cols but not recreate moles)
            # We pass skip_mole_recreation=True by using a flag - actually, let's just recalculate grid manually
            # Reserve space for UI (top and bottom)
            usable_width = self.width - 40  # 20px margin on each side
            usable_height = self.height - 150  # Space for UI elements
            
            # Calculate optimal grid
            target_mole_size = 75
            target_spacing = 60
            max_cols = int((usable_width + target_spacing) / (target_mole_size + target_spacing))
            max_rows = int((usable_height + target_spacing) / (target_mole_size + target_spacing))
            max_cols = min(max(max_cols, 3), 8)
            max_rows = min(max(max_rows, 3), 7)
            
            available_width = usable_width - (max_cols - 1) * target_spacing
            available_height = usable_height - (max_rows - 1) * target_spacing
            self.mole_size = max(60, min(120, min(available_width / max_cols, available_height / max_rows)))
            self.grid_cols = max_cols
            self.grid_rows = max_rows
            self.spacing = target_spacing
            
            # Now set game state and create moles
            self.game_active = True
            self.score = 0
            self.time_remaining = 60
            self.start_time = 0
            self.speed_factor = 1.0
            
            # Always recreate moles when starting game to ensure correct grid
            self.create_moles()
            
            self.schedule_mole()
            self.game_timer = Clock.schedule_interval(self.update_timer, 1.0)
        
        # Clear any existing game state before setting up
        self.game_active = False
        setup_game()
    
    def stop_game(self):
        self.game_active = False
        if self.mole_schedule:
            self.mole_schedule.cancel()
            self.mole_schedule = None
        if self.game_timer:
            self.game_timer.cancel()
            self.game_timer = None
        # Pop down all moles
        for mole in self.moles:
            mole.pop_down()
    
    def schedule_mole(self):
        if not self.game_active:
            return
        
        # Calculate speed based on elapsed time (gradual speed increase)
        elapsed_time = 60 - self.time_remaining
        # Speed increases over 60 seconds from 1.0x to 3.0x
        speed_multiplier = 1.0 + (elapsed_time / 60.0) * 2.0
        self.speed_factor = speed_multiplier
        
        # Pop up a random mole
        available_moles = [m for m in self.moles if not m.is_up]
        if available_moles:
            mole = random.choice(available_moles)
            
            # Decide if it's a bomb (25% chance) or normal mole (75% chance)
            mole_type = 'bomb' if random.random() < 0.25 else 'normal'
            mole.pop_up(mole_type)
            
            # Bombs stay up slightly less time to increase difficulty
            # Apply speed multiplier (faster = less time)
            if mole_type == 'bomb':
                pop_down_time = random.uniform(0.8, 2.0) / speed_multiplier  # Shorter time for bombs
            else:
                pop_down_time = random.uniform(1.0, 3.0) / speed_multiplier  # Normal time for moles
            
            Clock.schedule_once(lambda dt, m=mole: self.pop_down_mole(m), pop_down_time)
        
        # Schedule next mole to pop up - speed increases gradually
        # Base time divided by speed multiplier (starts at 1.0, increases to 3.0)
        base_next_time = random.uniform(self.base_speed * 0.5, self.base_speed * 1.2)
        next_pop_time = max(self.min_speed, base_next_time / speed_multiplier)
        self.mole_schedule = Clock.schedule_once(lambda dt: self.schedule_mole(), next_pop_time)
    
    def pop_down_mole(self, mole):
        if mole.is_up:
            mole.pop_down()
    
    def update_timer(self, dt):
        if not self.game_active:
            return
        
        self.time_remaining -= 1
        if self.time_remaining <= 0:
            self.stop_game()
    
    def on_touch_down(self, touch):
        # Let moles handle their own touches
        for mole in self.moles:
            if mole.on_touch_down(touch):
                return True
        return super(WhackAMoleGame, self).on_touch_down(touch)


class WhackAMoleApp(FloatLayout):
    def __init__(self, **kwargs):
        super(WhackAMoleApp, self).__init__(**kwargs)
        
        # Draw grass-like background
        with self.canvas.before:
            Color(0.2, 0.6, 0.2, 1)  # Green grass color
            self.bg_rect = Rectangle(pos=(0, 0), size=(1100, 850))  # Initial size, will update
        
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Create game widget (fills entire space)
        self.game = WhackAMoleGame()
        self.add_widget(self.game)
        # Make game widget fill the parent
        self.bind(size=self.update_game_size, pos=self.update_game_size)
        self.update_game_size()
        # Calculate initial grid after size is set
        Clock.schedule_once(lambda dt: self.game.calculate_grid_and_layout(), 0.1)
        
        # Create UI labels
        self.score_label = Label(
            text='Score: 0',
            size_hint=(None, None),
            size=(200, 50),
            pos=(10, self.height - 60),
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.score_label)
        
        self.timer_label = Label(
            text='Time: 60',
            size_hint=(None, None),
            size=(200, 50),
            pos=(self.width - 210, self.height - 60),
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.timer_label)
        
        # Create start/stop button
        self.start_button = Button(
            text='Start Game',
            size_hint=(None, None),
            size=(150, 50),
            pos=(self.width / 2 - 75, 10),
            font_size=20
        )
        self.start_button.bind(on_press=self.toggle_game)
        self.add_widget(self.start_button)
        
        # Update UI periodically
        self.ui_update = Clock.schedule_interval(self.update_ui, 0.1)
        
        # Bind size to update UI positions
        self.bind(size=self.update_ui_positions)
    
    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def update_game_size(self, *args):
        self.game.pos = self.pos
        self.game.size = self.size
    
    def update_ui_positions(self, *args):
        self.score_label.pos = (10, self.height - 60)
        self.timer_label.pos = (self.width - 210, self.height - 60)
        self.start_button.pos = (self.width / 2 - 75, 10)
    
    def update_ui(self, dt):
        if self.game.game_active:
            self.score_label.text = f'Score: {self.game.score}'
            self.timer_label.text = f'Time: {self.game.time_remaining}'
            self.start_button.text = 'Stop Game'
        else:
            self.score_label.text = f'Score: {self.game.score}'
            if self.game.time_remaining <= 0:
                self.timer_label.text = 'Game Over!'
            else:
                self.timer_label.text = 'Time: 60'
            self.start_button.text = 'Start Game'
    
    def toggle_game(self, instance):
        if self.game.game_active:
            self.game.stop_game()
        else:
            self.game.start_game()


class WhackAMole(App):
    def build(self):
        return WhackAMoleApp()


if __name__ == '__main__':
    WhackAMole().run()

