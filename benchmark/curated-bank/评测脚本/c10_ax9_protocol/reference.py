def crc16_xmodem(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode(payload: bytes) -> bytes:
    body = bytes([len(payload)]) + payload + crc16_xmodem(payload).to_bytes(2, "big")
    out = bytearray([0x7E])
    for b in body:
        if b == 0x7E:
            out += b"\x7d\x5e"
        elif b == 0x7D:
            out += b"\x7d\x5d"
        else:
            out.append(b)
    out.append(0x7E)
    return bytes(out)


def decode(frame: bytes) -> bytes:
    if len(frame) < 4 or frame[0] != 0x7E or frame[-1] != 0x7E:
        raise ValueError("frame boundary missing")
    body = frame[1:-1]
    out = bytearray()
    i = 0
    while i < len(body):
        b = body[i]
        if b == 0x7D:
            if i + 1 >= len(body):
                raise ValueError("stray escape")
            nxt = body[i + 1]
            if nxt == 0x5E:
                out.append(0x7E)
            elif nxt == 0x5D:
                out.append(0x7D)
            else:
                raise ValueError("bad escape")
            i += 2
        elif b == 0x7E:
            raise ValueError("unescaped 0x7E inside frame")
        else:
            out.append(b)
            i += 1
    if len(out) < 3:
        raise ValueError("frame too short")
    plen = out[0]
    if len(out) != 1 + plen + 2:
        raise ValueError("length mismatch")
    payload = bytes(out[1 : 1 + plen])
    crc = int.from_bytes(out[1 + plen : 1 + plen + 2], "big")
    if crc16_xmodem(payload) != crc:
        raise ValueError("crc mismatch")
    return payload
