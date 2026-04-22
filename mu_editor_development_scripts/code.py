import time
from seeed_xiao_nrf52840 import IMU

with IMU() as imu:
    while True:
        x, y, z = imu.acceleration
        print((x, y, z))  # Mu plotter format
        time.sleep(0.01)
