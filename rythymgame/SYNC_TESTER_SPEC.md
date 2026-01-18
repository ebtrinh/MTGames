# Audio-Visual Sync Tester

A minimal program to isolate and measure timing delays.

## Purpose

Test three things independently:
1. **Audio latency** - delay between `play()` and sound reaching ears
2. **Visual latency** - delay between drawing and seeing on screen
3. **Perception accuracy** - how accurately humans can tap to a beat

## Program Design

### Test 1: Audio-Only Tap Test
```
[LISTEN MODE]

♪ tick... tick... tick... tick...    (plays at exactly 500ms intervals)

[TAP SPACEBAR WHEN YOU HEAR EACH TICK]

Your timing:
  Tap 1: +12ms (late)
  Tap 2: -5ms (early)
  Tap 3: +8ms (late)
  Tap 4: +3ms (late)

Average offset: +4.5ms
```

This measures: **Human reaction time + audio latency**

### Test 2: Visual-Only Tap Test
```
[WATCH MODE]

  ●        (circle flashes white every 500ms)

[TAP SPACEBAR WHEN YOU SEE THE FLASH]

Your timing:
  Tap 1: +45ms (late)
  Tap 2: +38ms (late)
  ...

Average offset: +42ms
```

This measures: **Human reaction time + display latency**

### Test 3: Audio+Visual Combined
```
[SYNC MODE]

  ●  ♪     (flash + tick happen together)

[TAP WHEN THEY HAPPEN]

Average offset: +25ms
```

### Test 4: Falling Note Test
```
[RHYTHM GAME MODE]

     ○         <- note falls down
     ○
     ○
     ●         <- target line (tap when note reaches here)
  ───────
     ♪         <- tick plays when note SHOULD reach line

[TAP WHEN NOTE REACHES LINE]

Results:
  Visual arrival vs Audio: Note arrives 50ms BEFORE tick
  Your tap vs Audio: You tap 30ms AFTER tick
  Your tap vs Visual: You tap 80ms AFTER note arrives
```

This tells us exactly where the desync is.

## Implementation

### Minimal Code Structure

```python
# sync_tester.py
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
import time

class SyncTester(Widget):
    def __init__(self):
        self.mode = "audio_only"  # audio_only, visual_only, combined, falling
        self.tick_sound = self.create_tick()
        self.interval = 0.5  # 500ms = 120 BPM

        self.tick_times = []      # When we SCHEDULED the tick
        self.actual_times = []    # When tick ACTUALLY played (if measurable)
        self.tap_times = []       # When user tapped

    def start_test(self):
        self.test_start = time.perf_counter()
        self.next_tick = 0
        Clock.schedule_interval(self.update, 1/120)  # 120fps for precision

    def update(self, dt):
        now = time.perf_counter() - self.test_start

        # Time for next tick?
        if now >= self.next_tick * self.interval:
            scheduled_time = self.next_tick * self.interval
            self.tick_times.append(scheduled_time)

            if self.mode in ["audio_only", "combined", "falling"]:
                self.tick_sound.play()

            if self.mode in ["visual_only", "combined"]:
                self.flash()

            if self.mode == "falling":
                # Note should reach target NOW
                pass

            self.next_tick += 1

    def on_tap(self):
        now = time.perf_counter() - self.test_start
        self.tap_times.append(now)

        # Find closest tick
        closest_tick = min(self.tick_times, key=lambda t: abs(t - now))
        offset = (now - closest_tick) * 1000  # ms

        print(f"Tap offset: {offset:+.0f}ms")
```

## What We'll Learn

| If this is off... | It means... |
|-------------------|-------------|
| Audio-only test shows +50ms | Audio system has 50ms latency |
| Visual-only test shows +100ms | Display has 100ms latency |
| Falling note arrives early | Our spawn timing math is wrong |
| Falling note arrives late | Fall speed calculation is wrong |
| Combined shows different than sum | There's interference between systems |

## Controls

```
SPACE  - Tap (register a beat)
1      - Audio-only mode
2      - Visual-only mode
3      - Combined mode
4      - Falling note mode
R      - Reset/restart test
+/-    - Adjust interval (BPM)
ESC    - Quit
```

## Output

After each test (12 ticks), show:
```
=== TEST RESULTS ===
Mode: Audio Only
Ticks: 12
Taps registered: 11

Timing offsets (ms):
  Min: -15ms (early)
  Max: +45ms (late)
  Average: +18ms
  Std Dev: 12ms

Interpretation:
  Your system has approximately 18ms audio latency
  (or you naturally tap 18ms late)

To compensate in rhythm game:
  Set audio_latency = 18ms
```

## Building This

Create a single file `sync_tester.py` that:
1. Is completely standalone (no chart_generator dependency)
2. Uses minimal Kivy (just a window, keyboard input, basic shapes)
3. Generates its own tick sound (no external files)
4. Prints clear results to console
5. Can switch between test modes with number keys

## Why This Helps

Instead of guessing "is it the chart? the audio? the display? my timing?", this program isolates each variable so we can measure them independently and know exactly what to compensate for.
