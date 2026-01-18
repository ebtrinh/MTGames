# Rhythm Game Timing Problems - Comprehensive Diagnostic Guide

## Current Symptoms
- Notes appear on screen (some already below target) when game starts
- Timing is off for both 75 BPM and 120 BPM click tracks
- 75 BPM is closer to correct than 120 BPM (inconsistent gap)
- The gap between notes and audio is NOT consistent across different BPMs

---

## Problem Categories

### 1. Audio System Latency
**Description:** Delay between calling `sound.play()` and actual sound output from speakers.

**Evidence so far:** sync_tester.py measured ~140-175ms latency consistently.

**Test to perform:**
```
Test: Run sync_tester.py again with both 75 and 120 BPM
Expected: Consistent latency (within ~30ms) regardless of BPM
If latency differs by BPM: Audio system behaves differently for different files
If latency is consistent: This is NOT the varying factor between 75/120 BPM
```

---

### 2. Chart Generation (Librosa Onset Detection)
**Description:** Librosa detects onsets slightly AFTER the actual sound starts, and this delay may vary based on audio characteristics.

**Evidence so far:** We created timing_test.py with hardcoded times to bypass this - but we haven't compared results systematically.

**Test to perform:**
```
Test A: Print the first 10 note times from each chart file
- click_chart.json (120 BPM - should be 0.0, 0.5, 1.0, ...)
- click_75bpm_chart.json (75 BPM - should be 0.0, 0.8, 1.6, ...)

Test B: Compare librosa-detected times vs known times
- 120 BPM: Expected 0.0, 0.5, 1.0 - What does librosa say?
- 75 BPM: Expected 0.0, 0.8, 1.6 - What does librosa say?

If detected times are offset: Chart generation adds timing error
If detected times match: Chart generation is NOT the problem
```

---

### 3. First Note Time Handling
**Description:** The calculation `audio_delay = fall_time - first_note_time - audio_latency` assumes first_note_time is correct. If the first note in the chart is at the wrong time, everything shifts.

**Evidence so far:** Unknown - we haven't inspected what first_note_time actually is.

**Test to perform:**
```
Test: Add debug output showing:
- first_note_time from chart
- fall_time calculation
- audio_latency value
- resulting audio_delay

For 120 BPM: first_note should be ~0.0
For 75 BPM: first_note should be ~0.0
If first_note is significantly > 0: This explains early note appearance
```

---

### 4. Fall Time Calculation
**Description:** `fall_time = (self.height + 10 - 70) / self.note_speed`. If height is wrong or note_speed varies, fall time is wrong.

**Evidence so far:** Unknown.

**Test to perform:**
```
Test: Print at game start:
- self.height (should be ~700)
- self.note_speed (should be 350)
- calculated fall_time (should be ~1.83s for 700px height)

If height is wrong: Window initialization issue
If fall_time varies between songs: Something is changing these values
```

---

### 5. Negative Spawn Time Handling
**Description:** If a note's spawn_time (note_time - fall_time) is negative, the note should spawn at game start but adjusted lower. Currently we spawn at elapsed_time >= spawn_time, which fires immediately for negative values.

**Evidence so far:** This was identified as an issue, fix was attempted but caused other problems.

**Test to perform:**
```
Test: For each song, print:
- First note time
- Fall time
- First spawn time (note_time - fall_time)

If spawn_time is negative: Notes bunch up at start
Calculate: How many notes have negative spawn times?

For 120 BPM (0.5s interval, 1.83s fall):
  Notes at 0.0, 0.5, 1.0, 1.5 all have negative spawn times (spawn at -1.83, -1.33, -0.83, -0.33)

For 75 BPM (0.8s interval, 1.83s fall):
  Notes at 0.0, 0.8, 1.6 have negative spawn times (spawn at -1.83, -1.03, -0.23)

120 BPM has MORE notes with negative spawn times - could explain why it's MORE off!
```

---

### 6. Audio Delay Calculation
**Description:** `audio_delay = max(0, fall_time - first_note_time - audio_latency)`. This determines when audio starts relative to game loop start.

**Evidence so far:** Unknown exact values being used.

**Test to perform:**
```
Test: Print the exact audio_delay for each song

For 120 BPM (first_note=0, fall_time=1.83, latency=0.15):
  audio_delay = max(0, 1.83 - 0 - 0.15) = 1.68s

For 75 BPM (first_note=0, fall_time=1.83, latency=0.15):
  audio_delay = max(0, 1.83 - 0 - 0.15) = 1.68s

These SHOULD be the same if first_note is 0 for both.
If they differ: first_note_time is different
```

---

### 7. dt Accumulation Drift
**Description:** `elapsed_time += dt` accumulates small errors over time.

**Evidence so far:** This would cause progressive drift, not immediate offset.

**Test to perform:**
```
Test: Compare elapsed_time to perf_counter over 30 seconds
- Every second, print: elapsed_time vs actual_time vs drift

If drift increases over time: dt accumulation issue
If offset is constant: NOT a dt issue (our problem is immediate)
```

---

### 8. Clock.schedule_once Precision
**Description:** `Clock.schedule_once(start_audio, audio_delay)` may not fire exactly at the requested time.

**Evidence so far:** Unknown.

**Test to perform:**
```
Test: When audio starts, print:
- Requested delay (audio_delay)
- Actual elapsed_time when callback fires
- Difference (scheduling error)

If error is large (>50ms): Clock scheduling is imprecise
If error is small: NOT the main problem
```

---

### 9. Note Speed vs BPM Relationship
**Description:** Notes fall at constant pixel speed, but different BPMs have different note spacing. The visual density differs.

**Evidence so far:** 120 BPM notes are closer together (every 0.5s), 75 BPM notes are further apart (every 0.8s).

**Test to perform:**
```
Test: Calculate note spacing in pixels at arrival

120 BPM: 0.5s apart * 350 px/s = 175 pixels between notes
75 BPM: 0.8s apart * 350 px/s = 280 pixels between notes

If notes bunch up visually, the denser 120 BPM pattern
makes errors more noticeable (multiple notes off at once).
```

---

### 10. Audio Position Sync Code
**Description:** The game tries to sync elapsed_time to audio position, but audio.get_pos() may return 0 or be unreliable.

**Evidence so far:** timing_test.py showed audio.get_pos() returns 0 for some files.

**Test to perform:**
```
Test: During gameplay, print every second:
- elapsed_time
- audio.get_pos()
- audio.state

If get_pos() returns 0: Sync code is broken, elapsed_time drifts
If get_pos() works: Check if sync correction is working
```

---

### 11. Window Height at Start
**Description:** Notes spawn at `self.height + 10`, but if height isn't set correctly when game starts, spawn position is wrong.

**Evidence so far:** Unknown.

**Test to perform:**
```
Test: Print self.height at multiple points:
- In __init__
- When start_game is called
- When first note spawns
- After first frame update

If height changes: Early notes spawn at wrong position
If height is consistent and correct (~700): NOT the problem
```

---

### 12. Audio File Differences
**Description:** Different audio files may have different characteristics (encoding, sample rate, silent padding at start).

**Evidence so far:** 75 BPM and 120 BPM files behave differently.

**Test to perform:**
```
Test: Use audio editor (Audacity) to inspect:
- Exact time of first click in each file
- Any silent padding at the start
- Waveform alignment with expected beat times

If 120 BPM has more padding: First beat isn't at 0.0
If files are accurate: NOT an audio file issue
```

---

### 13. The "Immediate Spawn Bunching" Problem
**Description:** When game starts (elapsed_time=0), ALL notes with negative spawn_time spawn simultaneously at the same Y position.

**Evidence so far:** This was identified. The previous fix attempt adjusted Y but caused other issues.

**Test to perform:**
```
Test: Count how many notes spawn on first frame

For 120 BPM with fall_time=1.83s:
  Spawn times: -1.83, -1.33, -0.83, -0.33, 0.17, 0.67, ...
  At elapsed=0: 4 notes spawn at once!

For 75 BPM with fall_time=1.83s:
  Spawn times: -1.83, -1.03, -0.23, 0.57, ...
  At elapsed=0: 3 notes spawn at once

More bunched notes = looks more wrong
```

---

## Priority Testing Order

Based on symptoms (notes already visible, 75 BPM closer than 120 BPM):

1. **Test #5 (Negative Spawn Times)** - Most likely cause of "notes already there"
2. **Test #3 (First Note Time)** - Check if charts have correct first note
3. **Test #2 (Chart Generation)** - Compare librosa output to expected
4. **Test #6 (Audio Delay)** - Verify delay calculation
5. **Test #11 (Window Height)** - Rule out initialization issues
6. **Test #1 (Audio Latency)** - Confirm latency is consistent
7. **Test #10 (Audio Position)** - Check if sync is working

---

## Quick Diagnostic Script Needed

Create a script that, for each song:
1. Loads the chart
2. Prints first 5 note times
3. Calculates fall_time (assuming height=700, speed=350)
4. Calculates spawn_time for first 5 notes
5. Counts how many notes have negative spawn_time
6. Calculates audio_delay
7. Prints summary

This will tell us exactly what's happening mathematically before any animation runs.
