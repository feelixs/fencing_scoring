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


# Status constants for clarity
STATUS_NORMAL = "NORMAL"
STATUS_HITTING_OPPONENT = "HITTING_OPPONENT"
STATUS_HITTING_SELF = "HITTING_SELF"
STATUS_DISCONNECTED = "DISCONNECTED"
STATUS_WEAPONS_HIT = "WEAPONS_HIT"
STATUS_UNKNOWN = "UNKNOWN"


def detect_hit_state(data):
    """
    Detects the independent state of each player based on signature bytes.
    Returns a tuple: (left_player_status, right_player_status)
    """
    if len(data) < 4:  # Need at least up to byte 2, byte 3
        return STATUS_UNKNOWN, STATUS_UNKNOWN

    byte2 = data[2]
    byte3 = data[3]

    # --- Left Player Status (based on byte 2) ---
    if byte2 == 4:
        left_status = STATUS_NORMAL
    elif byte2 == 44:
        left_status = STATUS_HITTING_OPPONENT
    elif byte2 == 38:
        left_status = STATUS_HITTING_SELF
    elif byte2 in [0, 40, 34]:  # states include when disconnected, or hitting opponent/self while disconnected
        left_status = STATUS_DISCONNECTED
    elif byte2 == 20:
        left_status = STATUS_WEAPONS_HIT
    else:
        left_status = STATUS_UNKNOWN

    # --- Right Player Status (based on byte 3) ---
    if byte3 == 80:
        right_status = STATUS_NORMAL
    elif byte3 == 114:
        right_status = STATUS_HITTING_OPPONENT
    elif byte3 == 120:
        right_status = STATUS_HITTING_SELF
    elif byte3 in [64, 98, 104]:  # states include when disconnected, or hitting opponent/self while disconnected
        right_status = STATUS_DISCONNECTED
    elif byte3 == 84:
        right_status = STATUS_WEAPONS_HIT
    else:
        right_status = STATUS_UNKNOWN

    return left_status, right_status


if __name__ == "__main__":
    gui = FencingGui(find_vsm_device, detect_hit_state)
    gui.run()
