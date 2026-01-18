# Automatic Chart Generator for Rhythm Game
# Uses librosa for audio analysis and onset detection

# IMPORTANT: Suppress numba debug output BEFORE importing anything else
import os
import warnings

# Suppress numba JIT compilation debug spam
os.environ['NUMBA_DISABLE_JIT'] = '0'  # Keep JIT enabled but quiet
os.environ['NUMBA_DEBUG'] = '0'
os.environ['NUMBA_WARNINGS'] = '0'
os.environ['NUMBA_LOG_LEVEL'] = 'ERROR'

# Also suppress general warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

import json

print("[ChartGen] Importing numpy...")
import numpy as np
print("[ChartGen] Numpy imported successfully")

try:
    print("[ChartGen] Importing librosa (first time may take 30-60 seconds)...")
    # Suppress librosa/numba logging
    import logging
    logging.getLogger('numba').setLevel(logging.ERROR)
    logging.getLogger('librosa').setLevel(logging.ERROR)

    import librosa
    LIBROSA_AVAILABLE = True
    print("[ChartGen] Librosa imported successfully")
except ImportError as e:
    LIBROSA_AVAILABLE = False
    print(f"Warning: librosa not installed. Run: pip install librosa")
    print(f"Import error: {e}")


class ChartGenerator:
    """Generates note charts from audio files using beat/onset detection"""

    def __init__(self):
        # Minimum gap between notes (seconds) - prevents note spam
        self.min_note_gap = 0.15
        # Onset detection sensitivity (lower = more notes)
        self.onset_threshold = 0.5

    def generate(self, audio_path, song_name=None, difficulty='medium'):
        """
        Generate a note chart from an audio file.

        Args:
            audio_path: Path to the audio file (mp3, wav, etc.)
            song_name: Display name for the song
            difficulty: 'easy', 'medium', 'hard', or 'expert'

        Returns:
            dict with song data including generated notes
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa is required. Install with: pip install librosa")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if song_name is None:
            song_name = os.path.splitext(os.path.basename(audio_path))[0]

        print(f"[ChartGen] Loading audio: {audio_path}")
        print(f"[ChartGen] This may take 10-30 seconds for the first load...")
        try:
            y, sr = librosa.load(audio_path, sr=22050)  # Standard sample rate
            print(f"[ChartGen] Audio loaded into memory")
            duration = librosa.get_duration(y=y, sr=sr)
            print(f"[ChartGen] Duration: {duration:.1f}s, Sample rate: {sr}")
        except Exception as e:
            print(f"[ChartGen] ERROR loading audio: {e}")
            raise

        # Detect tempo (BPM)
        print("[ChartGen] Analyzing tempo (this takes a moment)...")
        try:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            # Handle both old and new librosa versions
            if hasattr(tempo, '__iter__'):
                tempo = float(tempo[0]) if len(tempo) > 0 else 120.0
            else:
                tempo = float(tempo)
            print(f"[ChartGen] Detected BPM: {tempo:.1f}")
        except Exception as e:
            print(f"[ChartGen] ERROR in tempo detection: {e}")
            tempo = 120.0

        # Detect onsets (when sounds begin)
        print("[ChartGen] Detecting onsets...")
        try:
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            print("[ChartGen] Onset strength computed")
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=sr,
                backtrack=False,
                units='frames'
            )
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            print(f"[ChartGen] Found {len(onset_times)} raw onsets")
        except Exception as e:
            print(f"[ChartGen] ERROR in onset detection: {e}")
            onset_times = []
            onset_env = np.array([])
            onset_frames = np.array([])

        # Compute spectral centroid for pitch-based lane assignment
        # Spectral centroid = "center of mass" of frequencies = perceived pitch
        print("[ChartGen] Computing spectral centroid for lane assignment...")
        try:
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            print(f"[ChartGen] Spectral centroid computed, range: {np.min(spectral_centroid):.0f} - {np.max(spectral_centroid):.0f} Hz")
        except Exception as e:
            print(f"[ChartGen] ERROR computing spectral centroid: {e}")
            spectral_centroid = np.zeros(1000)

        # Calculate percentiles for lane thresholds
        # This ensures roughly equal distribution across lanes
        centroid_33 = np.percentile(spectral_centroid, 33)
        centroid_66 = np.percentile(spectral_centroid, 66)
        print(f"[ChartGen] Lane thresholds: <{centroid_33:.0f}Hz=Left, <{centroid_66:.0f}Hz=Center, >={centroid_66:.0f}Hz=Right")

        # Generate notes from onsets
        print("[ChartGen] Generating notes from onsets...")
        notes = []
        last_note_time = -1

        # Get onset strengths for filtering
        if len(onset_frames) > 0 and len(onset_env) > 0:
            valid_frames = onset_frames[onset_frames < len(onset_env)]
            onset_strengths = onset_env[valid_frames] if len(valid_frames) > 0 else np.array([])
        else:
            onset_strengths = np.array([])

        mean_strength = np.mean(onset_strengths) if len(onset_strengths) > 0 else 0
        print(f"[ChartGen] Processing {len(onset_times)} onsets, mean strength: {mean_strength:.2f}")

        # Track lane distribution for debugging
        lane_counts = [0, 0, 0]

        for i, onset_time in enumerate(onset_times):
            # Skip if too close to last note
            if onset_time - last_note_time < self.min_note_gap:
                continue

            # Skip very weak onsets
            if i < len(onset_strengths) and mean_strength > 0:
                if onset_strengths[i] < mean_strength * self.onset_threshold:
                    continue

            # Get the frame index for this onset
            frame = librosa.time_to_frames(onset_time, sr=sr)
            if frame >= len(spectral_centroid):
                continue

            # Determine lane based on spectral centroid (perceived pitch)
            centroid_val = spectral_centroid[frame]

            if centroid_val < centroid_33:
                lane = 0  # Low pitch = Left
            elif centroid_val < centroid_66:
                lane = 1  # Mid pitch = Center
            else:
                lane = 2  # High pitch = Right

            lane_counts[lane] += 1
            notes.append((round(onset_time, 3), lane))
            last_note_time = onset_time

        print(f"[ChartGen] Lane distribution: Left={lane_counts[0]}, Center={lane_counts[1]}, Right={lane_counts[2]}")

        print(f"[ChartGen] Generated {len(notes)} notes before difficulty filter")

        # Apply difficulty filter
        notes = self._apply_difficulty(notes, difficulty, tempo)
        print(f"[ChartGen] Final note count: {len(notes)} ({difficulty})")
        print(f"[ChartGen] ===== CHART GENERATION COMPLETE =====")

        return {
            "name": song_name,
            "file": os.path.basename(audio_path),
            "bpm": int(tempo),
            "duration": round(duration, 2),
            "difficulty": difficulty,
            "notes": notes
        }

    def _apply_difficulty(self, notes, difficulty, tempo):
        """Filter/modify notes based on difficulty level"""
        if len(notes) == 0:
            return notes

        if difficulty == 'easy':
            # Keep only ~30% of notes, increase min gap
            filtered = []
            last_time = -1
            min_gap = 0.5  # Larger gap for easy
            for time, lane in notes:
                if time - last_time >= min_gap:
                    filtered.append((time, lane))
                    last_time = time
            return filtered

        elif difficulty == 'medium':
            # Keep ~50% of notes
            filtered = []
            last_time = -1
            min_gap = 0.25
            for time, lane in notes:
                if time - last_time >= min_gap:
                    filtered.append((time, lane))
                    last_time = time
            return filtered

        elif difficulty == 'hard':
            # Keep most notes
            return notes

        elif difficulty == 'expert':
            # Add double-notes for complexity
            enhanced = list(notes)
            additions = []

            for i, (time, lane) in enumerate(notes):
                # 25% chance to add a simultaneous note in different lane
                if np.random.random() < 0.25:
                    other_lane = (lane + np.random.choice([1, 2])) % 3
                    additions.append((time, other_lane))

            enhanced.extend(additions)
            return sorted(enhanced, key=lambda x: (x[0], x[1]))

        return notes

    def generate_and_cache(self, audio_path, cache_path=None, **kwargs):
        """Generate chart and save to cache file"""
        if cache_path is None:
            base = os.path.splitext(audio_path)[0]
            cache_path = base + "_chart.json"

        # Check if cache exists and is newer than audio file
        if os.path.exists(cache_path):
            audio_mtime = os.path.getmtime(audio_path)
            cache_mtime = os.path.getmtime(cache_path)
            if cache_mtime > audio_mtime:
                print(f"[ChartGen] Loading from cache: {cache_path}")
                with open(cache_path, 'r') as f:
                    return json.load(f)

        # Generate new chart
        chart = self.generate(audio_path, **kwargs)

        # Save to cache
        print(f"[ChartGen] Saving to cache: {cache_path}")
        with open(cache_path, 'w') as f:
            json.dump(chart, f, indent=2)

        return chart

    def load_or_generate(self, audio_path, **kwargs):
        """Load from cache if available, otherwise generate"""
        base = os.path.splitext(audio_path)[0]
        cache_path = base + "_chart.json"

        if os.path.exists(cache_path):
            print(f"[ChartGen] Loading cached chart: {cache_path}")
            with open(cache_path, 'r') as f:
                return json.load(f)

        return self.generate_and_cache(audio_path, cache_path, **kwargs)


def generate_chart_for_song(audio_path, difficulty='medium'):
    """Convenience function to generate a chart"""
    generator = ChartGenerator()
    return generator.generate(audio_path, difficulty=difficulty)


# Command-line usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chart_generator.py <audio_file> [difficulty]")
        print("Difficulties: easy, medium, hard, expert")
        sys.exit(1)

    audio_file = sys.argv[1]
    difficulty = sys.argv[2] if len(sys.argv) > 2 else 'medium'

    if not LIBROSA_AVAILABLE:
        print("Error: librosa is required. Install with: pip install librosa")
        sys.exit(1)

    generator = ChartGenerator()
    chart = generator.generate_and_cache(audio_file, difficulty=difficulty)

    print("\n" + "="*50)
    print(f"Song: {chart['name']}")
    print(f"BPM: {chart['bpm']}")
    print(f"Duration: {chart['duration']}s")
    print(f"Notes: {len(chart['notes'])}")
    print("="*50)

    # Print first 10 notes as preview
    print("\nFirst 10 notes:")
    for time, lane in chart['notes'][:10]:
        lane_names = ['LEFT', 'CENTER', 'RIGHT']
        print(f"  {time:6.2f}s - {lane_names[lane]}")
