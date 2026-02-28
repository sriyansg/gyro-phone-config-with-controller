# Gyro-Phone & Controller Config Tool

A simple configuration tool that allows you to use a **physical game controller** and a **smartphone (acting as a gyroscope steering wheel)** simultaneously in games. 

This is incredibly useful for racing games (like F1, Forza, Assetto Corsa, etc.) where you want the precise steering feel of a gyro-enabled phone, while continuing to use your actual controller's triggers for accelerator/brake and its buttons for shifting, DRS, ERS, etc.

The tool works by reading inputs from both connected controllers (e.g., your standard gamepad and the emulated controller from your phone) and merging them into a single **Virtual DualShock 4 Controller** that games can recognize.

## Included Tools

This repository retains the following essential scripts:

### 1. `combined_setting.py`
The core script. It creates a Virtual DS4 controller and actively listens for inputs from **two** physical (or emulated) controllers on your PC.
- **Steering & Joysticks**: Combines axis movements so your phone's horizontal tilt (usually mapped to an axis) directly controls the virtual steering stick.
- **Pedals / Triggers**: Checks both controllers for analog trigger inputs and uses whichever trigger is pressed more, allowing you to seamlessly use the accelerator/brake on your physical gamepad.
- **Buttons**: All buttons from both devices are merged seamlessly.

### 2. `controller_debug.py`
A crucial utility script for debugging and setup. Run this script to view real-time input data from all connected controllers. 
- Use this to determine which `Axis` numbers correspond to your phone's tilt.
- Use this to check connection status and ensure Pygame is successfully reading your physical controller and phone.

## Requirements

You will need Python 3 installed, along with the following libraries:
```bash
pip install pygame vgamepad
```
*Note: Depending on your OS, `vgamepad` might require additional virtual bus drivers (like ViGEmBus on Windows) to emulate the DS4 controller.*

## How to Use

1. **Connect Devices**: Connect your physical game controller to your PC. Start your phone controller app (e.g., PC Remote, Monect, or similar tools that emulate a controller using phone sensors) and connect it to your PC.
2. **Find Mappings**: Run `python controller_debug.py`. Move your phone and press your controller triggers to confirm they are recognized and observe their Axis IDs.
3. **Start Virtual Controller**: Run `python combined_setting.py`. Keep the terminal window open.
4. **Play**: Launch your game. Ensure the game is reading the newly created "Virtual DualShock 4" controller instead of your physical gamepad.
