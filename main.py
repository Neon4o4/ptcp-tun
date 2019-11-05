import socket
import select
from collections import defaultdict

listen_addr = ('0.0.0.0', 1234)
remote_addr = ('127.0.0.1', 4321)
target_addr = ('127.0.0.1', 1080)

chunk_size = 1024 * 32
listen_backlog = 256

'''
For client
application  --incoming--> client --outgoing--> server
=========
For server
client --incoming--> server --outgoing--> target 
'''


def client():
    incoming_socks = set()
    incoming_sending_caches = defaultdict(list)  # incoming socket -> [ (seq, bytes) ]
    incoming_sending_seq = defaultdict(lambda: 0)  # incoming socket -> last send
    outgoing_socks_map = {}  # outgoing socket -> incoming socket (n -> 1 mapping)
    read_socks, write_socks, exp_socks = [], [], []
    listen_sock = socket.socket()
    listen_sock.bind(listen_addr)
    listen_sock.listen(listen_backlog)
    read_socks.append(listen_sock)
    while True:
        r, w, x = select.select(read_socks, write_socks, exp_socks)
        for r_sock in r:
            if r_sock is listen_sock:
                # client new connection
                incoming, _ = r_sock.accept()
                incoming_socks.add(incoming)
                continue
            if r_sock in incoming_socks:
                # client sending data
                last_chunk = incoming_sending_caches.get(r_sock)
                if not last_chunk:
                    max_sending_seq = 1
                else:
                    max_sending_seq = last_chunk[-1] + 1
                data = r_sock.recv(chunk_size)
                if last_chunk is None:
                    incoming_sending_caches[r_sock] = []
                incoming_sending_caches[r_sock].append((max_sending_seq, data))
            else:
                # server replying data
                in_sock = outgoing_socks_map.get(r_sock, None)
                if in_sock is None:
                    r_sock.close()
                    read_socks.remove(r_sock)
                    continue


def server():
    pass


def main():
    client()


if __name__ == '__main__':
    main()
