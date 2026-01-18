# Games for Large TV with IR Touch Frame

## About the Setup

This project uses a large TV display with an infrared (IR) touch frame overlay. IR frames use a grid of infrared LEDs and sensors around the display edges to detect touch points when objects break the beams.

### IR Frame Characteristics
- **Multi-touch support**: Most frames support 6-20+ simultaneous touch points
- **Works with any object**: Fingers, styluses, or any opaque object
- **No pressure sensitivity**: Binary touch detection only
- **Edge detection**: Touch is detected at the frame edge, not the screen surface
- **Large interaction area**: Great for multiplayer and collaborative games

### Design Considerations
- **Touch targets should be large**: Minimum 50-80px for comfortable interaction on big screens
- **Account for parallax**: Players may stand at angles, so avoid precision requirements at screen edges
- **Multi-player friendly**: Large screens invite multiple simultaneous players
- **Standing play**: Players will likely be standing, so keep interactive elements reachable
- **Visual feedback is essential**: Confirm every touch with immediate visual response

---

## Game Ideas

### Currently Implemented
- **Hungry Hungry Hippos** (`hippos.py`) - Competitive collection game
- **Whack-a-Mole** (`mole.py`) - Reaction-based tapping game
- **Drawing App** (`draw.py`) - Collaborative canvas
- **Rhythm Game** (`rythymgame/`) - Music-based timing game

### Competitive Games (2-4 Players)

#### Air Hockey
- Split screen into zones for each player
- Physics-based puck movement
- Each player defends their goal while trying to score on others
- Perfect for multi-touch: each player controls their paddle simultaneously

#### Territory Control
- Players start in corners and expand by tapping/dragging
- Territories can be captured by surrounding opponent areas
- Fast-paced land-grab with simple mechanics
- Color-coded zones for each player

#### Button Bash Race
- Sequential buttons appear in each player's zone
- First to tap all their buttons wins
- Variations: memory sequence, simon-says patterns

#### Fruit Ninja Style
- Objects fly across screen, players slice by swiping
- Competitive: each player has a scoring zone
- Avoid bombs/penalties
- Combo system for quick successive hits

### Cooperative Games

#### Tower Defense
- Players work together to place and upgrade towers
- Drag-and-drop tower placement
- Tap to activate special abilities
- Different roles: builder, upgrader, ability user

#### Infection/Zombie Survival
- One player is "infected", tries to tag others' avatars
- Safe zones appear temporarily
- Power-ups to collect
- Last survivor or team-based scoring

#### Collaborative Puzzle
- Large jigsaw or tangram puzzles
- Players can grab and rotate pieces simultaneously
- Time challenge modes
- Scaling difficulty

### Reaction Games

#### Color Match Panic
- Colored circles appear randomly across screen
- Players must tap circles matching the current target color
- Speed increases over time
- Wrong taps add penalties

#### Pattern Memory
- Simon-says style with screen-wide patterns
- Multiple players must tap the correct sequence together
- Cooperative: all must succeed
- Competitive: individual scoring

#### Hot Potato
- Virtual object bounces between player zones
- Must tap to "catch" and redirect within time limit
- Miss = point against you
- Speed increases each round

### Party Games

#### Trivia Touch
- Questions displayed centrally
- Answer zones around the edges
- First to touch correct answer scores
- Categories and difficulty progression

#### Drawing Telephone
- One player draws a prompt
- Others guess by selecting from options
- Rotate through players
- Hilarious misinterpretations

#### Music Mixer
- Each screen zone controls different instrument/loop
- Players collaborate to create music
- Record and playback sessions
- Visual feedback synced to audio

---

## Technical Notes

### Kivy Framework
All apps use Kivy for Python-based touch input handling. Kivy provides:
- Native multi-touch support
- Easy fullscreen deployment
- Cross-platform compatibility
- Built-in gesture recognition

### Performance Tips
- Use object pooling for frequently spawned elements
- Limit particle effects on older hardware
- Test with actual IR frame - USB latency varies by device
- Consider 60fps target for smooth interactions

### Input Handling
```python
# Basic multi-touch in Kivy
def on_touch_down(self, touch):
    # touch.uid - unique ID for this touch point
    # touch.x, touch.y - coordinates
    # Can track multiple simultaneous touches
    pass
```

---

## Future Ideas
- [ ] Leaderboard system across games
- [ ] Player profiles with avatars
- [ ] Tournament/bracket mode for parties
- [ ] Sound effects and music library
- [ ] Accessibility options (colorblind modes, larger targets)
