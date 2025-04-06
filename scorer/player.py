from datetime import timedelta


class ScoringManager:
    """Manages player HP and applies damage based on game rules."""

    def __init__(self, settings):
        self.settings = settings
        self.left_hp = self.settings['max_hp']
        self.right_hp = self.settings['max_hp']

    @staticmethod
    def get_score_message(current_state: str) -> str:
        if current_state == "LEFT_GOT_HIT":
            return "*** SCORE: LEFT PLAYER HIT ***"
        elif current_state == "RIGHT_GOT_HIT":
            return "*** SCORE: RIGHT PLAYER HIT ***"
        elif current_state == "LEFT_HIT_SELF":
            return "*** SCORE: LEFT SELF-HIT ***"
        elif current_state == "RIGHT_SELF_HIT":
            return "*** SCORE: RIGHT SELF-HIT ***"
        elif current_state == "BOTH_HITTING":
            return "*** SCORE: BOTH HIT ***"
        return "*** SCORE: UNKNOWN STATE ***"

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

    def apply_continuous_damage(self, state, time_delta: timedelta):
        """Applies continuous damage based on the state during the time delta."""
        hp_changed = False
        damage_increment = time_delta.total_seconds() * 1000 * self.settings['hit_dmg_per_ms']

        if state == "LEFT_GOT_HIT" or state == "BOTH_HITTING":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - damage_increment)
                hp_changed = True
        if state == "RIGHT_GOT_HIT" or state == "BOTH_HITTING":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - damage_increment)
                hp_changed = True
        return hp_changed

    def apply_one_time_damage(self, current_state, last_reported_state):
        """Applies one-time damage based on state transitions."""
        hp_changed = False
        hit_dmg = self.settings['hit_dmg']
        hit_dmg_self = self.settings['hit_dmg_self']

        if current_state == "LEFT_GOT_HIT":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - hit_dmg)
                hp_changed = True
        elif current_state == "RIGHT_GOT_HIT":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - hit_dmg)
                hp_changed = True
        elif current_state == "LEFT_HIT_SELF":
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - hit_dmg_self)
                hp_changed = True
        elif current_state == "RIGHT_SELF_HIT":
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - hit_dmg_self)
                hp_changed = True
        elif current_state == "BOTH_HITTING":
            # Apply damage selectively based on the previous state
            if last_reported_state != "RIGHT_GOT_HIT":  # Left player scored (or both from neutral)
                if self.left_hp > 0:
                    self.left_hp = max(0, self.left_hp - hit_dmg)
                    hp_changed = True
            if last_reported_state != "LEFT_GOT_HIT":  # Right player scored (or both from neutral)
                if self.right_hp > 0:
                    self.right_hp = max(0, self.right_hp - hit_dmg)
                    # If both changed, hp_changed is already True or becomes True here
                    hp_changed = True
        return hp_changed
