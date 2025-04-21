# simulate the VSM device thru keyboard presses
import time
from threading import Event, Lock
from pynput import keyboard


last_listener = None


class DummyVSMDevice:
    def __init__(self, listener):
        self.lock = False
        self.stop_event = Event()
        self.l_pressed = False
        self.r_pressed = False
        self.state_lock = Lock()
        if listener is None:
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
        else:
            self.listener = listener

    def _on_press(self, key):
        try:
            with self.state_lock:
                if key.char == 'l':
                    self.l_pressed = True
                elif key.char == 'r':
                    self.r_pressed = True
        except AttributeError:
            pass  # Ignore non-character keys

    def _on_release(self, key):
        try:
            with self.state_lock:
                if key.char == 'l':
                    self.l_pressed = False
                elif key.char == 'r':
                    self.r_pressed = False
        except AttributeError:
            pass  # Ignore non-character keys

    def read(self, size, timeout_ms=None):
        # Simulate the ~100ms delay or blocking read of the real device
        time.sleep(0.1)

        with self.state_lock:
            if self.l_pressed and self.r_pressed:
                # Corresponds to "both_hitting" state (Left hits Right, Right hits Left)
                # From states/both_hitting: data[2]=44, data[3]=114
                data = [0, 0, 44, 114]
            elif self.l_pressed:
                # Corresponds to "leftgothit" state (Left hits Right)
                # From states/leftgothit: data[2]=4, data[3]=114
                data = [0, 0, 4, 114]
            elif self.r_pressed:
                # Corresponds to "rightgothit" state (Right hits Left)
                # From states/rightgothit: data[2]=44, data[3]=80
                data = [0, 0, 44, 80]
            else:  # Neither pressed
                # Corresponds to "neutral" state
                # From states/neutral: data[2]=4, data[3]=80
                data = [0, 0, 4, 80]

                # Pad to the requested size (typically 42 bytes)
        data = data[:size]  # Ensure we don't exceed size
        data += [0] * (size - len(data))
        time.sleep(0.01)
        return data

    def close(self):
        return


def find_dummy_device():
    global last_listener
    """Replacement for find_vsm_device that returns our dummy device"""
    print("Using DUMMY VSM device - press 'l' or 'r' keys to simulate hits")
    d = DummyVSMDevice(last_listener)
    last_listener = d.listener
    return d


if __name__ == "__main__":
    # Simple test of the dummy device
    print("Testing dummy device - press 'l' or 'r' keys, Ctrl+C to exit")
    device = DummyVSMDevice(None)
    while True:
        print(device.read(42))
        time.sleep(0.1)
