import hid
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import threading


from scorer.settings import (
    GLOBAL_HIT_DMG,
    GLOBAL_HIT_DMG_SELF,
    GLOBAL_HIT_DMG_PER_MILLISECOND,
    MAX_HP,
    DEBOUNCE_TIME,
)

# diff colors for each player? -> take up the whole side of the screen
# move debugging to bottom center
# flashing color on damage?

# beeping on hit & game over -> beep -> whistle
# diff beeps for each person being hit?


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
        return "UNKNOWN"

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

    max_hp = settings.get('max_hp', MAX_HP) if settings else MAX_HP
    left_hp = max_hp
    right_hp = max_hp

    last_reported_state = None
    time_last_reported = None
    debounce_time = settings.get('debounce_time', DEBOUNCE_TIME) if settings else DEBOUNCE_TIME
    start_time = datetime.now()
    last_loop_time = start_time  # Track time for delta calculation

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
            data = device.read(42, timeout_ms=100)

            if stop_event.is_set():
                # double check after potential blocking read
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
                                hp_changed = True  # Mark HP changed for update below
                        elif current_state == "RIGHT_SELF_HIT":
                            output_queue.put({'type': 'status', 'message': f"*** SCORE: RIGHT SELF-HIT ***"})
                            if right_hp > 0:
                                right_hp = max(0, right_hp - hit_dmg_self)
                                hp_changed = True  # Mark HP changed for update below

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
    from gui.gui import FencingGui
    root = tk.Tk()
    root.title("Fencing Hit Detector")
    root.attributes('-fullscreen', True)  # Make fullscreen
    gui = FencingGui(root)

    # Event to signal the device thread to stop
    stop_event = threading.Event()

    # Start the device monitoring thread
    device_thread = start_device_thread(gui.output_queue, stop_event, gui.settings)

    # Function to apply settings and reset game
    def apply_settings_and_reset():
        nonlocal device_thread
        try:
            new_settings = {
                'hit_dmg': float(gui.hit_dmg_entry.get()),
                'hit_dmg_self': float(gui.hit_dmg_self_entry.get()),
                'hit_dmg_per_ms': float(gui.hit_dmg_per_ms_entry.get()),
                'max_hp': float(gui.max_hp_entry.get()),
                'debounce_time': float(gui.debounce_time_entry.get())
            }

            # Update progress bars to use new max HP
            gui.left_hp_bar['maximum'] = new_settings['max_hp']
            gui.right_hp_bar['maximum'] = new_settings['max_hp']

            # Reset HP to full
            gui.left_hp_bar['value'] = new_settings['max_hp']
            gui.right_hp_bar['value'] = new_settings['max_hp']

            # Restart the device thread with new settings
            device_thread = restart_device_thread(gui.output_queue, stop_event, device_thread, new_settings)

            # Update status
            gui.output_queue.put({'type': 'status', 'message': "Game reset with new settings!"})

        except ValueError:
            gui.output_queue.put({'type': 'status', 'message': "Error: Invalid input values."})

    # Add Apply/Reset button
    reset_button = ttk.Button(
        master=gui.settings_frame,
        text="APPLY & RESET",
        command=apply_settings_and_reset,
        style="Accent.TButton"
    )
    reset_button.grid(row=2, column=2, columnspan=2, padx=20, pady=5, sticky="ew")

    # Function to handle window closing
    def on_closing():
        print("Closing application...")
        stop_event.set()  # Signal the thread to stop
        if device_thread:
            device_thread.join(timeout=1.0)  # Wait briefly for thread cleanup
        gui.root.destroy()

    gui.root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the GUI update loop, passing the necessary widgets
    gui.update_gui()

    # Start the Tkinter main loop
    gui.root.mainloop()


if __name__ == "__main__":
    main()
