import time
import tkinter as tk
from tkinter import ttk, font as tkFont
from threading import Thread, Event
from datetime import datetime, timedelta
import queue
from playsound import playsound
from scorer.player import ScoringManager
from scorer.settings import (
    GLOBAL_HIT_DMG,
    GLOBAL_HIT_DMG_SELF,
    GLOBAL_HIT_DMG_PER_MILLISECOND,
    MAX_HP,
    DEBOUNCE_TIME_SEC,
    secBeforeContDmg,
)


class FencingGui:
    def __init__(self, find_device, detect_hit_state):
        # Removed fixed _bar_thickness, will calculate dynamically

        # find_device should return the VSM device, or None if it's not found
        self.find_device = find_device

        # Queue for communication between threads
        self.output_queue = queue.Queue()
        self.stop_event = Event()

        self.root = tk.Tk()
        self.root.title("Fencing Hit Detector")
        self.root.attributes('-fullscreen', True)

        self.detect_hit_state = detect_hit_state

        self.style = ttk.Style(self.root)

        # Configure fonts
        self._label_font = tkFont.Font(family="Helvetica", size=18)  # Increased font size
        self._status_font = tkFont.Font(family="Helvetica", size=16)
        self._entry_font = tkFont.Font(family="Helvetica", size=12)
        self._button_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
        self._winner_font = tkFont.Font(family="Helvetica", size=48, weight="bold")  # Large font for winner display

        self.settings = {
            'hit_dmg': GLOBAL_HIT_DMG,
            'hit_dmg_self': GLOBAL_HIT_DMG_SELF,
            'hit_dmg_per_ms': GLOBAL_HIT_DMG_PER_MILLISECOND,
            'max_hp': MAX_HP,
            'debounce_time': DEBOUNCE_TIME_SEC,
            'sec_before_cont_dmg': secBeforeContDmg
        }
        # Instantiate the ScoringManager
        self.scoring_manager = ScoringManager(self.settings)

        self.current_device = None  # Store the active device instance
        self.device_thread = self.start_device_thread()

        self._configure_styles()

        # --- Layout using grid ---
        self.root.grid_columnconfigure(0, weight=1, uniform="group1")  # Left HP bar column
        self.root.grid_columnconfigure(1, weight=1, uniform="group1")  # Right HP bar column
        self.root.grid_rowconfigure(0, weight=0)  # Labels row
        self.root.grid_rowconfigure(1, weight=1)  # Progress bars row
        self.root.grid_rowconfigure(2, weight=0)  # Combined Status & Settings row
        # Row 3 is no longer used

        # Track if HP has reached zero to play sound only once
        self.left_hp_zero = False
        self.right_hp_zero = False

        # Create winner display frame (initially hidden)
        # Use high stacking order to appear on top of all other widgets
        self.winner_frame = tk.Frame(self.root, bg="black", borderwidth=4, relief="raised")
        # Higher stacking order value (z-order) ensures it appears on top of other widgets
        self.winner_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.25)
        self.winner_frame.lift()  # Raise to the top of stacking order
        self.winner_frame.place_forget()  # Hide initially

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

        # --- Left Player Elements ---
        self.left_label = tk.Label(self.root, text="LEFT PLAYER", font=self._label_font)  # Removed bg/fg
        self.left_label.grid(row=0, column=0, pady=(20, 5), sticky="ew")  # Increased padding

        self.left_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=800,  # Further increased height of the bar
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],  # Start full
            style="GreenHP.Vertical.TProgressbar"  # Initial style (will be updated dynamically)
        )
        self.left_hp_bar.grid(row=1, column=0, padx=20, pady=20, sticky="ns")  # Take up whole side

        # --- Right Player Elements ---
        self.right_label = tk.Label(self.root, text="RIGHT PLAYER", font=self._label_font)
        self.right_label.grid(row=0, column=1, pady=(20, 5), sticky="ew")  # Increased padding

        self.right_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=800,  # Further increased height of the bar
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],  # Start full
            style="GreenHP.Vertical.TProgressbar"  # Initial style (will be updated dynamically)
        )
        self.right_hp_bar.grid(row=1, column=1, padx=20, pady=20, sticky="ns")  # Take up whole side

        # --- Settings Panel Frame (Now on the right side of the bottom row) ---
        self.settings_frame = ttk.Frame(self.root, padding="10 10 10 10")
        # Settings frame now in row 2, column 1
        self.settings_frame.grid(row=2, column=1, sticky="nsew", padx=(10, 20), pady=10)

        # --- Status Label Frame (Now on the left side of the bottom row) ---
        # Create a frame to hold the status label to control its position better
        self.status_frame = ttk.Frame(self.root)
        # Status frame now in row 2, column 0
        self.status_frame.grid(row=2, column=0, sticky="nsew", padx=(20, 10), pady=10)
        # Configure the column within status_frame to expand
        self.status_frame.grid_columnconfigure(0, weight=1)
        # Configure the row within status_frame to expand if needed (optional)
        self.status_frame.grid_rowconfigure(0, weight=1)

        self.status_label = tk.Label(
            master=self.status_frame,
            text="Initializing...",
            font=self._status_font,
            justify=tk.CENTER,
            anchor=tk.CENTER,
            wraplength=600  # Adjust wrap length based on potentially smaller area
        )
        # Place status label within its frame using grid for better alignment
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

        # Add Apply/Reset button
        self.reset_button = ttk.Button(
            master=self.settings_frame,
            text="APPLY & RESET",
            command=self.apply_settings_and_reset,
            style="Accent.TButton"
        )
        self.reset_button.grid(row=3, column=2, columnspan=2, padx=20, pady=5, sticky="ew")

        self._setup_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _get_hp_style(self, hp, max_hp):
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
        won = self.update_gui()
        self.root.mainloop()

    def _configure_styles(self):
        # Calculate desired thickness based on screen width and padding
        # Need to update geometry first to get accurate width
        self.root.update_idletasks()
        screen_width = self.root.winfo_width()  # Use actual window width after layout
        # Bars are in columns 0 and 1, each with padx=20. Total padding = 40.
        # Each column gets roughly half the remaining width.
        bar_thickness = max(50, (screen_width - 40) // 2)  # Ensure a minimum thickness

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
                troughcolor='lightgray',
                background=color,
                thickness=bar_thickness
            )

    def _setup_labels(self):
        ttk.Label(
            master=self.settings_frame,
            text="Starting HP:",
            font=self._entry_font
        ).grid(row=1, column=2, padx=5, pady=5, sticky="e")

        ttk.Label(
            master=self.settings_frame,
            text="Debounce Time (s):",
            font=self._entry_font
        ).grid(row=2, column=0, padx=5, pady=5, sticky="e")
        
        ttk.Label(
            master=self.settings_frame,
            text="Cont. Damage Delay (s):",
            font=self._entry_font
        ).grid(row=3, column=0, padx=5, pady=5, sticky="e")

        ttk.Label(
            master=self.settings_frame,
            text="Continuous Damage/ms:",
            font=self._entry_font
        ).grid(row=1, column=0, padx=5, pady=5, sticky="e")

        ttk.Label(
            master=self.settings_frame,
            text="Self Hit Damage:",
            font=self._entry_font
        ).grid(row=0, column=2, padx=5, pady=5, sticky="e")

        ttk.Label(
            master=self.settings_frame,
            text="Initial Hit Damage:",
            font=self._entry_font
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

            # Reset sound flags when game is reset
            self.left_hp_zero = False
            self.right_hp_zero = False

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
        last_left_hit_time = datetime.min  # Initialize to minimum datetime to allow first hit
        last_right_hit_time = datetime.min  # Initialize to minimum datetime to allow first hit

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
                    data = device.read(42, timeout_ms=100)

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
                            
                            # Always update last reported state after handling changes
                            last_reported_state = current_state_tuple
                            time_last_reported = current_time

                    # --- Send HP Update if it Changed this Iteration (either continuous or one-time) ---
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
                        # Wait a bit before retrying
                        time.sleep(1)

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
        player_won = self.stop_event.is_set()  # if a player already won, the stop event would be set
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

                    # No longer need to lift status_frame as it's in its own row
                elif item['type'] == 'health':
                    left_hp = item['left']
                    right_hp = item['right']
                    max_hp = self.scoring_manager.settings.get('max_hp', MAX_HP) # Get current max_hp

                    # Determine the style based on current HP
                    left_style = self._get_hp_style(left_hp, max_hp)
                    right_style = self._get_hp_style(right_hp, max_hp)

                    # Update bar values and styles
                    self.left_hp_bar.config(style=left_style)
                    self.right_hp_bar.config(style=right_style)
                    self.left_hp_bar['value'] = left_hp
                    self.right_hp_bar['value'] = right_hp

                    # Play sound and display winner when a player's HP reaches 0
                    if left_hp <= 0 and not self.left_hp_zero: # Check <= 0 for safety
                        self.left_hp_zero = True
                        try:
                            playsound('sounds/defeat.mp3', block=False)
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
                            playsound('sounds/defeat.mp3', block=False)
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

                    # Styles are now dynamically updated based on health percentage above
                self.root.update_idletasks()  # Update GUI immediately
        except queue.Empty:
            pass  # No messages currently

        if player_won and not self.stop_event.is_set():
            print("Player has won, stopping device thread.")
            self.stop_event.set()  # Stop the device thread if a player has won

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
