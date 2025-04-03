import hid
from datetime import datetime
import tkinter as tk
from tkinter import ttk, font as tkFont
import threading
import queue

# diff colors for each player? -> take up the whole side of the screen
# move debugging to bottom center
# flashing color on damage?

# beeping on hit & game over -> beep -> whistle
# diff beeps for each person being hit?


GLOBAL_HIT_DMG = 10
GLOBAL_HIT_DMG_SELF = GLOBAL_HIT_DMG

GLOBAL_HIT_DMG_PER_MILLISECOND = 3 / 40  # 3 points per 40ms

RIGHT_HP = 250
LEFT_HP = 250

DEBOUNCE_TIME = 0.03


def find_vsm_device():
    # Vendor ID and Product ID for the VSM device
    vendor_id = 0x04bc
    product_id = 0xc001

    # Find the device
    device = hid.device()
    try:
        device.open(vendor_id, product_id)
        print(f"Manufacturer: {device.get_manufacturer_string()}")
        print(f"Product: {device.get_product_string()}")
        return device
    except IOError as e:
        print(f"Error opening device: {e}")
        print("Is the device connected and do you have the right permissions?")
        return None


def detect_hit_state(data):
    # Skip the first 2 bytes (counter and report ID)
    if len(data) < 5:  # Need at least counter, report ID, and one data pair
        return "Unknown"
    
    # Extract key signature bytes - using 3rd and 4th bytes as signature
    # The pattern repeats, so we check the first instance
    signature = (data[2], data[3])
    
    # Match the signature with known patterns
    hit_states = {
        (4, 80): "NEUTRAL",
        (4, 114): "RIGHT_GOT_HIT",
        (44, 80): "LEFT_GOT_HIT",
        (38, 80): "LEFT_HIT_SELF",
        (4, 120): "RIGHT_SELF_HIT",
        (20, 84): "WEAPONS_HIT",
        (0, 64): "BOTH_DISCONNECTED",
        (0, 80): "LEFT_DISCONNECTED",
        (4, 64): "RIGHT_DISCONNECTED",
        (44, 114): "BOTH_HITTING"
    }

    return hit_states.get(signature, "UNKNOWN")


def process_vsm_data(device, output_queue, stop_event, settings=None):
    """
    Reads data from the VSM device, detects state changes, applies debouncing,
    and puts formatted messages into the output queue.
    Runs until stop_event is set.
    
    Args:
        settings: Dictionary with dynamic settings (hit_dmg, hit_dmg_self, 
                 hit_dmg_per_ms, max_hp, debounce_time)
    """
    # Use provided settings or fallback to global defaults
    hit_dmg = settings.get('hit_dmg', GLOBAL_HIT_DMG) if settings else GLOBAL_HIT_DMG
    hit_dmg_self = settings.get('hit_dmg_self', GLOBAL_HIT_DMG_SELF) if settings else GLOBAL_HIT_DMG_SELF
    hit_dmg_per_ms = settings.get('hit_dmg_per_ms', GLOBAL_HIT_DMG_PER_MILLISECOND) if settings else GLOBAL_HIT_DMG_PER_MILLISECOND
    max_hp = settings.get('max_hp', LEFT_HP) if settings else LEFT_HP
    
    # Initialize health points
    left_hp = max_hp
    right_hp = max_hp

    last_reported_state = None
    time_last_reported = None
    debounce_time = settings.get('debounce_time', DEBOUNCE_TIME) if settings else DEBOUNCE_TIME
    start_time = datetime.now()
    last_loop_time = start_time # Track time for delta calculation

    # Initial status and health update
    output_queue.put({'type': 'status', 'message': "Monitoring fencing hits..."})
    output_queue.put({'type': 'status', 'message': "-" * 30})
    output_queue.put({'type': 'health', 'left': left_hp, 'right': right_hp})

    try:
        while not stop_event.is_set():
            current_time = datetime.now()
            time_delta = current_time - last_loop_time
            hp_changed = False

            # Read data from the device (with a short timeout to allow checking stop_event)
            data = device.read(42, timeout_ms=100)  # Reduced timeout

            if stop_event.is_set():  # Check again after potential blocking read
                break

            if data:
                current_state = detect_hit_state(data)

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
                        output_queue.put({'type': 'status', 'message': status_message})

                        # Apply one-time damage for initial hits and self-hits
                        # Handle BOTH_HITTING as a special case
                        if current_state == "BOTH_HITTING":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: BOTH HIT ***"})
                            # Apply damage to both players
                            if right_hp > 0:
                                right_hp = max(0, right_hp - hit_dmg)
                                hp_changed = True
                            if left_hp > 0:
                                left_hp = max(0, left_hp - hit_dmg)
                                hp_changed = True
                        # Handle individual hits
                        elif current_state == "LEFT_GOT_HIT":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: LEFT PLAYER HIT ***"})
                            # Apply initial hit damage
                            if right_hp > 0:
                                right_hp = max(0, right_hp - hit_dmg)
                                hp_changed = True
                        elif current_state == "RIGHT_GOT_HIT":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: RIGHT PLAYER HIT ***"})
                            # Apply initial hit damage
                            if left_hp > 0:
                                left_hp = max(0, left_hp - hit_dmg)
                                hp_changed = True
                        elif current_state == "LEFT_HIT_SELF":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: LEFT SELF-HIT ***"})
                            if left_hp > 0:
                                left_hp = max(0, left_hp - hit_dmg_self)
                                hp_changed = True # Mark HP changed for update below
                        elif current_state == "RIGHT_SELF_HIT":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: RIGHT SELF-HIT ***"})
                            if right_hp > 0:
                                right_hp = max(0, right_hp - hit_dmg_self)
                                hp_changed = True # Mark HP changed for update below

                        # Update reported state *after* handling the change
                        last_reported_state = current_state
                        time_last_reported = current_time

            # --- Send HP Update if it Changed this Iteration ---
            if hp_changed:
                output_queue.put({'type': 'health', 'left': left_hp, 'right': right_hp})

            # Update last loop time for next iteration's delta calculation
            last_loop_time = current_time

            # No need for time.sleep(0.01) as device.read timeout provides delay

    except Exception as e:
        output_queue.put({'type': 'status', 'message': f"Error in device loop: {e}"})
    finally:
        output_queue.put({'type': 'status', 'message': "Device monitoring stopped."})
        if device:
            device.close()


def update_gui(root, status_label, left_hp_bar, right_hp_bar, output_queue, max_hp):
    """ Checks the queue for messages and updates the GUI elements. """
    try:
        while True:  # Process all messages currently in queue
            item = output_queue.get_nowait()

            if item['type'] == 'status':
                message = item['message']
                # Keep only the last few lines (e.g., 5 lines) for display in status label
                current_lines = status_label.cget("text").split('\n')
                max_lines = 5
                new_lines = (current_lines + [message])[-max_lines:]
                status_label.config(text="\n".join(new_lines))
            elif item['type'] == 'health':
                left_hp = item['left']
                right_hp = item['right']

                left_hp_bar['value'] = left_hp
                right_hp_bar['value'] = right_hp

                # Update bar colors based on health
                left_style = get_hp_color_style(left_hp, max_hp)
                right_style = get_hp_color_style(right_hp, max_hp)
                left_hp_bar.config(style=left_style)
                right_hp_bar.config(style=right_style)


            root.update_idletasks()  # Update GUI immediately
    except queue.Empty:
        pass  # No messages currently

    # Schedule the next check
    root.after(100, update_gui, root, status_label, left_hp_bar, right_hp_bar, output_queue, max_hp) # Check every 100ms


def get_hp_color_style(current_hp, max_hp):
    """ Returns the ttk style name based on HP percentage. """
    percentage = (current_hp / max_hp) * 100
    if percentage > 75:
        return "Green.Vertical.TProgressbar"
    elif percentage > 50:
        return "Yellow.Vertical.TProgressbar"
    elif percentage > 25:
        return "Orange.Vertical.TProgressbar"
    else:
        return "Red.Vertical.TProgressbar"


def start_device_thread(output_queue, stop_event, settings=None):
    """ 
    Finds the device and starts the processing thread.
    
    Args:
        settings: Dictionary with dynamic settings to pass to the processing function.
    """
    def thread_target():
        vsm_device = find_vsm_device()
        if vsm_device:
            process_vsm_data(vsm_device, output_queue, stop_event, settings)
        else:
            output_queue.put({'type': 'status', 'message': "VSM device not found."})
            output_queue.put({'type': 'status', 'message': "Check connection/permissions."})

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread


def restart_device_thread(output_queue, stop_event, current_thread, settings=None):
    """
    Stops the current device thread and starts a new one with updated settings.
    
    Args:
        settings: Dictionary with dynamic settings to pass to the processing function.
    """
    # Stop the current thread if it's running
    if current_thread:
        stop_event.set()
        current_thread.join(timeout=1.0)
    
    # Reset the stop event
    stop_event.clear()
    
    # Start a new thread
    return start_device_thread(output_queue, stop_event, settings)


def main():
    root = tk.Tk()
    root.title("Fencing Hit Detector")
    # root.geometry("800x250") # Removed fixed size
    root.attributes('-fullscreen', True) # Make fullscreen

    # Initialize settings with default values
    settings = {
        'hit_dmg': GLOBAL_HIT_DMG,
        'hit_dmg_self': GLOBAL_HIT_DMG_SELF,
        'hit_dmg_per_ms': GLOBAL_HIT_DMG_PER_MILLISECOND,
        'max_hp': LEFT_HP,
        'debounce_time': DEBOUNCE_TIME
    }

    # Configure styles for progress bars
    style = ttk.Style(root)
    # Define colors and thickness for different health levels
    bar_thickness = 120 # Increased thickness for wider bars
    
    # Fix the ttk styles - this is crucial for proper coloring
    style.layout("Green.Vertical.TProgressbar",
                 [('Vertical.Progressbar.trough',
                   {'children': [('Vertical.Progressbar.pbar',
                                  {'side': 'bottom', 'sticky': 'ns'})],
                    'sticky': 'nswe'})])
    style.layout("Yellow.Vertical.TProgressbar",
                 [('Vertical.Progressbar.trough',
                   {'children': [('Vertical.Progressbar.pbar',
                                  {'side': 'bottom', 'sticky': 'ns'})],
                    'sticky': 'nswe'})])
    style.layout("Orange.Vertical.TProgressbar",
                 [('Vertical.Progressbar.trough',
                   {'children': [('Vertical.Progressbar.pbar',
                                  {'side': 'bottom', 'sticky': 'ns'})],
                    'sticky': 'nswe'})])
    style.layout("Red.Vertical.TProgressbar",
                 [('Vertical.Progressbar.trough',
                   {'children': [('Vertical.Progressbar.pbar',
                                  {'side': 'bottom', 'sticky': 'ns'})],
                    'sticky': 'nswe'})])
    
    # Configure the colors and thickness
    style.configure("Green.Vertical.TProgressbar", troughcolor='lightgray', 
                   background='green', thickness=bar_thickness)
    style.configure("Yellow.Vertical.TProgressbar", troughcolor='lightgray', 
                   background='yellow', thickness=bar_thickness)
    style.configure("Orange.Vertical.TProgressbar", troughcolor='lightgray', 
                   background='orange', thickness=bar_thickness)
    style.configure("Red.Vertical.TProgressbar", troughcolor='lightgray', 
                   background='red', thickness=bar_thickness)

    # Configure fonts
    label_font = tkFont.Font(family="Helvetica", size=18) # Increased font size
    status_font = tkFont.Font(family="Helvetica", size=16)
    hp_font = tkFont.Font(family="Helvetica", size=14, weight="bold")
    entry_font = tkFont.Font(family="Helvetica", size=12)
    button_font = tkFont.Font(family="Helvetica", size=12, weight="bold")

    # --- Layout using grid ---
    root.grid_columnconfigure(0, weight=1, uniform="group1") # Left HP bar column
    root.grid_columnconfigure(1, weight=1, uniform="group1") # Right HP bar column
    root.grid_rowconfigure(0, weight=0) # Labels row
    root.grid_rowconfigure(1, weight=1) # Progress bars row
    root.grid_rowconfigure(2, weight=0) # Debug/Status row
    root.grid_rowconfigure(3, weight=0) # Settings row

    # --- Left Player Elements ---
    left_label = tk.Label(root, text="LEFT PLAYER", font=label_font, bg="blue", fg="white")
    left_label.grid(row=0, column=0, pady=(20, 5), sticky="ew") # Increased padding

    left_hp_bar = ttk.Progressbar(
        root,
        orient="vertical",
        length=600, # Increased height of the bar
        mode="determinate",
        maximum=settings['max_hp'],
        value=settings['max_hp'], # Start full
        style="Green.Vertical.TProgressbar" # Initial style
    )
    left_hp_bar.grid(row=1, column=0, padx=20, pady=20, sticky="ns") # Take up whole side

    # --- Right Player Elements ---
    right_label = tk.Label(root, text="RIGHT PLAYER", font=label_font, bg="red", fg="white")
    right_label.grid(row=0, column=1, pady=(20, 5), sticky="ew") # Increased padding

    right_hp_bar = ttk.Progressbar(
        root,
        orient="vertical",
        length=600, # Increased height of the bar
        mode="determinate",
        maximum=settings['max_hp'],
        value=settings['max_hp'], # Start full
        style="Green.Vertical.TProgressbar" # Initial style
    )
    right_hp_bar.grid(row=1, column=1, padx=20, pady=20, sticky="ns") # Take up whole side

    # --- Bottom Center Status Label (Debug info) ---
    status_label = tk.Label(
        root,
        text="Initializing...",
        font=status_font,
        justify=tk.CENTER,
        anchor=tk.CENTER,
        wraplength=800 # Wrap text if it gets too long
    )
    status_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    # --- Settings Panel Frame ---
    settings_frame = ttk.Frame(root, padding="10 10 10 10")
    settings_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
    
    # Create a settings panel with input fields
    ttk.Label(settings_frame, text="Initial Hit Damage:", font=entry_font).grid(row=0, column=0, padx=5, pady=5, sticky="e")
    hit_dmg_entry = ttk.Entry(settings_frame, width=8, font=entry_font)
    hit_dmg_entry.insert(0, str(settings['hit_dmg']))
    hit_dmg_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    
    ttk.Label(settings_frame, text="Self Hit Damage:", font=entry_font).grid(row=0, column=2, padx=5, pady=5, sticky="e")
    hit_dmg_self_entry = ttk.Entry(settings_frame, width=8, font=entry_font)
    hit_dmg_self_entry.insert(0, str(settings['hit_dmg_self']))
    hit_dmg_self_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
    
    ttk.Label(settings_frame, text="Continuous Damage/ms:", font=entry_font).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    hit_dmg_per_ms_entry = ttk.Entry(settings_frame, width=8, font=entry_font)
    hit_dmg_per_ms_entry.insert(0, str(settings['hit_dmg_per_ms']))
    hit_dmg_per_ms_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    
    ttk.Label(settings_frame, text="Starting HP:", font=entry_font).grid(row=1, column=2, padx=5, pady=5, sticky="e")
    max_hp_entry = ttk.Entry(settings_frame, width=8, font=entry_font)
    max_hp_entry.insert(0, str(settings['max_hp']))
    max_hp_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")
    
    ttk.Label(settings_frame, text="Debounce Time (s):", font=entry_font).grid(row=2, column=0, padx=5, pady=5, sticky="e")
    debounce_time_entry = ttk.Entry(settings_frame, width=8, font=entry_font)
    debounce_time_entry.insert(0, str(settings['debounce_time']))
    debounce_time_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
    
    # Queue for communication between threads
    output_queue = queue.Queue()

    # Event to signal the device thread to stop
    stop_event = threading.Event()

    # Start the device monitoring thread
    device_thread = start_device_thread(output_queue, stop_event, settings)
    
    # Function to apply settings and reset game
    def apply_settings_and_reset():
        nonlocal device_thread
        try:
            new_settings = {
                'hit_dmg': float(hit_dmg_entry.get()),
                'hit_dmg_self': float(hit_dmg_self_entry.get()),
                'hit_dmg_per_ms': float(hit_dmg_per_ms_entry.get()),
                'max_hp': float(max_hp_entry.get()),
                'debounce_time': float(debounce_time_entry.get())
            }
            
            # Update progress bars to use new max HP
            left_hp_bar['maximum'] = new_settings['max_hp']
            right_hp_bar['maximum'] = new_settings['max_hp']
            
            # Reset HP to full
            left_hp_bar['value'] = new_settings['max_hp']
            right_hp_bar['value'] = new_settings['max_hp']
            
            # Restart the device thread with new settings
            device_thread = restart_device_thread(output_queue, stop_event, device_thread, new_settings)
            
            # Update status
            output_queue.put({'type': 'status', 'message': "Game reset with new settings!"})
            
        except ValueError:
            output_queue.put({'type': 'status', 'message': "Error: Invalid input values."})
    
    # Add Apply/Reset button
    reset_button = ttk.Button(settings_frame, text="APPLY & RESET", command=apply_settings_and_reset, style="Accent.TButton")
    reset_button.grid(row=2, column=2, columnspan=2, padx=20, pady=5, sticky="ew")
    
    # Configure button style
    style.configure("Accent.TButton", font=button_font)

    # Function to handle window closing
    def on_closing():
        print("Closing application...")
        stop_event.set()  # Signal the thread to stop
        if device_thread:
            device_thread.join(timeout=1.0)  # Wait briefly for thread cleanup
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the GUI update loop, passing the necessary widgets
    update_gui(root, status_label, left_hp_bar, right_hp_bar, output_queue, settings['max_hp'])

    # Start the Tkinter main loop
    root.mainloop()


if __name__ == "__main__":
    main()
