import hid
import time
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
    last_payload = [0] * 41  # Placeholder for the last payload
    last_length = 0
    last_print_time = 0
    debounce_seconds = 0.05  # Only print changes if they persist for 50ms

    try:
        while True:
            # Read data from the device (blocking read)
            data = device.read(42)
            if last_length != len(data):
                last_length = len(data)
                print(datetime.now(), f"Data length changed: {last_length}")
                # Removed duplicated last_length assignment below
            if data:
                current_time = time.time()
                trimmed_data = data[1:]  # skip the first byte (data's encoded timestamp)
                if trimmed_data != last_payload:
                    if current_time - last_print_time > debounce_seconds:
                        print(datetime.now(), f"Raw data: {data}")
                        last_payload = trimmed_data
                        last_print_time = current_time
                    # else: Debounced - data changed, but too quickly, so ignore for printing
                # else: Data is the same as last printed, do nothing
    except KeyboardInterrupt:
        print("\nMonitoring stopped")
    finally:
        device.close()


if __name__ == "__main__":
    try:
        vsm_device = find_vsm_device()
        process_vsm_data(vsm_device)
    except IOError as e:
        print(f"Error: {e}")
