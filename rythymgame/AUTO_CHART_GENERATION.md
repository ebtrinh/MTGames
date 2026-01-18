# Automatic Note Chart Generation from Audio

## Overview

Yes, it's absolutely possible to automatically generate note charts from audio! This is called **beat detection** or **onset detection** in audio processing. Games like Guitar Hero, Beat Saber, and osu! use variations of these techniques.

## How It Works (High Level)

```
Audio File → Frequency Analysis → Beat/Onset Detection → Note Placement → Chart Data
```

## The Core Techniques

### 1. **Onset Detection** (Detecting when sounds start)

An "onset" is when a new sound begins - a drum hit, a note being played, a vocal starting. The algorithm looks for sudden increases in energy.

```python
# Pseudocode
for each audio_frame:
    energy = calculate_energy(frame)
    if energy > previous_energy * threshold:
        # This is an onset! A note should go here
        onsets.append(current_time)
```

### 2. **Beat Tracking** (Finding the rhythm/tempo)

This finds the BPM and where beats fall. Most music has a steady pulse.

```python
# The algorithm:
# 1. Detect all onsets
# 2. Calculate intervals between onsets
# 3. Find the most common interval = beat length
# 4. BPM = 60 / beat_length
```

### 3. **Spectral Analysis** (Separating frequencies)

Different lanes can represent different frequency ranges:
- **Lane 0 (Left/Red)**: Bass frequencies (drums, bass guitar) - 20-200 Hz
- **Lane 1 (Center/Green)**: Mid frequencies (vocals, melody) - 200-2000 Hz
- **Lane 2 (Right/Blue)**: High frequencies (cymbals, hi-hats) - 2000+ Hz

## Python Implementation Approach

### Required Libraries

```python
pip install librosa numpy scipy
```

- **librosa**: Industry-standard audio analysis library
- **numpy**: Number crunching
- **scipy**: Signal processing

### Basic Implementation

```python
import librosa
import numpy as np

def generate_chart(audio_path, difficulty='medium'):
    # Load the audio file
    y, sr = librosa.load(audio_path)

    # Get the tempo (BPM) and beat frames
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Detect onsets (all note candidates)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    # Separate into frequency bands for lane assignment
    # Using mel spectrogram
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=3)

    notes = []
    for onset_time in onset_times:
        # Find which frequency band is loudest at this moment
        frame = librosa.time_to_frames(onset_time, sr=sr)
        if frame < S.shape[1]:
            band_energies = S[:, frame]
            lane = np.argmax(band_energies)  # 0, 1, or 2
            notes.append((round(onset_time, 3), lane))

    return notes
```

### More Advanced: Difficulty Scaling

```python
def filter_notes_by_difficulty(notes, difficulty):
    """
    Easy: Only strong beats (quarter notes)
    Medium: Beats + some onsets
    Hard: All detected onsets
    Expert: All onsets + generated fills
    """
    if difficulty == 'easy':
        # Keep only ~25% of notes, preferring on-beat notes
        return notes[::4]
    elif difficulty == 'medium':
        # Keep ~50% of notes
        return notes[::2]
    elif difficulty == 'hard':
        return notes
    elif difficulty == 'expert':
        # Add extra notes between existing ones
        return add_fills(notes)
```

### Separating Instruments (Advanced)

For better lane assignment, you can use source separation:

```python
# Using Spleeter or Demucs to separate:
# - Drums → Lane 0
# - Bass → Lane 0
# - Vocals → Lane 1
# - Other/Melody → Lane 2

from spleeter.separator import Separator

separator = Separator('spleeter:4stems')
separator.separate_to_file(audio_path, output_path)
# Now analyze each stem separately
```

## Complete Chart Generator Script

Here's a full script you could add to your project:

```python
# chart_generator.py
import librosa
import numpy as np
import json
import os

class ChartGenerator:
    def __init__(self):
        self.min_note_gap = 0.1  # Minimum seconds between notes

    def generate(self, audio_path, song_name, difficulty='medium'):
        """Generate a note chart from an audio file"""
        print(f"Loading {audio_path}...")
        y, sr = librosa.load(audio_path)
        duration = librosa.get_duration(y=y, sr=sr)

        print(f"Detecting tempo...")
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        print(f"Detected BPM: {tempo:.1f}")

        print(f"Detecting onsets...")
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            backtrack=True
        )
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        print(f"Analyzing frequency bands...")
        # 3 bands for 3 lanes
        S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128)

        # Split into low/mid/high
        low_band = S[:42, :].sum(axis=0)   # Bass
        mid_band = S[42:85, :].sum(axis=0)  # Mids
        high_band = S[85:, :].sum(axis=0)   # Highs

        print(f"Generating notes...")
        notes = []
        last_time = -1

        for onset_time in onset_times:
            # Skip if too close to last note
            if onset_time - last_time < self.min_note_gap:
                continue

            frame = librosa.time_to_frames(onset_time, sr=sr)
            if frame >= len(low_band):
                continue

            # Determine lane based on frequency content
            energies = [low_band[frame], mid_band[frame], high_band[frame]]
            lane = int(np.argmax(energies))

            notes.append((round(onset_time, 3), lane))
            last_time = onset_time

        # Apply difficulty filter
        notes = self._apply_difficulty(notes, difficulty)

        print(f"Generated {len(notes)} notes")

        return {
            "name": song_name,
            "file": os.path.basename(audio_path),
            "bpm": int(tempo),
            "duration": round(duration, 2),
            "notes": notes
        }

    def _apply_difficulty(self, notes, difficulty):
        """Filter notes based on difficulty"""
        if difficulty == 'easy':
            return notes[::3]  # Every 3rd note
        elif difficulty == 'medium':
            return notes[::2]  # Every 2nd note
        elif difficulty == 'hard':
            return notes
        elif difficulty == 'expert':
            return self._add_complexity(notes)
        return notes

    def _add_complexity(self, notes):
        """Add double-notes for expert difficulty"""
        enhanced = []
        for i, (time, lane) in enumerate(notes):
            enhanced.append((time, lane))
            # 20% chance to add simultaneous note
            if np.random.random() < 0.2:
                other_lane = (lane + np.random.choice([1, 2])) % 3
                enhanced.append((time, other_lane))
        return sorted(enhanced, key=lambda x: x[0])

    def save_to_songs_py(self, chart_data, song_id):
        """Append chart to songs.py format"""
        notes_str = ",\n            ".join(
            f"({t}, {l})" for t, l in chart_data["notes"]
        )

        output = f'''
    "{song_id}": {{
        "name": "{chart_data['name']}",
        "file": "{chart_data['file']}",
        "bpm": {chart_data['bpm']},
        "notes": [
            {notes_str}
        ]
    }}'''
        print(output)
        return output


# Usage
if __name__ == "__main__":
    generator = ChartGenerator()
    chart = generator.generate(
        "kevin-macleod-hall-of-the-mountain-king.mp3",
        "In the Hall of the Mountain King",
        difficulty='medium'
    )
    generator.save_to_songs_py(chart, "hall_of_the_mountain_king")
```

## Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Notes too dense | Add minimum gap between notes |
| Wrong lane assignments | Use source separation (Spleeter) |
| Off-beat notes | Quantize to nearest beat subdivision |
| Missed quiet notes | Lower onset detection threshold |
| Too many notes | Filter by onset strength |

## Quantization (Snapping to Beat)

To make charts feel more musical, snap notes to beat subdivisions:

```python
def quantize_to_beat(onset_time, tempo, subdivision=4):
    """Snap to nearest 1/4, 1/8, or 1/16 note"""
    beat_length = 60.0 / tempo
    sub_length = beat_length / subdivision

    quantized = round(onset_time / sub_length) * sub_length
    return quantized
```

## Recommended Approach for Your Game

1. **Start Simple**: Use librosa's beat detection + onset detection
2. **Test & Tune**: Adjust thresholds until charts feel right
3. **Add Manual Override**: Let users tweak generated charts
4. **Consider Hybrid**: Auto-generate base, manually polish

## Quick Start

```bash
# Install dependencies
pip install librosa numpy

# Run generator
python chart_generator.py your_song.mp3
```

## Resources

- [librosa documentation](https://librosa.org/doc/latest/index.html)
- [Beat tracking explained](https://librosa.org/doc/main/auto_examples/plot_beat_tracker.html)
- [Onset detection tutorial](https://musicinformationretrieval.com/onset_detection.html)
- [Spleeter (source separation)](https://github.com/deezer/spleeter)
