import pygame
import vgamepad as vg
import time

def main():
    # Initialize Pygame
    pygame.init()
    pygame.joystick.init()

    # Create virtual DS4 controller
    print("Creating virtual DS4 controller...")
    gamepad = vg.VDS4Gamepad()
    print("Virtual DS4 controller created successfully!\n")

    # Check for connected controllers
    controller_count = pygame.joystick.get_count()
    print(f"Found {controller_count} physical controller(s) connected\n")

    if controller_count < 2:
        print("Warning: Less than 2 controllers detected.")
        print("You need 2 controllers for this script to work properly.\n")
        if controller_count == 0:
            return

    # Initialize all controllers
    controllers = []
    for i in range(controller_count):
        controller = pygame.joystick.Joystick(i)
        controller.init()
        controllers.append(controller)
        print(f"Controller {i}: {controller.get_name()}")
        print(f"  Axes: {controller.get_numaxes()}")
        print(f"  Buttons: {controller.get_numbuttons()}")
        print(f"  Hats: {controller.get_numhats()}\n")

    print("=" * 60)
    print("COMBINED MAPPING (Both Controllers Active):")
    print("  STICKS:")
    print("    Both Controllers, Axis 0 -> DS4 Left Stick X")
    print("    Both Controllers, Axis 1 -> DS4 Left Stick Y")
    print("    Both Controllers, Axis 2 -> DS4 Right Stick X")
    print("    Both Controllers, Axis 3 -> DS4 Right Stick Y")
    print("  TRIGGERS:")
    print("    Both Controllers, Axis 4 -> DS4 Left Trigger")
    print("    Both Controllers, Axis 5 -> DS4 Right Trigger")
    print("  BUTTONS:")
    print("    All buttons from both controllers combined")
    print("  Strategy: Add for sticks, Max for triggers, OR for buttons")
    print("=" * 60)
    print("Virtual controller active! (Press Ctrl+C to exit)\n")

    # Main event loop
    try:
        while True:
            pygame.event.pump()  # Process event queue

            # --- COMBINED: Map Axis 0 & 1 from BOTH controllers to Left Stick ---
            axis_0_ctrl0 = 0
            axis_0_ctrl1 = 0
            axis_1_ctrl0 = 0
            axis_1_ctrl1 = 0

            if len(controllers) >= 1:
                controller0 = controllers[0]
                if controller0.get_numaxes() >= 1:
                    axis_0_ctrl0 = controller0.get_axis(0)
                if controller0.get_numaxes() >= 2:
                    axis_1_ctrl0 = controller0.get_axis(1)

            if len(controllers) >= 2:
                controller1 = controllers[1]
                if controller1.get_numaxes() >= 1:
                    axis_0_ctrl1 = controller1.get_axis(0)
                if controller1.get_numaxes() >= 2:
                    axis_1_ctrl1 = controller1.get_axis(1)

            # Combine values: add both controllers together
            left_stick_x = axis_0_ctrl0 + axis_0_ctrl1
            left_stick_y = axis_1_ctrl0 + axis_1_ctrl1

            # Clamp to -1 to 1 range
            left_stick_x = max(-1.0, min(1.0, left_stick_x))
            left_stick_y = max(-1.0, min(1.0, left_stick_y))

            # Convert to DS4 range (0-255, 128=center)
            left_x_value = int(128 + (left_stick_x * 128))
            left_y_value = int(128 + (left_stick_y * 128))
            left_x_value = max(0, min(255, left_x_value))
            left_y_value = max(0, min(255, left_y_value))
            gamepad.left_joystick(x_value=left_x_value, y_value=left_y_value)

            # --- COMBINED: Map Axis 4 from BOTH controllers to Left Trigger ---
            axis_4_ctrl0 = -1.0
            axis_4_ctrl1 = -1.0

            if len(controllers) >= 1:
                controller0 = controllers[0]
                if controller0.get_numaxes() >= 5:
                    axis_4_ctrl0 = controller0.get_axis(4)

            if len(controllers) >= 2:
                controller1 = controllers[1]
                if controller1.get_numaxes() >= 5:
                    axis_4_ctrl1 = controller1.get_axis(4)

            # Combine values: take whichever trigger is pressed more
            left_trigger_value = max(axis_4_ctrl0, axis_4_ctrl1)

            # Clamp to -1 to 1 range
            left_trigger_value = max(-1.0, min(1.0, left_trigger_value))

            # Apply trigger value
            lt_value = int((left_trigger_value + 1) * 127.5)
            lt_value = max(0, min(255, lt_value))
            gamepad.left_trigger(value=lt_value)

            # --- COMBINED: Map Axis 5 from BOTH controllers to Right Trigger ---
            axis_5_ctrl0 = -1.0
            axis_5_ctrl1 = -1.0

            if len(controllers) >= 1:
                controller0 = controllers[0]
                if controller0.get_numaxes() >= 6:
                    axis_5_ctrl0 = controller0.get_axis(5)

            if len(controllers) >= 2:
                controller1 = controllers[1]
                if controller1.get_numaxes() >= 6:
                    axis_5_ctrl1 = controller1.get_axis(5)

            # Combine values: take whichever trigger is pressed more
            right_trigger_value = max(axis_5_ctrl0, axis_5_ctrl1)

            # Clamp to -1 to 1 range
            right_trigger_value = max(-1.0, min(1.0, right_trigger_value))

            # Apply trigger value
            rt_value = int((right_trigger_value + 1) * 127.5)
            rt_value = max(0, min(255, rt_value))
            gamepad.right_trigger(value=rt_value)

            # --- COMBINED: Map Axis 2 & 3 from BOTH controllers to Right Stick ---
            axis_2_ctrl0 = 0
            axis_2_ctrl1 = 0
            axis_3_ctrl0 = 0
            axis_3_ctrl1 = 0

            if len(controllers) >= 1:
                controller0 = controllers[0]
                if controller0.get_numaxes() >= 3:
                    axis_2_ctrl0 = controller0.get_axis(2)
                if controller0.get_numaxes() >= 4:
                    axis_3_ctrl0 = controller0.get_axis(3)

            if len(controllers) >= 2:
                controller1 = controllers[1]
                if controller1.get_numaxes() >= 3:
                    axis_2_ctrl1 = controller1.get_axis(2)
                if controller1.get_numaxes() >= 4:
                    axis_3_ctrl1 = controller1.get_axis(3)

            # Combine values: add both controllers together
            right_stick_x = axis_2_ctrl0 + axis_2_ctrl1
            right_stick_y = axis_3_ctrl0 + axis_3_ctrl1

            # Clamp to -1 to 1 range
            right_stick_x = max(-1.0, min(1.0, right_stick_x))
            right_stick_y = max(-1.0, min(1.0, right_stick_y))

            # Convert to DS4 range (0-255, 128=center)
            right_x_value = int(128 + (right_stick_x * 128))
            right_y_value = int(128 + (right_stick_y * 128))
            right_x_value = max(0, min(255, right_x_value))
            right_y_value = max(0, min(255, right_y_value))
            gamepad.right_joystick(x_value=right_x_value, y_value=right_y_value)

            # --- COMBINED: Map Buttons from BOTH controllers ---
            # Face Buttons (Cross, Circle, Square, Triangle)
            button_cross = False
            button_circle = False
            button_square = False
            button_triangle = False

            # Shoulder Buttons (L1, R1)
            button_l1 = False
            button_r1 = False

            # D-pad
            dpad_up = False
            dpad_down = False
            dpad_left = False
            dpad_right = False

            # Special Buttons
            button_share = False
            button_options = False

            # Stick Clicks (L3, R3)
            button_l3 = False
            button_r3 = False

            # Collect button states from both controllers
            for controller in controllers:
                num_buttons = controller.get_numbuttons()

                # Standard Xbox/PS button layout
                # Button 0 = Cross/A
                if num_buttons >= 1 and controller.get_button(0):
                    button_cross = True
                # Button 1 = Circle/B
                if num_buttons >= 2 and controller.get_button(1):
                    button_circle = True
                # Button 2 = Square/X
                if num_buttons >= 3 and controller.get_button(2):
                    button_square = True
                # Button 3 = Triangle/Y
                if num_buttons >= 4 and controller.get_button(3):
                    button_triangle = True
                # Button 4 = L1/LB
                if num_buttons >= 5 and controller.get_button(4):
                    button_l1 = True
                # Button 5 = R1/RB
                if num_buttons >= 6 and controller.get_button(5):
                    button_r1 = True
                # Button 6 = Share/Back
                if num_buttons >= 7 and controller.get_button(6):
                    button_share = True
                # Button 7 = Options/Start
                if num_buttons >= 8 and controller.get_button(7):
                    button_options = True
                # Button 8 = L3 (Left stick click)
                if num_buttons >= 9 and controller.get_button(8):
                    button_l3 = True
                # Button 9 = R3 (Right stick click)
                if num_buttons >= 10 and controller.get_button(9):
                    button_r3 = True

                # D-pad via hat (most controllers use hat 0)
                if controller.get_numhats() >= 1:
                    hat = controller.get_hat(0)
                    if hat[1] == 1:  # Up
                        dpad_up = True
                    if hat[1] == -1:  # Down
                        dpad_down = True
                    if hat[0] == -1:  # Left
                        dpad_left = True
                    if hat[0] == 1:  # Right
                        dpad_right = True

            # Apply all button presses to virtual controller
            if button_cross:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
            if button_circle:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
            if button_square:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
            if button_triangle:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
            if button_l1:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
            if button_r1:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
            if button_share:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
            if button_options:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
            if button_l3:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
            if button_r3:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
            if dpad_up:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_DPAD_UP)
            if dpad_down:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_DPAD_DOWN)
            if dpad_left:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_DPAD_LEFT)
            if dpad_right:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_DPAD_RIGHT)

            # Update the virtual controller
            gamepad.update()

            # Small delay to prevent excessive CPU usage
            time.sleep(0.008)  # 8ms delay = ~125Hz update rate

    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        # Reset virtual controller
        gamepad.reset()
        pygame.quit()
        print("Virtual controller disconnected.")

if __name__ == "__main__":
    main()
