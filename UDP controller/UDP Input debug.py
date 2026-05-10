import socket
import struct
import time
import threading

UDP_IP = "0.0.0.0"
UDP_PORT = 9000
PRINT_INTERVAL = 0.5

PACKET_FORMAT = ">iqfff"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)

latest = {
    "seq": 0,
    "alpha": 0.0,
    "beta": 0.0,
    "gamma": 0.0,
    "connected": False,
}
lock = threading.Lock()

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

def receive_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, _ = sock.recvfrom(1024)
        if len(data) < PACKET_SIZE:
            continue

        seq, ts_ns, alpha, beta, gamma = struct.unpack(PACKET_FORMAT, data[:PACKET_SIZE])

        with lock:
            latest["seq"] = seq
            latest["alpha"] = alpha
            latest["beta"] = beta
            latest["gamma"] = gamma
            latest["connected"] = True

print("=" * 64)
print("GyroStreamer Receiver — alpha/beta/gamma mode")
print("=" * 64)

ips = get_local_ips()
if ips:
    print("\nEnter one of these IPs in your phone app:")
    for ip in ips:
        print(f"  {ip}:{UDP_PORT}")
else:
    print("\nCould not auto-detect local IP. Use ipconfig manually.")

print("\nWaiting for packets...\n")

threading.Thread(target=receive_loop, daemon=True).start()

try:
    while True:
        with lock:
            connected = latest["connected"]
            seq = latest["seq"]
            alpha = latest["alpha"]
            beta = latest["beta"]
            gamma = latest["gamma"]

        if connected:
            print(
                f"SEQ={seq:<8}  "
                f"ALPHA={alpha:+8.2f}°  "
                f"BETA={beta:+8.2f}°  "
                f"GAMMA={gamma:+8.2f}°"
            )
        else:
            print("No packets yet...")

        time.sleep(PRINT_INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")