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


def main():
    gui = FencingGui(find_vsm_device)

    # Start the GUI update loop & Tkinter main loop
    gui.update_gui()
    gui.root.mainloop()


if __name__ == "__main__":
    main()
