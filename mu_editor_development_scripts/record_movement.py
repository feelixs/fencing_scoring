import time
from seeed_xiao_nrf52840 import IMU

with IMU() as imu:
    while True:
        print("Ready - hit Enter then perform your motion")
        input()

        samples = []
        duration = 1.0
        start = time.monotonic()

        while time.monotonic() - start < duration:
            x, y, z = imu.acceleration
            mag = ((x**2) + (y**2) + ((z - 9.8)**2)) ** 0.5
            samples.append(round(mag, 2))
            time.sleep(0.01)

        print("Done!")
        print(samples)
        print("---")

