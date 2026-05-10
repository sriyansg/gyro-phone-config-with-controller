import os
import socket
import struct
import threading
import time
import pygame
import vgamepad as vg

# ============================================================
# CONFIG
# ============================================================
UDP_IP = "0.0.0.0"
UDP_PORT = 9000

# Android packet format:
# seq(int32), ts(int64), alpha(float32), beta(float32), gamma(float32)
PACKET_FORMAT = ">iqfff"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

# Use your latest measured values as starting limits
GAMMA_LEFT_LIMIT = 68.0   
GAMMA_RIGHT_LIMIT = 84.0   
# Increased up by 10
DEADZONE_NORM = 0.05
ENABLE_SMOOTHING = False
ALPHA_TURN = 0.35
ALPHA_RETURN = 0.18

INVERT_STEERING = False

LOOP_HZ = 120
UI_FPS = 30
PACKET_TIMEOUT_SEC = 1.0

# ============================================================
# SHARED GYRO / TILT STATE
# ============================================================
tilt_state = {
    "seq": 0,
    "alpha": 0.0,
    "beta": 0.0,
    "gamma": 0.0,
    "x": 0.0,
    "active": False,
    "last_packet_time": 0.0,
    "packets_total": 0,
    "packets_this_second": 0,
}
state_lock = threading.Lock()


# ============================================================
# HELPERS
# ============================================================
def apply_deadzone(value, threshold=0.08):
    if abs(value) < threshold:
        return 0.0
    return (value - threshold * (1 if value > 0 else -1)) / (1 - threshold)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def norm_to_ds4_byte(value):
    # -1.0 -> 0, 0.0 -> 128, +1.0 -> 255
    return max(0, min(255, int(round((value + 1.0) * 127.5))))


def gamma_to_x(gamma_deg):
    # Positive gamma = left, negative gamma = right based on your readings
    if gamma_deg >= 0:
        x = gamma_deg / GAMMA_LEFT_LIMIT
    else:
        x = gamma_deg / GAMMA_RIGHT_LIMIT  # gamma is negative -> x negative

    x = clamp(x, -1.0, 1.0)
    return x


def get_local_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for res in socket.getaddrinfo(hostname, None):
            ip = res[4][0]
            if ":" not in ip and ip != "127.0.0.1" and ip not in ips:
                ips.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip not in ips:
            ips.append(ip)
    except Exception:
        pass

    return ips


# ============================================================
# UDP RECEIVER THREAD
# ============================================================
def udp_receiver():
    global tilt_state

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"UDP receiver listening on {UDP_IP}:{UDP_PORT}")

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            if len(data) < PACKET_SIZE:
                continue

            seq, ts_ns, alpha, beta, gamma = struct.unpack(PACKET_FORMAT, data[:PACKET_SIZE])
            x = gamma_to_x(gamma)
            now = time.time()

            with state_lock:
                tilt_state["seq"] = seq
                tilt_state["alpha"] = alpha
                tilt_state["beta"] = beta
                tilt_state["gamma"] = gamma
                tilt_state["x"] = x
                tilt_state["active"] = True
                tilt_state["last_packet_time"] = now
                tilt_state["packets_total"] += 1
                tilt_state["packets_this_second"] += 1

        except Exception as e:
            print("UDP receive error:", e)


# ============================================================
# MAIN
# ============================================================
def main():
    global GAMMA_LEFT_LIMIT, GAMMA_RIGHT_LIMIT, INVERT_STEERING

    print("=" * 64)
    print(" Phone Tilt -> UDP -> Virtual DS4 ")
    print("=" * 64)
    ips = get_local_ips()
    if ips:
        print("Enter one of these IPs in the Android app:")
        for ip in ips:
            print(f"  {ip}:{UDP_PORT}")
    else:
        print("Could not auto-detect local IP. Use ipconfig manually.")
    print("=" * 64)

    threading.Thread(target=udp_receiver, daemon=True).start()

    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
    pygame.init()
    pygame.joystick.init()

    screen = pygame.display.set_mode((700, 420))
    pygame.display.set_caption("Tilt Steering Receiver")
    font = pygame.font.SysFont(None, 28)
    small_font = pygame.font.SysFont(None, 22)
    clock = pygame.time.Clock()

    print("Creating virtual DS4 controller...")
    gamepad = vg.VDS4Gamepad()
    print("Virtual DS4 controller created.")

    controller_count = pygame.joystick.get_count()
    controllers = []
    for i in range(controller_count):
        c = pygame.joystick.Joystick(i)
        c.init()
        controllers.append(c)
        print(f"Initialized physical controller {i}: {c.get_name()}")

    if not controllers:
        print("No physical controller found. Phone tilt will control steering by itself.")

    prev_left_x = 0.0
    prev_left_y = 0.0
    last_ui_update = 0.0
    last_rate_tick = time.time()
    packet_rate = 0
    
    invert_button_rect = pygame.Rect(450, 20, 220, 40)

    try:
        while True:
            # ------------------------------------------------------------
            # Pygame events
            # ------------------------------------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                        GAMMA_LEFT_LIMIT = max(1.0, GAMMA_LEFT_LIMIT - 1.0)
                        GAMMA_RIGHT_LIMIT = max(1.0, GAMMA_RIGHT_LIMIT - 1.0)
                        print(f"More sensitive -> limits L/R = {GAMMA_LEFT_LIMIT:.1f} / {GAMMA_RIGHT_LIMIT:.1f}")
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        GAMMA_LEFT_LIMIT += 1.0
                        GAMMA_RIGHT_LIMIT += 1.0
                        print(f"Less sensitive -> limits L/R = {GAMMA_LEFT_LIMIT:.1f} / {GAMMA_RIGHT_LIMIT:.1f}")
                    elif event.key == pygame.K_f:
                        INVERT_STEERING = not INVERT_STEERING
                        print(f"Invert steering set to {INVERT_STEERING}")
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if invert_button_rect.collidepoint(event.pos):
                            INVERT_STEERING = not INVERT_STEERING
                            print(f"Invert steering set to {INVERT_STEERING}")

            # ------------------------------------------------------------
            # Read latest tilt state
            # ------------------------------------------------------------
            with state_lock:
                seq = tilt_state["seq"]
                alpha = tilt_state["alpha"]
                beta = tilt_state["beta"]
                gamma = tilt_state["gamma"]
                gyro_x = tilt_state["x"]
                active = tilt_state["active"]
                last_packet_time = tilt_state["last_packet_time"]

            if active and (time.time() - last_packet_time > PACKET_TIMEOUT_SEC):
                with state_lock:
                    tilt_state["active"] = False
                    tilt_state["x"] = 0.0
                gyro_x = 0.0
                active = False

            if INVERT_STEERING:
                gyro_x = -gyro_x

            # packet rate
            now = time.time()
            if now - last_rate_tick >= 1.0:
                with state_lock:
                    packet_rate = tilt_state["packets_this_second"]
                    tilt_state["packets_this_second"] = 0
                last_rate_tick = now

            # ------------------------------------------------------------
            # Physical controller pass-through
            # ------------------------------------------------------------
            axis_0 = 0.0  # left stick X
            axis_1 = 0.0  # left stick Y
            axis_2 = 0.0  # right stick X
            axis_3 = 0.0  # right stick Y
            axis_4 = -1.0 # left trigger
            axis_5 = -1.0 # right trigger

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

            dpad_up = False
            dpad_down = False
            dpad_left = False
            dpad_right = False

            if controllers:
                c = controllers[0]

                num_axes = c.get_numaxes()
                num_buttons = c.get_numbuttons()

                if num_axes >= 1:
                    axis_0 = apply_deadzone(c.get_axis(0))
                if num_axes >= 2:
                    axis_1 = apply_deadzone(c.get_axis(1))
                if num_axes >= 3:
                    axis_2 = apply_deadzone(c.get_axis(2))
                if num_axes >= 4:
                    axis_3 = apply_deadzone(c.get_axis(3))
                if num_axes >= 5:
                    axis_4 = c.get_axis(4)
                if num_axes >= 6:
                    axis_5 = c.get_axis(5)

                if num_buttons >= 1 and c.get_button(0):
                    button_cross = True
                if num_buttons >= 2 and c.get_button(1):
                    button_circle = True
                if num_buttons >= 3 and c.get_button(2):
                    button_square = True
                if num_buttons >= 4 and c.get_button(3):
                    button_triangle = True
                if num_buttons >= 5 and c.get_button(4):
                    button_l1 = True
                if num_buttons >= 6 and c.get_button(5):
                    button_r1 = True
                if num_buttons >= 7 and c.get_button(6):
                    button_share = True
                if num_buttons >= 8 and c.get_button(7):
                    button_options = True
                if num_buttons >= 9 and c.get_button(8):
                    button_l3 = True
                if num_buttons >= 10 and c.get_button(9):
                    button_r3 = True

                if c.get_numhats() >= 1:
                    hat = c.get_hat(0)
                    if hat[1] == 1:
                        dpad_up = True
                    if hat[1] == -1:
                        dpad_down = True
                    if hat[0] == -1:
                        dpad_left = True
                    if hat[0] == 1:
                        dpad_right = True

            # ------------------------------------------------------------
            # Combine physical + phone steering
            # ------------------------------------------------------------
            raw_left_x = clamp(axis_0 + gyro_x, -1.0, 1.0)
            raw_left_y = clamp(axis_1, -1.0, 1.0)

            if ENABLE_SMOOTHING:
                alpha_x = ALPHA_TURN if abs(raw_left_x) > abs(prev_left_x) else ALPHA_RETURN
                left_stick_x = alpha_x * raw_left_x + (1 - alpha_x) * prev_left_x
                prev_left_x = left_stick_x

                alpha_y = ALPHA_TURN if abs(raw_left_y) > abs(prev_left_y) else ALPHA_RETURN
                left_stick_y = alpha_y * raw_left_y + (1 - alpha_y) * prev_left_y
                prev_left_y = left_stick_y
            else:
                left_stick_x = raw_left_x
                left_stick_y = raw_left_y
                prev_left_x = left_stick_x
                prev_left_y = left_stick_y

            # ------------------------------------------------------------
            # Map to virtual DS4
            # ------------------------------------------------------------
            gamepad.left_joystick(
                x_value=norm_to_ds4_byte(left_stick_x),
                y_value=norm_to_ds4_byte(left_stick_y)
            )

            gamepad.right_joystick(
                x_value=norm_to_ds4_byte(axis_2),
                y_value=norm_to_ds4_byte(axis_3)
            )

            gamepad.left_trigger(value=norm_to_ds4_byte(axis_4))
            gamepad.right_trigger(value=norm_to_ds4_byte(axis_5))

            if button_cross:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CROSS)

            if button_circle:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE)

            if button_square:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SQUARE)

            if button_triangle:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE)

            if button_l1:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT)

            if button_r1:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT)

            if button_share:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_SHARE)

            if button_options:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS)

            if button_l3:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT)

            if button_r3:
                gamepad.press_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)
            else:
                gamepad.release_button(button=vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT)

            if dpad_up and dpad_right:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST)
            elif dpad_down and dpad_right:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST)
            elif dpad_down and dpad_left:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST)
            elif dpad_up and dpad_left:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST)
            elif dpad_up:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH)
            elif dpad_down:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH)
            elif dpad_left:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST)
            elif dpad_right:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST)
            else:
                gamepad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)

            gamepad.update()

            # ------------------------------------------------------------
            # UI
            # ------------------------------------------------------------
            current_time = time.time()
            if current_time - last_ui_update > (1.0 / UI_FPS):
                last_ui_update = current_time
                screen.fill((28, 28, 28))

                status_color = (0, 220, 100) if active else (230, 70, 70)
                rows = [
                    (f"UDP Status: {'Connected' if active else 'Waiting / Disconnected'}", status_color),
                    (f"Seq: {seq}", (255, 255, 255)),
                    (f"Gamma: {gamma:+.2f} deg", (255, 255, 255)),
                    (f"Mapped Gyro X: {gyro_x:+.3f}", (255, 255, 255)),
                    (f"Physical Stick X: {axis_0:+.3f}", (255, 255, 255)),
                    (f"Combined Left X: {left_stick_x:+.3f}", (255, 255, 255)),
                    (f"Beta: {beta:+.2f} deg", (180, 180, 180)),
                    (f"Alpha: {alpha:+.2f} deg", (180, 180, 180)),
                    (f"Packet Rate: {packet_rate} Hz", (255, 255, 100)),
                    (f"Limits L/R: {GAMMA_LEFT_LIMIT:.1f} / {GAMMA_RIGHT_LIMIT:.1f}", (255, 255, 100)),
                    ("Press +/- to adjust sensitivity", (150, 150, 150)),
                ]

                y = 20
                for text, color in rows:
                    surf = font.render(text, True, color)
                    screen.blit(surf, (20, y))
                    y += 34

                # Draw invert button
                btn_color = (80, 160, 80) if INVERT_STEERING else (160, 80, 80)
                pygame.draw.rect(screen, btn_color, invert_button_rect, border_radius=6)
                btn_text = small_font.render(f"Invert Steering: {'ON' if INVERT_STEERING else 'OFF'} (Press F)", True, (255, 255, 255))
                btn_text_rect = btn_text.get_rect(center=invert_button_rect.center)
                screen.blit(btn_text, btn_text_rect)

                small = small_font.render("Phone tilt is added to physical left-stick X.", True, (170, 170, 170))
                screen.blit(small, (20, 380))

                pygame.display.flip()

            clock.tick(LOOP_HZ)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        try:
            gamepad.reset()
            gamepad.update()
        except Exception:
            pass
        pygame.quit()
        print("Virtual controller disconnected.")


if __name__ == "__main__":
    main()