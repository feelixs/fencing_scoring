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
    try:
        while True:
            # Read data from the device
            data = device.read(42)
            print(len(data))
            if data:
                print(datetime.now(), f"Raw data: {data}")

                # In HID protocols, we often need to check specific bits or bytes
                # Looking for the equivalent of Swift's usagePage == 9 && usage == 49

                # This is a simplified approach - the actual byte position and bit masks
                # would depend on the specific VSM HID report format
                if len(data) >= 2:
                    # Example check for button events (may need adjustment)
                    # First byte might contain report ID or button state info
                    # Second byte might contain specific button identifier

                    # Check if this is a button event (usage page 9)
                    if (data[0] & 0xF0) == 0x90:  # Example bit mask for button events
                        # Check if this is button 49
                        if data[1] == 49:
                            print("Detected button 49 event (equivalent to Swift code)")
                            # Handle the event

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