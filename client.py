import socket
import threading
import json
import pygame
import struct
from config import PORT, DISCOVERY_PORT, DISCOVERY_MESSAGE, RESPONSE_MESSAGE

WIDTH, HEIGHT = 800, 600
PLAYER_RADIUS = 15
MOVE_SPEED = 5

players = {}
player_id = None


def discover_server(timeout=3):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.settimeout(timeout)

    udp_sock.sendto(DISCOVERY_MESSAGE.encode(), ('<broadcast>', DISCOVERY_PORT))
    try:
        data, addr = udp_sock.recvfrom(1024)
        if data.decode() == RESPONSE_MESSAGE:
            return addr[0]
    except socket.timeout:
        return None


def send_msg(sock, data_dict):
    encoded = json.dumps(data_dict).encode()
    length = struct.pack('>I', len(encoded))
    sock.sendall(length + encoded)


def recv_msg(sock):
    try:
        raw_len = sock.recv(4)
        if not raw_len:
            return None
        msg_len = struct.unpack('>I', raw_len)[0]
        data = b''
        while len(data) < msg_len:
            chunk = sock.recv(msg_len - len(data))
            if not chunk:
                return None
            data += chunk
        return json.loads(data.decode())
    except:
        return None


def listen_to_server(sock):
    global players
    while True:
        data = recv_msg(sock)
        if data is None:
            break
        players = data.get('players', {})


def main():
    global player_id

    server_ip = discover_server()
    if not server_ip:
        print("No server found.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_ip, PORT))
    player_id = str(sock.getsockname())  # Match server’s key format

    threading.Thread(target=listen_to_server, args=(sock,), daemon=True).start()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    running = True
    while running:
        dx, dy = 0, 0
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            dx -= MOVE_SPEED
        if keys[pygame.K_RIGHT]:
            dx += MOVE_SPEED
        if keys[pygame.K_UP]:
            dy -= MOVE_SPEED
        if keys[pygame.K_DOWN]:
            dy += MOVE_SPEED

        send_msg(sock, {"move": [dx, dy]})

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))

        for pid, pdata in players.items():
            x, y = pdata['pos']
            color = (0, 255, 0) if pid == player_id else (255, 255, 255)
            pygame.draw.circle(screen, color, (int(x), int(y)), PLAYER_RADIUS)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sock.close()


if __name__ == "__main__":
    main()
