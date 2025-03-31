import hid
from datetime import datetime


def find_vsm_device():
    # Vendor ID and Product ID for the VSM device
    vendor_id = 0x04bc
    product_id = 0xc001

    # Find the device
    device = hid.device()
    device.open(vendor_id, product_id)
    print(f"Manufacturer: {device.get_manufacturer_string()}")
    print(f"Product: {device.get_product_string()}")
    return device


def process_vsm_data(device):
    last_state = None
    last_time = None

    try:
        while True:
            # Read data from the device
            data = device.read(42)

            if not data or len(data) < 6:
                continue

            current_time = datetime.now()

            # Determine connection state based on the observed patterns
            current_state = {
                "timestamp": current_time,
                "sequence": data[0],
                "connection": "none"
            }

            # No connection pattern:
            # - data[2] == 0
            # - data[3] and beyond alternate between 64, 0
            if data[2] == 0 and data[3] == 64 and data[5] == 64:
                current_state["connection"] = "none"

            # Connection a->b pattern:
            # - data[2] == 0
            # - data[3] and beyond alternate between 98, 0
            elif 98 in data:
                current_state["connection"] = "a->b"

            # Connection b->a pattern:
            # - data[2] == 40
            # - data[3] and beyond contain 64, 40 pattern
            elif 40 in data:
                current_state["connection"] = "b->a"

                # You could look for hit patterns here too

            # Only print when state changes to avoid flooding the console
            if not last_state or current_state["connection"] != last_state["connection"]:
                print(f"STATE CHANGE: {current_state['connection']}")
                print(f"Timestamp: {current_time}")
                print(f"Data sample: {data[:10]}...")  # Just show first 10 bytes

                # Calculate time since last state change
                if last_state:
                    delta_ms = (current_time - last_state["timestamp"]).total_seconds() * 1000
                    print(f"Time since last state change: {delta_ms:.2f} ms\n")

                # Update last state
                last_state = current_state

    except KeyboardInterrupt:
        print("Monitoring stopped")
    finally:
        device.close()


if __name__ == "__main__":
    try:
        vsm_device = find_vsm_device()
        process_vsm_data(vsm_device)
    except IOError as e:
        print(f"Error: {e}")