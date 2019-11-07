import socket
import select
from collections import defaultdict

from buffer import Steam2PacketBuffer

listen_addr = ('0.0.0.0', 1234)
remote_addr = ('127.0.0.1', 4321)
target_addr = ('127.0.0.1', 1080)

chunk_size = 1024 * 32
listen_backlog = 256
outgoing_incoming_rate = 2
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
    incoming_sending_seq = defaultdict(lambda: 1)  # incoming socket -> last send
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
                for _ in range(outgoing_incoming_rate):
                    outgoing = socket.socket()
                    outgoing.connect(remote_addr)
                    outgoing_socks_map[outgoing] = incoming
                    read_socks.append(outgoing)
                    write_socks.append(outgoing)
                    exp_socks.append(outgoing)

                read_socks.append(incoming)
                write_socks.append(incoming)
                exp_socks.append(incoming)
                continue
            if r_sock in incoming_socks:
                # client sending data
                sending_seq = incoming_sending_seq[r_sock] + 1
                data = r_sock.recv(chunk_size)
                incoming_sending_caches[r_sock].append((sending_seq, data))
                incoming_sending_seq[r_sock] = sending_seq
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
