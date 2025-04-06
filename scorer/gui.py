import tkinter as tk
from tkinter import ttk, font as tkFont
from threading import Thread, Event
from datetime import datetime
import queue
from scorer.settings import (
    GLOBAL_HIT_DMG,
    GLOBAL_HIT_DMG_SELF,
    GLOBAL_HIT_DMG_PER_MILLISECOND,
    MAX_HP,
    DEBOUNCE_TIME,
)


class FencingGui:
    def __init__(self, find_device, detect_hit_state):
        self._bar_thickness = 120  # health bar thickness

        # Queue for communication between threads
        self.output_queue = queue.Queue()
        self.stop_event = Event()

        self.root = tk.Tk()
        self.root.title("Fencing Hit Detector")
        self.root.attributes('-fullscreen', True)

        self.find_device = find_device
        self.detect_hit_state = detect_hit_state

        self.style = ttk.Style(self.root)

        # Configure fonts
        self._label_font = tkFont.Font(family="Helvetica", size=18)  # Increased font size
        self._status_font = tkFont.Font(family="Helvetica", size=16)
        self._entry_font = tkFont.Font(family="Helvetica", size=12)
        self._button_font = tkFont.Font(family="Helvetica", size=12, weight="bold")

        self.settings = {
            'hit_dmg': GLOBAL_HIT_DMG,
            'hit_dmg_self': GLOBAL_HIT_DMG_SELF,
            'hit_dmg_per_ms': GLOBAL_HIT_DMG_PER_MILLISECOND,
            'max_hp': MAX_HP,
            'debounce_time': DEBOUNCE_TIME
        }
        self.device_thread = self.start_device_thread()

        self._configure_styles()

        # --- Layout using grid ---
        self.root.grid_columnconfigure(0, weight=1, uniform="group1")  # Left HP bar column
        self.root.grid_columnconfigure(1, weight=1, uniform="group1")  # Right HP bar column
        self.root.grid_rowconfigure(0, weight=0)  # Labels row
        self.root.grid_rowconfigure(1, weight=1)  # Progress bars row
        self.root.grid_rowconfigure(2, weight=0)  # Debug/Status row
        self.root.grid_rowconfigure(3, weight=0)  # Settings row

        # --- Left Player Elements ---
        self.left_label = tk.Label(self.root, text="LEFT PLAYER", font=self._label_font)  # Removed bg/fg
        self.left_label.grid(row=0, column=0, pady=(20, 5), sticky="ew")  # Increased padding

        self.left_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=600,  # Increased height of the bar
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],  # Start full
            style="Green.Vertical.TProgressbar"  # Initial style
        )
        self.left_hp_bar.grid(row=1, column=0, padx=20, pady=20, sticky="ns")  # Take up whole side

        # --- Right Player Elements ---
        self.right_label = tk.Label(self.root, text="RIGHT PLAYER", font=self._label_font)
        self.right_label.grid(row=0, column=1, pady=(20, 5), sticky="ew")  # Increased padding

        self.right_hp_bar = ttk.Progressbar(
            master=self.root,
            orient="vertical",
            length=600,  # Increased height of the bar
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],  # Start full
            style="Red.Vertical.TProgressbar"  # Set to Red style
        )
        self.right_hp_bar.grid(row=1, column=1, padx=20, pady=20, sticky="ns")  # Take up whole side

        # --- Bottom Center Status Label (Debug info) ---
        self.status_label = tk.Label(
            master=self.root,
            text="Initializing...",
            font=self._status_font,
            justify=tk.CENTER,
            anchor=tk.CENTER,
            wraplength=800  # Wrap text if it gets too long
        )
        self.status_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Settings Panel Frame ---
        self.settings_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.settings_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)

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

        self.style.configure(style="Accent.TButton", font=self._button_font)

        # Add Apply/Reset button
        self.reset_button = ttk.Button(
            master=self.settings_frame,
            text="APPLY & RESET",
            command=self.apply_settings_and_reset,
            style="Accent.TButton"
        )
        self.reset_button.grid(row=2, column=2, columnspan=2, padx=20, pady=5, sticky="ew")

        self._setup_labels()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def run(self):
        # Start the GUI update loop & Tkinter main loop
        self.update_gui()
        self.root.mainloop()

    def _configure_styles(self):
        # Define styles for the progress bars
        self.style.layout(
            style="Green.Vertical.TProgressbar",
            layoutspec=[
                ('Vertical.Progressbar.trough',
                 {'children': [('Vertical.Progressbar.pbar', {'side': 'bottom', 'sticky': 'ns'})], 'sticky': 'nswe'})
            ]
        )
        self.style.layout(
            style="Red.Vertical.TProgressbar",
            layoutspec=[
                ('Vertical.Progressbar.trough',
                 {'children': [('Vertical.Progressbar.pbar', {'side': 'bottom', 'sticky': 'ns'})], 'sticky': 'nswe'})
            ]
        )

        # Configure the colors and thickness
        self.style.configure(
            style="Green.Vertical.TProgressbar",
            troughcolor='lightgray',
            background='green',
            thickness=self._bar_thickness
        )
        self.style.configure(
            style="Red.Vertical.TProgressbar",
            troughcolor='lightgray',
            background='red',
            thickness=self._bar_thickness
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
        try:
            new_settings = {
                'hit_dmg': float(self.hit_dmg_entry.get()),
                'hit_dmg_self': float(self.hit_dmg_self_entry.get()),
                'hit_dmg_per_ms': float(self.hit_dmg_per_ms_entry.get()),
                'max_hp': float(self.max_hp_entry.get()),
                'debounce_time': float(self.debounce_time_entry.get())
            }

            # Update progress bars to use new max HP
            self.left_hp_bar['maximum'] = new_settings['max_hp']
            self.right_hp_bar['maximum'] = new_settings['max_hp']

            # Reset HP to full
            self.left_hp_bar['value'] = new_settings['max_hp']
            self.right_hp_bar['value'] = new_settings['max_hp']

            # Restart the device thread with new settings
            self.device_thread = self.restart_device_thread(self.device_thread)

            # Update status
            self.output_queue.put({'type': 'status', 'message': "Game reset with new settings!"})

        except ValueError:
            self.output_queue.put({'type': 'status', 'message': "Error: Invalid input values."})

    def start_device_thread(self):
        """
        Finds the device and starts the processing thread.

        Args:
            settings: Dictionary with dynamic settings to pass to the processing function.
        """

        def thread_target():
            vsm_device = self.find_device()
            if vsm_device:
                self.process_vsm_data(vsm_device)
            else:
                self.output_queue.put({'type': 'status', 'message': "VSM device not found."})
                self.output_queue.put({'type': 'status', 'message': "Check connection/permissions."})

        thread = Thread(target=thread_target, daemon=True)
        thread.start()
        return thread

    def restart_device_thread(self, current_thread=None):
        """
        Stops the current device thread and starts a new one with updated settings.
        """
        # Stop the current thread if it's running
        if current_thread:
            self.stop_event.set()
            current_thread.join(timeout=1.0)

        # Reset the stop event
        self.stop_event.clear()

        # Start a new thread
        return self.start_device_thread()

    def process_vsm_data(self, device):
        """
        Reads data from the VSM device, detects state changes, applies debouncing,
        and puts formatted messages into the output queue.
        Runs until stop_event is set.
        """
        # Use provided settings or fallback to global defaults
        hit_dmg = self.settings.get('hit_dmg', GLOBAL_HIT_DMG) if self.settings else GLOBAL_HIT_DMG
        hit_dmg_self = self.settings.get('hit_dmg_self', GLOBAL_HIT_DMG_SELF) if self.settings else GLOBAL_HIT_DMG_SELF
        hit_dmg_per_ms = self.settings.get('hit_dmg_per_ms', GLOBAL_HIT_DMG_PER_MILLISECOND) if self.settings else GLOBAL_HIT_DMG_PER_MILLISECOND

        max_hp = self.settings.get('max_hp', MAX_HP) if self.settings else MAX_HP
        left_hp = max_hp
        right_hp = max_hp

        last_reported_state = None
        time_last_reported = None
        debounce_time = self.settings.get('debounce_time', DEBOUNCE_TIME) if self.settings else DEBOUNCE_TIME
        start_time = datetime.now()
        last_loop_time = start_time  # Track time for delta calculation

        # Initial status and health update
        self.output_queue.put({'type': 'status', 'message': "Monitoring fencing hits..."})
        self.output_queue.put({'type': 'status', 'message': "-" * 30})
        self.output_queue.put({'type': 'health', 'left': left_hp, 'right': right_hp})

        try:
            while not self.stop_event.is_set():
                current_time = datetime.now()
                time_delta = current_time - last_loop_time
                hp_changed = False

                # Read data from the device (with a short timeout to allow checking stop_event)
                data = device.read(42, timeout_ms=100)

                if self.stop_event.is_set():
                    # double check after potential blocking read
                    break

                if data:
                    current_state = self.detect_hit_state(data)

                    # --- Continuous Damage Calculation (Opponent Hits) ---
                    damage_increment = time_delta.total_seconds() * 1000 * hit_dmg_per_ms

                    if current_state == "LEFT_GOT_HIT" or current_state == "BOTH_HITTING":
                        if right_hp > 0:
                            right_hp = max(0, right_hp - damage_increment)
                            hp_changed = True

                    if current_state == "RIGHT_GOT_HIT" or current_state == "BOTH_HITTING":
                        if left_hp > 0:
                            left_hp = max(0, left_hp - damage_increment)
                            hp_changed = True

                    # --- State Change Reporting & One-Time Damage (Self-Hits) ---
                    if current_state != last_reported_state:
                        if time_last_reported is None or \
                                (current_time - time_last_reported).total_seconds() > debounce_time:

                            elapsed = (current_time - start_time).total_seconds()
                            status_message = f"[{elapsed:.2f}s] {current_state}"
                            self.output_queue.put({'type': 'status', 'message': status_message})

                            # Apply one-time damage for initial hits and self-hits
                            # Handle BOTH_HITTING as a special case
                            if current_state == "BOTH_HITTING":
                                self.output_queue.put({'type': 'status', 'message': f"*** SCORE: BOTH HIT ***"})
                                # Apply damage to both players
                                if right_hp > 0:
                                    right_hp = max(0, right_hp - hit_dmg)
                                    hp_changed = True
                                if left_hp > 0:
                                    left_hp = max(0, left_hp - hit_dmg)
                                    hp_changed = True
                            # Handle individual hits
                            elif current_state == "LEFT_GOT_HIT":
                                self.output_queue.put({'type': 'status', 'message': f"*** SCORE: LEFT PLAYER HIT ***"})
                                # Apply initial hit damage
                                if right_hp > 0:
                                    right_hp = max(0, right_hp - hit_dmg)
                                    hp_changed = True
                            elif current_state == "RIGHT_GOT_HIT":
                                self.output_queue.put({'type': 'status', 'message': f"*** SCORE: RIGHT PLAYER HIT ***"})
                                # Apply initial hit damage
                                if left_hp > 0:
                                    left_hp = max(0, left_hp - hit_dmg)
                                    hp_changed = True
                            elif current_state == "LEFT_HIT_SELF":
                                self.output_queue.put({'type': 'status', 'message': f"*** SCORE: LEFT SELF-HIT ***"})
                                if left_hp > 0:
                                    left_hp = max(0, left_hp - hit_dmg_self)
                                    hp_changed = True  # Mark HP changed for update below
                            elif current_state == "RIGHT_SELF_HIT":
                                self.output_queue.put({'type': 'status', 'message': f"*** SCORE: RIGHT SELF-HIT ***"})
                                if right_hp > 0:
                                    right_hp = max(0, right_hp - hit_dmg_self)
                                    hp_changed = True  # Mark HP changed for update below

                            # Update reported state *after* handling the change
                            last_reported_state = current_state
                            time_last_reported = current_time

                # --- Send HP Update if it Changed this Iteration ---
                if hp_changed:
                    self.output_queue.put({'type': 'health', 'left': left_hp, 'right': right_hp})

                # Update last loop time for next iteration's delta calculation
                last_loop_time = current_time

                # No need for time.sleep(0.01) as device.read timeout provides delay

        except Exception as e:
            self.output_queue.put({'type': 'status', 'message': f"Error in device loop: {e}"})
        finally:
            self.output_queue.put({'type': 'status', 'message': "Device monitoring stopped."})
            if device:
                device.close()

    def update_gui(self):
        """ Checks the queue for messages and updates the GUI elements. """
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
                elif item['type'] == 'health':
                    left_hp = item['left']
                    right_hp = item['right']

                    self.left_hp_bar['value'] = left_hp
                    self.right_hp_bar['value'] = right_hp

                    # Styles are now static (Green for left, Red for right)
                    # No need to update style based on health anymore
                self.root.update_idletasks()  # Update GUI immediately
        except queue.Empty:
            pass  # No messages currently

        # Schedule the next check
        self.root.after(100, self.update_gui)  # Check every 100ms

    # Function to handle window closing
    def on_closing(self):
        print("Closing application...")
        self.stop_event.set()  # Signal the thread to stop
        if self.device_thread:
            self.device_thread.join(timeout=1.0)  # Wait briefly for thread cleanup
        self.root.destroy()
