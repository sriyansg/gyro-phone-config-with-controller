import pygame
import vgamepad as vg
import time
import json
import asyncio
import websockets
import threading
import ssl
import http.server
import socketserver
import os
import socket
import struct


# Global state for gyro
gyro_state = {
    'x': 0.0,
    'y': 0.0,
    'active': False
}

# Configuration
SENSITIVITY = 45.0  # Degrees for full stick deflection
# Adjust these based on the max values you see when turning full left and full right
GYRO_BETA_LEFT_LIMIT = -65.0  # The negative Beta value for max left turn
GYRO_BETA_RIGHT_LIMIT = 65.0  # The positive Beta value for max right turn
# Set to True to enable Exponential Moving Average smoothing, False for raw instant input
ENABLE_SMOOTHING = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
WEB_DIR = os.path.join(BASE_DIR, "web")
HTTP_PORT = 8000
WS_PORT = 8001

def apply_deadzone(value, threshold=0.08):
    if abs(value) < threshold:
        return 0.0
    return (value - threshold * (1 if value > 0 else -1)) / (1 - threshold)

class SecureHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_http_server(cert_file, key_file):
    import functools
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WEB_DIR)
    
    httpd = SecureHTTPServer(("", HTTP_PORT), handler)
    
    # Wrap with SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"HTTPS Server running on https://0.0.0.0:{HTTP_PORT}")
    httpd.serve_forever()

async def ws_handler(websocket):
    global gyro_state
    print("WebSocket client connected!")
    gyro_state['active'] = True
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                if len(message) == 12:
                    alpha, beta, gamma = struct.unpack('<fff', message)
                else:
                    continue
            else:
                data = json.loads(message)
                beta = data.get('beta', 0)
            
            # User requested Beta only mapped to X axis
            
            if beta < 0:
                # Map 0 to Left Limit -> 0 to -1.0
                x = max(-1.0, beta / abs(GYRO_BETA_LEFT_LIMIT))
            else:
                # Map 0 to Right Limit -> 0 to 1.0
                x = min(1.0, beta / abs(GYRO_BETA_RIGHT_LIMIT))
                
            y = 0.0  # Ignore Y axis
            
            gyro_state['x'] = x
            gyro_state['y'] = y
    except websockets.exceptions.ConnectionClosed:
        print("WebSocket client disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        gyro_state['active'] = False
        gyro_state['x'] = 0.0
        gyro_state['y'] = 0.0

async def ws_server(cert_file, key_file):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT, ssl=context):
        print(f"WebSocket Server running on wss://0.0.0.0:{WS_PORT}")
        await asyncio.Future()  # run forever

def start_ws_server(cert_file, key_file):
    asyncio.run(ws_server(cert_file, key_file))

def main():
    global GYRO_BETA_LEFT_LIMIT, GYRO_BETA_RIGHT_LIMIT
    # --- Start Servers ---
    cert_path = os.path.join(PROJECT_ROOT, "certs", "cert.pem")
    key_path = os.path.join(PROJECT_ROOT, "certs", "key.pem")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("Error: cert.pem or key.pem not found. Run generate_cert.py first.")
        return

    # Start HTTPS Server in a background thread
    http_thread = threading.Thread(target=start_http_server, args=(cert_path, key_path), daemon=True)
    http_thread.start()

    # Start WebSocket Server in a background thread
    ws_thread = threading.Thread(target=start_ws_server, args=(cert_path, key_path), daemon=True)
    ws_thread.start()

    # Get local IP for convenience print
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("=" * 60)
    print(f"1. Connect your phone to the same Wi-Fi network.")
    print(f"2. Open your phone browser and go to: https://{local_ip}:{HTTP_PORT}")
    print(f"3. Ignore the security warning (Advanced -> Proceed).")
    print(f"4. Press 'Connect & Start Gyro' in the web app.")
    print("=" * 60)

    # --- Initialize Pygame and Controllers ---
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    pygame.init()
    pygame.joystick.init()

    # Create UI Window
    screen = pygame.display.set_mode((500, 300))
    pygame.display.set_caption("Gyro Controller Status")
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

    # Smoothing state variables for left stick
    prev_left_x = 0.0
    prev_left_y = 0.0
    alpha_turn = 0.3
    alpha_return = 0.15

    print("\nVirtual controller active! Processing inputs. (Press Ctrl+C to exit)\n")

    last_ui_update = 0
    # Main event loop
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        # More sensitive -> smaller limits
                        GYRO_BETA_LEFT_LIMIT = min(-1.0, GYRO_BETA_LEFT_LIMIT + 1.0)
                        GYRO_BETA_RIGHT_LIMIT = max(1.0, GYRO_BETA_RIGHT_LIMIT - 1.0)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        # Less sensitive -> larger limits
                        GYRO_BETA_LEFT_LIMIT -= 1.0
                        GYRO_BETA_RIGHT_LIMIT += 1.0

            # --- Physical Controller Inputs ---
            axis_0 = 0.0 # Left stick X
            axis_1 = 0.0 # Left stick Y
            axis_2 = 0.0 # Right stick X
            axis_3 = 0.0 # Right stick Y
            axis_4 = -1.0 # Left trigger
            axis_5 = -1.0 # Right trigger
            
            # Buttons
            button_cross = False
            button_circle = False
            button_square = False
            button_triangle = False
            button_l1 = False
            button_r1 = False
            button_share = False
            button_options = False
            button_l3 = False
            button_r3 = False
            
            # D-pad
            dpad_up = False
            dpad_down = False
            dpad_left = False
            dpad_right = False

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
            
            # Combine physical stick and gyro stick
            raw_left_x = axis_0 + gyro_state['x']
            raw_left_y = axis_1 + gyro_state['y']
            
            # Clamp after combining
            raw_left_x = max(-1.0, min(1.0, raw_left_x))
            raw_left_y = max(-1.0, min(1.0, raw_left_y))

            # Apply smoothing (Exponential Moving Average)
            if ENABLE_SMOOTHING:
                alpha_x = alpha_turn if abs(raw_left_x) > abs(prev_left_x) else alpha_return
                left_stick_x = alpha_x * raw_left_x + (1 - alpha_x) * prev_left_x
                prev_left_x = left_stick_x

                alpha_y = alpha_turn if abs(raw_left_y) > abs(prev_left_y) else alpha_return
                left_stick_y = alpha_y * raw_left_y + (1 - alpha_y) * prev_left_y
                prev_left_y = left_stick_y
            else:
                left_stick_x = raw_left_x
                left_stick_y = raw_left_y
                prev_left_x = left_stick_x
                prev_left_y = left_stick_y

            # Convert to DS4 range (0-255, 128=center)
            # Utilizing (val + 1.0) * 127.5 with rounding correctly maps:
            # -1.0 -> 0, 0.0 -> 128, 1.0 -> 255 without clipping.
            left_x_value = max(0, min(255, int(round((left_stick_x + 1.0) * 127.5))))
            left_y_value = max(0, min(255, int(round((left_stick_y + 1.0) * 127.5))))
            gamepad.left_joystick(x_value=left_x_value, y_value=left_y_value)

            # --- Map Right Stick ---
            right_x_value = max(0, min(255, int(round((axis_2 + 1.0) * 127.5))))
            right_y_value = max(0, min(255, int(round((axis_3 + 1.0) * 127.5))))
            gamepad.right_joystick(x_value=right_x_value, y_value=right_y_value)

            # --- Map Triggers ---
            lt_value = max(0, min(255, int(round((axis_4 + 1.0) * 127.5))))
            gamepad.left_trigger(value=lt_value)

            rt_value = max(0, min(255, int(round((axis_5 + 1.0) * 127.5))))
            gamepad.right_trigger(value=rt_value)

            # --- Map Buttons ---
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
            if current_time - last_ui_update > 0.033:  # Render at ~30 FPS
                last_ui_update = current_time
                screen.fill((30, 30, 30))
                
                y_offset = 20
                
                status_color = (0, 255, 0) if gyro_state['active'] else (255, 0, 0)
                status_text = font.render(f"Connection Status: {'Connected' if gyro_state['active'] else 'Disconnected'}", True, status_color)
                screen.blit(status_text, (20, y_offset))
                y_offset += 35
                
                gyro_text = font.render(f"Gyro X: {gyro_state['x']:.3f}", True, (255, 255, 255))
                screen.blit(gyro_text, (20, y_offset))
                y_offset += 35
                
                stick_text = font.render(f"Physical Stick X: {axis_0:.3f}", True, (255, 255, 255))
                screen.blit(stick_text, (20, y_offset))
                y_offset += 35
                
                combined_text = font.render(f"Combined Left X: {left_stick_x:.3f}", True, (255, 255, 255))
                screen.blit(combined_text, (20, y_offset))
                y_offset += 35
                
                limits_text = font.render(f"Limits (L/R): {GYRO_BETA_LEFT_LIMIT:.1f} / {GYRO_BETA_RIGHT_LIMIT:.1f}", True, (255, 255, 100))
                screen.blit(limits_text, (20, y_offset))
                y_offset += 35
                
                help_text = font.render("Press +/- to adjust sensitivity", True, (150, 150, 150))
                screen.blit(help_text, (20, y_offset))
                
                pygame.display.flip()

            gamepad.update()
            time.sleep(0.008) # ~120Hz loop

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        gamepad.reset()
        pygame.quit()
        print("Virtual controller disconnected.")

if __name__ == "__main__":
    main()
