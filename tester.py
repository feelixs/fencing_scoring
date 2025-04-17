import time
from threading import Thread, Event, Lock
from pynput import keyboard


class DummyVSMDevice:
    def __init__(self):
        self.stop_event = Event()
        self.l_pressed = False
        self.r_pressed = False
        self.state_lock = Lock()
        self._close_lock = Lock() # Lock for ensuring close runs once
        self._closing = False     # Flag to indicate close is in progress/done
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
        with self._close_lock:
            if self._closing:
                print("Close already in progress or finished.")
                return # Already closing/closed
            self._closing = True # Mark as closing

            # Get the listener reference and immediately clear the instance variable
            listener_to_close = self.listener
            self.listener = None

        print("Stopping pynput listener...")
        self.stop_event.set() # Signal any internal loops

        if listener_to_close:
            try:
                # Stop the listener
                listener_to_close.stop()

                # Join the listener thread
                # Check if the current thread is the listener thread itself to avoid deadlock
                import threading
                if threading.current_thread() != listener_to_close.thread:
                     # Wait for the listener thread to actually terminate
                     # This is crucial to prevent conflicts when restarting
                     listener_to_close.join(timeout=2.0) # Use a timeout
                     if listener_to_close.is_alive():
                         print("Warning: pynput listener thread did not join cleanly after timeout.")
                     else:
                         print("pynput listener stopped and joined.")
                else:
                     print("Skipping join() because close() called from listener thread itself.")

            except Exception as e:
                # Catch potential errors during stop/join
                print(f"Error stopping/joining pynput listener thread: {e}")
        else:
            print("No active pynput listener to stop.")


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
