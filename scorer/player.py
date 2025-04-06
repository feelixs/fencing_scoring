from datetime import timedelta


class ScoringManager:
    """Manages player HP and applies damage based on game rules."""

    def __init__(self, settings):
        self.settings = settings
        self.left_hp = self.settings['max_hp']
        self.right_hp = self.settings['max_hp']

    # Removed get_score_message - scoring messages handled in GUI based on transitions

    def update_settings(self, new_settings):
        """Updates the game settings."""
        self.settings = new_settings
        # Optionally, you might want to validate or adjust HP if max_hp changes mid-game
        # For now, we assume reset happens after settings change.

    def reset(self):
        """Resets both players' HP to the maximum."""
        self.left_hp = self.settings['max_hp']
        self.right_hp = self.settings['max_hp']

    def get_hp(self):
        """Returns the current HP of both players."""
        return self.left_hp, self.right_hp

    def apply_continuous_damage(self, last_state_tuple, time_delta: timedelta):
        """Applies continuous damage based on the individual player states *during* the time delta."""
        if last_state_tuple is None:
            return False # Cannot apply damage if previous state is unknown

        hp_changed = False
        damage_increment = time_delta.total_seconds() * 1000 * self.settings['hit_dmg_per_ms']
        last_left, last_right = last_state_tuple

        # If Left player was hitting opponent, damage Right player
        if last_left == "HITTING_OPPONENT":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - damage_increment)
                hp_changed = True

        # If Right player was hitting opponent, damage Left player
        if last_right == "HITTING_OPPONENT":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - damage_increment)
                hp_changed = True # Will be True if either condition met

        return hp_changed

    def apply_one_time_damage(self, last_state_tuple, current_state_tuple):
        """Applies one-time damage based on *transitions* into hitting states."""
        if last_state_tuple is None or current_state_tuple is None:
             return False # Cannot determine transitions without both states

        hp_changed = False
        hit_dmg = self.settings['hit_dmg']
        hit_dmg_self = self.settings['hit_dmg_self']
        last_left, last_right = last_state_tuple
        current_left, current_right = current_state_tuple

        # --- Check Transitions for One-Time Damage ---

        # Left player starts hitting opponent
        if current_left == "HITTING_OPPONENT" and last_left != "HITTING_OPPONENT":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - hit_dmg)
                hp_changed = True

        # Right player starts hitting opponent
        if current_right == "HITTING_OPPONENT" and last_right != "HITTING_OPPONENT":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - hit_dmg)
                hp_changed = True

        # Left player starts hitting self
        if current_left == "HITTING_SELF" and last_left != "HITTING_SELF":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - hit_dmg_self)
                hp_changed = True

        # Right player starts hitting self
        if current_right == "HITTING_SELF" and last_right != "HITTING_SELF":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - hit_dmg_self)
                hp_changed = True

        # Note: WEAPONS_HIT state isn't explicitly handled for damage here,
        # but transitions involving it might trigger opponent/self hits if mapped that way.

        return hp_changed
