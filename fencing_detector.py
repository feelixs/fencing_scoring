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
    # Track the last reported state and the time it was reported
    last_reported_state = None
    time_last_reported = None
    debounce_time = 0.3  # 300ms debounce time (cooldown period)
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

                # Check if the state is different from the last reported one
                if current_state != last_reported_state:
                    # Check if enough time has passed since the last report (or if it's the first report)
                    if time_last_reported is None or \
                       (current_time - time_last_reported).total_seconds() > debounce_time:
                        
                        # Report the new state immediately
                        elapsed = (current_time - start_time).total_seconds()
                        print(f"[{elapsed:.2f}s] {current_state}")
                        if current_state in ["LEFT_GOT_HIT", "RIGHT_GOT_HIT"]:
                            print(f"*** SCORE: {current_state} ***")

                        # Update the last reported state and the time it was reported
                        last_reported_state = current_state
                        time_last_reported = current_time
                    # else: # State changed, but within the debounce period - ignore it.
                    #     pass 

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
