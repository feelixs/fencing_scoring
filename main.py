import hid
from scorer.gui import FencingGui

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


if __name__ == "__main__":
    gui = FencingGui(find_vsm_device, detect_hit_state)
    gui.run()
