import unittest
import random
import struct
from buffer import Steam2PacketBuffer


def _generate_packet(size, seq):
    header = struct.pack('!HL', size, seq)
    data = bytes(random.getrandbits(8) for _ in range(size))
    return header, data


class Stream2PacketTest(unittest.TestCase):

    def test_empty(self):
        s2p = Steam2PacketBuffer()
        s2p.append_raw_data(b'')
        self.assertEqual(s2p.get_first_packet_seq(), -1)
        self.assertEqual(s2p.read_packet(), [])
        self.assertEqual(s2p.read_packet(10), [])

    def test_complete_packet(self):
        s2p = Steam2PacketBuffer()
        size, seq = 321, 123
        header, data = _generate_packet(size, seq)
        s2p.append_raw_data(header + data)
        self.assertEqual(s2p.read_packet(), [(seq, data)])
        self.assertEqual(s2p.read_packet(), [])

        size1, seq1 = 111, 333
        size2, seq2 = 222, 444
        header1, data1 = _generate_packet(size1, seq1)
        header2, data2 = _generate_packet(size2, seq2)
        s2p.append_raw_data(header1)
        s2p.append_raw_data(data1)
        s2p.append_raw_data(header2)
        s2p.append_raw_data(data2)
        self.assertEqual(s2p.read_packet(), [(seq1, data1)])
        self.assertEqual(s2p.read_packet(), [(seq2, data2)])
        self.assertEqual(s2p.read_packet(), [])

    def test_incomplete_packet(self):
        s2p = Steam2PacketBuffer()
        size, seq = 123, 321
        header, data = _generate_packet(size, seq)
        # incomplete header
        s2p.append_raw_data(header[:3])
        self.assertEqual(s2p.get_first_packet_seq(), -1)
        self.assertEqual(s2p.read_packet(), [])
        # still incomplete header
        s2p.append_raw_data(header[3:5])
        self.assertEqual(s2p.get_first_packet_seq(), -1)
        self.assertEqual(s2p.read_packet(), [])
        # header complete but no data
        s2p.append_raw_data(header[5:6])
        self.assertEqual(s2p.get_first_packet_seq(), -1)
        self.assertEqual(s2p.read_packet(), [])
        # incomplete data
        s2p.append_raw_data(data[:size // 2])
        self.assertEqual(s2p.get_first_packet_seq(), -1)
        self.assertEqual(s2p.current_seq, seq)
        self.assertEqual(s2p.packet_remain_bytes, len(data) - size // 2)
        self.assertEqual(s2p.read_packet(), [])
        # packet complete, but also contain data from next packet
        incomplete_header = b'12321'
        s2p.append_raw_data(data[size // 2:] + b'12321')
        self.assertEqual(s2p.get_first_packet_seq(), seq)
        self.assertEqual(s2p.read_packet(), [(seq, data)])
        self.assertEqual(s2p.incomplete_packet_header, incomplete_header)
        self.assertEqual(s2p.read_packet(), [])

    def test_random(self):
        s2p = Steam2PacketBuffer()
        send_data = []
        for _ in range(random.randint(0, 100)):
            size, seq = random.randint(0, 30), random.randint(0, 1000)
            header, data = _generate_packet(size, seq)
            send_data.append((size, seq, header, data))
        recv_data = b''.join(h + d for _, _, h, d in send_data)
        pos, total_len = 0, len(recv_data)
        while pos < total_len:
            recv_len = random.randint(0, 50)
            s2p.append_raw_data(recv_data[pos: pos + recv_len])
            pos += recv_len

        self.assertEqual(s2p.num_ready_packet(), len(send_data))
        for send_packet in send_data:
            size, seq, _, data = send_packet
            recv_packet = s2p.read_packet()
            self.assertEqual(len(recv_packet), 1)
            r_seq, r_data = recv_packet[0]
            self.assertEqual(r_seq, seq)
            self.assertEqual(r_data, data)
        self.assertEqual(s2p.num_ready_packet(), 0)
        self.assertEqual(s2p.read_packet(), [])


if __name__ == '__main__':
    unittest.main()
