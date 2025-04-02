import hid
from datetime import datetime
import time
import tkinter as tk
from tkinter import font as tkFont
import threading
import queue


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
        (20, 84): "WEAPONS_HIT"
    }
    
    return hit_states.get(signature, "UNKNOWN")


def process_vsm_data(device, output_queue, stop_event):
    """
    Reads data from the VSM device, detects state changes, applies debouncing,
    and puts formatted messages into the output queue.
    Runs until stop_event is set.
    """
    last_reported_state = None
    time_last_reported = None
    debounce_time = 0.3  # 300ms debounce time (cooldown period)
    start_time = datetime.now()

    output_queue.put("Monitoring fencing hits...")
    output_queue.put("-" * 30)

    try:
        while not stop_event.is_set():
            # Read data from the device (with a short timeout to allow checking stop_event)
            data = device.read(42, timeout_ms=100)  # Reduced timeout

            if stop_event.is_set():  # Check again after potential blocking read
                break

            if data:
                current_time = datetime.now()
                current_state = detect_hit_state(data)

                if current_state != last_reported_state:
                    if time_last_reported is None or \
                       (current_time - time_last_reported).total_seconds() > debounce_time:

                        elapsed = (current_time - start_time).total_seconds()
                        message = f"[{elapsed:.2f}s] {current_state}"
                        output_queue.put(message)

                        if current_state in ["LEFT_GOT_HIT", "RIGHT_GOT_HIT"]:
                            output_queue.put(f"*** SCORE: {current_state} ***")

                        last_reported_state = current_state
                        time_last_reported = current_time

            # No need for time.sleep(0.01) as device.read timeout provides delay
            # If read is non-blocking or very fast, a small sleep might be needed again

    except Exception as e:
        output_queue.put(f"Error in device loop: {e}")
    finally:
        output_queue.put("Device monitoring stopped.")
        if device:
            device.close()


def update_gui(root, label, output_queue):
    """ Checks the queue for messages and updates the GUI label. """
    try:
        while True:  # Process all messages currently in queue
            message = output_queue.get_nowait()
            # Keep only the last few lines (e.g., 5 lines) for display
            current_lines = label.cget("text").split('\n')
            max_lines = 5
            new_lines = (current_lines + [message])[-max_lines:]
            label.config(text="\n".join(new_lines))
            root.update_idletasks()  # Update GUI immediately
    except queue.Empty:
        pass  # No messages currently

    # Schedule the next check
    root.after(100, update_gui, root, label, output_queue)  # Check every 100ms


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
    root.geometry("400x200")  # Initial size

    # Configure font
    display_font = tkFont.Font(family="Helvetica", size=16)

    # Create label for displaying status
    status_label = tk.Label(
        root,
        text="Initializing...",
        font=display_font,
        justify=tk.CENTER,
        anchor=tk.CENTER  # Center text within the label
    )
    # Make label expand to fill window and center content
    status_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

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

    # Start the GUI update loop
    update_gui(root, status_label, output_queue)

    # Start the Tkinter main loop
    root.mainloop()


if __name__ == "__main__":
    main()
