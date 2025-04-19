# Fencing Scoring System

A customizable scoring system for fencing that processes data from VSM HID devices. The system monitors hit states between two players, manages player health points, and displays a GUI with health bars and real-time status information.

## Features

- Processes real-time hit detection data from VSM (Vango-Sport Manufacturers) HID devices
- Displays dynamic health bars for left and right players
- Provides visual feedback for hits and damage
- Supports continuous damage for prolonged touches
- Plays sound effects for health thresholds and victories
- Configurable health/damage settings

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fencing_scoring.git
   cd fencing_scoring
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

To run the application:

```bash
python main.py
```

To run in dummy mode (without an actual VSM device):

```bash
python main.py --dummy
```

### Hardware Requirements

- VSM fencing scoring device (Vendor ID: 0x04bc, Product ID: 0xc001)
- Two fencing weapons connected to the VSM device

### Device Monitoring

To monitor raw data from the VSM device for debugging:

```bash
python testing/device.py
```

## Game Settings

The application provides a settings panel to customize:

- Initial hit damage
- Self-hit damage
- Continuous damage per millisecond
- Maximum health points
- Debounce time (seconds)
- Continuous damage delay (seconds)

Changes to settings can be applied using the "APPLY & RESET" button, which also resets the match.

## Game States

The system detects several hit states for each player:

- **NORMAL**: No hit detected
- **HITTING_OPPONENT**: Player is hitting their opponent
- **HITTING_SELF**: Player is hitting themself
- **DISCONNECTED**: Player's weapon is disconnected
- **WEAPONS_HIT**: Weapons are touching each other


## TODOs

- "APPLY & RESET" in dummy mode causes a Python interpreter crash :/
