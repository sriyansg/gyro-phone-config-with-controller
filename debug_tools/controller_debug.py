import pygame
import sys

def main():
    # Initialize Pygame
    pygame.init()
    pygame.joystick.init()

    # Check for connected controllers
    controller_count = pygame.joystick.get_count()
    print(f"Found {controller_count} controller(s) connected\n")

    if controller_count == 0:
        print("No controllers detected. Please connect your controllers and try again.")
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
    print("Listening for controller input... (Press Ctrl+C to exit)")
    print("=" * 60 + "\n")

    # Main event loop
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                # Button press
                elif event.type == pygame.JOYBUTTONDOWN:
                    controller_name = controllers[event.joy].get_name()
                    print(f"[Controller {event.joy}] ({controller_name}) Button {event.button} PRESSED")

                # Button release
                elif event.type == pygame.JOYBUTTONUP:
                    controller_name = controllers[event.joy].get_name()
                    print(f"[Controller {event.joy}] ({controller_name}) Button {event.button} RELEASED")

                # Axis motion (analog sticks, triggers)
                elif event.type == pygame.JOYAXISMOTION:
                    # Only show axis movement if it's significant (to reduce spam)
                    if abs(event.value) > 0.1:
                        controller_name = controllers[event.joy].get_name()
                        print(f"[Controller {event.joy}] ({controller_name}) Axis {event.axis}: {event.value:.3f}")

                # Hat (D-pad) motion
                elif event.type == pygame.JOYHATMOTION:
                    controller_name = controllers[event.joy].get_name()
                    print(f"[Controller {event.joy}] ({controller_name}) Hat {event.hat}: {event.value}")

                # Controller connected/disconnected
                elif event.type == pygame.JOYDEVICEADDED:
                    print(f"\n*** Controller {event.device_index} CONNECTED ***\n")

                elif event.type == pygame.JOYDEVICEREMOVED:
                    print(f"\n*** Controller {event.instance_id} DISCONNECTED ***\n")

            # Small delay to prevent excessive CPU usage
            pygame.time.wait(10)

    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()
