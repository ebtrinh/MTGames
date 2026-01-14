from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.clock import Clock
from kivy.config import Config
import random

# Configure for touchscreen multi-touch
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'width', '1000')
Config.set('graphics', 'height', '700')

# Ensure Windows touch input is enabled
Config.set('input', 'wm_touch', 'wm_touch')
Config.set('input', 'wm_pen', 'wm_pen')


class Note(Widget):
    """A falling note that the player must hit"""
    def __init__(self, lane, player, speed, **kwargs):
        super(Note, self).__init__(**kwargs)
        self.lane = lane
        self.player = player
        self.speed = speed
        self.active = True
        self.radius = 40
        self.size = (self.radius * 2, self.radius * 2)
        self.bind(pos=self.update_canvas)
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        if not self.active:
            return
        with self.canvas:
            colors = [(1, 0.3, 0.3, 1), (0.3, 1, 0.3, 1), (0.3, 0.3, 1, 1)]
            Color(*colors[self.lane])
            Ellipse(pos=self.pos, size=self.size)
            Color(1, 1, 1, 0.3)
            inner_margin = self.radius * 0.3
            Ellipse(
                pos=(self.x + inner_margin, self.y + inner_margin),
                size=(self.width - inner_margin * 2, self.height - inner_margin * 2)
            )

    def move(self, dt):
        if self.active:
            self.y -= self.speed * dt

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
            if self.game.game_active:
                self.game.check_hit(self.player, self.lane)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.ud.get('button') == self:
            self.set_pressed(False)
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
        self.note_speed = 250
        self.update_timer = None

        self.total_notes = 30
        self.notes_spawned = 0
        self.spawn_timer = None
        self.spawn_interval = 0.8
        self.game_ended = False

        self.player_labels = []

        # Bind to size changes to update layout
        self.bind(size=self.on_size_change, pos=self.on_size_change)

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

    def start_game(self):
        if not self.game_started:
            return

        self.game_active = True
        self.scores = [0] * self.num_players
        self.combos = [0] * self.num_players
        self.notes_spawned = 0
        self.game_ended = False

        for note in self.notes:
            self.remove_widget(note)
        self.notes = []

        for popup in self.score_popups:
            self.remove_widget(popup)
        self.score_popups = []

        self.spawn_timer = Clock.schedule_interval(self.spawn_note, self.spawn_interval)
        self.update_timer = Clock.schedule_interval(self.update_game, 1/60.0)

    def stop_game(self):
        self.game_active = False
        if self.spawn_timer:
            self.spawn_timer.cancel()
            self.spawn_timer = None
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None

    def spawn_note(self, dt=None):
        if not self.game_active:
            return

        if self.notes_spawned >= self.total_notes:
            if self.spawn_timer:
                self.spawn_timer.cancel()
                self.spawn_timer = None
            return

        # Generate same lane(s) for all players
        lane = random.randint(0, 2)
        # 25% chance to spawn a second note in a different lane
        lanes = [lane]
        if random.random() < 0.25:
            other_lanes = [l for l in range(3) if l != lane]
            lanes.append(random.choice(other_lanes))

        for p in range(self.num_players):
            for current_lane in lanes:
                note = Note(lane=current_lane, player=p, speed=self.note_speed)
                note.radius = 40
                note.size = (note.radius * 2, note.radius * 2)

                btn = self.target_buttons[p][current_lane]
                note.center_x = btn.center_x
                note.y = self.height + 10

                self.notes.append(note)
                self.add_widget(note)

        self.notes_spawned += 1

    def update_game(self, dt):
        if not self.game_active:
            return

        for note in self.notes[:]:
            note.move(dt)

            # Update note x position to follow button (in case of resize)
            if note.active and note.player < len(self.target_buttons):
                btn = self.target_buttons[note.player][note.lane]
                note.center_x = btn.center_x

            if note.active and note.y + note.height < 0:
                note.deactivate()
                self.combos[note.player] = 0
                btn = self.target_buttons[note.player][note.lane]
                self.show_score_popup("MISS", (0.5, 0.5, 0.5, 1), btn.center_x, 120)
                # Remove missed note immediately
                self.notes.remove(note)
                self.remove_widget(note)

        if self.notes_spawned >= self.total_notes and len(self.notes) == 0 and not self.game_ended:
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
                distance = abs(note.center_y - target_center_y)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_note = note

        if closest_note:
            hit_range = target_btn.radius + closest_note.radius

            if closest_distance <= hit_range:
                # Remove the note immediately
                closest_note.deactivate()
                if closest_note in self.notes:
                    self.notes.remove(closest_note)
                    self.remove_widget(closest_note)

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

                self.combos[player] += 1
                combo_bonus = min(self.combos[player], 10)
                total_points = points + (points * combo_bonus // 10)
                self.scores[player] += total_points

                popup_text = f"{rating}\n+{total_points}"
                self.show_score_popup(popup_text, color, closest_note.center_x, closest_note.center_y)

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

    def update_ui_positions(self, *args):
        self.player_select_label.center_x = self.width / 2
        self.player_select_label.center_y = self.height / 2 + 40

        total_btn_width = len(self.player_buttons) * 100 + (len(self.player_buttons) - 1) * 10
        start_x = (self.width - total_btn_width) / 2
        for i, btn in enumerate(self.player_buttons):
            btn.x = start_x + i * 110
            btn.center_y = self.height / 2 - 20

        self.start_button.center_x = self.width / 2
        self.start_button.center_y = self.height / 2

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

        self.start_button.opacity = 1
        self.start_button.disabled = False

        self.update_ui_positions()

    def update_ui(self, dt):
        if not self.game.game_started:
            return

        for i, label in enumerate(self.score_labels):
            if i < len(self.game.scores):
                label.text = f'P{i + 1}: {self.game.scores[i]}'

        if self.game.game_ended:
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
        else:
            self.winner_label.opacity = 0
            self.start_button.opacity = 0
            self.start_button.disabled = True
            self.hide_leaderboard()
            self.game.start_game()

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

        # Hide leaderboard
        self.hide_leaderboard()
        self.winner_label.opacity = 0

        # Hide start button
        self.start_button.opacity = 0
        self.start_button.disabled = True
        self.start_button.text = 'Start'

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

        self.update_ui_positions()


class RhythmApp(App):
    def build(self):
        return RhythmGameApp()


if __name__ == '__main__':
    RhythmApp().run()
