# pc/app/net/net_discovery.py
import socket
import threading

DISCOVERY_PORT = 37020


def _get_local_ip_for_peer(peer_ip: str) -> str:
    """Infer local outbound IP for the peer's subnet (no actual packets sent)."""
    tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        tmp.connect((peer_ip, 9))
        return tmp.getsockname()[0]
    finally:
        tmp.close()


def start_discovery_responder(http_port: int, daemon: bool = True) -> threading.Thread:
    """
    Start a UDP discovery responder:
      - Phone sends: FIND_PHONECAM_SERVER
      - PC replies:  PHONECAM_SERVER http://<ip>:<port>
    """
    def run():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", DISCOVERY_PORT))
        while True:
            data, addr = s.recvfrom(1024)
            msg = data.decode("utf-8", errors="ignore").strip()
            if msg == "FIND_PHONECAM_SERVER":
                ip = _get_local_ip_for_peer(addr[0])
                reply = f"PHONECAM_SERVER http://{ip}:{http_port}"
                s.sendto(reply.encode("utf-8"), addr)

    t = threading.Thread(target=run, daemon=daemon)
    t.start()
    return t