# Timing Test - Bypass chart generator, use KNOWN beat times
# This isolates whether the problem is chart generation or game logic

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
import time
import os

# Test settings
USE_75BPM = True

if USE_75BPM:
    BPM = 75
    BEAT_INTERVAL = 0.8  # 800ms
    TOTAL_BEATS = 61
    AUDIO_FILE = "click_75bpm_4-4time_61beats_ZJM6si (online-audio-converter.com).mp3"
else:
    BPM = 120
    BEAT_INTERVAL = 0.5  # 500ms
    TOTAL_BEATS = 60
    AUDIO_FILE = "click.mp3"

# Generate exact beat times (what we KNOW they should be)
KNOWN_BEAT_TIMES = [i * BEAT_INTERVAL for i in range(TOTAL_BEATS)]


class FallingNote(Widget):
    def __init__(self, target_time, **kwargs):
        super().__init__(**kwargs)
        self.target_time = target_time  # When this note should reach the target
        self.active = True
        self.size = (60, 60)

    def draw(self, canvas):
        if not self.active:
            return
        with canvas:
            Color(0.3, 0.8, 1, 1)
            Ellipse(pos=self.pos, size=self.size)


class TimingTest(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Game settings
        self.note_speed = 350  # pixels per second
        self.target_y = 100    # where notes should land
        self.spawn_y = 650     # where notes spawn

        # Calculate fall time
        self.fall_time = (self.spawn_y - self.target_y) / self.note_speed
        print(f"Fall time: {self.fall_time:.3f}s ({self.fall_time*1000:.0f}ms)")

        # Audio latency compensation (measured from sync_tester)
        self.audio_latency = 0.15  # 150ms

        # State
        self.running = False
        self.start_time = 0
        self.notes = []
        self.next_note_idx = 0
        self.audio = None
        self.audio_started = False
        self.audio_start_time = 0

        # Load audio
        script_dir = os.path.dirname(os.path.abspath(__file__))
        audio_path = os.path.join(script_dir, AUDIO_FILE)
        print(f"Loading: {audio_path}")
        self.audio = SoundLoader.load(audio_path)
        if self.audio:
            print(f"Audio loaded: {self.audio.length:.1f}s")
        else:
            print("ERROR: Could not load audio!")

        # Keyboard
        self._keyboard = Window.request_keyboard(lambda: None, self)
        self._keyboard.bind(on_key_down=self.on_key_down)

        # UI
        self.info_label = Label(
            text=f'TIMING TEST\n\n{AUDIO_FILE}\n{BPM} BPM, {TOTAL_BEATS} beats\nFall time: {self.fall_time*1000:.0f}ms\n\nSPACE = Start\nNotes use HARDCODED times (not librosa)',
            font_size=16,
            color=(1, 1, 1, 1),
            halign='center',
            pos=(250, 450),
            size=(500, 200)
        )
        self.add_widget(self.info_label)

        self.timing_label = Label(
            text='',
            font_size=14,
            color=(0.7, 0.7, 0.7, 1),
            pos=(50, 20),
            size=(400, 100)
        )
        self.add_widget(self.timing_label)

        self.debug_label = Label(
            text='',
            font_size=12,
            color=(0.5, 1, 0.5, 1),
            pos=(500, 20),
            size=(450, 150),
            halign='left',
            valign='top'
        )
        self.add_widget(self.debug_label)

        # Draw loop
        Clock.schedule_interval(self.update, 1/120)

        print("\n" + "="*60)
        print("TIMING TEST - Using HARDCODED beat times")
        print("="*60)
        print(f"Beat times: 0.0, {BEAT_INTERVAL}, {BEAT_INTERVAL*2}, ...")
        print(f"Fall time: {self.fall_time:.3f}s")
        print(f"Audio latency compensation: {self.audio_latency:.3f}s")
        print("")
        print("If notes still don't sync, problem is in GAME LOGIC")
        print("If notes DO sync, problem was in CHART GENERATION")
        print("="*60)

    def on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key in ['spacebar', 'space']:
            if not self.running:
                self.start()
            else:
                self.tap()
        elif key == 'r':
            self.reset()
        return True

    def start(self):
        print("\n--- Starting ---")
        self.running = True
        self.start_time = time.perf_counter()
        self.notes = []
        self.next_note_idx = 0
        self.audio_started = False

        # Calculate when to start audio
        # First beat is at time 0.0
        # We need to spawn note at: beat_time - fall_time
        # First note spawns at: 0.0 - fall_time = -fall_time (immediately)
        # Audio should start when first note reaches target, which is at elapsed = fall_time
        # But we subtract audio_latency to compensate for playback delay

        first_beat = KNOWN_BEAT_TIMES[0]
        self.audio_delay = self.fall_time - first_beat - self.audio_latency

        print(f"First beat at: {first_beat}s")
        print(f"Audio will start at elapsed: {self.audio_delay:.3f}s")
        print(f"First note spawns immediately, falls for {self.fall_time:.3f}s")

        self.info_label.text = 'RUNNING...\n\nWatch if notes hit target line\nwhen you hear the click'

    def reset(self):
        self.running = False
        self.notes = []
        if self.audio:
            self.audio.stop()
        self.audio_started = False
        self.info_label.text = f'TIMING TEST\n\n{AUDIO_FILE}\n{BPM} BPM\n\nSPACE = Start, R = Reset'
        self.timing_label.text = ''
        self.debug_label.text = ''
        print("Reset")

    def tap(self):
        """User tapped - measure timing"""
        if not self.running or not self.audio_started:
            return

        elapsed = time.perf_counter() - self.start_time
        audio_pos = self.audio.get_pos() if self.audio else 0

        # Find nearest beat
        nearest_beat_idx = round(audio_pos / BEAT_INTERVAL)
        nearest_beat_time = nearest_beat_idx * BEAT_INTERVAL
        offset_ms = (audio_pos - nearest_beat_time) * 1000

        print(f"TAP: elapsed={elapsed:.3f}s, audio_pos={audio_pos:.3f}s, offset={offset_ms:+.0f}ms")

    def update(self, dt):
        if not self.running:
            self.draw()
            return

        elapsed = time.perf_counter() - self.start_time

        # Start audio at the right time
        if not self.audio_started and elapsed >= self.audio_delay:
            print(f"Starting audio at elapsed={elapsed:.3f}s")
            if self.audio:
                self.audio.play()
            self.audio_started = True
            self.audio_start_time = elapsed

        # Spawn notes based on KNOWN beat times
        while self.next_note_idx < len(KNOWN_BEAT_TIMES):
            beat_time = KNOWN_BEAT_TIMES[self.next_note_idx]

            # Spawn note early enough that it reaches target at beat_time
            spawn_time = beat_time - self.fall_time

            if elapsed >= spawn_time:
                note = FallingNote(target_time=beat_time)
                note.center_x = self.width / 2

                # KEY FIX: If spawn_time was negative, note should have spawned earlier
                # Adjust Y position as if it had already been falling
                if spawn_time < 0:
                    # How long ago should this note have spawned?
                    time_already_falling = elapsed - spawn_time
                    note.y = self.spawn_y - (time_already_falling * self.note_speed)
                    print(f"Spawned note {self.next_note_idx}: beat={beat_time:.2f}s, ADJUSTED y={note.y:.0f} (already falling {time_already_falling:.3f}s)")
                else:
                    note.y = self.spawn_y
                    print(f"Spawned note {self.next_note_idx}: beat={beat_time:.2f}s, spawn_time={spawn_time:.3f}s, y={note.y:.0f}")

                self.notes.append(note)
                self.next_note_idx += 1
            else:
                break

        # Move notes
        for note in self.notes[:]:
            note.y -= self.note_speed * dt

            # Check if note reached target
            if note.active and note.y <= self.target_y:
                note.active = False

                # Calculate timing accuracy
                audio_pos = self.audio.get_pos() if self.audio and self.audio_started else 0
                expected_audio_pos = note.target_time
                timing_error = (audio_pos - expected_audio_pos) * 1000

                print(f"Note reached target: expected_audio={expected_audio_pos:.3f}s, actual_audio={audio_pos:.3f}s, error={timing_error:+.0f}ms")

            # Remove off-screen notes
            if note.y < -50:
                self.notes.remove(note)

        # Update debug info
        audio_pos = self.audio.get_pos() if self.audio and self.audio_started else 0
        self.timing_label.text = f'Elapsed: {elapsed:.2f}s\nAudio pos: {audio_pos:.2f}s\nNotes active: {len(self.notes)}'

        # Check if done
        if self.next_note_idx >= len(KNOWN_BEAT_TIMES) and len(self.notes) == 0:
            self.finish()

        self.draw()

    def finish(self):
        self.running = False
        if self.audio:
            self.audio.stop()
        self.info_label.text = 'TEST COMPLETE\n\nCheck console for timing errors\nR = Reset'
        print("\n--- Test Complete ---")

    def draw(self):
        self.canvas.before.clear()
        with self.canvas.before:
            # Background
            Color(0.1, 0.1, 0.15, 1)
            Rectangle(pos=(0, 0), size=self.size)

            # Target line
            Color(1, 1, 1, 0.8)
            Line(points=[100, self.target_y, self.width - 100, self.target_y], width=2)

            # Target zone
            Color(0.3, 0.8, 0.3, 0.2)
            Rectangle(pos=(self.width/2 - 50, self.target_y - 20), size=(100, 40))

            # Draw notes
            for note in self.notes:
                if note.active:
                    Color(0.3, 0.8, 1, 1)
                    Ellipse(pos=(note.center_x - 30, note.y - 30), size=(60, 60))


class TimingTestApp(App):
    def build(self):
        Window.size = (1000, 700)
        return TimingTest()


if __name__ == '__main__':
    TimingTestApp().run()
