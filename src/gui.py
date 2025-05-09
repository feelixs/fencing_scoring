import time
import tkinter as tk
from tkinter import ttk, font as tkFont
from threading import Thread, Event
from datetime import datetime, timedelta
import queue
from playsound import playsound
from src.player import ScoringManager
from src.settings import (
    GLOBAL_HIT_DMG,
    GLOBAL_HIT_DMG_SELF,
    GLOBAL_HIT_DMG_PER_MILLISECOND,
    MAX_HP,
    DEBOUNCE_TIME_SEC,
    secBeforeContDmg,
)


class FencingGui:
    def __init__(self, find_device, detect_hit_state):
        # find_device should return the VSM device, or None if it's not found
        self.find_device = find_device

        self.output_queue = queue.Queue()
        self.stop_event = Event()

        self._playing_sound = False  # configure so we only play 1 sound at a time (no overlapping sound effects)
        self._left_side_sounds_played = {'75': False, '50': False, '25': False}
        self._right_side_sounds_played = {'75': False, '50': False, '25': False}

        self.root = tk.Tk()
        self.root.title("Fencing Hit Detector")
        self.root.attributes('-fullscreen', True)
        self.root.config(bg="black")

        self.detect_hit_state = detect_hit_state

        self.style = ttk.Style(self.root)

        self._label_font = tkFont.Font(family="Helvetica", size=18)
        self._status_font = tkFont.Font(family="Helvetica", size=16)
        self._entry_font = tkFont.Font(family="Helvetica", size=12)
        self._button_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
        self._winner_font = tkFont.Font(family="Helvetica", size=48, weight="bold")

        self.settings = {
            'hit_dmg': GLOBAL_HIT_DMG,
            'hit_dmg_self': GLOBAL_HIT_DMG_SELF,
            'hit_dmg_per_ms': GLOBAL_HIT_DMG_PER_MILLISECOND,
            'max_hp': MAX_HP,
            'debounce_time': DEBOUNCE_TIME_SEC,
            'sec_before_cont_dmg': secBeforeContDmg
        }
        self.scoring_manager = ScoringManager(self.settings)

        self.current_device = None
        self.device_thread = self.start_device_thread()

        self._configure_styles()

        self.root.grid_columnconfigure(0, weight=1, uniform="group1")
        self.root.grid_columnconfigure(1, weight=1, uniform="group1")
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)

        self.left_hp_zero = False
        self.right_hp_zero = False

        self.left_shaking = False
        self.right_shaking = False
        self.shake_offset = 0
        self.shake_direction = 1
        self.shake_magnitude = 5
        self.left_bar_original_padx = (20, 20)
        self.right_bar_original_padx = (20, 20)

        self.winner_frame = tk.Frame(self.root, bg="black", borderwidth=4, relief="raised")
        self.winner_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.25)
        self.winner_frame.lift()
        self.winner_frame.place_forget()

        self.winner_label = tk.Label(
            self.winner_frame,
            text="",
            font=self._winner_font,
            fg="white",
            bg="black",
            padx=20,
            pady=20
        )
        self.winner_label.pack(expand=True, fill="both")

        # Initialize labels with starting percentage
        self.left_label = tk.Label(self.root, text="LEFT PLAYER - 100%", font=self._label_font, bg="black", fg="white")
        self.left_label.grid(row=0, column=0, pady=(20, 5), sticky="ew")

        self.left_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=800,
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],
            style="GreenHP.Vertical.TProgressbar"
        )
        self.left_hp_bar.grid(row=1, column=0, padx=self.left_bar_original_padx, pady=20, sticky="ns")

        # Initialize labels with starting percentage
        self.right_label = tk.Label(self.root, text="RIGHT PLAYER - 100%", font=self._label_font, bg="black", fg="white")
        self.right_label.grid(row=0, column=1, pady=(20, 5), sticky="ew")

        self.right_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=800,
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],
            style="GreenHP.Vertical.TProgressbar"
        )
        self.right_hp_bar.grid(row=1, column=1, padx=self.right_bar_original_padx, pady=20, sticky="ns")

        self.settings_frame = tk.Frame(self.root, bg="black") # Removed padding argument
        self.settings_frame.grid(row=2, column=1, sticky="nsew", padx=(10, 20), pady=10)
        self.status_frame = tk.Frame(self.root, bg="black")
        self.status_frame.grid(row=2, column=0, sticky="nsew", padx=(20, 10), pady=10)
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_rowconfigure(0, weight=1)

        self.status_label = tk.Label(
            master=self.status_frame,
            text="Initializing...",
            font=self._status_font,
            justify=tk.CENTER,
            anchor=tk.CENTER,
            wraplength=600,  # Adjust wrap length based on potentially smaller area
            bg="black",       # Set background
            fg="white"        # Set text color
        )
        self.status_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.hit_dmg_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.hit_dmg_entry.insert(0, str(self.settings['hit_dmg']))
        self.hit_dmg_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.hit_dmg_self_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.hit_dmg_self_entry.insert(0, str(self.settings['hit_dmg_self']))
        self.hit_dmg_self_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.hit_dmg_per_ms_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.hit_dmg_per_ms_entry.insert(0, str(self.settings['hit_dmg_per_ms']))
        self.hit_dmg_per_ms_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.max_hp_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.max_hp_entry.insert(0, str(self.settings['max_hp']))
        self.max_hp_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.debounce_time_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.debounce_time_entry.insert(0, str(self.settings['debounce_time']))
        self.debounce_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        self.sec_before_cont_dmg_entry = ttk.Entry(self.settings_frame, width=8, font=self._entry_font)
        self.sec_before_cont_dmg_entry.insert(0, str(self.settings['sec_before_cont_dmg']))
        self.sec_before_cont_dmg_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.style.configure(style="Accent.TButton", font=self._button_font)

        self.reset_button = ttk.Button(
            master=self.settings_frame,
            text="APPLY & RESET",
            command=self.apply_settings_and_reset,
            style="Accent.TButton"
        )
        self.reset_button.grid(row=3, column=2, columnspan=2, padx=20, pady=5, sticky="ew")

        self._setup_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _schedule_sound_for_hp_intervals(self, new_hp, max_hp, side: str):
        percentage = 100 * (new_hp / max_hp)
        thresholds = [
            '75',
            #'50',
            '25'
        ]
        sounds_played = self._left_side_sounds_played if side == "left" else self._right_side_sounds_played
        for x in thresholds:
            if percentage < int(x) and not sounds_played[x]:
                playsound(f"sounds/left_damage.mp3" if side == "left" else f"sounds/right_damage.mp3", block=False)
                sounds_played[x] = True
                break  # Play only one sound per drop

    @staticmethod
    def _get_hp_style(hp, max_hp):
        """Determines the ttk style name based on HP percentage."""
        if max_hp <= 0:  # Avoid division by zero and handle edge case
            return "RedHP.Vertical.TProgressbar"
        percentage = (hp / max_hp) * 100
        if percentage > 75:
            return "GreenHP.Vertical.TProgressbar"
        elif percentage > 50:
            return "YellowHP.Vertical.TProgressbar"
        elif percentage > 25:
            return "OrangeHP.Vertical.TProgressbar"
        else:
            return "RedHP.Vertical.TProgressbar"

    def run(self):
        # Start the GUI update loop & Tkinter main loop
        self.update_gui()
        self._animate_shake()
        self.root.mainloop()

    def _animate_shake(self):
        """Periodically updates the position of bars that should be shaking."""
        # Calculate the next offset
        self.shake_offset += self.shake_direction * 2 # Adjust step size as needed
        if abs(self.shake_offset) >= self.shake_magnitude:
            self.shake_offset = self.shake_magnitude * self.shake_direction  # Clamp to magnitude
            self.shake_direction *= -1  # Reverse direction

        # Apply offset to left bar if shaking
        if self.left_shaking:
            current_left_padx = (self.left_bar_original_padx[0] + self.shake_offset, self.left_bar_original_padx[1])
            self.left_hp_bar.grid_configure(padx=current_left_padx)
        else:
            # Ensure bar is back to original position if not shaking
            self.left_hp_bar.grid_configure(padx=self.left_bar_original_padx)

        # Apply offset to right bar if shaking
        if self.right_shaking:
            # Use negative offset for the right bar if desired, or same offset
            current_right_padx = (self.right_bar_original_padx[0] + self.shake_offset, self.right_bar_original_padx[1])
            self.right_hp_bar.grid_configure(padx=current_right_padx)
        else:
            # Ensure bar is back to original position if not shaking
            self.right_hp_bar.grid_configure(padx=self.right_bar_original_padx)

        # Schedule the next animation frame
        self.root.after(30, self._animate_shake)  # ~33 FPS for animation

    def _configure_styles(self):
        # Calculate desired thickness based on screen width and padding
        # Need to update geometry first to get accurate width
        self.root.update_idletasks()
        screen_width = self.root.winfo_width()  # Use actual window width after layout
        # Bars are in columns 0 and 1, each with padx=20. Total padding = 40.
        # Reduce thickness: Use a smaller fraction and minimum
        bar_thickness = max(30, (screen_width - 40) // 4)  # Ensure a minimum thickness of 30

        # Define the base layout for all HP bars
        base_style_layout = [
            ('Vertical.Progressbar.trough', {
                'children': [('Vertical.Progressbar.pbar', {'side': 'bottom', 'sticky': 'ns'})],
                'sticky': 'nswe'
            })
        ]

        # Define the style names and corresponding colors
        style_color_map = {
            "GreenHP.Vertical.TProgressbar": "green",
            "YellowHP.Vertical.TProgressbar": "yellow",
            "OrangeHP.Vertical.TProgressbar": "orange",
            "RedHP.Vertical.TProgressbar": "red"
        }

        for name, color in style_color_map.items():
            # Apply the base layout to each style
            self.style.layout(name, base_style_layout)
            # Configure the specific colors and thickness for each style
            self.style.configure(
                name,
                troughcolor='black',  # Change trough color to black
                background=color,
                thickness=bar_thickness
            )

    def _setup_labels(self):
        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Starting HP:",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=1, column=2, padx=5, pady=5, sticky="e")

        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Debounce Time (s):",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        
        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Cont. Damage Delay (s):",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=3, column=0, padx=5, pady=5, sticky="e")

        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Continuous Damage/ms:",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=1, column=0, padx=5, pady=5, sticky="e")

        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Self Hit Damage:",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=0, column=2, padx=5, pady=5, sticky="e")

        # Use tk.Label and set bg/fg
        tk.Label(
            master=self.settings_frame,
            text="Initial Hit Damage:",
            font=self._entry_font,
            bg="black", fg="white"
        ).grid(row=0, column=0, padx=5, pady=5, sticky="e")

    def apply_settings_and_reset(self):
        print("Applying settings and resetting game...")
        try:
            new_settings = {
                'hit_dmg': float(self.hit_dmg_entry.get()),
                'hit_dmg_self': float(self.hit_dmg_self_entry.get()),
                'hit_dmg_per_ms': float(self.hit_dmg_per_ms_entry.get()),
                'max_hp': float(self.max_hp_entry.get()),
                'debounce_time': float(self.debounce_time_entry.get()),
                'sec_before_cont_dmg': float(self.sec_before_cont_dmg_entry.get())
            }

            # Update progress bars to use new max HP
            self.left_hp_bar['maximum'] = new_settings['max_hp']
            self.right_hp_bar['maximum'] = new_settings['max_hp']

            # Update settings in ScoringManager and reset HP
            self.scoring_manager.update_settings(new_settings)
            self.scoring_manager.reset()

            # Reset all game state flags when game is reset
            self.left_hp_zero = False
            self.right_hp_zero = False
            
            # Reset sound interval flags
            self._left_side_sounds_played = {'75': False, '50': False, '25': False}
            self._right_side_sounds_played = {'75': False, '50': False, '25': False}

            # Hide winner display
            self.winner_frame.place_forget()

            # Restart the device thread (it will use the updated self.scoring_manager)
            self.device_thread = self.restart_device_thread(self.device_thread)

            # Trigger an immediate HP update in the GUI based on the reset state
            left_hp, right_hp = self.scoring_manager.get_hp()
            self.output_queue.put({'type': 'health', 'left': left_hp, 'right': right_hp})

            self.stop_event.clear()  # Reset the stop event to allow monitoring again

            # Update status
            self.output_queue.put({'type': 'status', 'message': "Game reset with new settings!"})

        except ValueError:
            self.output_queue.put({'type': 'status', 'message': "Error: Invalid input values."})

    def start_device_thread(self):
        """Finds the device and starts the processing thread."""

        def thread_target():
            vsm_device = self.find_device()
            if vsm_device:
                return self.process_vsm_data(vsm_device)  # this is a blocking call (while loop)
            else:
                self.output_queue.put({'type': 'status', 'message': "VSM device not found."})
                self.output_queue.put({'type': 'status', 'message': "Check connection/permissions."})

            while not vsm_device:
                time.sleep(1)  # Wait before retrying
                vsm_device = self.find_device()
            return self.process_vsm_data(vsm_device)

        thread = Thread(target=thread_target, daemon=True)
        thread.start()
        return thread

    def restart_device_thread(self, current_thread=None):
        """Stops the current device thread and starts a new one with updated settings."""
        print("Restarting device thread...")
        # 1. Signal the thread to stop
        self.stop_event.set()

        # 2. Explicitly close the current device *before* joining
        #    This helps ensure resources like the pynput listener are released promptly.
        if self.current_device:
            print(f"Closing current device: {self.current_device}")
            try:
                self.current_device.close()
            except Exception as e:
                print(f"Error closing device during restart: {e}")
            self.current_device = None  # Clear the reference

        # 3. Wait for the old thread to terminate
        if current_thread and current_thread.is_alive():
            print("Joining old device thread...")
            current_thread.join(timeout=2.0)  # Increased timeout slightly
            if current_thread.is_alive():
                print("Warning: Old device thread did not terminate cleanly.")

        # 4. Reset the stop event for the new thread
        self.stop_event.clear()
        print("Stop event cleared.")

        # Start a new thread
        return self.start_device_thread()

    def process_vsm_data(self, device):
        """
        Reads data from the VSM device, detects state changes, applies debouncing,
        and puts formatted messages into the output queue.
        Reads data from the VSM device, detects state changes, applies debouncing,
        delegates scoring logic to ScoringManager, and puts formatted messages
        into the output queue. Runs until stop_event is set.
        """
        # Settings are managed by self.scoring_manager
        last_reported_state = (None, None)  # Will store state tuples (left_status, right_status)
        time_last_reported = None  # Initialize to None, set on first valid state
        debounce_time = self.scoring_manager.settings.get('debounce_time', DEBOUNCE_TIME_SEC)
        start_time = datetime.now()
        last_state_change_time_l, last_state_change_time_r = start_time, start_time
        last_loop_time = start_time  # Track time for delta calculation

        # Track last hit time for each player (for proper debouncing)
        last_left_hit_time = datetime.min
        last_right_hit_time = datetime.min

        # Track continuous damage status to only send updates on change
        last_cont_dmg_status = {'left': False, 'right': False}

        # Initial status and health update using ScoringManager
        self.output_queue.put({'type': 'status', 'message': "Monitoring fencing hits..."})
        self.output_queue.put({'type': 'status', 'message': "-" * 30})
        initial_left_hp, initial_right_hp = self.scoring_manager.get_hp()
        self.output_queue.put({'type': 'health', 'left': initial_left_hp, 'right': initial_right_hp})

        try:
            while not self.stop_event.is_set():
                try:
                    current_time = datetime.now()
                    time_delta: timedelta = current_time - last_loop_time
                    hp_changed_continuous = False
                    hp_changed_one_time = False

                    # Read data from the device (with a short timeout to allow checking stop_event)
                    data = device.read(42, timeout_ms=50)

                    if self.stop_event.is_set():
                        # double check after potential blocking read
                        break

                    if data:
                        current_state_tuple = self.detect_hit_state(data)

                        # continuous damage
                        hp_changed_continuous = self.scoring_manager.apply_continuous_damage(
                            last_state_tuple=last_reported_state,
                            time_delta=time_delta,
                            last_state_change_times=(last_state_change_time_l, last_state_change_time_r),
                            current_time=current_time
                        )

                        state_changed = False
                        left_status, right_status = current_state_tuple
                        left_last, right_last = last_reported_state

                        # Detect state changes
                        if left_status != left_last:
                            print(f"Left status changed: {left_last} -> {left_status}")
                            last_state_change_time_l = current_time
                            state_changed = True

                        if right_status != right_last:
                            print(f"Right status changed: {right_last} -> {right_status}")
                            last_state_change_time_r = current_time
                            state_changed = True

                        if state_changed:
                            # Log state change
                            elapsed = (current_time - start_time).total_seconds()
                            status_message = f"[{elapsed:.2f}s] L: {left_status}, R: {right_status}"
                            self.output_queue.put({'type': 'status', 'message': status_message})
                            
                            # Check for new hits with proper debouncing logic
                            left_hit_now = False
                            right_hit_now = False
                            
                            # Check for left player hit transitions
                            if ((left_status == "HITTING_OPPONENT" and left_last != "HITTING_OPPONENT") or 
                                (left_status == "HITTING_SELF" and left_last != "HITTING_SELF")):
                                # Only apply debounce for repeated hits, not the first hit
                                if (current_time - last_left_hit_time).total_seconds() >= debounce_time:
                                    left_hit_now = True
                                    last_left_hit_time = current_time  # Update last hit time
                            
                            # Check for right player hit transitions
                            if ((right_status == "HITTING_OPPONENT" and right_last != "HITTING_OPPONENT") or 
                                (right_status == "HITTING_SELF" and right_last != "HITTING_SELF")):
                                # Only apply debounce for repeated hits, not the first hit
                                if (current_time - last_right_hit_time).total_seconds() >= debounce_time:
                                    right_hit_now = True
                                    last_right_hit_time = current_time  # Update last hit time
                            
                            # Apply one-time damage logic if we have valid hits
                            if left_hit_now or right_hit_now:
                                score_messages = []
                                
                                # Only add messages for hits that passed the debounce check
                                if left_hit_now:
                                    if left_status == "HITTING_OPPONENT":
                                        score_messages.append("*** SCORE: LEFT PLAYER HIT ***")
                                    elif left_status == "HITTING_SELF":
                                        score_messages.append("*** SCORE: LEFT SELF-HIT ***")
                                
                                if right_hit_now:
                                    if right_status == "HITTING_OPPONENT":
                                        score_messages.append("*** SCORE: RIGHT PLAYER HIT ***")
                                    elif right_status == "HITTING_SELF":
                                        score_messages.append("*** SCORE: RIGHT SELF-HIT ***")

                                for msg in score_messages:
                                    self.output_queue.put({'type': 'status', 'message': msg})

                                # Apply one-time damage without using the debounce method
                                hp_changed_one_time = self.scoring_manager.apply_one_time_damage(
                                    last_state_tuple=last_reported_state,
                                    current_state_tuple=current_state_tuple
                                )
                            
                            last_reported_state = current_state_tuple
                            time_last_reported = current_time

                    sec_before_cont_dmg = self.scoring_manager.settings.get('sec_before_cont_dmg', secBeforeContDmg)
                    cont_dmg_delay = timedelta(seconds=sec_before_cont_dmg)

                    # Left takes continuous damage if Right was hitting opponent/weapons continuously
                    left_is_taking_cont_dmg = (
                        last_reported_state[1] in ("HITTING_OPPONENT", "WEAPONS_HIT") and
                        (current_time - last_state_change_time_r) >= cont_dmg_delay
                    )
                    # Right takes continuous damage if Left was hitting opponent/weapons continuously
                    right_is_taking_cont_dmg = (
                        last_reported_state[0] in ("HITTING_OPPONENT", "WEAPONS_HIT") and
                        (current_time - last_state_change_time_l) >= cont_dmg_delay
                    )

                    current_cont_dmg_status = {'left': left_is_taking_cont_dmg, 'right': right_is_taking_cont_dmg}

                    if current_cont_dmg_status != last_cont_dmg_status:
                        self.output_queue.put({'type': 'cont_dmg_status', **current_cont_dmg_status})
                        last_cont_dmg_status = current_cont_dmg_status

                    if hp_changed_continuous or hp_changed_one_time:
                        current_left_hp, current_right_hp = self.scoring_manager.get_hp()
                        self.output_queue.put({'type': 'health', 'left': current_left_hp, 'right': current_right_hp})

                    # Update last loop time for next iteration's delta calculation
                    last_loop_time = current_time
                except IOError as e:
                    # Handle device read error (e.g., device disconnected)
                    self.output_queue.put(
                        {'type': 'status', 'message': f"Device read error: {e}. Attempting to reconnect..."})
                    if device:
                        try:
                            device.close()  # Attempt to close the old device/listener first
                        except Exception as close_err:
                            # Log if closing fails, but continue trying to reconnect
                            print(f"Error closing device during reconnect: {close_err}")
                    self.current_device = None  # Clear the reference in GUI
                    device = None  # Local variable in this function

                    # Attempt to find a new device
                    while not self.stop_event.is_set():
                        new_device = self.find_device()  # Creates a new instance (dummy or real)
                        if new_device:
                            device = new_device
                            self.current_device = device  # Update GUI reference
                            break  # Found a device
                        time.sleep(1)  # Wait a bit before retrying

                    if self.stop_event.is_set():  # Exit if stopped during reconnect attempt
                        break

                    if not device:  # If still no device after trying, exit loop
                        self.output_queue.put(
                            {'type': 'status', 'message': "Failed to reconnect. Stopping monitoring."})
                        break

                    # Device reconnected, restart the loop
                    # Device reconnected, restart the loop
                    time_last_reported = None
                    last_reported_state = (None, None)  # reset these
                    self.output_queue.put({'type': 'status', 'message': "Device reconnected. Resuming monitoring..."})
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.output_queue.put({'type': 'status', 'message': f"Error in device loop: {e}"})
        finally:
            self.output_queue.put({'type': 'status', 'message': "Device monitoring stopped."})
            if device:
                device.close()

    def update_gui(self) -> bool:
        """ Checks the queue for messages and updates the GUI elements. """
        # Get current health to determine if we're still in a winning state
        left_hp, right_hp = self.scoring_manager.get_hp()
        is_winning_state = left_hp <= 0 or right_hp <= 0
        
        # If players have health, it's not a winning state regardless of stop_event
        player_won = self.stop_event.is_set() and is_winning_state
        try:
            while True:  # Process all messages currently in queue
                item = self.output_queue.get_nowait()

                if item['type'] == 'status':
                    message = item['message']
                    # Keep only the last few lines (e.g., 5 lines) for display in status label
                    current_lines = self.status_label.cget("text").split('\n')
                    max_lines = 5
                    new_lines = (current_lines + [message])[-max_lines:]
                    self.status_label.config(text="\n".join(new_lines))

                elif item['type'] == 'cont_dmg_status':
                    # Update shaking state based on continuous damage status
                    self.left_shaking = item.get('left', False)
                    self.right_shaking = item.get('right', False)

                elif item['type'] == 'health':
                    left_hp = item['left']
                    right_hp = item['right']
                    max_hp = self.scoring_manager.settings.get('max_hp', MAX_HP)

                    # Determine the style based on current HP
                    left_style = self._get_hp_style(left_hp, max_hp)
                    right_style = self._get_hp_style(right_hp, max_hp)

                    self._schedule_sound_for_hp_intervals(
                        new_hp=left_hp,
                        max_hp=max_hp,
                        side="left"
                    )
                    self._schedule_sound_for_hp_intervals(
                        new_hp=right_hp,
                        max_hp=max_hp,
                        side="right"
                    )

                    # Update bar values and styles
                    # Calculate percentages
                    left_percent = int((left_hp / max_hp) * 100) if max_hp > 0 else 0
                    right_percent = int((right_hp / max_hp) * 100) if max_hp > 0 else 0

                    # Update labels with percentages
                    self.left_label.config(text=f"LEFT PLAYER - {left_percent}%")
                    self.right_label.config(text=f"RIGHT PLAYER - {right_percent}%")

                    # Update bar values and styles
                    self.left_hp_bar.config(style=left_style)
                    self.right_hp_bar.config(style=right_style)
                    self.left_hp_bar['value'] = left_hp
                    self.right_hp_bar['value'] = right_hp

                    # Play sound and display winner when a player's HP reaches 0
                    if left_hp <= 0 and not self.left_hp_zero: # Check <= 0 for safety
                        self.left_hp_zero = True
                        try:
                            playsound('sounds/gameover.mp3', block=False)
                            self.output_queue.put({'type': 'status', 'message': "*** PLAYER 2: RIGHT WINS ***"})
                            # Show winner message with RIGHT player color (red)
                            self.winner_label.config(text="PLAYER 2: RIGHT WINS", fg="white", bg="red")
                            self.winner_frame.config(bg="red")
                            self.winner_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.25)
                            self.winner_frame.lift()  # Make sure it appears on top
                            player_won = True
                        except Exception as e:
                            print(f"Sound error: {e}")

                    if right_hp <= 0 and not self.right_hp_zero: # Check <= 0 for safety
                        self.right_hp_zero = True
                        try:
                            playsound('sounds/gameover.mp3', block=False)
                            self.output_queue.put({'type': 'status', 'message': "*** PLAYER 1: LEFT WINS ***"})
                            # Show winner message with LEFT player color (green)
                            self.winner_label.config(text="PLAYER 1: LEFT WINS", fg="white", bg="green")
                            self.winner_frame.config(bg="green")
                            self.winner_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.25)
                            self.winner_frame.lift()  # Make sure it appears on top
                            player_won = True
                        except Exception as e:
                            print(f"Sound error: {e}")

                    # Reset the flags if HP is restored
                    if left_hp > 0:
                        self.left_hp_zero = False
                    if right_hp > 0:
                        self.right_hp_zero = False
                self.root.update_idletasks()
        except queue.Empty:
            pass  # No messages currently

        # Only update stop_event if we're in a winning state and it's not already set
        if is_winning_state and not self.stop_event.is_set():
            self.left_shaking = False  # Stop left bar shaking
            self.right_shaking = False  # Stop right bar shaking
            self.stop_event.set()  # Stop the device thread if a player has won
        # If we're not in a winning state but stop_event is set, something might have gone wrong
        elif not is_winning_state and self.stop_event.is_set():
            print("Game state mismatch detected: not a winning state but stop_event is set")
            # We don't clear stop_event here as that should happen in apply_settings_and_reset

        # Schedule the next check
        self.root.after(100, self.update_gui)  # Check every 100ms
        return player_won

    # Function to handle window closing
    def on_closing(self):
        print("Closing application...")
        self.stop_event.set()  # Signal the processing thread to stop

        # Explicitly close the device if it exists
        if self.current_device:
            print("Closing device on exit...")
            try:
                self.current_device.close()
            except Exception as e:
                print(f"Error closing device on exit: {e}")
            self.current_device = None

        # Wait for the thread to finish
        if self.device_thread and self.device_thread.is_alive():
            print("Joining device thread on exit...")
            self.device_thread.join(timeout=1.0)  # Wait briefly

        print("Destroying root window.")
        self.root.destroy()
