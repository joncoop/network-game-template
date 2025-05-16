import socket
import threading
import json
import struct
import tkinter as tk
from tkinter import messagebox
from config import HOST, PORT, DISCOVERY_PORT, DISCOVERY_MESSAGE, RESPONSE_MESSAGE

# Define server globals
players = {}
clients = {}

# Create the main application window
root = tk.Tk()
root.title("Game Server")

# Create a Text widget to display server messages
text_area = tk.Text(root, height=15, width=50)
text_area.pack(padx=10, pady=10)

# Function to update the text area
def update_text_area(message):
    text_area.insert(tk.END, message + '\n')
    text_area.yview(tk.END)

# UDP discovery listener
def listen_for_discovery():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_sock.bind(("", DISCOVERY_PORT))
    update_text_area(f"Listening for discovery on UDP port {DISCOVERY_PORT}")

    while True:
        data, addr = udp_sock.recvfrom(1024)
        if data.decode() == DISCOVERY_MESSAGE:
            update_text_area(f"Discovery request from {addr}")
            udp_sock.sendto(RESPONSE_MESSAGE.encode(), addr)

# Function to receive a message
def recv_msg(conn):
    raw_len = conn.recv(4)
    if not raw_len:
        return None
    msg_len = struct.unpack('>I', raw_len)[0]
    data = b''
    while len(data) < msg_len:
        more = conn.recv(msg_len - len(data))
        if not more:
            return None
        data += more
    return data

# Function to send a message
def send_msg(conn, data):
    msg = struct.pack('>I', len(data)) + data
    conn.sendall(msg)

# Handle client connections
def handle_client(conn, addr):
    player_id = str(addr)
    players[player_id] = {'pos': [100, 100], 'angle': 0}
    clients[player_id] = conn
    update_text_area(f"[+] New connection: {addr}")

    try:
        while True:
            msg_data = recv_msg(conn)
            if not msg_data:
                break
            message = json.loads(msg_data.decode())
            dx, dy = message.get('move', [0, 0])
            players[player_id]['pos'][0] += dx
            players[player_id]['pos'][1] += dy

            state = json.dumps({'players': players}).encode()
            for c in clients.values():
                send_msg(c, state)
    except Exception as e:
        update_text_area(f"[-] Error with {addr}: {e}")
    finally:
        conn.close()
        clients.pop(player_id, None)
        players.pop(player_id, None)
        update_text_area(f"[-] Connection closed: {addr}")

# Start the server
def start_server():
    # Start the UDP discovery listener thread
    threading.Thread(target=listen_for_discovery, daemon=True).start()

    # Set up TCP server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    update_text_area(f"Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        update_text_area(f"Connection from {addr}")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

# Function to start the server in a new thread
def start_server_thread():
    threading.Thread(target=start_server, daemon=True).start()

# Function to stop the server gracefully
def stop_server():
    # Close all connections and clean up
    for conn in clients.values():
        conn.close()
    update_text_area("Server stopped.")
    root.quit()

# Add start and stop buttons to the GUI
start_button = tk.Button(root, text="Start Server", command=start_server_thread)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Stop Server", command=stop_server)
stop_button.pack(pady=5)

# Set up the window to keep it running
root.protocol("WM_DELETE_WINDOW", stop_server)
root.mainloop()
