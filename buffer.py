import struct

CHUNK_SIZE_FORMAT = '!H'  # unsigned short, 2 bytes, big-endian (network)
CHUNK_SIZE_SIZE = 2


class Chunk2StreamBuffer:
    def __init__(self):
        self.chunk_size_remain_bytes = 0
        self.chunk_size_parts = b''
        self.chunk_remain_bytes = 0
        self.unread_bytes = []

    def append_raw_data(self, data: bytes):
        if self.chunk_size_remain_bytes > 0:
            chunk_size_s, data = data[:self.chunk_size_remain_bytes], data[self.chunk_size_remain_bytes:]
            self.chunk_size_parts += chunk_size_s
            self.chunk_size_remain_bytes -= len(chunk_size_s)
            if self.chunk_size_remain_bytes <= 0:
                self.chunk_remain_bytes, = struct.unpack(CHUNK_SIZE_FORMAT, self.chunk_size_parts)
                self.chunk_size_parts = b''
                self.chunk_size_remain_bytes = 0
            else:
                return

        if self.chunk_remain_bytes > 0 and len(data) > 0:
            last_chunk, data = data[:self.chunk_remain_bytes], data[self.chunk_remain_bytes:]
            self.unread_bytes.append(last_chunk)
            self.chunk_remain_bytes -= len(last_chunk)
        # here, at most 1 of the following holds:
        #  1. self.chunk_remain_bytes is 0: data in last chunk is read,
        #     we may still have some (complete or in complete) chunks
        #  2. self.chunk_remain_bytes is not 0 ( > 0): which means, the original `data` contains less data than
        #     expected by `self.chunk_remain_bytes`, hence len(data) will be 0 and we do not need to do anything
        size: int
        while len(data) > 0:
            size_s, data = data[:CHUNK_SIZE_SIZE], data[CHUNK_SIZE_SIZE:]
            if len(size_s) < CHUNK_SIZE_SIZE:
                self.chunk_size_remain_bytes = CHUNK_SIZE_SIZE - len(size_s)
                self.chunk_size_parts = size_s
                return

            size, = struct.unpack(CHUNK_SIZE_FORMAT, size_s)
            chunk, data = data[:size], data[size:]
            self.unread_bytes.append(chunk)
            self.chunk_remain_bytes = size - len(chunk)

    def get_ready_size(self):
        return sum((len(d) for d in self.unread_bytes))

    def read(self, size: int = -1):
        if size == 0 or len(self.unread_bytes) == 0:
            return b''
        if size < 0:
            data = b''.join(self.unread_bytes)
            self.unread_bytes = []
            return data
        len_sum = 0
        idx = 0
        while idx < len(self.unread_bytes) and len_sum < size:
            idx += 1
            len_sum += len(self.unread_bytes[idx])
        if len_sum <= size:
            data, self.unread_bytes = self.unread_bytes[:idx], self.unread_bytes[idx:]
            return b''.join(data)
        else:
            data, self.unread_bytes = self.unread_bytes[:idx], self.unread_bytes[idx:]
            data = b''.join(data)
            data_rtn, data_keep = data[:size], data[size:]
            self.unread_bytes.insert(0, data_keep)
            return data_rtn


class Stream2ChunkBuffer:
    # TODO
    def __init__(self):
        pass
