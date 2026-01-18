# IMPORTANT: Suppress numba debug spam BEFORE any imports
import os
import warnings
os.environ['NUMBA_DISABLE_JIT'] = '0'
os.environ['NUMBA_DEBUG'] = '0'
os.environ['NUMBA_WARNINGS'] = '0'
os.environ['NUMBA_LOG_LEVEL'] = 'ERROR'
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
import random
import threading

# Import chart generator (uses librosa/numba)
from chart_generator import ChartGenerator, LIBROSA_AVAILABLE

# Configure for touchscreen multi-touch
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '700')

# Ensure Windows touch input is enabled
Config.set('input', 'wm_touch', 'wm_touch')
Config.set('input', 'wm_pen', 'wm_pen')


class Note(Widget):
    """A falling note that the player must hit - supports both tap and hold notes"""
    def __init__(self, lane, player, speed, duration=0, **kwargs):
        super(Note, self).__init__(**kwargs)
        self.lane = lane
        self.player = player
        self.speed = speed
        self.duration = duration  # 0 = tap note, >0 = hold note duration in seconds
        self.active = True
        self.radius = 40
        self.size = (self.radius * 2, self.radius * 2)

        # Hold note state
        self.is_hold_note = duration > 0
        self.hold_started = False  # True when player starts holding
        self.hold_completed = False  # True when hold is successfully completed
        self.hold_progress = 0.0  # 0.0 to 1.0, how much of the hold is complete
        self.tail_length = 0  # Calculated based on duration and speed

        if self.is_hold_note:
            self.tail_length = duration * speed  # Pixels of tail

        self.bind(pos=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        if not self.active:
            return
        with self.canvas:
            colors = [(1, 0.3, 0.3, 1), (0.3, 1, 0.3, 1), (0.3, 0.3, 1, 1)]
            dark_colors = [(0.7, 0.2, 0.2, 1), (0.2, 0.7, 0.2, 1), (0.2, 0.2, 0.7, 1)]

            # Draw hold tail first (behind the note head)
            if self.is_hold_note and self.tail_length > 0:
                tail_width = self.radius * 0.8
                tail_x = self.center_x - tail_width / 2

                # If hold is in progress, the tail shrinks from bottom up
                if self.hold_started:
                    # Remaining tail length decreases as hold progresses
                    # Cap at 0 so it doesn't go negative when holding too long
                    remaining_length = max(0, self.tail_length * (1.0 - self.hold_progress))

                    # Draw remaining tail from note head upward
                    if remaining_length > 0:
                        Color(*colors[self.lane])
                        Rectangle(
                            pos=(tail_x, self.y + self.radius),
                            size=(tail_width, remaining_length)
                        )

                        # Tail end cap (rounded top)
                        Ellipse(
                            pos=(tail_x, self.y + self.radius + remaining_length - tail_width / 2),
                            size=(tail_width, tail_width)
                        )
                else:
                    # Not holding yet - draw full tail
                    Color(*dark_colors[self.lane])
                    Rectangle(
                        pos=(tail_x, self.y + self.radius),
                        size=(tail_width, self.tail_length)
                    )

                    # Tail end cap (rounded top)
                    Ellipse(
                        pos=(tail_x, self.y + self.radius + self.tail_length - tail_width / 2),
                        size=(tail_width, tail_width)
                    )

            # Draw note head
            Color(*colors[self.lane])
            Ellipse(pos=self.pos, size=self.size)

            # Inner highlight
            Color(1, 1, 1, 0.3)
            inner_margin = self.radius * 0.3
            Ellipse(
                pos=(self.x + inner_margin, self.y + inner_margin),
                size=(self.width - inner_margin * 2, self.height - inner_margin * 2)
            )

            # Hold note indicator (ring around note head)
            if self.is_hold_note:
                if self.hold_started:
                    if self.hold_progress >= 1.0:
                        # Pulse green when ready to release
                        Color(0, 1, 0, 0.9)
                        Line(circle=(self.center_x, self.center_y, self.radius + 5), width=3)
                    else:
                        Color(1, 1, 1, 0.8)  # Bright when holding
                        Line(circle=(self.center_x, self.center_y, self.radius + 3), width=2)
                else:
                    Color(1, 1, 1, 0.4)  # Dimmer when not holding
                    Line(circle=(self.center_x, self.center_y, self.radius + 3), width=2)

    def move(self, dt):
        if self.active:
            # Hold notes stop moving once the hold has started
            if self.is_hold_note and self.hold_started:
                return  # Stay in place while being held
            self.y -= self.speed * dt

    def start_hold(self):
        """Called when player starts holding this note"""
        if self.is_hold_note and not self.hold_started:
            self.hold_started = True
            self.update_canvas()

    def update_hold(self, dt):
        """Update hold progress - call each frame while held"""
        if self.is_hold_note and self.hold_started and not self.hold_completed:
            # Progress based on time held vs duration
            # Allow progress to go past 1.0 so we can detect "too late" releases
            self.hold_progress += dt / self.duration
            self.update_canvas()
            # Don't auto-complete - let player release manually for timing score
            return False
        return False

    def release_hold(self):
        """Called when player releases - returns True if completed successfully"""
        if self.is_hold_note:
            return self.hold_completed
        return True

    def deactivate(self):
        self.active = False
        self.update_canvas()


class TargetButton(Widget):
    """A target button at the bottom that the player presses"""
    def __init__(self, lane, player, game, **kwargs):
        super(TargetButton, self).__init__(**kwargs)
        self.lane = lane
        self.player = player
        self.game = game
        self.pressed = False
        self.radius = 45
        self.size = (self.radius * 2, self.radius * 2)
        self.bind(pos=self.update_canvas, size=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            colors = [(1, 0.3, 0.3, 1), (0.3, 1, 0.3, 1), (0.3, 0.3, 1, 1)]
            if self.pressed:
                bright_colors = [(1, 0.6, 0.6, 1), (0.6, 1, 0.6, 1), (0.6, 0.6, 1, 1)]
                Color(*bright_colors[self.lane])
            else:
                Color(*colors[self.lane])

            Ellipse(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.8)
            Line(circle=(self.center_x, self.center_y, self.radius), width=2)

            if not self.pressed:
                colors_dark = [(0.6, 0.1, 0.1, 1), (0.1, 0.6, 0.1, 1), (0.1, 0.1, 0.6, 1)]
                Color(*colors_dark[self.lane])
                inner_margin = self.radius * 0.4
                Ellipse(
                    pos=(self.x + inner_margin, self.y + inner_margin),
                    size=(self.width - inner_margin * 2, self.height - inner_margin * 2)
                )

    def set_pressed(self, pressed):
        self.pressed = pressed
        self.update_canvas()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.set_pressed(True)
            touch.ud['button'] = self

            # Handle calibration mode
            if self.game.calibration_mode:
                self.game.calibration_tap()
            # Handle recording mode
            elif self.game.recording_mode:
                self.game.record_note(self.lane)
            elif self.game.game_active:
                self.game.check_hit(self.player, self.lane)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.ud.get('button') == self:
            self.set_pressed(False)

            # Handle recording mode - record release for hold notes
            if self.game.recording_mode:
                self.game.record_note_release(self.lane)
            # Handle hold note release in gameplay
            elif self.game.game_active:
                self.game.release_hold(self.player, self.lane)

            return True
        return False


class ScorePopup(Widget):
    """Floating score text that fades out"""
    def __init__(self, text, color, **kwargs):
        super(ScorePopup, self).__init__(**kwargs)
        self.text = text
        self.color = color
        self.alpha = 1.0
        self.rise_speed = 80
        self.label = Label(
            text=text,
            font_size=22,
            bold=True,
            color=color
        )
        self.add_widget(self.label)
        self.bind(pos=self.update_label_pos)

    def update_label_pos(self, *args):
        self.label.center = self.center

    def update(self, dt):
        self.y += self.rise_speed * dt
        self.alpha -= dt * 2
        self.label.color = (self.color[0], self.color[1], self.color[2], self.alpha)
        return self.alpha > 0


class RhythmGame(Widget):
    def __init__(self, **kwargs):
        super(RhythmGame, self).__init__(**kwargs)
        self.notes = []
        self.target_buttons = []
        self.score_popups = []
        self.scores = []
        self.combos = []
        self.num_players = 1
        self.game_active = False
        self.game_started = False
        self.note_speed = 350  # Pixels per second
        self.update_timer = None

        # Song-based note system
        self.current_song = None
        self.song_audio = None
        self.song_notes = []  # List of (time, lane) from chart
        self.next_note_index = 0
        self.song_start_time = 0
        self.elapsed_time = 0

        # Keyboard controls for testing (H=left, J=center, K=right)
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self._keyboard.bind(on_key_up=self._on_key_up)
        self._keys_pressed = set()

        # Audio sync offset (seconds) - adjust if notes are early/late
        # Positive = notes appear higher/earlier, Negative = notes appear lower/later
        self.audio_offset = 0.0  # Visual offset for note positions

        # Audio latency compensation (seconds) - compensates for audio system delay
        # Higher value = start audio earlier to compensate for playback latency
        # Measured via sync_tester.py: ~150ms on this system
        self.audio_latency = 0.15  # Default 150ms - measured audio buffer latency

        # Track if audio has started for position-based sync
        self.audio_playing = False
        self.audio_start_elapsed = 0  # elapsed_time when audio started

        # Calibration mode
        self.calibration_mode = False
        self.calibration_tick_sound = None
        self.calibration_interval = 0.75  # Time between ticks (seconds) - 80 BPM
        self.calibration_tick_times = []  # When ticks should happen
        self.calibration_tap_offsets = []  # Measured offsets from user taps
        self.calibration_next_tick = 0
        self.calibration_current_tick = 0
        self.calibration_notes_spawned = 0  # Track how many notes we've spawned
        self.calibration_total_ticks = 12  # Number of ticks for calibration
        self.calibration_timer = None
        self.calibration_start_time = 0
        self.last_tick_time = 0  # When the last tick occurred

        # Note fall time is calculated dynamically based on screen height
        # Target buttons are at y=70, notes spawn at y=height+10

        self.game_ended = False
        self.player_labels = []

        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Chart generator
        self.chart_generator = ChartGenerator() if LIBROSA_AVAILABLE else None
        self.chart_loading = False
        self.chart_ready = False

        # Recording mode
        self.recording_mode = False
        self.recorded_notes = []  # List of [time, lane] or [time, lane, duration] for holds
        self.recording_start_time = 0
        self.recording_key_down_times = {}  # Track when each lane key was pressed {lane: time}

        # Hold note tracking during gameplay
        self.active_holds = {}  # {(player, lane): note} - notes currently being held

        # Test playback mode
        self.test_playback_mode = False
        self.test_next_note_index = 0

        # Bind to size changes to update layout
        self.bind(size=self.on_size_change, pos=self.on_size_change)

    def _on_keyboard_closed(self):
        """Called when keyboard is released"""
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard.unbind(on_key_up=self._on_key_up)
            self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        """Handle keyboard press - H=left(0), J=center(1), K=right(2), Space=calibration tap"""
        key = keycode[1]  # Get the key name

        # Handle calibration mode - any key works as a tap
        if self.calibration_mode:
            if key in ['h', 'j', 'k', 'spacebar', 'space']:
                self.calibration_tap()
                # Visual feedback
                if self.target_buttons and len(self.target_buttons) > 0:
                    self.target_buttons[0][1].set_pressed(True)  # Center button
                    Clock.schedule_once(lambda dt: self.target_buttons[0][1].set_pressed(False), 0.1)
            return True

        # Map keys to lanes for player 0
        key_to_lane = {'h': 0, 'j': 1, 'k': 2}

        if key in key_to_lane and key not in self._keys_pressed:
            self._keys_pressed.add(key)
            lane = key_to_lane[key]

            # Visual feedback - press the button
            if self.target_buttons and len(self.target_buttons) > 0:
                if lane < len(self.target_buttons[0]):
                    self.target_buttons[0][lane].set_pressed(True)

            # Handle recording mode
            if self.recording_mode:
                self.record_note(lane)
            # Check for hit in normal game mode
            elif self.game_active:
                self.check_hit(0, lane)

        return True

    def _on_key_up(self, keyboard, keycode):
        """Handle keyboard release"""
        key = keycode[1]

        key_to_lane = {'h': 0, 'j': 1, 'k': 2}

        if key in key_to_lane:
            self._keys_pressed.discard(key)
            lane = key_to_lane[key]

            # Visual feedback - release the button
            if self.target_buttons and len(self.target_buttons) > 0:
                if lane < len(self.target_buttons[0]):
                    self.target_buttons[0][lane].set_pressed(False)

            # Handle recording mode - record release for hold notes
            if self.recording_mode:
                self.record_note_release(lane)
            # Handle hold note release in gameplay
            elif self.game_active:
                self.release_hold(0, lane)

        return True

    # ========== CALIBRATION MODE ==========

    def start_calibration(self):
        """Start audio/visual calibration mode"""
        print("[Calibration] Starting calibration mode...")
        self.calibration_mode = True
        self.calibration_tap_offsets = []
        self.calibration_current_tick = 0
        self.calibration_notes_spawned = 0
        self.calibration_start_time = 0
        self.last_tick_time = -1  # Use -1 so first tick at time 0 works

        # Load tick sound (use a short beep - we'll generate one)
        self._create_tick_sound()

        # Set up a simple single-player layout for calibration
        if not self.game_started:
            self.setup_game(1)

        # Clear any existing notes
        for note in self.notes:
            self.remove_widget(note)
        self.notes = []

        # Start calibration after a short delay
        self.calibration_start_time = 0
        self.calibration_timer = Clock.schedule_interval(self.update_calibration, 1/60.0)

    def _create_tick_sound(self):
        """Create a simple tick/beep sound for calibration"""
        # Try to load a tick sound, or use the existing audio system
        try:
            # Generate a simple beep using wave file
            import wave
            import struct
            import tempfile

            sample_rate = 44100
            duration = 0.05  # 50ms beep
            frequency = 880  # A5 note

            n_samples = int(sample_rate * duration)
            samples = []

            for i in range(n_samples):
                t = i / sample_rate
                # Sine wave with envelope
                envelope = 1.0 - (i / n_samples)  # Fade out
                value = int(32767 * envelope * 0.5 *
                           (1.0 if (int(t * frequency * 2) % 2) else -1.0))  # Square wave
                samples.append(struct.pack('<h', value))

            # Save to temp file
            self.tick_sound_path = os.path.join(self.script_dir, '_calibration_tick.wav')
            with wave.open(self.tick_sound_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b''.join(samples))

            self.calibration_tick_sound = SoundLoader.load(self.tick_sound_path)
            if self.calibration_tick_sound:
                self.calibration_tick_sound.volume = 1.0
                print("[Calibration] Tick sound created successfully")
            else:
                print("[Calibration] Warning: Could not load tick sound")
        except Exception as e:
            print(f"[Calibration] Error creating tick sound: {e}")
            self.calibration_tick_sound = None

    def update_calibration(self, dt):
        """Update calibration mode - play ticks and spawn visual notes"""
        if not self.calibration_mode:
            return

        self.calibration_start_time += dt

        # Spawn notes and play ticks for each beat
        fall_time = self.get_note_fall_time()

        # Check each tick we haven't spawned yet
        while self.calibration_notes_spawned < self.calibration_total_ticks:
            tick_time = self.calibration_notes_spawned * self.calibration_interval
            spawn_time = tick_time - fall_time

            if self.calibration_start_time >= spawn_time:
                # Spawn a note in the center lane
                self.spawn_note_for_chart(1)
                self.calibration_notes_spawned += 1
                print(f"[Calibration] Spawned note {self.calibration_notes_spawned}/{self.calibration_total_ticks}")
            else:
                break

        # Play ticks when it's time
        while self.calibration_current_tick < self.calibration_total_ticks:
            tick_time = self.calibration_current_tick * self.calibration_interval

            if self.calibration_start_time >= tick_time:
                self._play_tick()
                self.calibration_current_tick += 1
                print(f"[Calibration] Tick {self.calibration_current_tick}/{self.calibration_total_ticks} at {tick_time:.2f}s")
            else:
                break

        # Move notes
        for note in self.notes[:]:
            note.move(dt)
            if note.y + note.height < -50:
                self.notes.remove(note)
                self.remove_widget(note)

        # Check if calibration is complete
        if self.calibration_current_tick >= self.calibration_total_ticks and len(self.notes) == 0:
            self.finish_calibration()

    def _play_tick(self):
        """Play the tick sound"""
        if self.calibration_tick_sound:
            self.calibration_tick_sound.stop()
            self.calibration_tick_sound.play()

    def calibration_tap(self):
        """Called when user taps during calibration"""
        if not self.calibration_mode:
            return

        # Find the closest note to the target
        target_y = 70  # Target button y position

        closest_note = None
        closest_distance = float('inf')

        for note in self.notes:
            if note.active:
                distance = abs(note.center_y - target_y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_note = note

        if closest_note and closest_distance < 150:  # Within reasonable range
            # Calculate offset: positive = tapped late, negative = tapped early
            # Distance in pixels / speed = time offset
            time_offset = (closest_note.center_y - target_y) / self.note_speed

            self.calibration_tap_offsets.append(time_offset)
            print(f"[Calibration] Tap offset: {time_offset*1000:.0f}ms (note was {closest_distance:.0f}px away)")

            # Visual feedback
            closest_note.deactivate()
            self.notes.remove(closest_note)
            self.remove_widget(closest_note)

            # Show feedback
            if abs(time_offset) < 0.05:
                self.show_score_popup("PERFECT", (0, 1, 0, 1), closest_note.center_x, target_y + 50)
            elif abs(time_offset) < 0.1:
                self.show_score_popup("GOOD", (1, 1, 0, 1), closest_note.center_x, target_y + 50)
            else:
                offset_text = f"{time_offset*1000:.0f}ms"
                self.show_score_popup(offset_text, (1, 0.5, 0, 1), closest_note.center_x, target_y + 50)

    def finish_calibration(self):
        """Finish calibration and calculate audio offset"""
        print("[Calibration] Finishing calibration...")
        self.calibration_mode = False

        if self.calibration_timer:
            self.calibration_timer.cancel()
            self.calibration_timer = None

        if len(self.calibration_tap_offsets) >= 3:
            # Remove outliers (highest and lowest) if we have enough samples
            offsets = sorted(self.calibration_tap_offsets)
            if len(offsets) > 4:
                offsets = offsets[1:-1]  # Remove first and last

            # Calculate average offset
            avg_offset = sum(offsets) / len(offsets)

            # The audio_offset should compensate for the measured offset
            # If user taps late (positive offset), we need to delay audio more
            self.audio_offset = avg_offset

            print(f"[Calibration] Calculated audio offset: {self.audio_offset*1000:.0f}ms")
            print(f"[Calibration] Based on {len(self.calibration_tap_offsets)} taps")

            # Store result for display
            self.calibration_result = self.audio_offset
        else:
            print("[Calibration] Not enough taps to calibrate (need at least 3)")
            self.calibration_result = None

        # Clean up
        for note in self.notes[:]:
            self.remove_widget(note)
        self.notes = []

        # Reset game state
        self.game_started = False

    def stop_calibration(self):
        """Stop calibration mode"""
        self.calibration_mode = False
        if self.calibration_timer:
            self.calibration_timer.cancel()
            self.calibration_timer = None

        for note in self.notes[:]:
            self.remove_widget(note)
        self.notes = []

    def get_note_fall_time(self):
        """Calculate how long it takes a note to fall from spawn to target"""
        # Notes spawn at height + 10, target is at y = 70
        fall_distance = self.height + 10 - 70
        return fall_distance / self.note_speed

    def on_size_change(self, *args):
        """Update layout when window size changes"""
        if self.game_started:
            self.update_button_positions()

    def update_button_positions(self):
        """Recalculate button positions based on current size"""
        if not self.target_buttons:
            return

        button_y = 70
        button_spacing = 25
        button_radius = 45

        total_width = self.width
        section_width = total_width / self.num_players
        group_width = 3 * (button_radius * 2) + 2 * button_spacing

        for p in range(self.num_players):
            section_center = section_width * p + section_width / 2
            group_start = section_center - group_width / 2

            for i in range(3):
                btn = self.target_buttons[p][i]
                btn.center_x = group_start + button_radius + i * (button_radius * 2 + button_spacing)
                btn.center_y = button_y
                btn.update_canvas()  # Force redraw after position change

            # Update player label position
            if p < len(self.player_labels):
                self.player_labels[p].center_x = section_center
                self.player_labels[p].y = button_y + button_radius + 20

    def setup_game(self, num_players):
        """Set up the game UI after player count is selected"""
        self.num_players = num_players
        self.scores = [0] * num_players
        self.combos = [0] * num_players
        self.notes_spawned = 0
        self.game_ended = False

        # Clear existing
        for btn_list in self.target_buttons:
            for btn in btn_list:
                self.remove_widget(btn)
        self.target_buttons = []

        for label in self.player_labels:
            self.remove_widget(label)
        self.player_labels = []

        for note in self.notes:
            self.remove_widget(note)
        self.notes = []

        for popup in self.score_popups:
            self.remove_widget(popup)
        self.score_popups = []

        button_y = 70
        button_spacing = 25
        button_radius = 45

        total_width = self.width
        section_width = total_width / num_players
        group_width = 3 * (button_radius * 2) + 2 * button_spacing

        for p in range(num_players):
            section_center = section_width * p + section_width / 2
            group_start = section_center - group_width / 2

            player_buttons = []
            for i in range(3):
                btn = TargetButton(lane=i, player=p, game=self)
                btn.radius = button_radius
                btn.size = (button_radius * 2, button_radius * 2)
                btn.center_x = group_start + button_radius + i * (button_radius * 2 + button_spacing)
                btn.center_y = button_y
                btn.update_canvas()  # Force redraw with correct position
                player_buttons.append(btn)
                self.add_widget(btn)

            self.target_buttons.append(player_buttons)

            label = Label(
                text=f"P{p + 1}",
                font_size=18,
                color=(1, 1, 1, 0.8),
                size_hint=(None, None),
                size=(60, 35)
            )
            label.center_x = section_center
            label.y = button_y + button_radius + 20
            self.player_labels.append(label)
            self.add_widget(label)

        self.game_started = True

    def load_song(self, audio_filename, difficulty='medium'):
        """Load a song and generate/load its note chart"""
        audio_path = os.path.join(self.script_dir, audio_filename)
        print(f"[Game] load_song called for: {audio_path}")

        if not os.path.exists(audio_path):
            print(f"[Game] ERROR: Audio file not found: {audio_path}")
            return False

        # Stop any existing audio
        if self.song_audio:
            print("[Game] Stopping existing audio...")
            self.song_audio.stop()
            self.song_audio.unload()

        # Load audio for playback
        print("[Game] Loading audio with SoundLoader...")
        self.song_audio = SoundLoader.load(audio_path)
        if not self.song_audio:
            print(f"[Game] ERROR: Failed to load audio: {audio_path}")
            return False
        print(f"[Game] Audio loaded successfully! Length: {self.song_audio.length}s, State: {self.song_audio.state}")

        # Check if we have a cached chart (fast path)
        cache_path = os.path.splitext(audio_path)[0] + "_chart.json"
        if os.path.exists(cache_path):
            print(f"[Game] Found cached chart: {cache_path}")
            try:
                import json
                with open(cache_path, 'r') as f:
                    chart_data = json.load(f)
                self.current_song = chart_data
                self.song_notes = sorted(chart_data["notes"], key=lambda x: x[0])
                print(f"[Game] Loaded {len(self.song_notes)} notes from cache")
                self.chart_ready = True
                return True
            except Exception as e:
                print(f"[Game] Cache load failed: {e}, will regenerate")

        # Generate chart (this will be slow first time, fast after due to caching)
        print("[Game] ========================================")
        print("[Game] GENERATING CHART - First time takes 30-60 seconds!")
        print("[Game] Subsequent plays will load from cache instantly.")
        print("[Game] ========================================")

        if self.chart_generator:
            try:
                chart_data = self.chart_generator.generate_and_cache(
                    audio_path,
                    difficulty=difficulty
                )
                self.current_song = chart_data
                self.song_notes = sorted(chart_data["notes"], key=lambda x: x[0])
                print(f"[Game] Generated {len(self.song_notes)} notes")
                self.chart_ready = True
                return True
            except Exception as e:
                print(f"[Game] ERROR: Chart generation failed: {e}")
                import traceback
                traceback.print_exc()
                self.song_notes = []
                return False
        else:
            print("[Game] ERROR: No chart generator (librosa not installed)")
            self.song_notes = []
            return False

    def start_game(self, song_filename=None):
        print("[Game] start_game called")
        if not self.game_started:
            print("[Game] Game not set up yet, aborting")
            return

        # Default to Mountain King if no song specified
        if song_filename is None:
            song_filename = "kevin-macleod-hall-of-the-mountain-king.mp3"

        # Load the selected song
        print(f"[Game] Calling load_song for: {song_filename}")
        result = self.load_song(song_filename, difficulty='medium')

        if not result:
            print("[Game] Failed to load song!")
            return

        print(f"[Game] Song loaded! Notes: {len(self.song_notes)}")

        # Start the game
        self.game_active = True
        self.scores = [0] * self.num_players
        self.combos = [0] * self.num_players
        self.game_ended = False
        self.next_note_index = 0
        self.active_holds = {}  # Clear any previous holds
        self.elapsed_time = 0

        # Clear any existing notes/popups
        for note in self.notes:
            self.remove_widget(note)
        self.notes = []

        for popup in self.score_popups:
            self.remove_widget(popup)
        self.score_popups = []

        # Calculate how long notes take to fall
        fall_time = self.get_note_fall_time()

        # Get the first note time from the chart
        first_note_time = self.song_notes[0][0] if self.song_notes else 0

        # Start audio quickly - notes will be pre-positioned to arrive at correct times
        # Just add a tiny delay for audio system to be ready
        audio_delay = 0.05

        # Reset audio sync tracking
        self.audio_playing = False
        self.audio_start_elapsed = 0
        self.first_note_time = first_note_time  # Store for sync calculations

        print(f"[Game] Note fall time: {fall_time:.2f}s")
        print(f"[Game] First note at: {first_note_time:.3f}s")
        print(f"[Game] Audio latency compensation: {self.audio_latency:.3f}s")
        print(f"[Game] Calculated audio delay: {audio_delay:.3f}s")
        print(f"[Game] Visual note offset: {self.audio_offset:.3f}s")

        # Start update loop immediately (notes start spawning)
        print("[Game] Starting game loop...")
        self.update_timer = Clock.schedule_interval(self.update_game, 1/60.0)

        # Schedule audio to start with calculated delay
        def start_audio(dt):
            print(f"[Game] Starting audio playback at elapsed_time={self.elapsed_time:.3f}s")
            if self.song_audio:
                self.song_audio.volume = 1.0
                self.song_audio.play()
                self.audio_playing = True
                self.audio_start_elapsed = self.elapsed_time
                print(f"[Game] Audio playing!")
            else:
                print("[Game] ERROR: No audio loaded!")

        Clock.schedule_once(start_audio, audio_delay)
        print(f"[Game] Audio scheduled to start in {audio_delay:.2f}s")
        print("[Game] Game is now ACTIVE!")

    def stop_game(self):
        self.game_active = False
        self.audio_playing = False
        self.active_holds = {}  # Clear any active holds
        if self.song_audio:
            self.song_audio.stop()
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    # ========== RECORDING MODE ==========

    def start_recording(self, song_filename):
        """Start recording mode - play song and record button presses"""
        print("[Recording] Starting recording mode...")

        if not self.game_started:
            self.setup_game(1)

        # Load the audio file
        audio_path = os.path.join(self.script_dir, song_filename)
        if not os.path.exists(audio_path):
            print(f"[Recording] ERROR: Audio file not found: {audio_path}")
            return False

        # Stop any existing audio
        if self.song_audio:
            self.song_audio.stop()
            self.song_audio.unload()

        self.song_audio = SoundLoader.load(audio_path)
        if not self.song_audio:
            print(f"[Recording] ERROR: Failed to load audio: {audio_path}")
            return False

        print(f"[Recording] Audio loaded! Length: {self.song_audio.length}s")

        # Initialize recording state
        self.recording_mode = True
        self.recorded_notes = []
        self.recording_key_down_times = {}  # Clear any pending key presses
        self.elapsed_time = 0
        self.current_song_filename = song_filename

        # Start update loop
        self.update_timer = Clock.schedule_interval(self.update_recording, 1/60.0)

        # Start audio immediately
        self.song_audio.volume = 1.0
        self.song_audio.play()
        self.audio_playing = True

        print("[Recording] Recording started! Press buttons to record notes.")
        return True

    def record_note(self, lane):
        """Record a button press during recording mode (start of tap or hold)"""
        if not self.recording_mode:
            return

        # Record the note with current elapsed time, compensating for audio latency
        # When you hear a beat and press, there's latency between audio.get_pos() and
        # what you're actually hearing, so subtract the latency to get the "true" time
        note_time = max(0, self.elapsed_time - self.audio_latency)

        # Track when this key was pressed for potential hold note
        self.recording_key_down_times[lane] = note_time

        print(f"[Recording] Note DOWN: time={note_time:.3f}s, lane={lane}")

        # Visual feedback
        self.show_score_popup(f"{note_time:.2f}s", (0, 1, 0.5, 1),
                             self.target_buttons[0][lane].center_x, 150)

    def record_note_release(self, lane):
        """Record a button release during recording mode (end of hold)"""
        if not self.recording_mode:
            return

        release_time = max(0, self.elapsed_time - self.audio_latency)

        if lane in self.recording_key_down_times:
            press_time = self.recording_key_down_times[lane]
            duration = release_time - press_time

            # If held for more than 0.2s, treat as a hold note
            if duration > 0.2:
                self.recorded_notes.append([press_time, lane, round(duration, 3)])
                print(f"[Recording] HOLD note: time={press_time:.3f}s, lane={lane}, duration={duration:.3f}s")
                self.show_score_popup(f"HOLD {duration:.1f}s", (1, 0.5, 0, 1),
                                     self.target_buttons[0][lane].center_x, 180)
            else:
                # Short press = tap note
                self.recorded_notes.append([press_time, lane])
                print(f"[Recording] TAP note: time={press_time:.3f}s, lane={lane}")

            del self.recording_key_down_times[lane]
        else:
            print(f"[Recording] Warning: Release without matching press for lane {lane}")

    def update_recording(self, dt):
        """Update loop for recording mode"""
        if not self.recording_mode:
            return

        self.elapsed_time += dt

        # Sync to audio position if available
        if self.song_audio and self.song_audio.state == 'play':
            audio_pos = self.song_audio.get_pos()
            if audio_pos > 0:
                # Sync elapsed time to audio position
                drift = audio_pos - self.elapsed_time
                if abs(drift) > 0.1:
                    self.elapsed_time = audio_pos
                elif abs(drift) > 0.01:
                    self.elapsed_time += drift * 0.1

        # Update score popups
        for popup in self.score_popups[:]:
            if not popup.update(dt):
                self.score_popups.remove(popup)
                self.remove_widget(popup)

        # Check if song finished
        if self.song_audio and self.song_audio.state == 'stop' and self.elapsed_time > 1:
            self.stop_recording()

    def stop_recording(self):
        """Stop recording and save the chart"""
        print("[Recording] Stopping recording...")

        # Flush any pending hold notes (keys still held when recording stopped)
        release_time = max(0, self.elapsed_time - self.audio_latency)
        for lane, press_time in list(self.recording_key_down_times.items()):
            duration = release_time - press_time
            if duration > 0.2:
                self.recorded_notes.append([press_time, lane, round(duration, 3)])
                print(f"[Recording] Flushed pending HOLD: lane={lane}, duration={duration:.3f}s")
            else:
                self.recorded_notes.append([press_time, lane])
                print(f"[Recording] Flushed pending TAP: lane={lane}")
        self.recording_key_down_times = {}

        self.recording_mode = False

        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

        if self.song_audio:
            self.song_audio.stop()

        self.audio_playing = False

        if len(self.recorded_notes) > 0:
            # Clean up timing
            self.cleanup_timing()

            # Save to chart file
            self.save_recorded_chart()

            print(f"[Recording] Recording complete! {len(self.recorded_notes)} notes saved.")
        else:
            print("[Recording] No notes recorded.")

        # Clear popups
        for popup in self.score_popups[:]:
            self.remove_widget(popup)
        self.score_popups = []

    def cleanup_timing(self):
        """Clean up the timing of recorded notes by quantizing to nearest subdivision"""
        if not self.recorded_notes:
            return

        print(f"[Recording] Cleaning up timing for {len(self.recorded_notes)} notes...")

        # Sort notes by time
        self.recorded_notes.sort(key=lambda x: x[0])

        # Estimate BPM from note intervals (if enough notes)
        if len(self.recorded_notes) >= 4:
            intervals = []
            for i in range(1, min(len(self.recorded_notes), 20)):
                interval = self.recorded_notes[i][0] - self.recorded_notes[i-1][0]
                if 0.1 < interval < 2.0:  # Reasonable interval range
                    intervals.append(interval)

            if intervals:
                # Use median interval as the base beat
                intervals.sort()
                median_interval = intervals[len(intervals) // 2]

                # Quantize to 1/4 of the median interval (16th note subdivision)
                quantize_unit = median_interval / 4

                print(f"[Recording] Detected beat interval: {median_interval:.3f}s, quantize unit: {quantize_unit:.3f}s")

                # Quantize each note
                for i, note in enumerate(self.recorded_notes):
                    original_time = note[0]
                    # Round to nearest quantize unit
                    quantized_time = round(original_time / quantize_unit) * quantize_unit
                    self.recorded_notes[i][0] = round(quantized_time, 3)

                    if abs(original_time - quantized_time) > 0.01:
                        print(f"[Recording] Adjusted note {i}: {original_time:.3f}s -> {quantized_time:.3f}s")

        # Remove duplicate notes (same time and lane)
        seen = set()
        unique_notes = []
        for note in self.recorded_notes:
            key = (round(note[0], 2), note[1])
            if key not in seen:
                seen.add(key)
                unique_notes.append(note)

        self.recorded_notes = unique_notes
        print(f"[Recording] After cleanup: {len(self.recorded_notes)} notes")

    def save_recorded_chart(self):
        """Save recorded notes to the chart file"""
        if not hasattr(self, 'current_song_filename'):
            print("[Recording] ERROR: No song filename set")
            return

        import json

        # Build chart path
        base_name = os.path.splitext(self.current_song_filename)[0]
        chart_path = os.path.join(self.script_dir, f"{base_name}_chart.json")

        # Create chart data
        chart_data = {
            "name": base_name,
            "file": self.current_song_filename,
            "bpm": 112,  # Default, could be detected
            "duration": self.song_audio.length if self.song_audio else 0,
            "difficulty": "custom",
            "notes": self.recorded_notes
        }

        # Save to file
        with open(chart_path, 'w') as f:
            json.dump(chart_data, f, indent=2)

        print(f"[Recording] Chart saved to: {chart_path}")

    # ========== TEST PLAYBACK MODE ==========

    def start_test_playback(self, song_filename):
        """Start test playback - plays recorded notes as falling notes with audio"""
        print(f"[Test] Starting test playback with {len(self.recorded_notes)} notes...")

        if not self.recorded_notes:
            print("[Test] No notes to play!")
            return False

        if not self.game_started:
            self.setup_game(1)

        # Load the audio file
        audio_path = os.path.join(self.script_dir, song_filename)
        if not os.path.exists(audio_path):
            print(f"[Test] ERROR: Audio file not found: {audio_path}")
            return False

        # Stop any existing audio
        if self.song_audio:
            self.song_audio.stop()
            self.song_audio.unload()

        self.song_audio = SoundLoader.load(audio_path)
        if not self.song_audio:
            print(f"[Test] ERROR: Failed to load audio: {audio_path}")
            return False

        # Clear existing notes
        for note in self.notes[:]:
            self.remove_widget(note)
        self.notes = []

        # Initialize test playback state
        self.test_playback_mode = True
        self.test_next_note_index = 0

        # Sort recorded notes by time
        self.recorded_notes.sort(key=lambda x: x[0])

        # Start elapsed_time at 0, notes will be pre-positioned
        fall_time = self.get_note_fall_time()
        self.elapsed_time = 0
        self.audio_start_elapsed = 0  # Will be set when audio starts

        # Start update loop
        self.update_timer = Clock.schedule_interval(self.update_test_playback, 1/60.0)

        # Start audio quickly - notes will be pre-positioned
        audio_delay = 0.05

        def start_audio(dt):
            if self.song_audio and self.test_playback_mode:
                self.song_audio.volume = 1.0
                self.song_audio.play()
                self.audio_playing = True
                self.audio_start_elapsed = self.elapsed_time  # Track when audio started
                print(f"[Test] Audio started at elapsed_time={self.elapsed_time:.3f}s")

        Clock.schedule_once(start_audio, audio_delay)

        print(f"[Test] Test playback started! Fall time: {fall_time:.2f}s")
        return True

    def update_test_playback(self, dt):
        """Update loop for test playback mode"""
        if not self.test_playback_mode:
            return

        self.elapsed_time += dt

        # Sync to audio position (accounting for when audio started)
        if self.song_audio and self.song_audio.state == 'play':
            audio_pos = self.song_audio.get_pos()
            if audio_pos > 0:
                # Calculate expected elapsed_time based on audio position
                expected_elapsed = self.audio_start_elapsed + audio_pos
                drift = expected_elapsed - self.elapsed_time
                if abs(drift) > 0.1:
                    self.elapsed_time = expected_elapsed
                elif abs(drift) > 0.01:
                    self.elapsed_time += drift * 0.1

        # Spawn notes based on recorded notes
        fall_time = self.get_note_fall_time()

        while self.test_next_note_index < len(self.recorded_notes):
            note_data = self.recorded_notes[self.test_next_note_index]
            note_time = note_data[0]
            note_lane = note_data[1]
            note_duration = note_data[2] if len(note_data) > 2 else 0

            # Note HEAD should arrive at target at note_time
            spawn_time = note_time - fall_time

            if self.elapsed_time >= spawn_time:
                # Calculate how late we are spawning (for pre-positioning)
                late_by = self.elapsed_time - spawn_time
                self.spawn_note_for_chart(note_lane, duration=note_duration, late_by=late_by)
                self.test_next_note_index += 1
            else:
                break

        # Move existing notes
        for note in self.notes[:]:
            note.move(dt)

            # Update note x position
            if note.active and note.player < len(self.target_buttons):
                btn = self.target_buttons[note.player][note.lane]
                note.center_x = btn.center_x

            # Remove notes that have fallen off screen
            # For hold notes, wait until the tail has also passed
            removal_threshold = -50
            if note.is_hold_note:
                removal_threshold = -50 - note.tail_length

            if note.y + note.height < removal_threshold:
                self.notes.remove(note)
                self.remove_widget(note)

        # Update popups
        for popup in self.score_popups[:]:
            if not popup.update(dt):
                self.score_popups.remove(popup)
                self.remove_widget(popup)

        # Check if test is complete
        all_spawned = self.test_next_note_index >= len(self.recorded_notes)
        all_cleared = len(self.notes) == 0
        no_active_holds = len(self.active_holds) == 0

        if all_spawned and all_cleared and no_active_holds:
            self.stop_test_playback()
        elif self.song_audio and self.song_audio.state == 'stop' and self.elapsed_time > 1:
            self.stop_test_playback()

    def stop_test_playback(self):
        """Stop test playback"""
        print("[Test] Stopping test playback...")
        self.test_playback_mode = False

        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

        if self.song_audio:
            self.song_audio.stop()

        self.audio_playing = False

        # Clear notes
        for note in self.notes[:]:
            self.remove_widget(note)
        self.notes = []

        print("[Test] Test playback stopped.")

    def spawn_note_for_chart(self, lane, duration=0, late_by=0):
        """Spawn a note for a specific lane (from song chart)

        Args:
            lane: Which lane (0, 1, or 2)
            duration: For hold notes, how long to hold in seconds (0 = tap note)
            late_by: How many seconds late we are spawning (for pre-positioning)
        """
        for p in range(self.num_players):
            note = Note(lane=lane, player=p, speed=self.note_speed, duration=duration)
            note.radius = 40
            note.size = (note.radius * 2, note.radius * 2)

            btn = self.target_buttons[p][lane]
            note.center_x = btn.center_x

            # Base spawn position - note HEAD spawns here
            base_y = self.height + 10

            # Apply audio_offset to starting Y position
            offset_pixels = self.audio_offset * self.note_speed

            # If spawning late, pre-position the note as if it had already been falling
            late_pixels = late_by * self.note_speed

            note.y = base_y + offset_pixels - late_pixels

            self.notes.append(note)
            self.add_widget(note)

    def update_game(self, dt):
        if not self.game_active:
            return

        # Update elapsed time
        self.elapsed_time += dt

        # Once audio is playing, we can sync to actual audio position for accuracy
        # This prevents drift between our elapsed_time and actual playback
        if self.audio_playing and self.song_audio and self.song_audio.state == 'play':
            audio_pos = self.song_audio.get_pos()
            if audio_pos > 0:  # get_pos() returns valid position
                # Calculate what elapsed_time should be based on audio position
                # audio_pos is the current position in the audio file
                # We want: audio_pos = elapsed_time - audio_start_elapsed
                expected_elapsed = self.audio_start_elapsed + audio_pos
                # Gently sync to avoid jumps (blend towards expected)
                drift = expected_elapsed - self.elapsed_time
                if abs(drift) > 0.1:  # If drift is significant, snap
                    self.elapsed_time = expected_elapsed
                elif abs(drift) > 0.01:  # Small drift, blend
                    self.elapsed_time += drift * 0.1

        # Debug: print every 2 seconds
        if int(self.elapsed_time) % 2 == 0 and int(self.elapsed_time * 60) % 120 == 0:
            audio_pos = self.song_audio.get_pos() if self.song_audio else -1
            print(f"[Game] Elapsed: {self.elapsed_time:.2f}s, Audio pos: {audio_pos:.2f}s, Notes: {self.next_note_index}/{len(self.song_notes)}, Active: {len(self.notes)}")

        # Spawn notes based on song chart
        # Notes should be spawned early so they arrive at the target at the right time
        # audio_offset is applied to note Y position at spawn time, NOT to spawn timing
        # This ensures offset changes don't cause notes to bunch up
        fall_time = self.get_note_fall_time()

        while self.next_note_index < len(self.song_notes):
            note_data = self.song_notes[self.next_note_index]
            note_time = note_data[0]
            note_lane = note_data[1]
            note_duration = note_data[2] if len(note_data) > 2 else 0

            # Calculate when to spawn: note_time minus fall_time
            spawn_time = note_time - fall_time

            if self.elapsed_time >= spawn_time:
                # Calculate how late we are spawning (for pre-positioning)
                late_by = self.elapsed_time - spawn_time
                self.spawn_note_for_chart(note_lane, duration=note_duration, late_by=late_by)
                self.next_note_index += 1
            else:
                break  # No more notes to spawn yet

        # Update active hold notes
        for key, note in list(self.active_holds.items()):
            player, lane = key
            # Check if the button is still being held
            button_held = False
            if player < len(self.target_buttons) and lane < len(self.target_buttons[player]):
                button_held = self.target_buttons[player][lane].pressed

            # Also check keyboard for player 0
            if player == 0:
                key_map = {0: 'h', 1: 'j', 2: 'k'}
                if key_map.get(lane) in self._keys_pressed:
                    button_held = True

            if button_held:
                note.update_hold(dt)
                # Don't auto-release - let player release for timing score
            else:
                # Button was released - handle in release_hold
                pass

        # Move existing notes
        for note in self.notes[:]:
            note.move(dt)

            # Update note x position to follow button (in case of resize)
            if note.active and note.player < len(self.target_buttons):
                btn = self.target_buttons[note.player][note.lane]
                note.center_x = btn.center_x

            # Check for missed notes
            if note.active and note.y + note.height < 0:
                # Never remove notes that are actively being held
                key = (note.player, note.lane)
                if key in self.active_holds:
                    continue

                # Also keep hold notes that were started (safety check)
                if note.is_hold_note and note.hold_started:
                    continue

                note.deactivate()
                self.combos[note.player] = 0
                # Show MISS in the player's section, above the buttons
                section_width = self.width / self.num_players
                popup_x = section_width * note.player + section_width / 2
                self.show_score_popup("MISS", (0.5, 0.5, 0.5, 1), popup_x, 180)
                # Remove missed note immediately
                self.notes.remove(note)
                self.remove_widget(note)

        # Check if song is over (all notes spawned, processed, and no active holds)
        all_notes_spawned = self.next_note_index >= len(self.song_notes)
        all_notes_cleared = len(self.notes) == 0
        no_active_holds = len(self.active_holds) == 0

        if all_notes_spawned and all_notes_cleared and no_active_holds and not self.game_ended:
            self.end_game()

        for popup in self.score_popups[:]:
            if not popup.update(dt):
                self.score_popups.remove(popup)
                self.remove_widget(popup)

    def end_game(self):
        self.game_ended = True
        self.stop_game()

    def get_winner(self):
        if not self.game_ended:
            return None
        max_score = max(self.scores)
        winners = [i + 1 for i, s in enumerate(self.scores) if s == max_score]
        return winners, max_score

    def check_hit(self, player, lane):
        if not self.game_active:
            return
        if player >= len(self.target_buttons) or lane >= len(self.target_buttons[player]):
            return

        target_btn = self.target_buttons[player][lane]
        target_center_y = target_btn.center_y

        closest_note = None
        closest_distance = float('inf')

        for note in self.notes:
            if note.active and note.player == player and note.lane == lane:
                # For hold notes, check if the head is in range
                distance = abs(note.center_y - target_center_y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_note = note

        if closest_note:
            hit_range = target_btn.radius + closest_note.radius

            if closest_distance <= hit_range:
                # Determine hit quality
                if closest_distance < 15:
                    points = 100
                    rating = "PERFECT"
                    color = (1, 1, 0, 1)
                elif closest_distance < 30:
                    points = 75
                    rating = "GREAT"
                    color = (0, 1, 0, 1)
                elif closest_distance < 45:
                    points = 50
                    rating = "GOOD"
                    color = (0, 0.7, 1, 1)
                else:
                    points = 25
                    rating = "OK"
                    color = (0.7, 0.7, 0.7, 1)

                # Show popup in the player's section, above the buttons
                section_width = self.width / self.num_players
                popup_x = section_width * player + section_width / 2
                popup_y = 180  # A little above the buttons

                if closest_note.is_hold_note:
                    # Start holding - don't remove note yet
                    closest_note.start_hold()
                    self.active_holds[(player, lane)] = closest_note

                    # Give initial points for hitting the start
                    self.combos[player] += 1
                    combo_bonus = min(self.combos[player], 10)
                    initial_points = (points // 2) + (points * combo_bonus // 20)
                    self.scores[player] += initial_points

                    self.show_score_popup(rating, color, popup_x, popup_y)
                else:
                    # Regular tap note - remove immediately
                    closest_note.deactivate()
                    if closest_note in self.notes:
                        self.notes.remove(closest_note)
                        self.remove_widget(closest_note)

                    self.combos[player] += 1
                    combo_bonus = min(self.combos[player], 10)
                    total_points = points + (points * combo_bonus // 10)
                    self.scores[player] += total_points

                    self.show_score_popup(rating, color, popup_x, popup_y)

    def release_hold(self, player, lane):
        """Handle release of a hold note with timing-based scoring"""
        key = (player, lane)
        if key not in self.active_holds:
            return

        note = self.active_holds[key]
        del self.active_holds[key]

        # Calculate how close to perfect timing (1.0 = exactly on time)
        # < 1.0 means early, > 1.0 means late
        timing_error = abs(note.hold_progress - 1.0)

        # Determine rating based on timing error
        if timing_error < 0.05:  # Within 5% of perfect
            points = 100
            rating = "PERFECT"
            color = (1, 1, 0, 1)
            self.combos[player] += 1
        elif timing_error < 0.10:  # Within 10%
            points = 75
            rating = "GREAT"
            color = (0, 1, 0, 1)
            self.combos[player] += 1
        elif timing_error < 0.20:  # Within 20%
            points = 50
            rating = "GOOD"
            color = (0, 0.7, 1, 1)
            self.combos[player] += 1
        elif timing_error < 0.35:  # Within 35%
            points = 25
            rating = "OK"
            color = (0.7, 0.7, 0.7, 1)
        else:
            # Too early or too late - counts as MISS
            points = 0
            rating = "MISS"
            color = (0.5, 0.5, 0.5, 1)
            self.combos[player] = 0  # Break combo

        combo_bonus = min(self.combos[player], 10)
        total_points = points + (points * combo_bonus // 10)
        self.scores[player] += total_points

        # Show popup in the player's section, above the buttons
        section_width = self.width / self.num_players
        popup_x = section_width * player + section_width / 2
        popup_y = 180  # A little above the buttons

        self.show_score_popup(rating, color, popup_x, popup_y)

        # Remove the note
        note.deactivate()
        if note in self.notes:
            self.notes.remove(note)
            self.remove_widget(note)

    def show_score_popup(self, text, color, x, y):
        popup = ScorePopup(text=text, color=color)
        popup.center_x = x
        popup.center_y = y
        popup.size = (80, 40)
        self.score_popups.append(popup)
        self.add_widget(popup)


class RhythmGameApp(FloatLayout):
    def __init__(self, **kwargs):
        super(RhythmGameApp, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.bg_rect = Rectangle(pos=(0, 0), size=(1000, 700))
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.game = RhythmGame()
        self.game.size_hint = (1, 1)  # Make game fill parent
        self.add_widget(self.game)

        self.player_select_label = Label(
            text='Select Number of Players',
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(300, 40)
        )
        self.add_widget(self.player_select_label)

        self.player_buttons = []
        for i in range(1, 5):
            btn = Button(
                text=f'{i} Player{"s" if i > 1 else ""}',
                size_hint=(None, None),
                size=(100, 40),
                font_size=16
            )
            btn.bind(on_press=lambda x, n=i: self.select_players(n))
            self.player_buttons.append(btn)
            self.add_widget(btn)

        # Calibration button
        self.calibrate_button = Button(
            text='Calibrate',
            size_hint=(None, None),
            size=(120, 40),
            font_size=16
        )
        self.calibrate_button.bind(on_release=self.start_calibration)
        self.add_widget(self.calibrate_button)
        print("[Debug] Calibrate button created and bound")

        # Calibration status label
        self.calibration_label = Label(
            text='',
            font_size=16,
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(None, None),
            size=(300, 30)
        )
        self.add_widget(self.calibration_label)

        # Offset slider (on the right side) - adjusts note visual position
        self.offset_label = Label(
            text='Note\nOffset\n0ms',
            font_size=12,
            color=(1, 1, 1, 0.8),
            size_hint=(None, None),
            size=(60, 50),
            halign='center'
        )
        self.add_widget(self.offset_label)

        self.offset_slider = Slider(
            min=-2000,
            max=2000,
            value=0,
            orientation='vertical',
            size_hint=(None, None),
            size=(50, 200)
        )
        self.offset_slider.bind(value=self.on_offset_change)
        self.add_widget(self.offset_slider)

        # Audio latency slider - compensates for audio system delay
        self.latency_label = Label(
            text='Audio\nLatency\n150ms',
            font_size=12,
            color=(0.8, 1, 0.8, 0.8),
            size_hint=(None, None),
            size=(60, 50),
            halign='center'
        )
        self.add_widget(self.latency_label)

        self.latency_slider = Slider(
            min=0,
            max=500,
            value=150,  # Default 150ms
            orientation='vertical',
            size_hint=(None, None),
            size=(50, 200)
        )
        self.latency_slider.bind(value=self.on_latency_change)
        self.add_widget(self.latency_slider)

        # End game button (top right, visible during gameplay)
        self.end_game_button = Button(
            text='End Game',
            size_hint=(None, None),
            size=(100, 40),
            font_size=14,
            opacity=0,
            disabled=True,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.end_game_button.bind(on_press=self.end_game_early)
        self.add_widget(self.end_game_button)

        # Song selection UI
        self.song_select_label = Label(
            text='Select Song',
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(300, 40),
            opacity=0
        )
        self.add_widget(self.song_select_label)

        # Available songs: (filename, display_name)
        self.available_songs = [
            ("kevin-macleod-hall-of-the-mountain-king.mp3", "Hall of the Mountain King"),
            ("click.mp3", "Click (120 BPM)"),
            ("click_75bpm_4-4time_61beats_ZJM6si (online-audio-converter.com).mp3", "Click (75 BPM)"),
        ]
        self.selected_song = None

        self.song_buttons = []
        for filename, name in self.available_songs:
            btn = Button(
                text=name,
                size_hint=(None, None),
                size=(250, 50),
                font_size=16,
                opacity=0,
                disabled=True
            )
            btn.bind(on_press=lambda x, f=filename: self.select_song(f))
            self.song_buttons.append(btn)
            self.add_widget(btn)

        # Back button for song selection
        self.song_back_button = Button(
            text='Back',
            size_hint=(None, None),
            size=(100, 40),
            font_size=14,
            opacity=0,
            disabled=True
        )
        self.song_back_button.bind(on_press=self.back_to_player_select)
        self.add_widget(self.song_back_button)

        # Mode selection UI (for Hall of the Mountain King)
        self.mode_select_label = Label(
            text='Select Mode',
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(300, 40),
            opacity=0
        )
        self.add_widget(self.mode_select_label)

        self.record_mode_button = Button(
            text='Record Notes',
            size_hint=(None, None),
            size=(200, 50),
            font_size=16,
            opacity=0,
            disabled=True
        )
        self.record_mode_button.bind(on_press=self.start_record_mode)
        self.add_widget(self.record_mode_button)

        self.play_mode_button = Button(
            text='Play Game',
            size_hint=(None, None),
            size=(200, 50),
            font_size=16,
            opacity=0,
            disabled=True
        )
        self.play_mode_button.bind(on_press=self.start_play_mode)
        self.add_widget(self.play_mode_button)

        # Recording status label
        self.recording_label = Label(
            text='',
            font_size=18,
            color=(1, 0.5, 0.5, 1),
            size_hint=(None, None),
            size=(400, 40),
            opacity=0
        )
        self.add_widget(self.recording_label)

        # Recording control buttons
        self.recording_stop_button = Button(
            text='Stop & Save',
            size_hint=(None, None),
            size=(120, 45),
            font_size=14,
            opacity=0,
            disabled=True
        )
        self.recording_stop_button.bind(on_press=self.stop_recording_early)
        self.add_widget(self.recording_stop_button)

        self.recording_restart_button = Button(
            text='Restart',
            size_hint=(None, None),
            size=(120, 45),
            font_size=14,
            opacity=0,
            disabled=True
        )
        self.recording_restart_button.bind(on_press=self.restart_recording)
        self.add_widget(self.recording_restart_button)

        self.recording_test_button = Button(
            text='Test Playback',
            size_hint=(None, None),
            size=(120, 45),
            font_size=14,
            opacity=0,
            disabled=True
        )
        self.recording_test_button.bind(on_press=self.test_recorded_notes)
        self.add_widget(self.recording_test_button)

        self.recording_back_button = Button(
            text='Back',
            size_hint=(None, None),
            size=(120, 45),
            font_size=14,
            opacity=0,
            disabled=True
        )
        self.recording_back_button.bind(on_press=self.back_from_recording)
        self.add_widget(self.recording_back_button)

        self.score_labels = []

        self.start_button = Button(
            text='Start',
            size_hint=(None, None),
            size=(150, 50),
            font_size=18,
            opacity=0,
            disabled=True
        )
        self.start_button.bind(on_press=self.toggle_game)
        self.add_widget(self.start_button)

        self.winner_label = Label(
            text='',
            font_size=28,
            bold=True,
            color=(1, 1, 0, 1),
            size_hint=(None, None),
            size=(400, 50),
            opacity=0
        )
        self.add_widget(self.winner_label)

        # Leaderboard box background
        self.leaderboard_box = Widget(size_hint=(None, None), size=(350, 300))
        self.add_widget(self.leaderboard_box)
        self.leaderboard_box_visible = False

        # Leaderboard elements
        self.leaderboard_title = Label(
            text='Leaderboard',
            font_size=32,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(300, 50),
            opacity=0
        )
        self.add_widget(self.leaderboard_title)

        self.leaderboard_labels = []

        self.back_to_menu_button = Button(
            text='Back to Menu',
            size_hint=(None, None),
            size=(150, 50),
            font_size=18,
            opacity=0,
            disabled=True
        )
        self.back_to_menu_button.bind(on_press=self.go_to_menu)
        self.add_widget(self.back_to_menu_button)

        self.ui_update = Clock.schedule_interval(self.update_ui, 0.1)
        self.bind(size=self.update_ui_positions, pos=self.update_ui_positions)
        Clock.schedule_once(lambda dt: self.update_ui_positions(), 0.1)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def on_touch_down(self, touch):
        # Check if touch hits calibrate button - manually trigger since button events aren't working
        if self.calibrate_button.opacity > 0 and not self.calibrate_button.disabled:
            if self.calibrate_button.collide_point(*touch.pos):
                print(f"[Debug] Touch on calibrate button! Triggering calibration...")
                self.start_calibration(self.calibrate_button)
                return True

        # Check if touch hits song back button
        if self.song_back_button.opacity > 0 and not self.song_back_button.disabled:
            if self.song_back_button.collide_point(*touch.pos):
                print(f"[Debug] Touch on back button!")
                self.back_to_player_select(self.song_back_button)
                return True

        # Check if touch hits player selection buttons
        for i, btn in enumerate(self.player_buttons):
            if btn.opacity > 0 and not btn.disabled:
                if btn.collide_point(*touch.pos):
                    print(f"[Debug] Touch on player button {i+1}!")
                    self.select_players(i + 1)
                    return True

        # Check if touch hits song selection buttons
        for i, btn in enumerate(self.song_buttons):
            if btn.opacity > 0 and not btn.disabled:
                if btn.collide_point(*touch.pos):
                    print(f"[Debug] Touch on song button!")
                    self.select_song(self.available_songs[i][0])
                    return True

        return super().on_touch_down(touch)

    def on_offset_change(self, instance, value):
        """Called when the offset slider value changes - adjusts note visual position"""
        # Convert from ms to seconds
        offset_ms = int(value)
        old_offset = self.game.audio_offset
        new_offset = value / 1000.0

        # Calculate the position change needed
        # offset in seconds * note_speed = pixels to move
        offset_delta = new_offset - old_offset
        pixel_delta = offset_delta * self.game.note_speed

        # Move all existing notes by the delta (positive offset = notes move up)
        for note in self.game.notes:
            note.y += pixel_delta

        self.game.audio_offset = new_offset
        self.offset_label.text = f'Note\nOffset\n{offset_ms}ms'

    def on_latency_change(self, instance, value):
        """Called when the audio latency slider changes - adjusts audio start timing"""
        latency_ms = int(value)
        self.game.audio_latency = value / 1000.0
        self.latency_label.text = f'Audio\nLatency\n{latency_ms}ms'

    def update_ui_positions(self, *args):
        self.player_select_label.center_x = self.width / 2
        self.player_select_label.center_y = self.height / 2 + 40

        total_btn_width = len(self.player_buttons) * 100 + (len(self.player_buttons) - 1) * 10
        start_x = (self.width - total_btn_width) / 2
        for i, btn in enumerate(self.player_buttons):
            btn.x = start_x + i * 110
            btn.center_y = self.height / 2 - 20

        # Calibration button position (below player buttons)
        self.calibrate_button.pos = (self.width / 2 - 60, self.height / 2 - 100)
        self.calibration_label.center_x = self.width / 2
        self.calibration_label.center_y = self.height / 2 - 140

        # Sliders position (right side of screen)
        # Note Offset slider (rightmost)
        self.offset_slider.pos = (self.width - 60, self.height / 2 - 100)
        self.offset_label.center_x = self.width - 35
        self.offset_label.y = self.height / 2 + 110

        # Audio Latency slider (second from right)
        self.latency_slider.pos = (self.width - 130, self.height / 2 - 100)
        self.latency_label.center_x = self.width - 105
        self.latency_label.y = self.height / 2 + 110

        # End game button (top right corner)
        self.end_game_button.x = self.width - 110
        self.end_game_button.y = self.height - 50

        # Song selection positioning - spread buttons to avoid overlap with start_button
        self.song_select_label.center_x = self.width / 2
        self.song_select_label.center_y = self.height / 2 + 120

        for i, btn in enumerate(self.song_buttons):
            btn.center_x = self.width / 2
            btn.center_y = self.height / 2 + 60 - i * 55

        # Song selection back button
        self.song_back_button.center_x = self.width / 2
        self.song_back_button.center_y = self.height / 2 - 120

        # Mode selection positioning
        self.mode_select_label.center_x = self.width / 2
        self.mode_select_label.center_y = self.height / 2 + 80

        self.record_mode_button.center_x = self.width / 2
        self.record_mode_button.center_y = self.height / 2 + 20

        self.play_mode_button.center_x = self.width / 2
        self.play_mode_button.center_y = self.height / 2 - 40

        self.recording_label.center_x = self.width / 2
        self.recording_label.center_y = self.height - 50

        # Recording control buttons - positioned at bottom
        button_y = 140
        total_width = 4 * 120 + 3 * 10  # 4 buttons, 10px gaps
        start_x = (self.width - total_width) / 2

        self.recording_stop_button.x = start_x
        self.recording_stop_button.center_y = button_y

        self.recording_restart_button.x = start_x + 130
        self.recording_restart_button.center_y = button_y

        self.recording_test_button.x = start_x + 260
        self.recording_test_button.center_y = button_y

        self.recording_back_button.x = start_x + 390
        self.recording_back_button.center_y = button_y

        self.start_button.center_x = self.width / 2
        self.start_button.center_y = self.height / 2 - 130

        self.winner_label.center_x = self.width / 2
        self.winner_label.center_y = self.height / 2 + 200

        if self.score_labels and self.game.game_started:
            section_width = self.width / self.game.num_players
            for i, label in enumerate(self.score_labels):
                label.center_x = section_width * i + section_width / 2
                label.y = self.height - 40

    def select_players(self, num_players):
        self.player_select_label.opacity = 0
        for btn in self.player_buttons:
            btn.opacity = 0
            btn.disabled = True

        # Hide calibration button
        self.calibrate_button.opacity = 0
        self.calibrate_button.disabled = True

        self.game.setup_game(num_players)

        for label in self.score_labels:
            self.remove_widget(label)
        self.score_labels = []

        for i in range(num_players):
            label = Label(
                text=f'P{i + 1}: 0',
                font_size=20,
                bold=True,
                color=(1, 1, 1, 1),
                size_hint=(None, None),
                size=(120, 35)
            )
            self.score_labels.append(label)
            self.add_widget(label)

        # Show song selection instead of start button
        self.song_select_label.opacity = 1
        for btn in self.song_buttons:
            btn.opacity = 1
            btn.disabled = False
        self.song_back_button.opacity = 1
        self.song_back_button.disabled = False

        self.update_ui_positions()

    def back_to_player_select(self, instance):
        """Go back from song selection to player selection"""
        # Hide song selection
        self.song_select_label.opacity = 0
        for btn in self.song_buttons:
            btn.opacity = 0
            btn.disabled = True
        self.song_back_button.opacity = 0
        self.song_back_button.disabled = True

        # Remove score labels
        for label in self.score_labels:
            self.remove_widget(label)
        self.score_labels = []

        # Clean up game state
        for btn_list in self.game.target_buttons:
            for btn in btn_list:
                self.game.remove_widget(btn)
        self.game.target_buttons = []

        for label in self.game.player_labels:
            self.game.remove_widget(label)
        self.game.player_labels = []

        self.game.game_started = False

        # Show player selection
        self.player_select_label.opacity = 1
        for btn in self.player_buttons:
            btn.opacity = 1
            btn.disabled = False
        self.calibrate_button.opacity = 1
        self.calibrate_button.disabled = False

        self.update_ui_positions()

    def select_song(self, song_filename):
        """Called when a song is selected"""
        print(f"[UI] Song selected: {song_filename}")
        self.selected_song = song_filename

        # Hide song selection
        self.song_select_label.opacity = 0
        for btn in self.song_buttons:
            btn.opacity = 0
            btn.disabled = True
        self.song_back_button.opacity = 0
        self.song_back_button.disabled = True

        # Check if this is Hall of the Mountain King - show mode selection
        if "mountain-king" in song_filename.lower():
            # Show mode selection
            self.mode_select_label.opacity = 1
            self.record_mode_button.opacity = 1
            self.record_mode_button.disabled = False
            self.play_mode_button.opacity = 1
            self.play_mode_button.disabled = False
        else:
            # Show start button for other songs
            self.start_button.opacity = 1
            self.start_button.disabled = False

        self.update_ui_positions()

    def hide_mode_selection(self):
        """Hide mode selection UI"""
        self.mode_select_label.opacity = 0
        self.record_mode_button.opacity = 0
        self.record_mode_button.disabled = True
        self.play_mode_button.opacity = 0
        self.play_mode_button.disabled = True
        self.recording_label.opacity = 0

    def show_recording_controls(self):
        """Show recording control buttons"""
        self.recording_stop_button.opacity = 1
        self.recording_stop_button.disabled = False
        self.recording_restart_button.opacity = 1
        self.recording_restart_button.disabled = False
        self.recording_test_button.opacity = 1
        self.recording_test_button.disabled = False
        self.recording_back_button.opacity = 1
        self.recording_back_button.disabled = False

    def hide_recording_controls(self):
        """Hide recording control buttons"""
        self.recording_stop_button.opacity = 0
        self.recording_stop_button.disabled = True
        self.recording_restart_button.opacity = 0
        self.recording_restart_button.disabled = True
        self.recording_test_button.opacity = 0
        self.recording_test_button.disabled = True
        self.recording_back_button.opacity = 0
        self.recording_back_button.disabled = True

    def start_record_mode(self, instance):
        """Start recording mode for Hall of the Mountain King"""
        print("[UI] Record mode selected!")

        # Hide mode selection
        self.hide_mode_selection()

        # Show recording status and controls
        self.recording_label.text = "RECORDING - Press H/J/K or tap buttons"
        self.recording_label.opacity = 1
        self.show_recording_controls()

        # Start recording
        if self.game.start_recording(self.selected_song):
            # Schedule check for recording completion
            Clock.schedule_interval(self.check_recording_complete, 0.1)
        else:
            self.recording_label.text = "Failed to start recording"
            self.hide_recording_controls()
            Clock.schedule_once(lambda dt: self.return_to_song_selection(), 2.0)

    def start_play_mode(self, instance):
        """Start play mode for Hall of the Mountain King"""
        print("[UI] Play mode selected!")

        # Hide mode selection
        self.hide_mode_selection()

        # Ensure game is set up (may have been reset after recording)
        if not self.game.game_started:
            self.game.setup_game(self.game.num_players if self.game.num_players > 0 else 1)

        # Start the game normally
        self.winner_label.opacity = 0
        self.start_button.opacity = 0
        self.start_button.disabled = True
        self.hide_leaderboard()

        # Show end game button
        self.end_game_button.opacity = 1
        self.end_game_button.disabled = False

        self.game.start_game(self.selected_song)

    def check_recording_complete(self, dt):
        """Check if recording is finished"""
        if not self.game.recording_mode and not self.game.test_playback_mode:
            Clock.unschedule(self.check_recording_complete)

            # Show completion message
            num_notes = len(self.game.recorded_notes) if hasattr(self.game, 'recorded_notes') else 0
            self.recording_label.text = f"Recording stopped. {num_notes} notes recorded."

            # Clean up game UI
            for popup in self.game.score_popups[:]:
                self.game.remove_widget(popup)
            self.game.score_popups = []

            # Keep controls visible so user can test or restart

    def stop_recording_early(self, instance):
        """Stop recording and save"""
        print("[UI] Stop & Save pressed")
        if self.game.recording_mode:
            self.game.stop_recording()
        num_notes = len(self.game.recorded_notes) if hasattr(self.game, 'recorded_notes') else 0
        self.recording_label.text = f"Saved! {num_notes} notes recorded."

    def restart_recording(self, instance):
        """Restart recording from beginning"""
        print("[UI] Restart pressed")
        # Stop current recording/test without saving
        if self.game.recording_mode:
            self.game.recording_mode = False
            if self.game.update_timer:
                self.game.update_timer.cancel()
                self.game.update_timer = None
            if self.game.song_audio:
                self.game.song_audio.stop()
        if self.game.test_playback_mode:
            self.game.stop_test_playback()

        # Clear notes
        self.game.recorded_notes = []
        for note in self.game.notes[:]:
            self.game.remove_widget(note)
        self.game.notes = []

        # Start fresh recording
        self.recording_label.text = "RECORDING - Press H/J/K or tap buttons"
        if self.game.start_recording(self.selected_song):
            Clock.schedule_interval(self.check_recording_complete, 0.1)

    def test_recorded_notes(self, instance):
        """Test playback of recorded notes"""
        print("[UI] Test Playback pressed")
        num_notes = len(self.game.recorded_notes) if hasattr(self.game, 'recorded_notes') else 0
        if num_notes == 0:
            self.recording_label.text = "No notes to test! Record some first."
            return

        # Stop any current recording
        if self.game.recording_mode:
            self.game.recording_mode = False
            if self.game.update_timer:
                self.game.update_timer.cancel()
                self.game.update_timer = None
            if self.game.song_audio:
                self.game.song_audio.stop()

        self.recording_label.text = f"TESTING - {num_notes} notes"

        # Start test playback
        if self.game.start_test_playback(self.selected_song):
            Clock.schedule_interval(self.check_test_complete, 0.1)

    def check_test_complete(self, dt):
        """Check if test playback is finished"""
        if not self.game.test_playback_mode:
            Clock.unschedule(self.check_test_complete)
            num_notes = len(self.game.recorded_notes) if hasattr(self.game, 'recorded_notes') else 0
            self.recording_label.text = f"Test complete. {num_notes} notes."

    def back_from_recording(self, instance):
        """Go back from recording mode"""
        print("[UI] Back pressed")
        # Stop everything
        if self.game.recording_mode:
            self.game.recording_mode = False
            if self.game.update_timer:
                self.game.update_timer.cancel()
                self.game.update_timer = None
            if self.game.song_audio:
                self.game.song_audio.stop()
        if self.game.test_playback_mode:
            self.game.stop_test_playback()

        # Clean up notes
        for note in self.game.notes[:]:
            self.game.remove_widget(note)
        self.game.notes = []

        # Hide controls
        self.hide_recording_controls()
        self.recording_label.opacity = 0

        # Return to song selection
        self.return_to_song_selection()

    def return_to_song_selection(self):
        """Return to song selection screen"""
        self.recording_label.opacity = 0

        # Clean up game state
        for btn_list in self.game.target_buttons:
            for btn in btn_list:
                self.game.remove_widget(btn)
        self.game.target_buttons = []

        for label in self.game.player_labels:
            self.game.remove_widget(label)
        self.game.player_labels = []

        self.game.game_started = False

        # Show song selection
        self.song_select_label.opacity = 1
        for btn in self.song_buttons:
            btn.opacity = 1
            btn.disabled = False
        self.song_back_button.opacity = 1
        self.song_back_button.disabled = False

        self.update_ui_positions()

    def start_calibration(self, instance):
        """Start calibration mode"""
        print("[UI] Calibration button pressed!")

        # Hide main menu elements
        self.player_select_label.opacity = 0
        for btn in self.player_buttons:
            btn.opacity = 0
            btn.disabled = True
        self.calibrate_button.opacity = 0
        self.calibrate_button.disabled = True
        self.calibration_label.text = "Tap when notes reach the target\nPress H, J, K, or Space"
        self.calibration_label.opacity = 1
        self.calibration_label.size = (400, 60)

        print("[UI] Starting game calibration...")

        # Start calibration in game
        self.game.start_calibration()

        # Schedule check for calibration completion
        Clock.schedule_interval(self.check_calibration_complete, 0.1)
        print("[UI] Calibration started!")

    def check_calibration_complete(self, dt):
        """Check if calibration is finished and update UI"""
        if not self.game.calibration_mode:
            # Calibration finished
            Clock.unschedule(self.check_calibration_complete)

            if hasattr(self.game, 'calibration_result') and self.game.calibration_result is not None:
                offset_ms = self.game.audio_offset * 1000
                self.calibration_label.text = f"Calibration complete!\nAudio offset: {offset_ms:.0f}ms"
                # Update slider to match
                self.offset_slider.value = offset_ms
                self.offset_label.text = f'Offset: {int(offset_ms)}ms'
            else:
                self.calibration_label.text = "Calibration failed\n(Need at least 3 taps)"

            # Show main menu again after delay
            Clock.schedule_once(self.return_to_menu_after_calibration, 2.0)

    def return_to_menu_after_calibration(self, dt):
        """Return to main menu after calibration"""
        self.player_select_label.opacity = 1
        for btn in self.player_buttons:
            btn.opacity = 1
            btn.disabled = False
        self.calibrate_button.opacity = 1
        self.calibrate_button.disabled = False

        # Update calibration label to show current offset
        if self.game.audio_offset != 0:
            offset_ms = self.game.audio_offset * 1000
            self.calibration_label.text = f"Offset: {offset_ms:.0f}ms"
        else:
            self.calibration_label.text = ""

        # Clean up game state
        for btn_list in self.game.target_buttons:
            for btn in btn_list:
                self.game.remove_widget(btn)
        self.game.target_buttons = []

        for label in self.game.player_labels:
            self.game.remove_widget(label)
        self.game.player_labels = []

        self.game.game_started = False

    def update_ui(self, dt):
        if not self.game.game_started:
            return

        for i, label in enumerate(self.score_labels):
            if i < len(self.game.scores):
                label.text = f'P{i + 1}: {self.game.scores[i]}'

        if self.game.game_ended:
            # Hide end game button
            self.end_game_button.opacity = 0
            self.end_game_button.disabled = True

            self.start_button.text = 'Play Again'
            self.start_button.opacity = 1
            self.start_button.disabled = False
            result = self.game.get_winner()
            if result:
                winners, score = result
                if len(winners) > 1:
                    self.winner_label.text = f"TIE! Players {', '.join(map(str, winners))} - {score} pts"
                else:
                    self.winner_label.text = f"Player {winners[0]} Wins! - {score} pts"
                self.winner_label.opacity = 1

            # Show leaderboard
            self.show_leaderboard()
        else:
            self.winner_label.opacity = 0
            self.hide_leaderboard()

    def toggle_game(self, instance):
        if self.game.game_active:
            self.game.stop_game()
            self.end_game_button.opacity = 0
            self.end_game_button.disabled = True
        else:
            self.winner_label.opacity = 0
            self.start_button.opacity = 0
            self.start_button.disabled = True
            self.hide_leaderboard()

            # Show end game button
            self.end_game_button.opacity = 1
            self.end_game_button.disabled = False

            self.game.start_game(self.selected_song)

    def end_game_early(self, instance):
        """End the game early when the End Game button is pressed"""
        if self.game.game_active:
            print("[UI] End Game button pressed - ending game early")
            self.game.end_game()

            # Hide the end game button
            self.end_game_button.opacity = 0
            self.end_game_button.disabled = True

    def show_leaderboard(self):
        # Only create labels once per game end
        if self.leaderboard_labels:
            return

        self.leaderboard_title.opacity = 1

        # Sort players by score (descending)
        player_scores = [(i + 1, self.game.scores[i]) for i in range(self.game.num_players)]
        player_scores.sort(key=lambda x: x[1], reverse=True)

        num_players = self.game.num_players
        label_height = 35
        title_height = 50
        button_height = 50
        padding = 20
        button_spacing = 10

        # Calculate box dimensions
        box_width = 350
        content_height = title_height + (num_players * label_height) + button_height + padding * 3
        box_height = content_height

        # Position box in center
        box_x = (self.width - box_width) / 2
        box_y = (self.height - box_height) / 2

        # Draw the box
        self.leaderboard_box.canvas.clear()
        with self.leaderboard_box.canvas:
            Color(0.2, 0.2, 0.25, 0.95)
            Rectangle(pos=(box_x, box_y), size=(box_width, box_height))
            Color(0.4, 0.4, 0.5, 1)
            Line(rectangle=(box_x, box_y, box_width, box_height), width=2)
        self.leaderboard_box_visible = True

        # Position title at top of box
        self.leaderboard_title.center_x = self.width / 2
        self.leaderboard_title.center_y = box_y + box_height - padding - title_height / 2

        # Create leaderboard labels
        label_start_y = box_y + box_height - padding - title_height - padding

        for rank, (player, score) in enumerate(player_scores):
            medal = ""
            if rank == 0:
                color = (1, 0.84, 0, 1)  # Gold
                medal = "1st "
            elif rank == 1:
                color = (0.75, 0.75, 0.75, 1)  # Silver
                medal = "2nd "
            elif rank == 2:
                color = (0.8, 0.5, 0.2, 1)  # Bronze
                medal = "3rd "
            else:
                color = (1, 1, 1, 1)
                medal = f"{rank + 1}th "

            label = Label(
                text=f'{medal}P{player}: {score} pts',
                font_size=22,
                bold=True,
                color=color,
                size_hint=(None, None),
                size=(250, label_height)
            )
            label.center_x = self.width / 2
            label.center_y = label_start_y - (rank * label_height) - label_height / 2
            self.leaderboard_labels.append(label)
            self.add_widget(label)

        # Position buttons side by side at bottom of box
        buttons_y = box_y + padding + button_height / 2
        total_buttons_width = 150 + button_spacing + 150  # Two 150-wide buttons
        buttons_start_x = (self.width - total_buttons_width) / 2

        self.start_button.center_x = buttons_start_x + 75  # First button center
        self.start_button.center_y = buttons_y

        self.back_to_menu_button.center_x = buttons_start_x + 150 + button_spacing + 75  # Second button center
        self.back_to_menu_button.center_y = buttons_y

        # Show buttons
        self.back_to_menu_button.opacity = 1
        self.back_to_menu_button.disabled = False

    def hide_leaderboard(self):
        self.leaderboard_title.opacity = 0
        for label in self.leaderboard_labels:
            self.remove_widget(label)
        self.leaderboard_labels = []
        self.back_to_menu_button.opacity = 0
        self.back_to_menu_button.disabled = True
        # Clear the box
        self.leaderboard_box.canvas.clear()
        self.leaderboard_box_visible = False

    def go_to_menu(self, instance):
        # Stop any running game
        self.game.stop_game()

        # Stop recording if active
        if self.game.recording_mode:
            self.game.stop_recording()

        # Stop test playback if active
        if self.game.test_playback_mode:
            self.game.stop_test_playback()

        # Hide leaderboard
        self.hide_leaderboard()
        self.winner_label.opacity = 0

        # Hide start button
        self.start_button.opacity = 0
        self.start_button.disabled = True
        self.start_button.text = 'Start'

        # Hide end game button
        self.end_game_button.opacity = 0
        self.end_game_button.disabled = True

        # Hide mode selection and recording controls
        self.hide_mode_selection()
        self.hide_recording_controls()

        # Hide song selection
        self.song_select_label.opacity = 0
        for btn in self.song_buttons:
            btn.opacity = 0
            btn.disabled = True
        self.song_back_button.opacity = 0
        self.song_back_button.disabled = True
        self.selected_song = None

        # Clear game state
        self.game.game_started = False
        self.game.game_ended = False

        # Remove target buttons and player labels from game
        for btn_list in self.game.target_buttons:
            for btn in btn_list:
                self.game.remove_widget(btn)
        self.game.target_buttons = []

        for label in self.game.player_labels:
            self.game.remove_widget(label)
        self.game.player_labels = []

        for note in self.game.notes:
            self.game.remove_widget(note)
        self.game.notes = []

        # Remove score labels
        for label in self.score_labels:
            self.remove_widget(label)
        self.score_labels = []

        # Show player selection
        self.player_select_label.opacity = 1
        for btn in self.player_buttons:
            btn.opacity = 1
            btn.disabled = False

        # Show calibration button
        self.calibrate_button.opacity = 1
        self.calibrate_button.disabled = False

        # Update calibration label to show current offset
        if self.game.audio_offset != 0:
            offset_ms = self.game.audio_offset * 1000
            self.calibration_label.text = f"Offset: {offset_ms:.0f}ms"
        else:
            self.calibration_label.text = ""

        self.update_ui_positions()


class RhythmApp(App):
    def build(self):
        return RhythmGameApp()


if __name__ == '__main__':
    RhythmApp().run()
