# Feasibility Analysis: Accelerometer-Based Fencing Sabre Slash Detection

## System Overview

The existing fencing scoring machine is binary — it detects blade contact and fires. The goal is to insert the Seeed XIAO nRF52840 as a **gate in series** with the scoring circuit: the scoring machine still handles all scoring logic, but it can only register a touch when the XIAO allows electricity to pass through.

The XIAO closes or opens a relay on the weapon line based on two conditions:
- Was the hit delivered with the **edge** of the blade (not the flat or point)?
- Was the hit delivered with **sufficient force**?

Parries, lunges, footwork, and missed swings are irrelevant — if the blade isn't touching the opponent, the scoring machine never fires regardless, so there's nothing to gate.

---

## The Physics of a Sabre Hit

A sabre cut is a whipping motion terminating in blade contact. The key physical characteristics:

| Property | Value |
|---|---|
| Primary motion | Lateral or diagonal arc (head, flank, chest cuts) |
| Acceleration profile | Sharp spike on contact → rapid decay |
| Duration of contact impulse | ~10–50ms |
| Peak acceleration at guard | ~5–20g for a solid hit; lower for taps/grazes |
| Edge hit acceleration axis | Perpendicular to the flat of the blade |
| Flat hit acceleration axis | Along the flat of the blade (different axis) |

A thrust (point contact) has a different profile: acceleration along the blade's long axis (forward). This is detectable but less relevant since sabre scoring machines already filter point hits via the lame system.

---

## Hardware Capabilities

**Board**: Seeed XIAO nRF52840
**IMU**: LSM6DS3TR-C (onboard)

| Capability | Spec |
|---|---|
| Accelerometer range | ±2 / ±4 / ±8 / ±16g (selectable) |
| Accelerometer ODR | Up to 6.66kHz |
| Gyroscope range | ±125–2000 dps |
| Gyroscope ODR | Up to 6.66kHz |
| Wireless | Bluetooth LE |
| Form factor | 21 × 17.5mm — fits in a sabre guard |
| Power | USB or LiPo battery |

At 100Hz (a conservative operating rate), we get a reading every 10ms. At 1kHz, every 1ms. The hardware resolution is not a limiting factor.

---

## What the XIAO Needs to Detect

### Condition 1: Edge Orientation

A sabre blade has two flat faces and one edge (the cutting surface). When the edge strikes a target, the impact force is directed **perpendicular to the flat** of the blade. When the flat strikes, the force is directed **across the flat**.

By mounting the XIAO with a known, fixed orientation relative to the blade:
- One IMU axis aligns with the **edge direction** (valid hit axis)
- A perpendicular IMU axis aligns with the **flat direction** (invalid hit axis)

An edge hit will show high acceleration on the edge axis and low on the flat axis. A flat hit will show the opposite. The ratio between these two axes at impact is the discriminator.

### Condition 2: Sufficient Force

A valid scoring hit requires meaningful force. Light contact, grazes, and incidental touches should not score. This is a simple magnitude threshold on the edge-axis acceleration (or total vector magnitude):

```
if edge_axis_accel > FORCE_THRESHOLD:   # e.g. 3–5g
    valid_force = True
```

The exact threshold needs empirical calibration — see Recommended Path below.

---

## Detection Logic

Both conditions evaluated continuously:

```python
edge_accel = abs(imu.acceleration[EDGE_AXIS])
flat_accel = abs(imu.acceleration[FLAT_AXIS])

sufficient_force = edge_accel > FORCE_THRESHOLD
edge_dominant = edge_accel > flat_accel * EDGE_RATIO

if sufficient_force and edge_dominant:
    relay.close()   # pass signal to scoring machine
else:
    relay.open()
```

**Tunable parameters:**
- `FORCE_THRESHOLD`: minimum g-force to count as a scoring hit (e.g. 3g)
- `EDGE_RATIO`: how much more edge-axis vs flat-axis acceleration is required (e.g. 1.5×)
- `EDGE_AXIS` / `FLAT_AXIS`: which IMU axes correspond to blade geometry (determined by mounting orientation)

No gesture recognition, ML, or temporal windowing needed for V1.

---

## Hardware Integration

The XIAO sits **in series** with the scoring machine's weapon line:

```
Weapon tip contact → XIAO relay (open/closed) → Scoring machine input
```

- **Relay closed** (slash detected): scoring machine sees contact, registers touch normally
- **Relay open** (no valid slash): scoring machine is isolated, contact never registered

**Relay choice**: A small signal relay or solid-state relay driven by a GPIO pin. Reed relays switch in <1ms. Optocouplers are even faster and electrically isolate the XIAO from the scoring machine circuit.

**Timing concern**: The scoring machine has an internal timing window for contact evaluation. The XIAO must close the relay while that window is open. At 100Hz sampling, worst-case detection lag is ~10ms. Most scoring machines have contact windows of 15–25ms, so this is likely within tolerance — but should be validated empirically.

---

## Key Challenges

| Challenge | Severity | Mitigation |
|---|---|---|
| Mounting precision | Medium | Fixed bracket (3D printed or machined) inside guard; consistent axis alignment |
| Threshold tuning | Low-Medium | One calibration session with real hits; easily adjusted in firmware |
| Timing vs. scoring machine window | Low-Medium | Validate empirically; increase sample rate if needed (up to 6.66kHz available) |
| IMU axis identification | Low | One-time characterization with the Mu plotter |
| Relay electrical compatibility | Low | Match relay voltage/current to scoring machine circuit specs |

---

## Complexity Assessment

| Aspect | Complexity |
|---|---|
| Hardware (XIAO + IMU) | Low — already have it, already running |
| Physical mounting in guard | Low-Medium — needs a bracket |
| Relay wiring in series with scoring circuit | Low-Medium — standard electronics |
| Detection algorithm | Low — two-condition threshold check |
| Axis identification | Low — one session with Mu plotter |
| Threshold calibration | Low-Medium — empirical, iterative |

**Overall: Low-Medium.** This is significantly simpler than gesture recognition. The algorithm itself is straightforward; the work is in physical mounting and calibration.

---

## Recommended Path

1. **Axis identification**: Mount the XIAO in the guard with a fixed orientation. Use the existing raw IMU plotter (`code.py`) to observe which axis responds to edge hits vs flat hits.

2. **Data collection**: Strike a practice target with: solid edge hits, light edge taps, flat hits, point contact. Record the peak accelerations on each axis for each type.

3. **Set thresholds**: From the data, choose `FORCE_THRESHOLD` and `EDGE_RATIO` that cleanly separate valid from invalid contacts.

4. **Wire relay**: Install a signal relay in series with the scoring machine weapon line, driven by a XIAO GPIO pin.

5. **Implement and validate**: Code the two-condition check, validate live against the scoring machine.

6. **Iterate**: Adjust thresholds based on real-world testing.

---

## Open Questions

- What is the scoring machine's contact timing window? (Determines whether 100Hz is fast enough or if we need higher sample rate)
- Is the XIAO mounted rigidly inside the guard, or does it move relative to the blade? (Affects axis consistency)
- Does the scoring machine use a standard weapon line voltage/current that a small relay can handle?
