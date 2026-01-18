# Simple Sync Tester using click.mp3
# click.mp3 = 120 BPM, 4/4 time, 60 beats
# Beats SHOULD occur at: 0.0s, 0.5s, 1.0s, 1.5s, 2.0s, ...
#
# TEST: We blink the light when WE THINK the beat happens
#       User taps when they HEAR the beat
#       Compare to find the difference

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
import time
import os
import statistics

# Choose which click track to test
# click.mp3 = 120 BPM, 60 beats
# click_75bpm = 75 BPM, 61 beats

USE_75BPM = True  # Set to False for 120 BPM test

if USE_75BPM:
    BPM = 75
    TOTAL_BEATS = 61
    CLICK_FILE = "click_75bpm_4-4time_61beats_ZJM6si (online-audio-converter.com).mp3"
else:
    BPM = 120
    TOTAL_BEATS = 60
    CLICK_FILE = "click.mp3"

BEAT_INTERVAL = 60.0 / BPM  # 0.8s for 75bpm, 0.5s for 120bpm


class SyncTester(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Load click track
        script_dir = os.path.dirname(os.path.abspath(__file__))
        click_path = os.path.join(script_dir, CLICK_FILE)

        print(f"Loading: {click_path}")
        self.audio = SoundLoader.load(click_path)

        if self.audio:
            print(f"Loaded! Length: {self.audio.length}s")
        else:
            print("ERROR: Could not load click.mp3!")

        # State
        self.running = False
        self.start_time = 0  # When we started (called play())
        self.current_beat = 0  # Which beat we're on
        self.tap_offsets = []

        # Visual flash state
        self.flash = 0
        self.last_flash_beat = -1

        # Keyboard
        self._keyboard = Window.request_keyboard(lambda: None, self)
        self._keyboard.bind(on_key_down=self.on_key_down)

        # UI Labels
        self.status = Label(
            text=f'SYNC TESTER\n\nUsing: {CLICK_FILE}\n{BPM} BPM ({BEAT_INTERVAL*1000:.0f}ms per beat)\n\nSPACE = Start/Tap, R = Reset',
            font_size=18,
            color=(1, 1, 1, 1),
            halign='center',
            pos=(250, 420),
            size=(500, 180)
        )
        self.add_widget(self.status)

        self.offset_display = Label(
            text='',
            font_size=32,
            bold=True,
            color=(1, 1, 0, 1),
            pos=(350, 280),
            size=(300, 50)
        )
        self.add_widget(self.offset_display)

        self.beat_display = Label(
            text='',
            font_size=16,
            color=(0.6, 0.6, 0.6, 1),
            pos=(400, 230),
            size=(200, 30)
        )
        self.add_widget(self.beat_display)

        self.results = Label(
            text='',
            font_size=14,
            color=(0.7, 1, 0.7, 1),
            halign='left',
            valign='top',
            pos=(50, 30),
            size=(500, 180)
        )
        self.add_widget(self.results)

        # Draw loop - high precision
        Clock.schedule_interval(self.update, 1/240)

        print("\n" + "="*50)
        print("SYNC TESTER")
        print("="*50)
        print(f"File: {CLICK_FILE}")
        print(f"BPM: {BPM} ({BEAT_INTERVAL*1000:.0f}ms per beat)")
        print(f"Total beats: {TOTAL_BEATS}")
        print("="*50)
        print("Light blinks = when we THINK beat should happen")
        print("You tap      = when you HEAR the beat")
        print("="*50)
        print("SPACE = Start / Tap")
        print("R     = Reset")
        print("="*50)

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
        """Start the test - play audio and start our timer"""
        if not self.audio:
            print("No audio loaded!")
            return

        print("\n--- Starting ---")
        print("Light will blink at 0.0s, 0.5s, 1.0s, ...")
        print("Tap when you HEAR each click")
        print("")

        self.running = True
        self.start_time = time.perf_counter()
        self.current_beat = 0
        self.last_flash_beat = -1
        self.tap_offsets = []

        # Play audio immediately
        self.audio.play()

        self.status.text = 'RUNNING\n\nLight = our prediction\nTap = when you hear it'
        self.results.text = ''

    def reset(self):
        """Stop and reset"""
        if self.audio:
            self.audio.stop()
        self.running = False
        self.tap_offsets = []
        self.flash = 0
        self.current_beat = 0
        self.status.text = f'SYNC TESTER\n\nUsing: {CLICK_FILE}\n{BPM} BPM ({BEAT_INTERVAL*1000:.0f}ms per beat)\n\nSPACE = Start/Tap, R = Reset'
        self.offset_display.text = ''
        self.beat_display.text = ''
        self.results.text = ''
        print("Reset")

    def tap(self):
        """User tapped - they heard a beat"""
        if not self.running:
            return

        # Time since we started
        elapsed = time.perf_counter() - self.start_time

        # We PREDICTED beats at 0.0, 0.5, 1.0, ...
        # Find which beat they're tapping for
        beat_number = round(elapsed / BEAT_INTERVAL)
        predicted_time = beat_number * BEAT_INTERVAL

        # Offset: positive = they tapped AFTER our prediction (audio is late)
        #         negative = they tapped BEFORE our prediction (audio is early)
        offset_ms = (elapsed - predicted_time) * 1000

        # Also calculate offset from previous beat (to detect half-beat drift)
        prev_beat_time = (beat_number - 1) * BEAT_INTERVAL if beat_number > 0 else 0
        offset_from_prev = (elapsed - prev_beat_time) * 1000

        self.tap_offsets.append(offset_ms)

        # Display
        if offset_ms > 20:
            self.offset_display.text = f'+{offset_ms:.0f}ms'
            self.offset_display.color = (1, 0.5, 0.3, 1)
            desc = "Audio LATE"
        elif offset_ms < -20:
            self.offset_display.text = f'{offset_ms:.0f}ms'
            self.offset_display.color = (0.3, 0.5, 1, 1)
            desc = "Audio EARLY"
        else:
            self.offset_display.text = f'{offset_ms:+.0f}ms'
            self.offset_display.color = (0.3, 1, 0.3, 1)
            desc = "SYNCED!"

        # Print raw elapsed time so we can see the actual pattern
        print(f"Tap #{len(self.tap_offsets):2d}: elapsed={elapsed:.3f}s (beat {beat_number}, offset {offset_ms:+.0f}ms, from_prev={offset_from_prev:.0f}ms)")

    def update(self, dt):
        if not self.running:
            self.draw()
            return

        # Time since we started
        elapsed = time.perf_counter() - self.start_time

        # Which beat should we be on?
        current_beat = int(elapsed / BEAT_INTERVAL)

        # Blink on new beats
        if current_beat > self.last_flash_beat and current_beat < TOTAL_BEATS:
            self.flash = 1.0
            self.last_flash_beat = current_beat
            self.beat_display.text = f'Beat {current_beat + 1}/{TOTAL_BEATS}'

        # Check if done
        if elapsed > TOTAL_BEATS * BEAT_INTERVAL + 0.5:
            self.finish()

        # Fade flash
        if self.flash > 0:
            self.flash -= dt * 10

        self.draw()

    def finish(self):
        """Test complete - show results"""
        self.running = False
        if self.audio:
            self.audio.stop()

        print("\n" + "="*50)
        print("RESULTS")
        print("="*50)

        if len(self.tap_offsets) < 5:
            self.results.text = "Not enough taps. Try again!"
            print("Not enough taps")
            self.status.text = 'Not enough taps\n\nPress SPACE to try again'
            return

        avg = statistics.mean(self.tap_offsets)
        median = statistics.median(self.tap_offsets)
        stdev = statistics.stdev(self.tap_offsets)
        min_off = min(self.tap_offsets)
        max_off = max(self.tap_offsets)

        results_text = f"""RESULTS ({len(self.tap_offsets)} taps):

  Average: {avg:+.1f}ms
  Median:  {median:+.1f}ms
  Std Dev: {stdev:.1f}ms
  Range:   {min_off:+.0f}ms to {max_off:+.0f}ms

INTERPRETATION:
  Positive = Audio plays AFTER our visual (audio latency)
  Negative = Audio plays BEFORE our visual (unlikely)

  If avg is ~0ms: Our timer matches audio perfectly!
  If avg is +100ms: Audio has 100ms latency"""

        self.results.text = results_text
        self.status.text = f'DONE - Average: {avg:+.1f}ms\n\nPress R to reset'

        print(f"Average: {avg:+.1f}ms")
        print(f"Median:  {median:+.1f}ms")
        print(f"Std Dev: {stdev:.1f}ms")
        print("")
        if abs(avg) < 30:
            print("CONCLUSION: Audio timing is accurate!")
            print("Problem is likely in chart generation or note spawning.")
        else:
            print(f"CONCLUSION: Audio has ~{abs(avg):.0f}ms latency")
            print(f"Set audio_latency compensation to {max(0, avg):.0f}ms")
        print("="*50)

    def draw(self):
        self.canvas.before.clear()
        with self.canvas.before:
            # Background
            Color(0.1, 0.1, 0.15, 1)
            Rectangle(pos=(0, 0), size=self.size)

            # Flash circle - this is our PREDICTION of when the beat is
            if self.flash > 0.5:
                Color(1, 1, 1, 1)  # Bright white when flashing
            elif self.flash > 0:
                Color(0.5, 0.5, 0.5, self.flash * 2)  # Fading
            else:
                Color(0.15, 0.15, 0.15, 1)  # Dim when not flashing

            size = 180
            Ellipse(pos=(self.width/2 - size/2, self.height/2 - size/2 + 30), size=(size, size))


class SyncTesterApp(App):
    def build(self):
        Window.size = (1000, 700)
        return SyncTester()


if __name__ == '__main__':
    SyncTesterApp().run()
