# joystick-to-keyboard
This python app takes the input from a joystick and converts it to keyboard output

# Gamepad to Keyboard & Mouse Mapper

This small desktop application allows you to use a gamepad/joystick connected to your computer as a keyboard and mouse.

For example, while the gamepad's left stick moves the mouse cursor, you can assign its buttons to any keyboard keys you want.

## What Does It Do?

- Converts gamepad buttons to keyboard keys
- Can convert analog sticks to mouse movement or scrolling
- Allows custom key mapping through JSON file configuration
- Adaptable to many scenarios such as gaming, presentations, or one-handed computer control

## Files

- `joysticktokeyboard.py`: The application itself
- `advanced_gamepad_mappings.json`: Configuration file containing default button and axis mappings

## How to Use

1. Connect a gamepad to your computer
2. Run the program with `python joysticktokeyboard.py` on a system with Python installed
3. In the opened window, select the connected gamepad and click "Start Mapping"
4. You can modify mouse movement, key assignments, and sensitivity settings from the left controls or the JSON editor on the right
5. Save your desired mappings and reuse them later

## Requirements

- Python 3
- pygame and pynput libraries
- A gamepad/joystick

Basic installation command:
```bash
pip install pygame pynput
```

## Notes

- Don't forget to press the "Save and Apply JSON Settings" button after changing settings
- The program automatically stops if the joystick connection is lost

