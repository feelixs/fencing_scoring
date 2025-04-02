import hid
from datetime import datetime
import time

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

def process_vsm_data(device):
    # Track the last reported state and potential pending changes
    last_reported_state = None
    pending_state = None
    time_pending_state_detected = None
    debounce_time = 0.3  # 300ms debounce time
    start_time = datetime.now()

    try:
        print("Monitoring fencing hits. Press Ctrl+C to stop.")
        print("-" * 50)
        
        while True:
            # Read data from the device
            data = device.read(42, timeout_ms=1000)

            if data:
                current_time = datetime.now()
                current_state = detect_hit_state(data)

                if current_state == last_reported_state:
                    # State is stable and matches the last reported state, clear any pending change
                    pending_state = None
                    time_pending_state_detected = None
                else:
                    # State is different from the last reported one
                    if current_state != pending_state:
                        # This is a new potential state change, start the timer
                        pending_state = current_state
                        time_pending_state_detected = current_time
                    else:
                        # State is still the same as the pending one, check if debounce time has passed
                        if time_pending_state_detected and \
                           (current_time - time_pending_state_detected).total_seconds() > debounce_time:
                            # Debounce time passed, report the change
                            elapsed = (current_time - start_time).total_seconds()
                            print(f"[{elapsed:.2f}s] {pending_state}")
                            if pending_state in ["LEFT_GOT_HIT", "RIGHT_GOT_HIT"]:
                                print(f"*** SCORE: {pending_state} ***")

                            # Update the reported state and clear pending status
                            last_reported_state = pending_state
                            pending_state = None
                            time_pending_state_detected = None

            # Small delay to prevent hogging CPU
            time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    finally:
        if device:
            device.close()

def main():
    # Find and open the device
    vsm_device = find_vsm_device()
    if vsm_device:
        process_vsm_data(vsm_device)
    else:
        print("Could not find VSM device. Check connection and permissions.")

if __name__ == "__main__":
    main()
