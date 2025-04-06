import tkinter as tk
from tkinter import ttk, font as tkFont
import queue
from scorer.settings import (
    GLOBAL_HIT_DMG,
    GLOBAL_HIT_DMG_SELF,
    GLOBAL_HIT_DMG_PER_MILLISECOND,
    MAX_HP,
    DEBOUNCE_TIME,
)


class FencingGui:
    def __init__(self, root):
        self._bar_thickness = 120  # health bar thickness

        # Queue for communication between threads
        self.output_queue = queue.Queue()

        self.root = root
        self.style = ttk.Style(root)

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

        self._configure_styles()

        # --- Layout using grid ---
        root.grid_columnconfigure(0, weight=1, uniform="group1")  # Left HP bar column
        root.grid_columnconfigure(1, weight=1, uniform="group1")  # Right HP bar column
        root.grid_rowconfigure(0, weight=0)  # Labels row
        root.grid_rowconfigure(1, weight=1)  # Progress bars row
        root.grid_rowconfigure(2, weight=0)  # Debug/Status row
        root.grid_rowconfigure(3, weight=0)  # Settings row

        # --- Left Player Elements ---
        self.left_label = tk.Label(root, text="LEFT PLAYER", font=self._label_font)  # Removed bg/fg
        self.left_label.grid(row=0, column=0, pady=(20, 5), sticky="ew")  # Increased padding

        self.left_hp_bar = ttk.Progressbar(
            master=root,
            orient="vertical",
            length=600,  # Increased height of the bar
            mode="determinate",
            maximum=self.settings['max_hp'],
            value=self.settings['max_hp'],  # Start full
            style="Green.Vertical.TProgressbar"  # Initial style
        )
        self.left_hp_bar.grid(row=1, column=0, padx=20, pady=20, sticky="ns")  # Take up whole side

        # --- Right Player Elements ---
        self.right_label = tk.Label(root, text="RIGHT PLAYER", font=self._label_font)
        self.right_label.grid(row=0, column=1, pady=(20, 5), sticky="ew")  # Increased padding

        self.right_hp_bar = ttk.Progressbar(
            master=root,
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
            master=root,
            text="Initializing...",
            font=self._status_font,
            justify=tk.CENTER,
            anchor=tk.CENTER,
            wraplength=800  # Wrap text if it gets too long
        )
        self.status_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Settings Panel Frame ---
        self.settings_frame = ttk.Frame(root, padding="10 10 10 10")
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

        self._setup_labels()

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


