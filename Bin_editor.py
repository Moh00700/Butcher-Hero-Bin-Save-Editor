#!/usr/bin/env python3
"""Edit values in game_data.bin and re-sign it so the game accepts it.

  python3 save_tool.py in.bin --verify                    check the hash
  python3 save_tool.py in.bin --list [filter]             list every editable value
  python3 save_tool.py in.bin --timers [filter]           show spawner / respawn / cooldown timers
  python3 save_tool.py in.bin out.bin PATH=VALUE ...      edit values + re-sign
  python3 save_tool.py in.bin out.bin --respawn [filter] [--in 30m] [--all]
  python3 save_tool.py in.bin out.bin --refill [filter]   (experimental) top up spawner charges

PATH uses "/" between levels. Items in a list are addressed by their key:
  player/gems=100000          (bare names are treated as player/...)
  player/deaths_count=0
  player/seen_boss_tutorial=true
  player/items/knife/level=10
  currency/balances/soul.common=99999
The value keeps its original type: true/false for booleans, whole numbers for
integers, any number for decimal fields.

TIMER FIELDS also accept times, relative to the REAL current time:
  now   +30m   +2h   -1d   +90s   0 (= ready now)
Seconds / milliseconds / .NET ticks are detected automatically.

SPAWNERS (trees, ice, chests-of-ore ...) live under spawners/spawners_v3/<name>
as 7 numbers; they can be addressed by name:
  last_spawn_time  saved_count  remaining_charges  next_big_spawn_time
  cleared_once  charges_sync_period  known_max_charges
e.g.  "spawners/spawners_v3/tree_1 (1)_cab298/next_big_spawn_time=0"

--respawn  makes depleted spawners (the ones with a respawn timer running) ready:
           timer -> 0 (ready on next load), or -> now + --in DURATION.
           [filter] matches the spawner name, e.g. tree, ice, dragon, Spawner_1.
           --all also rewrites spawners that have no timer running.
--refill   sets saved_count = known_max_charges and remaining_charges = 0 for
           matching spawners (a guess at "everything present"; try on one first).

Hash = MD5(data_bytes + msgpack_str(HASH_SALT) + msgpack_int(salt, minimal width)), as AA-BB-...
"""
import sys, struct, hashlib, time, re, argparse, datetime, os

def _now():
    return float(os.environ.get('SAVE_TOOL_NOW') or time.time())   # SAVE_TOOL_NOW only for testing

K = b'5b5496vn7456oodw976d95mo'
SPAWNER_FIELDS = ['last_spawn_time', 'saved_count', 'remaining_charges', 'next_big_spawn_time',
                  'cleared_once', 'charges_sync_period', 'known_max_charges']
TICKS_EPOCH = 621355968000000000  # .NET ticks at 1970-01-01

# ---------- minimal MessagePack walking (works on byte offsets) ----------
def vspan(b, i):
    """return (end, kind) of the value starting at i; end is None for containers"""
    t = b[i]
    if t < 0x80 or t >= 0xe0: return i + 1, 'int'
    if 0x80 <= t <= 0x8f: return None, 'map'
    if 0x90 <= t <= 0x9f: return None, 'arr'
    if 0xa0 <= t <= 0xbf: return i + 1 + (t & 31), 'str'
    if t == 0xc0: return i + 1, 'nil'
    if t in (0xc2, 0xc3): return i + 1, 'bool'
    if t == 0xca: return i + 5, 'float'
    if t == 0xcb: return i + 9, 'float'
    ints = {0xcc: 1, 0xcd: 2, 0xce: 4, 0xcf: 8, 0xd0: 1, 0xd1: 2, 0xd2: 4, 0xd3: 8}
    if t in ints: return i + 1 + ints[t], 'int'
    if t in (0xd4, 0xd5, 0xd6, 0xd7, 0xd8): return i + 2 + {0xd4: 1, 0xd5: 2, 0xd6: 4, 0xd7: 8, 0xd8: 16}[t], 'ext'
    if t in (0xd9, 0xc4): return i + 2 + b[i + 1], 'str' if t == 0xd9 else 'bin'
    if t in (0xda, 0xc5): return i + 3 + struct.unpack('>H', b[i + 1:i + 3])[0], 'str' if t == 0xda else 'bin'
    if t in (0xdc, 0xdd): return None, 'arr'
    if t in (0xde, 0xdf): return None, 'map'
    raise ValueError('unsupported type 0x%02x at %d' % (t, i))

def header(b, i):
    t = b[i]
    if 0x80 <= t <= 0x8f or 0x90 <= t <= 0x9f: return t & 15, i + 1
    if t in (0xdc, 0xde): return struct.unpack('>H', b[i + 1:i + 3])[0], i + 3
    if t in (0xdd, 0xdf): return struct.unpack('>I', b[i + 1:i + 5])[0], i + 5
    raise ValueError

def skip(b, i):
    end, kind = vspan(b, i)
    if end is not None: return end
    n, j = header(b, i)
    for _ in range(n * (2 if kind == 'map' else 1)): j = skip(b, j)
    return j

def rdstr(b, i):
    t = b[i]
    if 0xa0 <= t <= 0xbf: return b[i + 1:i + 1 + (t & 31)].decode(), i + 1 + (t & 31)
    if t == 0xd9: n = b[i + 1]; return b[i + 2:i + 2 + n].decode(), i + 2 + n
    if t == 0xda: n = struct.unpack('>H', b[i + 1:i + 3])[0]; return b[i + 3:i + 3 + n].decode(), i + 3 + n
    raise ValueError

def rdint(b, i):
    t = b[i]
    if t < 0x80: return t
    if t >= 0xe0: return t - 256
    f = {0xcc: '>B', 0xcd: '>H', 0xce: '>I', 0xcf: '>Q', 0xd0: '>b', 0xd1: '>h', 0xd2: '>i', 0xd3: '>q'}[t]
    return struct.unpack(f, b[i + 1:i + 1 + struct.calcsize(f)])[0]

def rdscalar(b, i):
    end, kind = vspan(b, i)
    if kind == 'int': return rdint(b, i)
    if kind == 'float': return struct.unpack('>d' if b[i] == 0xcb else '>f', b[i + 1:end])[0]
    if kind == 'bool': return b[i] == 0xc3
    if kind == 'str': return rdstr(b, i)[0]
    return None

def enc_int(v):
    if 0 <= v < 128: return bytes([v])
    if -32 <= v < 0: return struct.pack('>b', v)
    if v >= 0:
        for c, f, m in ((0xcc, '>B', 1 << 8), (0xcd, '>H', 1 << 16), (0xce, '>I', 1 << 32), (0xcf, '>Q', 1 << 64)):
            if v < m: return bytes([c]) + struct.pack(f, v)
    else:
        for c, f, lo in ((0xd0, '>b', -1 << 7), (0xd1, '>h', -1 << 15), (0xd2, '>i', -1 << 31), (0xd3, '>q', -1 << 63)):
            if v >= lo: return bytes([c]) + struct.pack(f, v)
    raise ValueError('integer out of range')

# ---------- walking by path ----------
def children(b, i):
    """yield (label, value_offset). Array items with a 'key' field are labelled by it."""
    _, kind = vspan(b, i)
    n, j = header(b, i)
    if kind == 'map':
        for _ in range(n):
            k, j2 = rdstr(b, j)
            yield k, j2
            j = skip(b, j2)
    else:
        for idx in range(n):
            label = str(idx)
            if vspan(b, j)[1] == 'map':
                for k, v in children(b, j):
                    if k == 'key' and vspan(b, v)[1] == 'str':
                        label = rdstr(b, v)[0]; break
            yield label, j
            j = skip(b, j)

def find(b, root, path):
    i = root
    for n, seg in enumerate(path):
        if vspan(b, i)[1] not in ('map', 'arr'): raise KeyError('no such field: ' + '/'.join(path))
        is_spawner = path[:2] == ['spawners', 'spawners_v3'] and n == 3
        if is_spawner and seg in SPAWNER_FIELDS: seg = str(SPAWNER_FIELDS.index(seg))
        for label, off in children(b, i):
            if label == seg: i = off; break
        else: raise KeyError('no such field: ' + '/'.join(path))
    return i

def walk(b, i, prefix=()):
    end, kind = vspan(b, i)
    if kind in ('map', 'arr'):
        for label, off in children(b, i):
            if prefix[:2] == ('spawners', 'spawners_v3') and len(prefix) == 3 and label.isdigit() and int(label) < 7:
                label = SPAWNER_FIELDS[int(label)]
            yield from walk(b, off, prefix + (label,))
    elif kind in ('int', 'float', 'bool'):
        yield '/'.join(prefix), kind, rdscalar(b, i)

# ---------- file structure + signing ----------
def parts(b):
    d = b.index(b'\xa4data') + 5
    s = b.index(b'\xa4salt') + 5
    return d, skip(b, d), rdint(b, s)

def make_hash(data, salt):
    # the game hashes the salt as a *minimal-width* MessagePack int (d2 for big negatives, ce for big positives, ...)
    h = hashlib.md5(data + bytes([0xa0 | len(K)]) + K + enc_int(salt)).digest()
    return '-'.join('%02X' % x for x in h).encode()

def hash_pos(b): return b.index(b'\xa4hash\xd9\x2f') + 7

def resign(b):
    d, end, salt = parts(b)
    p = hash_pos(b)
    b[p:p + 47] = make_hash(bytes(b[d:end]), salt)

def verify(b):
    d, end, salt = parts(b)
    p = hash_pos(b)
    return bytes(b[p:p + 47]) == make_hash(bytes(b[d:end]), salt)

# ---------- time helpers ----------
def parse_duration(text):
    m = re.fullmatch(r'([+-]?)(\d+(?:\.\d+)?)([smhdw]?)', text.strip().lower())
    if not m: raise ValueError(f'bad time "{text}" (use e.g. now, +30m, +2h, -1d, +90s)')
    n = float(m.group(2)) * {'': 1, 's': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}[m.group(3)]
    return -n if m.group(1) == '-' else n

def parse_time_text(text):
    """-> unix seconds (float) for now / +30m / -1d ..., or None if text is not a time expression"""
    t = text.strip().lower()
    if t == 'now': return _now()
    if t[:1] in '+-' and re.fullmatch(r'[+-]\d+(\.\d+)?[smhdw]?', t): return _now() + parse_duration(t)
    return None

def unit_of(path, old):
    p = path.lower()
    if 'ticks' in p or 'last_geode_timestamp' in p or abs(old) > 1e17: return 'ticks'
    if abs(old) > 1e11: return 'ms'
    return 's'

def from_unix(unix, unit):
    if unit == 'ticks': return int(TICKS_EPOCH + unix * 1e7)
    if unit == 'ms': return int(unix * 1000)
    return int(unix)

def to_unix(v, unit):
    return (v - TICKS_EPOCH) / 1e7 if unit == 'ticks' else (v / 1000 if unit == 'ms' else v)

def human(v, unit, now):
    u = to_unix(v, unit)
    if u <= 0: return 'not set'
    when = datetime.datetime.fromtimestamp(u, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    d = u - now
    s = abs(d)
    span = f'{int(s // 86400)}d {int(s % 86400 // 3600)}h' if s >= 86400 else f'{int(s // 3600)}h {int(s % 3600 // 60)}m'
    return f'{when} ({"in " + span if d > 0 else span + " ago"})'

# ---------- edits ----------
def set_value(b, path, text):
    d, end, salt = parts(b)
    if '/' not in path: path = 'player/' + path          # shorthand: gems -> player/gems
    i = find(b, d, path.split('/'))
    e, kind = vspan(b, i)
    old = rdscalar(b, i)
    shown = None
    if kind == 'bool':
        if text.lower() not in ('true', 'false', '1', '0'): raise ValueError(f'{path}: expected true/false')
        shown = text.lower() in ('true', '1')
        new = bytes([0xc3 if shown else 0xc2])
    elif kind in ('int', 'float'):
        unix = parse_time_text(text)
        if unix is not None:
            unit = unit_of(path, old)
            v = from_unix(unix, unit)
            shown = f'{v} ({human(v, unit, _now())})'
            val = float(v) if kind == 'float' else v
        else:
            val = float(text)
            if kind == 'int':
                if val != int(val): raise ValueError(f'{path}: needs a whole number')
                val = int(val)
            shown = val
        if kind == 'int': new = enc_int(int(val))
        else: new = (b'\xcb' + struct.pack('>d', val)) if b[i] == 0xcb else (b'\xca' + struct.pack('>f', val))
    else:
        raise ValueError(f'{path}: not a number/boolean field')
    b[i:e] = new
    print(f'{path}: {old} -> {shown}')

def spawner_names(b, flt):
    d, _, _ = parts(b)
    root = find(b, d, ['spawners', 'spawners_v3'])
    return [lab for lab, _ in children(b, root) if flt.lower() in lab.lower()]

def spawner_vals(b, name):
    d, _, _ = parts(b)
    off = find(b, d, ['spawners', 'spawners_v3', name])
    return dict(zip(SPAWNER_FIELDS, (rdint(b, o) for _, o in children(b, off))))

def cmd_respawn(b, flt, delay, all_):
    now = _now()
    target = 0 if delay is None else int(now + parse_duration(delay))
    n = 0
    for name in spawner_names(b, flt):
        v = spawner_vals(b, name)
        if not all_ and v['next_big_spawn_time'] <= now: continue
        set_value(b, f'spawners/spawners_v3/{name}/next_big_spawn_time', str(target))
        n += 1
    print(f'{n} spawner(s) updated' + ('' if n else ' (none had a respawn timer running; use --all to force)'))

def cmd_refill(b, flt):
    n = 0
    for name in spawner_names(b, flt):
        v = spawner_vals(b, name)
        if v['known_max_charges'] <= 0: continue
        if v['saved_count'] == v['known_max_charges'] and v['remaining_charges'] == 0: continue
        set_value(b, f'spawners/spawners_v3/{name}/saved_count', str(v['known_max_charges']))
        set_value(b, f'spawners/spawners_v3/{name}/remaining_charges', '0')
        n += 1
    print(f'{n} spawner(s) refilled')

TIMER_NAME = re.compile(r'(timestamp|_time$|_at_unix_seconds|_at_seconds|_at_ticks|ticks$|cooldown|reset_day|reset_time|_ts$|unix_seconds)')
TIMER_SKIP = re.compile(r'(install_time|playtime|purchase_time|last_trusted_time|last_online|last_schedule_check|mobs_day_ticks)')

def cmd_timers(b, flt):
    d, _, _ = parts(b)
    now = _now()
    flt = flt.lower()
    rows, ready, dep = [], 0, []
    for name in spawner_names(b, ''):
        v = spawner_vals(b, name)
        if v['next_big_spawn_time'] > now: dep.append((name, v))
        else: ready += 1
    if 'spawner'.startswith(flt) or any(flt in n.lower() for n, _ in dep):
        print(f'SPAWNERS: {ready + len(dep)} total, {ready} ready, {len(dep)} on a respawn timer')
        for name, v in dep:
            if flt in name.lower() or 'spawner'.startswith(flt):
                print(f'  {name}: respawns {human(v["next_big_spawn_time"], "s", now)}  '
                      f'[saved {v["saved_count"]}, charges {v["remaining_charges"]}/{v["known_max_charges"]}]')
    print('OTHER TIMERS (nonzero):')
    zero = 0
    for p, k, v in walk(b, d):
        if p.startswith('spawners/') or k == 'bool': continue
        if not TIMER_NAME.search(p.lower().split('/')[-1]) or TIMER_SKIP.search(p.lower()): continue
        if flt and flt not in p.lower() and 'spawner'.startswith(flt) is False: continue
        if not v: zero += 1; continue
        if unit_of(p, v) == 's' and abs(v) < 1e8: continue   # not a timestamp (e.g. a duration)
        print(f'  {p} = {int(v)}  -> {human(v, unit_of(p, v), now)}')
    print(f'  (+ {zero} timer fields currently 0 = ready)')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Edit and re-sign game_data.bin', usage=__doc__, add_help=False)
    ap.add_argument('input'); ap.add_argument('output', nargs='?'); ap.add_argument('edits', nargs='*')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--list', nargs='?', const='')
    ap.add_argument('--timers', nargs='?', const='')
    ap.add_argument('--respawn', nargs='?', const='')
    ap.add_argument('--refill', nargs='?', const='')
    ap.add_argument('--in', dest='delay'); ap.add_argument('--all', action='store_true')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args()
    if a.help: print(__doc__); sys.exit()
    b = bytearray(open(a.input, 'rb').read())
    if a.verify: print('hash valid:', verify(b)); sys.exit()
    if a.list is not None:
        d, _, _ = parts(b)
        for p, kind, v in walk(b, d):
            if a.list.lower() in p.lower(): print(f'{p} [{kind}] = {v}')
        sys.exit()
    if a.timers is not None: cmd_timers(b, a.timers); sys.exit()
    # editing commands need an output file; allow "in --respawn out" ordering mistakes gracefully
    if a.output is None: print('error: need an output file, e.g.  save_tool.py in.bin out.bin ...'); sys.exit(1)
    try:
        if a.respawn is not None: cmd_respawn(b, a.respawn, a.delay, a.all)
        if a.refill is not None: cmd_refill(b, a.refill)
        for e in a.edits:
            path, _, val = e.partition('=')
            set_value(b, path, val)
    except (KeyError, ValueError) as ex:
        print('error:', ex.args[0] if ex.args else ex); sys.exit(1)
    resign(b)
    open(a.output, 'wb').write(b)
    print('written', a.output, '| hash valid:', verify(b))
