# Rhythm Game Timing Offset Analysis

## The Problem
Even on a local computer with theoretically 0ms display/audio latency, there's still noticeable offset between when notes reach the target and when the corresponding sound plays.

## Potential Causes (Most to Least Likely)

### 1. Audio Playback Latency (MOST LIKELY)
**The Issue:** When you call `sound.play()`, the audio doesn't actually start outputting immediately. There's a buffer that needs to fill first.

```
Timeline:
  play() called ──────> Audio buffer fills ──────> Sound actually plays
                        ↑
                   ~50-200ms delay (varies by system/driver)
```

**Why this matters:** We schedule `Clock.schedule_once(start_audio, audio_delay)` and assume audio starts exactly then. But SDL2/Kivy's audio system has inherent startup latency that we're not accounting for.

**Evidence:** This is the #1 issue in rhythm game development. Games like osu!, Guitar Hero, and Beat Saber all have audio calibration specifically for this reason.

---

### 2. Onset Detection Timing (LIKELY)
**The Issue:** Librosa's onset detection doesn't detect the exact moment a sound starts - it detects when energy increases significantly, which is slightly AFTER the attack begins.

```
Actual sound:    |████████████████
Detected onset:     ↑ (slightly late)
                    ~10-50ms after actual start
```

**Why this matters:** Every note in our chart might be 10-50ms late compared to the actual audio.

**The Fix:** Librosa has a `backtrack` parameter that tries to find the actual start, but it's not perfect. We could add a global "chart offset" to shift all detected notes earlier.

---

### 3. Fall Time Calculation Timing (POSSIBLE)
**The Issue:** We calculate fall time in `start_game()`:
```python
fall_time = self.get_note_fall_time()  # Uses self.height
```

But `self.height` might not be the final window height if the window is still initializing or resizing. If `height` is wrong, all our timing math is wrong.

**Test:** Add debug output to verify height is correct:
```python
print(f"Window height: {self.height}, Expected: 700")
```

---

### 4. Clock.schedule_once Imprecision (POSSIBLE)
**The Issue:** `Clock.schedule_once(callback, delay)` doesn't guarantee exact timing. It schedules for "at least" that delay, but the actual callback happens on the next frame after the delay passes.

```
Requested: 1.57s delay
Actual:    1.58s (next frame boundary)
Error:     ~16ms (one frame at 60fps)
```

**Why this matters:** Up to 16ms error per scheduled event.

---

### 5. Frame Rate / dt Accumulation Drift (UNLIKELY BUT CUMULATIVE)
**The Issue:** `elapsed_time += dt` accumulates small floating-point errors over time.

```python
# Each frame:
elapsed_time += dt  # dt varies slightly each frame
```

Over a 3-minute song, small errors could accumulate to noticeable drift. However, this would cause notes to get progressively more off-sync, not a constant offset.

---

### 6. Chart Generation vs Playback Sample Rate Mismatch (UNLIKELY)
**The Issue:** Librosa loads audio at 22050 Hz for analysis, but playback might be at 44100 Hz or 48000 Hz. If there's any sample-rate-dependent timing, this could cause issues.

---

## Most Likely Root Cause

**Audio playback latency** combined with **onset detection being slightly late**.

The audio system has ~50-150ms of startup latency that we're not accounting for. We assume `play()` = instant sound, but it's not.

## Recommended Fixes

### Fix 1: Measure and Compensate for Audio Latency
Add a constant offset to compensate for typical audio latency:

```python
# In start_game():
AUDIO_SYSTEM_LATENCY = 0.1  # 100ms - tune this value
audio_delay = max(0, fall_time - first_note_time - AUDIO_SYSTEM_LATENCY)
```

### Fix 2: Pre-buffer Audio Before Playing
Instead of:
```python
Clock.schedule_once(start_audio, audio_delay)
```

Do:
```python
# Load and seek to beginning to "warm up" the audio
self.song_audio.seek(0)
Clock.schedule_once(start_audio, audio_delay)
```

### Fix 3: Add Chart-Level Offset
In the chart generator, add a global offset to all note times:

```python
ONSET_DETECTION_COMPENSATION = -0.03  # 30ms earlier
notes.append((round(onset_time + ONSET_DETECTION_COMPENSATION, 3), lane))
```

### Fix 4: Use Audio Position Instead of Elapsed Time
Instead of tracking `elapsed_time` independently, sync to the actual audio position:

```python
def update_game(self, dt):
    if self.song_audio and self.song_audio.state == 'play':
        # Use actual audio position instead of accumulated time
        audio_position = self.song_audio.get_pos()
        # Spawn notes based on audio_position instead of elapsed_time
```

This is the most robust solution but requires restructuring the spawn logic.

## Quick Test to Identify the Culprit

Add this debug output to see what's happening:

```python
def start_audio(dt):
    import time
    print(f"[TIMING] Audio scheduled to start at: {audio_delay:.3f}s")
    print(f"[TIMING] Actual elapsed when play() called: {self.elapsed_time:.3f}s")
    print(f"[TIMING] System time: {time.time()}")
    self.song_audio.play()
    print(f"[TIMING] play() returned at: {time.time()}")
```

Then tap along and see if the offset is:
- **Constant throughout song** → Audio startup latency
- **Getting worse over time** → dt accumulation drift
- **Random/inconsistent** → Frame timing issues

## My Best Guess

The offset you're experiencing is **audio playback latency** (~100-150ms). The audio system buffers before outputting, and we're not accounting for this.

Try adding `AUDIO_SYSTEM_LATENCY = 0.1` (100ms) as a compensation factor and see if it improves. If it overcorrects, reduce it. If it's still off, increase it.
