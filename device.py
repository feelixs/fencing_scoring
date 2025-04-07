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
    last_payload = [0 * 41]  # Placeholder for the last payload
    last_length = 0
    try:
        while True:
            # Read data from the device
            data = device.read(42)
            if last_length != len(data):
                last_length = len(data)
                print(datetime.now(), f"Data length changed: {last_length}")
                last_length = len(data)
            if data:
                trimmed_data = data[1:]  # skip the first byte (data's encoded timestamp)
                if trimmed_data != last_payload:
                    print(datetime.now(), f"Raw data: {data}")
                    last_payload = trimmed_data
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
