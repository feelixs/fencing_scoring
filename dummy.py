import time
from threading import Event, Lock
from pynput import keyboard


# simulate the VSM device thru keyboard presses

class DummyVSMDevice:
    def __init__(self):
        self.lock = False
        self.stop_event = Event()
        self.l_pressed = False
        self.r_pressed = False
        self.state_lock = Lock()
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

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
        if self.lock:
            return
        self.lock = True
        print("Stopping pynput listener...")
        self.stop_event.set()  # Signal any internal loops using this event (though read() doesn't use it)
        if self.listener:
            self.listener.stop()
            # Wait for the listener thread to actually terminate
            # This is crucial to prevent conflicts when restarting
            try:
                # Check if the listener thread is alive before joining
                # pynput listener might already be stopped/joined internally sometimes
                if self.listener.is_alive():
                    time.sleep(0.3)  # Give it a moment to stop
                    self.listener.join()
                    if self.listener.is_alive():
                        print("Warning: pynput listener thread did not join cleanly.")
                print("pynput listener stopped.")
            except Exception as e:
                print(f"Error joining pynput listener thread: {e}")
            self.listener = None  # Clear the reference


def find_dummy_device():
    """Replacement for find_vsm_device that returns our dummy device"""
    print("Using DUMMY VSM device - press 'l' or 'r' keys to simulate hits")
    return DummyVSMDevice()


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
