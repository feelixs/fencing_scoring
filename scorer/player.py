from datetime import timedelta, datetime
from typing import Optional, Tuple
from scorer.settings import secBeforeContDmg


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

    def apply_continuous_damage(self, last_state_tuple, time_delta: timedelta, current_time: datetime, last_state_change_times: Optional[Tuple[datetime, datetime]]):
        """Applies continuous damage based on the individual player states *during* the time delta."""
        if last_state_tuple is None:
            return False  # Cannot apply damage if previous state is unknown

        if last_state_change_times is None:
            time_last_change_left, time_last_change_right = None, None
        else:
            time_last_change_left, time_last_change_right = last_state_change_times

        hp_changed = False
        damage_increment = time_delta.total_seconds() * 1000 * self.settings['hit_dmg_per_ms']
        last_left, last_right = last_state_tuple

        # If Left player was hitting opponent, damage Right player
        if last_left == "HITTING_OPPONENT":
            if time_last_change_left is not None:
                if (current_time - time_last_change_left).total_seconds() < secBeforeContDmg:
                    return False
            else:
                print("WARNING: time_last_change_left was None")
            if self.right_hp > 0:
                self.right_hp = max(0, self.right_hp - damage_increment)
                hp_changed = True

        # If Right player was hitting opponent, damage Left player
        if last_right == "HITTING_OPPONENT":
            if time_last_change_right is not None:
                if (current_time - time_last_change_right).total_seconds() < secBeforeContDmg:
                    return False
            else:
                print("WARNING: time_last_change_right was None")
            if self.left_hp > 0:
                self.left_hp = max(0, self.left_hp - damage_increment)
                hp_changed = True

        return hp_changed

    @staticmethod
    def check_one_time_damage_debounce(cur_states, last_states, l_debounce_valid, r_debounce_valid) -> [bool, bool]:
        left_status, right_status = cur_states

        valid_hits = [False, False]
        if l_debounce_valid or r_debounce_valid:
            # Determine score messages based on transitions *before* applying damage
            last_left, last_right = last_states if last_states else (None, None)
            if l_debounce_valid:
                # Check for transitions that indicate a score
                if left_status == "HITTING_OPPONENT" and last_left != "HITTING_OPPONENT":
                    valid_hits[0] = True
                if left_status == "HITTING_SELF" and last_left != "HITTING_SELF":
                    valid_hits[0] = True  # self hit for left -> left is still doing the action

            if r_debounce_valid:
                if right_status == "HITTING_OPPONENT" and last_right != "HITTING_OPPONENT":
                    valid_hits[1] = True
                if right_status == "HITTING_SELF" and last_right != "HITTING_SELF":
                    valid_hits[1] = True

        return valid_hits


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
