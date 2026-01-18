# Song data for rhythm game
# Each song has:
#   - name: Display name
#   - file: Audio file path (relative to rythymgame folder)
#   - bpm: Starting BPM (for reference)
#   - notes: List of (time_in_seconds, lane) tuples
#            lane: 0=left (red), 1=center (green), 2=right (blue)

SONGS = {
    "hall_of_the_mountain_king": {
        "name": "In the Hall of the Mountain King",
        "file": "kevin-macleod-hall-of-the-mountain-king.mp3",
        "bpm": 80,  # Starting BPM, accelerates throughout
        "notes": [
            # Opening - slow and mysterious (BPM ~80)
            # Main theme: D E F G E - C - D pattern
            (2.0, 1),    # First note
            (2.75, 0),
            (3.5, 1),
            (4.25, 2),
            (5.0, 1),
            (5.75, 0),
            (6.5, 1),

            # Theme repeat
            (7.5, 1),
            (8.25, 0),
            (9.0, 1),
            (9.75, 2),
            (10.5, 1),
            (11.25, 0),
            (12.0, 1),

            # Building up slightly
            (13.0, 2),
            (13.7, 1),
            (14.4, 0),
            (15.1, 1),
            (15.8, 2),
            (16.5, 1),
            (17.2, 0),

            # Theme again - getting faster
            (18.0, 1),
            (18.6, 0),
            (19.2, 1),
            (19.8, 2),
            (20.4, 1),
            (21.0, 0),
            (21.6, 1),

            # More intensity
            (22.2, 2),
            (22.8, 1),
            (23.4, 0),
            (24.0, 1),
            (24.6, 2),
            (25.2, 1),
            (25.8, 0),

            # Accelerating section
            (26.4, 1),
            (26.9, 0),
            (27.4, 1),
            (27.9, 2),
            (28.4, 1),
            (28.9, 0),
            (29.4, 1),

            # Double notes start appearing
            (30.0, 0),
            (30.0, 2),  # Simultaneous!
            (30.5, 1),
            (31.0, 0),
            (31.5, 2),
            (32.0, 1),
            (32.5, 0),
            (32.5, 2),  # Simultaneous!

            # Getting faster
            (33.0, 1),
            (33.4, 0),
            (33.8, 1),
            (34.2, 2),
            (34.6, 1),
            (35.0, 0),
            (35.4, 1),
            (35.8, 2),

            # More double notes
            (36.2, 0),
            (36.2, 2),
            (36.6, 1),
            (37.0, 0),
            (37.4, 1),
            (37.8, 2),
            (38.2, 1),
            (38.6, 0),

            # Really picking up speed now
            (39.0, 1),
            (39.35, 2),
            (39.7, 1),
            (40.05, 0),
            (40.4, 1),
            (40.75, 2),
            (41.1, 1),
            (41.45, 0),

            # Intense section
            (41.8, 0),
            (41.8, 2),
            (42.15, 1),
            (42.5, 0),
            (42.85, 2),
            (43.2, 1),
            (43.55, 0),
            (43.9, 2),

            # Even faster
            (44.2, 1),
            (44.5, 0),
            (44.8, 1),
            (45.1, 2),
            (45.4, 1),
            (45.7, 0),
            (46.0, 1),
            (46.3, 2),

            # Rapid fire section
            (46.6, 0),
            (46.85, 1),
            (47.1, 2),
            (47.35, 1),
            (47.6, 0),
            (47.85, 1),
            (48.1, 2),
            (48.35, 1),

            # More chaos
            (48.6, 0),
            (48.6, 2),
            (48.85, 1),
            (49.1, 0),
            (49.35, 2),
            (49.6, 1),
            (49.85, 0),
            (50.1, 2),

            # Building to climax
            (50.35, 1),
            (50.55, 0),
            (50.75, 1),
            (50.95, 2),
            (51.15, 1),
            (51.35, 0),
            (51.55, 1),
            (51.75, 2),

            # Very fast
            (51.95, 0),
            (52.15, 1),
            (52.35, 2),
            (52.55, 1),
            (52.75, 0),
            (52.95, 1),
            (53.15, 2),
            (53.35, 1),

            # Triple notes!
            (53.55, 0),
            (53.55, 1),
            (53.55, 2),
            (53.8, 1),
            (54.05, 0),
            (54.3, 2),
            (54.55, 1),
            (54.8, 0),

            # Frantic
            (55.0, 2),
            (55.2, 1),
            (55.4, 0),
            (55.6, 1),
            (55.8, 2),
            (56.0, 1),
            (56.2, 0),
            (56.4, 1),

            # More triples
            (56.6, 0),
            (56.6, 1),
            (56.6, 2),
            (56.85, 1),
            (57.1, 0),
            (57.35, 2),
            (57.6, 1),
            (57.85, 0),

            # Climax approach
            (58.05, 2),
            (58.25, 1),
            (58.45, 0),
            (58.65, 1),
            (58.85, 2),
            (59.05, 1),
            (59.25, 0),
            (59.45, 2),

            # Maximum speed
            (59.6, 1),
            (59.75, 0),
            (59.9, 1),
            (60.05, 2),
            (60.2, 1),
            (60.35, 0),
            (60.5, 1),
            (60.65, 2),

            # Final burst
            (60.8, 0),
            (60.8, 1),
            (60.8, 2),
            (61.0, 1),
            (61.2, 0),
            (61.2, 2),
            (61.4, 1),
            (61.6, 0),
            (61.6, 1),
            (61.6, 2),

            # Grand finale
            (61.9, 0),
            (61.9, 1),
            (61.9, 2),
            (62.2, 0),
            (62.2, 1),
            (62.2, 2),
        ]
    }
}

def get_song(song_id):
    """Get song data by ID"""
    return SONGS.get(song_id)

def get_song_list():
    """Get list of all available songs"""
    return [(song_id, data["name"]) for song_id, data in SONGS.items()]
