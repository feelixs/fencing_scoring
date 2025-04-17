import time
from threading import Thread, Event
import keyboard


class DummyVSMDevice:
    def __init__(self):
        self.stop_event = Event()
        self.current_state = "neutral"
        self.key_thread = Thread(target=self._monitor_keys, daemon=True)
        self.key_thread.start()

    def _monitor_keys(self):
        while not self.stop_event.is_set():
            if keyboard.is_pressed('l'):
                self.current_state = "leftgothit"
            elif keyboard.is_pressed('r'):
                self.current_state = "rightgothit"
            else:
                self.current_state = "neutral"
            time.sleep(0.05)  # Reduce CPU usage

    def read(self, size, timeout_ms=None):
        if self.current_state == "leftgothit":
            data = [0, 0, 4, 114] + [4, 114] * 19  # Left hitting right pattern
        elif self.current_state == "rightgothit":
            data = [0, 0, 44, 80] + [44, 80] * 19  # Right hitting left pattern
        else:  # neutral
            data = [0, 0, 4, 80] + [4, 80] * 19   # Neutral pattern
        
        # Pad to 42 bytes if needed
        data = data[:42]
        data += [0] * (42 - len(data))
        return data

    def close(self):
        self.stop_event.set()
        self.key_thread.join()


def find_dummy_device():
    """Replacement for find_vsm_device that returns our dummy device"""
    print("Using DUMMY VSM device - press 'l' or 'r' keys to simulate hits")
    return  DummyVSMDevice()


if __name__ == "__main__":
    # Simple test of the dummy device
    print("Testing dummy device - press 'l' or 'r' keys, Ctrl+C to exit")
    device = DummyVSMDevice()
    try:
        while True:
            print(device.read(42))
            time.sleep(0.1)
    except KeyboardInterrupt:
        device.close()
