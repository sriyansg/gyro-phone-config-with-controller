import pygame
import vgamepad as vg
import time
import socket
import struct
import os
import threading

# Configuration
GYRO_ALPHA_LEFT_LIMIT = 30.0   # 0 to 30 mapped to left
GYRO_ALPHA_RIGHT_LIMIT = 30.0  # 360 to 330 mapped to right
UDP_IP = "0.0.0.0"
UDP_PORT = 8002
ENABLE_SMOOTHING = False

# Global state for gyro
gyro_state = {
    'x': 0.0,
    'y': 0.0,
    'active': False,
    'last_recv': 0,
    'packet_timestamp': 0
}

def apply_deadzone(value, threshold=0.08):
    if abs(value) < threshold:
        return 0.0
    return (value - threshold * (1 if value > 0 else -1)) / (1 - threshold)

def udp_server_loop():
    global gyro_state
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    print(f"UDP Server listening on port {UDP_PORT}")
    
    last_timestamp = 0
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            if len(data) >= 20:
                # We expect 1 long long (8 bytes) + 3 floats (12 bytes) from the Android App
                timestamp, alpha, beta, gamma = struct.unpack('<qfff', data[:20])
                
                # Anti-jitter: Drop out-of-order packets
                if timestamp <= last_timestamp and last_timestamp != 0:
                    continue
                last_timestamp = timestamp
                
                alpha = alpha % 360.0
                
                if 0 <= alpha <= 180:
                    x = max(-1.0, -(alpha / abs(GYRO_ALPHA_LEFT_LIMIT)))
                else:
                    x = min(1.0, (360.0 - alpha) / abs(GYRO_ALPHA_RIGHT_LIMIT))
                    
                gyro_state['x'] = x
                gyro_state['y'] = 0.0
                gyro_state['active'] = True
                gyro_state['last_recv'] = time.time()
                
        except Exception as e:
            print(f"UDP Error: {e}")

def main():
    global GYRO_ALPHA_LEFT_LIMIT, GYRO_ALPHA_RIGHT_LIMIT
    
    # Start UDP receiver in a background thread
    udp_thread = threading.Thread(target=udp_server_loop, daemon=True)
    udp_thread.start()

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("=" * 60)
    print(f"1. Open your Android UDP Sensor App.")
    print(f"2. Set Target IP to: {local_ip}")
    print(f"3. Set Target Port to: {UDP_PORT}")
    print(f"4. Start streaming sensor data!")
    print("=" * 60)

    # --- Initialize Pygame and Controllers ---
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    pygame.init()
    pygame.joystick.init()

    # Create UI Window
    screen = pygame.display.set_mode((500, 300))
    pygame.display.set_caption("UDP Gyro Controller Status")
    font = pygame.font.SysFont(None, 28)

    print("Creating virtual DS4 controller...")
    gamepad = vg.VDS4Gamepad()
    print("Virtual DS4 controller created successfully!\n")

    controller_count = pygame.joystick.get_count()
    print(f"Found {controller_count} physical controller(s) connected")

    controllers = []
    for i in range(controller_count):
        controller = pygame.joystick.Joystick(i)
        controller.init()
        controllers.append(controller)
        print(f"Initialized physical controller {i}: {controller.get_name()}")

    prev_left_x = 0.0
    prev_left_y = 0.0
    alpha_turn = 0.8
    alpha_return = 0.6

    print("\nVirtual controller active! Processing UDP inputs. (Press Ctrl+C to exit)\n")

    last_ui_update = 0
    try:
        while True:
            # Auto-disconnect if no packet received in last 1 second
            if gyro_state['active'] and time.time() - gyro_state['last_recv'] > 1.0:
                gyro_state['active'] = false
                gyro_state['x'] = 0.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        GYRO_ALPHA_LEFT_LIMIT = max(1.0, GYRO_ALPHA_LEFT_LIMIT - 1.0)
                        GYRO_ALPHA_RIGHT_LIMIT = max(1.0, GYRO_ALPHA_RIGHT_LIMIT - 1.0)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        GYRO_ALPHA_LEFT_LIMIT += 1.0
                        GYRO_ALPHA_RIGHT_LIMIT += 1.0

            # --- Physical Controller Inputs ---
            axis_0 = 0.0; axis_1 = 0.0; axis_2 = 0.0; axis_3 = 0.0
            axis_4 = -1.0; axis_5 = -1.0
            
            button_cross = False; button_circle = False; button_square = False; button_triangle = False
            button_l1 = False; button_r1 = False; button_share = False; button_options = False
            button_l3 = False; button_r3 = False
            
            dpad_up = False; dpad_down = False; dpad_left = False; dpad_right = False

            if len(controllers) > 0:
                c = controllers[0]
                num_axes = c.get_numaxes()
                num_buttons = c.get_numbuttons()
                
                if num_axes >= 1: axis_0 = apply_deadzone(c.get_axis(0))
                if num_axes >= 2: axis_1 = apply_deadzone(c.get_axis(1))
                if num_axes >= 3: axis_2 = apply_deadzone(c.get_axis(2))
                if num_axes >= 4: axis_3 = apply_deadzone(c.get_axis(3))
                if num_axes >= 5: axis_4 = c.get_axis(4)
                if num_axes >= 6: axis_5 = c.get_axis(5)
                
                if num_buttons >= 1 and c.get_button(0): button_cross = True
                if num_buttons >= 2 and c.get_button(1): button_circle = True
                if num_buttons >= 3 and c.get_button(2): button_square = True
                if num_buttons >= 4 and c.get_button(3): button_triangle = True
                if num_buttons >= 5 and c.get_button(4): button_l1 = True
                if num_buttons >= 6 and c.get_button(5): button_r1 = True
                if num_buttons >= 7 and c.get_button(6): button_share = True
                if num_buttons >= 8 and c.get_button(7): button_options = True
                if num_buttons >= 9 and c.get_button(8): button_l3 = True
                if num_buttons >= 10 and c.get_button(9): button_r3 = True
                
                if c.get_numhats() >= 1:
                    hat = c.get_hat(0)
                    if hat[1] == 1: dpad_up = True
                    if hat[1] == -1: dpad_down = True
                    if hat[0] == -1: dpad_left = True
                    if hat[0] == 1: dpad_right = True

            # --- Map Left Stick (Physical + Gyro) ---
            raw_left_x = max(-1.0, min(1.0, axis_0 + gyro_state['x']))
            raw_left_y = max(-1.0, min(1.0, axis_1 + gyro_state['y']))

            if ENABLE_SMOOTHING:
                ax = alpha_turn if abs(raw_left_x) > abs(prev_left_x) else alpha_return
                left_stick_x = ax * raw_left_x + (1 - ax) * prev_left_x
                prev_left_x = left_stick_x

                ay = alpha_turn if abs(raw_left_y) > abs(prev_left_y) else alpha_return
                left_stick_y = ay * raw_left_y + (1 - ay) * prev_left_y
                prev_left_y = left_stick_y
            else:
                left_stick_x = raw_left_x
                left_stick_y = raw_left_y
                prev_left_x = left_stick_x
                prev_left_y = left_stick_y

            left_x_value = max(0, min(255, int(round((left_stick_x + 1.0) * 127.5))))
            left_y_value = max(0, min(255, int(round((left_stick_y + 1.0) * 127.5))))
            gamepad.left_joystick(x_value=left_x_value, y_value=left_y_value)

            right_x_value = max(0, min(255, int(round((axis_2 + 1.0) * 127.5))))
            right_y_value = max(0, min(255, int(round((axis_3 + 1.0) * 127.5))))
            gamepad.right_joystick(x_value=right_x_value, y_value=right_y_value)

            lt_value = max(0, min(255, int(round((axis_4 + 1.0) * 127.5))))
            gamepad.left_trigger(value=lt_value)
            rt_value = max(0, min(255, int(round((axis_5 + 1.0) * 127.5))))
            gamepad.right_trigger(value=rt_value)

            if button_cross: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
            if button_circle: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
            if button_square: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
            if button_triangle: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
            if button_l1: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
            if button_r1: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
            if button_share: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
            if button_options: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
            if button_l3: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
            if button_r3: gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
            else: gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
            
            if dpad_up and dpad_right: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST)
            elif dpad_down and dpad_right: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST)
            elif dpad_down and dpad_left: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST)
            elif dpad_up and dpad_left: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST)
            elif dpad_up: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
            elif dpad_down: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
            elif dpad_left: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST)
            elif dpad_right: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST)
            else: gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)

            # --- Update UI ---
            current_time = time.time()
            if current_time - last_ui_update > 0.033:
                last_ui_update = current_time
                screen.fill((30, 30, 30))
                
                y_offset = 20
                status_color = (0, 255, 0) if gyro_state['active'] else (255, 0, 0)
                screen.blit(font.render(f"UDP Status: {'Receiving' if gyro_state['active'] else 'Waiting...'}", True, status_color), (20, y_offset)); y_offset += 35
                screen.blit(font.render(f"Gyro X: {gyro_state['x']:.3f}", True, (255, 255, 255)), (20, y_offset)); y_offset += 35
                screen.blit(font.render(f"Physical Stick X: {axis_0:.3f}", True, (255, 255, 255)), (20, y_offset)); y_offset += 35
                screen.blit(font.render(f"Combined Left X: {left_stick_x:.3f}", True, (255, 255, 255)), (20, y_offset)); y_offset += 35
                screen.blit(font.render(f"Limits (L/R): {GYRO_ALPHA_LEFT_LIMIT:.1f} / {GYRO_ALPHA_RIGHT_LIMIT:.1f}", True, (255, 255, 100)), (20, y_offset)); y_offset += 35
                screen.blit(font.render("Press +/- to adjust sensitivity", True, (150, 150, 150)), (20, y_offset))
                
                pygame.display.flip()

            gamepad.update()
            time.sleep(0.008)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        gamepad.reset()
        pygame.quit()
        print("Virtual controller disconnected.")

if __name__ == "__main__":
    main()
