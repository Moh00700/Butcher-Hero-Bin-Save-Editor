#!/usr/bin/env python3
"""Recompute the integrity hash of game_data.bin. No values are changed.

  python3 resign.py game_data.bin [out.bin]   re-sign (default out: <name>_resigned.bin)
  python3 resign.py game_data.bin --verify    only check whether the hash is valid

Hash = MD5(data_bytes + msgpack_str(HASH_SALT) + msgpack_int(salt, minimal width)), as AA-BB-...
"""
import sys, struct, hashlib

K = b'5b5496vn7456oodw976d95mo'  # UdRoot.HASH_SALT


def skip(b, i):
    """Return the offset just after the MessagePack value starting at i."""
    t = b[i]; i += 1
    if t < 0x80 or t >= 0xe0 or t in (0xc0, 0xc2, 0xc3): return i
    if 0x80 <= t <= 0x8f:
        for _ in range((t & 15) * 2): i = skip(b, i)
        return i
    if 0x90 <= t <= 0x9f:
        for _ in range(t & 15): i = skip(b, i)
        return i
    if 0xa0 <= t <= 0xbf: return i + (t & 31)
    fixed = {0xca: 4, 0xcb: 8, 0xcc: 1, 0xcd: 2, 0xce: 4, 0xcf: 8, 0xd0: 1, 0xd1: 2, 0xd2: 4, 0xd3: 8,
             0xd4: 2, 0xd5: 3, 0xd6: 5, 0xd7: 9, 0xd8: 17}
    if t in fixed: return i + fixed[t]
    if t in (0xc4, 0xd9): return i + 1 + b[i]
    if t in (0xc5, 0xda): return i + 2 + struct.unpack('>H', b[i:i + 2])[0]
    if t in (0xdc, 0xde):
        n = struct.unpack('>H', b[i:i + 2])[0]; i += 2
        for _ in range(n * (2 if t == 0xde else 1)): i = skip(b, i)
        return i
    raise ValueError('unsupported MessagePack type 0x%02x' % t)


def read_int(b, i):
    t = b[i]
    if t < 0x80: return t
    if t >= 0xe0: return t - 256
    f = {0xcc: '>B', 0xcd: '>H', 0xce: '>I', 0xcf: '>Q', 0xd0: '>b', 0xd1: '>h', 0xd2: '>i', 0xd3: '>q'}[t]
    return struct.unpack(f, b[i + 1:i + 1 + struct.calcsize(f)])[0]


def enc_int(v):
    """Minimal-width MessagePack integer (how the game encodes the salt for hashing)."""
    if 0 <= v < 128: return bytes([v])
    if -32 <= v < 0: return struct.pack('>b', v)
    if v >= 0:
        for c, f, m in ((0xcc, '>B', 1 << 8), (0xcd, '>H', 1 << 16), (0xce, '>I', 1 << 32), (0xcf, '>Q', 1 << 64)):
            if v < m: return bytes([c]) + struct.pack(f, v)
    for c, f, lo in ((0xd0, '>b', -1 << 7), (0xd1, '>h', -1 << 15), (0xd2, '>i', -1 << 31), (0xd3, '>q', -1 << 63)):
        if v >= lo: return bytes([c]) + struct.pack(f, v)
    raise ValueError('integer out of range')


def compute(b):
    """Return (hash_offset, new_hash_bytes) for the save in b."""
    d = b.index(b'\xa4data') + 5                       # start of the "data" value
    end = skip(b, d)
    salt = read_int(b, b.index(b'\xa4salt') + 5)
    h = hashlib.md5(bytes(b[d:end]) + bytes([0xa0 | len(K)]) + K + enc_int(salt)).digest()
    return b.index(b'\xa4hash\xd9\x2f') + 7, '-'.join('%02X' % x for x in h).encode()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    b = bytearray(open(src, 'rb').read())
    pos, new = compute(b)
    valid = bytes(b[pos:pos + 47]) == new
    if len(sys.argv) > 2 and sys.argv[2] == '--verify':
        print('hash valid:', valid); sys.exit()
    out = sys.argv[2] if len(sys.argv) > 2 else (src[:-4] if src.endswith('.bin') else src) + '_resigned.bin'
    b[pos:pos + 47] = new
    open(out, 'wb').write(b)
    print(f'hash was {"already valid" if valid else "invalid/outdated"}; re-signed -> {out}')
