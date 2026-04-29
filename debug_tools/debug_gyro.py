import json
import asyncio
import websockets
import threading
import ssl
import http.server
import socketserver
import os
import socket
import functools
import time
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
WEB_DIR = os.path.join(PROJECT_ROOT, "web_controller", "web")
HTTP_PORT = 8000
WS_PORT = 8001

class SecureHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_http_server(cert_file, key_file):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WEB_DIR)
    httpd = SecureHTTPServer(("", HTTP_PORT), handler)
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"HTTPS Server running on https://0.0.0.0:{HTTP_PORT}")
    httpd.serve_forever()

async def ws_handler(websocket):
    print("\n--- WebSocket client connected! ---")
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                if len(message) == 12:
                    alpha, beta, gamma = struct.unpack('<fff', message)
                else:
                    continue
            else:
                data = json.loads(message)
                alpha = data.get('alpha', 0)
                beta = data.get('beta', 0)
                gamma = data.get('gamma', 0)
            
            # Print with carriage return (\r) to overwrite the same line for readability
            print(f"\rAlpha (Z): {alpha:7.2f} | Beta (X/Pitch): {beta:7.2f} | Gamma (Y/Roll): {gamma:7.2f}", end="")
            
    except websockets.exceptions.ConnectionClosed:
        print("\n\n--- WebSocket client disconnected. ---")
    except Exception as e:
        print(f"\nWebSocket error: {e}")

async def ws_server(cert_file, key_file):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT, ssl=context):
        print(f"WebSocket Server running on wss://0.0.0.0:{WS_PORT}")
        await asyncio.Future()

def start_ws_server(cert_file, key_file):
    asyncio.run(ws_server(cert_file, key_file))

def main():
    cert_path = os.path.join(PROJECT_ROOT, "certs", "cert.pem")
    key_path = os.path.join(PROJECT_ROOT, "certs", "key.pem")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print("Error: cert.pem or key.pem not found. Run generate_cert.py first.")
        return

    # Start HTTPS server
    http_thread = threading.Thread(target=start_http_server, args=(cert_path, key_path), daemon=True)
    http_thread.start()

    # Start WebSocket server
    ws_thread = threading.Thread(target=start_ws_server, args=(cert_path, key_path), daemon=True)
    ws_thread.start()

    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("=" * 60)
    print(f"DEBUG MODE - READING GYRO INPUTS")
    print(f"1. Connect your phone to the same Wi-Fi network.")
    print(f"2. Go to: https://{local_ip}:{HTTP_PORT}")
    print(f"3. Press 'Connect & Start Gyro' in the web app.")
    print("=" * 60)

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
