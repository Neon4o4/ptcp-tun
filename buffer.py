import struct
from typing import Tuple, List

'''
Packet format:
header (6 bytes)
    length of data  2B
    sequence number 4B
data `length of data` bytes
'''
PACKET_HEADER_FORMAT = '!HL'  # unsigned short, 2 bytes, big-endian (network)
PACKET_HEADER_SIZE = 6


# TODO: verify each new client -> server

class Steam2PacketBuffer:
    def __init__(self):
        self.current_seq: int = -1
        self.header_remain_bytes: int = 0
        self.incomplete_packet_header: bytes = b''
        self.incomplete_packet_data: bytes = b''
        self.packet_remain_bytes: int = 0
        self.unread_packets: List[Tuple[int, bytes]] = []

    def append_raw_data(self, data: bytes):
        if self.header_remain_bytes > 0:
            chunk_size_s, data = data[:self.header_remain_bytes], data[self.header_remain_bytes:]
            self.incomplete_packet_header += chunk_size_s
            self.header_remain_bytes -= len(chunk_size_s)
            if self.header_remain_bytes <= 0:
                self.packet_remain_bytes, self.current_seq \
                    = struct.unpack(PACKET_HEADER_FORMAT, self.incomplete_packet_header)
                self.incomplete_packet_header = b''
                self.header_remain_bytes = 0
            else:
                return

        assert (self.header_remain_bytes == 0 and self.incomplete_packet_header == b'')

        if self.packet_remain_bytes > 0 and len(data) > 0:
            last_packet, data = data[:self.packet_remain_bytes], data[self.packet_remain_bytes:]
            self.incomplete_packet_data += last_packet
            self.packet_remain_bytes -= len(last_packet)
            if self.packet_remain_bytes <= 0:
                self.unread_packets.append((self.current_seq, self.incomplete_packet_data))
                self.current_seq = -1
                self.incomplete_packet_data = b''
        # here, at most 1 of the following holds:
        #  1. self.packet_remain_bytes is 0: data in last packet is read,
        #     we may still have some (complete or in complete) packets
        #  2. self.packet_remain_bytes is not 0 ( > 0): which means, the original `data` contains less data than
        #     expected by `self.packet_remain_bytes`, hence len(data) will be 0 and we do not need to do anything
        packet_data_size: int
        while len(data) > 0:
            # if len(data) > 0, we must have read all data from last packet,
            #   otherwise len(data) should be 0 because in last `if` we tried to read all remaining data in last packet
            #   and thus, we also have `self.packet_remain_bytes` is 0, which means clean buffer for header and data
            assert (
                    self.packet_remain_bytes == 0 and
                    self.current_seq == -1 and
                    self.incomplete_packet_header == b'' and
                    self.incomplete_packet_data == b''
            )
            header_s, data = data[:PACKET_HEADER_SIZE], data[PACKET_HEADER_SIZE:]
            if len(header_s) < PACKET_HEADER_SIZE:
                self.header_remain_bytes = PACKET_HEADER_SIZE - len(header_s)
                self.incomplete_packet_header = header_s
                return

            packet_data_size, seq = struct.unpack(PACKET_HEADER_FORMAT, header_s)
            packet_data, data = data[:packet_data_size], data[packet_data_size:]
            if len(packet_data) == packet_data_size:
                self.unread_packets.append((seq, packet_data))
            else:
                # all data read, but there is still data to read for current packet
                #   keep these data and continue
                self.current_seq = seq
                self.incomplete_packet_data = packet_data
                self.packet_remain_bytes = packet_data_size - len(packet_data)

    def get_first_packet_seq(self) -> int:
        """
        get the seq number of the first unread packet
        :return: seq of first packet, or -1 if no packet is ready
        """
        return self.unread_packets[0][0] if self.unread_packets else -1

    def num_ready_packet(self) -> int:
        """
        :return: the number of packets that are ready to be read
        """
        return len(self.unread_packets)

    def read_packet(self, count: int = 1) -> List[Tuple[int, bytes]]:
        rtn, self.unread_packets = self.unread_packets[:count], self.unread_packets[count:]
        return rtn


class Packet2StreamBuffer:
    def __init__(self):
        self.unread_stream_data: List[bytes] = []

    def append_packet(self, seq: int, data: bytes):
        data_len: int = len(data)
        packet_header = struct.pack(PACKET_HEADER_FORMAT, data_len, seq)
        self.unread_stream_data.append(packet_header)
        self.unread_stream_data.append(data)

    def read_stream_data(self, size: int = -1) -> bytes:
        if size == 0 or len(self.unread_stream_data) == 0:
            return b''
        current_total_len: int = sum((len(d) for d in self.unread_stream_data))
        if size < 0 or size >= current_total_len:
            data = b''.join(self.unread_stream_data)
            self.unread_stream_data = []
            return data
        len_sum = 0
        idx = 0
        while idx < len(self.unread_stream_data) and len_sum < size:
            len_sum += len(self.unread_stream_data[idx])
            idx += 1

        # note that 0 <= size < current_total_len
        data, self.unread_stream_data = self.unread_stream_data[:idx], self.unread_stream_data[idx:]
        data = b''.join(data)
        data_rtn, data_keep = data[:size], data[size:]
        self.unread_stream_data.insert(0, data_keep)
        return data_rtn
