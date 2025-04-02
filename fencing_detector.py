import hid
from datetime import datetime
import tkinter as tk
from tkinter import ttk, font as tkFont
import threading
import queue


GLOBAL_HIT_DMG = 80
GLOBAL_HIT_DMG_SELF = GLOBAL_HIT_DMG

GLOBAL_HIT_DMG_PER_MILLISECOND = 0.1

RIGHT_HP = 250
LEFT_HP = 250


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
        (4, 114): "LEFT_GOT_HIT",
        (44, 80): "RIGHT_GOT_HIT",
        (38, 80): "LEFT_HIT_SELF",
        (4, 120): "RIGHT_SELF_HIT",
        (20, 84): "WEAPONS_HIT",
        (0, 64): "BOTH_DISCONNECTED",
        (0, 80): "LEFT_DISCONNECTED",
        (4, 64): "RIGHT_DISCONNECTED"
    }
    
    return hit_states.get(signature, "UNKNOWN")


def process_vsm_data(device, output_queue, stop_event):
    """
    Reads data from the VSM device, detects state changes, applies debouncing,
    and puts formatted messages into the output queue.
    Runs until stop_event is set.
    """
    # Initialize health points
    left_hp = LEFT_HP
    right_hp = RIGHT_HP

    left_hp = LEFT_HP
    right_hp = RIGHT_HP

    last_reported_state = None
    time_last_reported = None
    debounce_time = 0.3  # 300ms debounce time (cooldown period)
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
                if current_state == "LEFT_GOT_HIT":
                    damage_increment = time_delta.total_seconds() * 1000 * GLOBAL_HIT_DMG_PER_MILLISECOND
                    if right_hp > 0:
                        right_hp = max(0, right_hp - damage_increment)
                        hp_changed = True

                elif current_state == "RIGHT_GOT_HIT":
                    damage_increment = time_delta.total_seconds() * 1000 * GLOBAL_HIT_DMG_PER_MILLISECOND
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
                        if current_state == "LEFT_GOT_HIT":
                            # Apply initial hit damage plus report score
                            if right_hp > 0:
                                right_hp = max(0, right_hp - GLOBAL_HIT_DMG)
                                hp_changed = True
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: {current_state} ***"})
                        elif current_state == "RIGHT_GOT_HIT":
                            # Apply initial hit damage plus report score
                            if left_hp > 0:
                                left_hp = max(0, left_hp - GLOBAL_HIT_DMG)
                                hp_changed = True
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: {current_state} ***"})
                        elif current_state == "LEFT_HIT_SELF":
                            if left_hp > 0:
                                left_hp = max(0, left_hp - GLOBAL_HIT_DMG_SELF)
                                hp_changed = True # Mark HP changed for update below
                        elif current_state == "RIGHT_SELF_HIT":
                            if right_hp > 0:
                                right_hp = max(0, right_hp - GLOBAL_HIT_DMG_SELF)
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


def update_gui(root, status_label, left_hp_bar, right_hp_bar, output_queue):
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
                left_style = get_hp_color_style(left_hp, LEFT_HP)
                right_style = get_hp_color_style(right_hp, RIGHT_HP)
                left_hp_bar.config(style=left_style)
                right_hp_bar.config(style=right_style)


            root.update_idletasks()  # Update GUI immediately
    except queue.Empty:
        pass  # No messages currently

    # Schedule the next check
    root.after(100, update_gui, root, status_label, left_hp_bar, right_hp_bar, output_queue) # Check every 100ms


def get_hp_color_style(current_hp, max_hp):
    """ Returns the ttk style name based on HP percentage. """
    percentage = (current_hp / max_hp) * 100
    if percentage > 60:
        return "Green.Vertical.TProgressbar"
    elif percentage > 25:
        return "Yellow.Vertical.TProgressbar"
    else:
        return "Red.Vertical.TProgressbar"


def start_device_thread(output_queue, stop_event):
    """ Finds the device and starts the processing thread. """
    def thread_target():
        vsm_device = find_vsm_device()
        if vsm_device:
            process_vsm_data(vsm_device, output_queue, stop_event)
        else:
            output_queue.put("VSM device not found.")
            output_queue.put("Check connection/permissions.")

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread


def main():
    root = tk.Tk()
    root.title("Fencing Hit Detector")
    # root.geometry("800x250") # Removed fixed size
    root.attributes('-fullscreen', True) # Make fullscreen

    # Configure styles for progress bars
    style = ttk.Style(root)
    # Define colors for different health levels
    style.configure("Green.Vertical.TProgressbar", background='green')
    style.configure("Yellow.Vertical.TProgressbar", background='yellow')
    style.configure("Red.Vertical.TProgressbar", background='red')

    # Configure fonts
    label_font = tkFont.Font(family="Helvetica", size=18) # Increased font size
    status_font = tkFont.Font(family="Helvetica", size=16)
    hp_font = tkFont.Font(family="Helvetica", size=14, weight="bold")

    # --- Layout using grid ---
    root.grid_columnconfigure(0, weight=1, uniform="group1") # Left HP bar column
    root.grid_columnconfigure(1, weight=2, uniform="group1") # Status label column
    root.grid_columnconfigure(2, weight=1, uniform="group1") # Right HP bar column
    root.grid_rowconfigure(0, weight=0) # Labels row
    root.grid_rowconfigure(1, weight=1) # Progress bars/Status row

    # --- Left Player Elements ---
    left_label = tk.Label(root, text="LEFT PLAYER", font=label_font)
    left_label.grid(row=0, column=0, pady=(20, 5)) # Increased padding

    left_hp_bar = ttk.Progressbar(
        root,
        orient="vertical",
        length=500, # Increased height of the bar
        mode="determinate",
        maximum=LEFT_HP,
        value=LEFT_HP, # Start full
        style="Green.Vertical.TProgressbar" # Initial style
    )
    left_hp_bar.grid(row=1, column=0, padx=50, pady=20, sticky="ns") # Increased padding

    # --- Center Status Label ---
    status_label = tk.Label(
        root,
        text="Initializing...",
        font=status_font,
        justify=tk.CENTER,
        anchor=tk.CENTER,
        wraplength=350 # Wrap text if it gets too long
    )
    status_label.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")

    # --- Right Player Elements ---
    right_label = tk.Label(root, text="RIGHT PLAYER", font=label_font)
    right_label.grid(row=0, column=2, pady=(20, 5)) # Increased padding

    right_hp_bar = ttk.Progressbar(
        root,
        orient="vertical",
        length=500, # Increased height of the bar
        mode="determinate",
        maximum=RIGHT_HP,
        value=RIGHT_HP, # Start full
        style="Green.Vertical.TProgressbar" # Initial style
    )
    right_hp_bar.grid(row=1, column=2, padx=50, pady=20, sticky="ns") # Increased padding

    # Queue for communication between threads
    output_queue = queue.Queue()

    # Event to signal the device thread to stop
    stop_event = threading.Event()

    # Start the device monitoring thread
    device_thread = start_device_thread(output_queue, stop_event)

    # Function to handle window closing
    def on_closing():
        print("Closing application...")
        stop_event.set()  # Signal the thread to stop
        if device_thread:
            device_thread.join(timeout=1.0)  # Wait briefly for thread cleanup
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the GUI update loop, passing the necessary widgets
    update_gui(root, status_label, left_hp_bar, right_hp_bar, output_queue)

    # Start the Tkinter main loop
    root.mainloop()


if __name__ == "__main__":
    main()
