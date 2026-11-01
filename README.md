![description]([https://site.com/image.png](https://i.imgur.com/KELjgud.png))


# 🛠 game_data.bin Save Tools

![Python](https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

Two dependency-free Python scripts for working with a `game_data.bin` save file. The game stores an integrity hash in the save and rejects any file whose hash does not match, so both scripts **re-sign the file** after changing it.

| Script | Use it when you want to... |
| --- | --- |
| [`save_tool.py`](save_tool.py) | Edit values (gems, items, timers, respawns) and re-sign automatically |
| [`resign.py`](resign.py) | **Only** fix the hash of a save you edited yourself, changing no values |

With `save_tool.py` you can:

- 💎 Change gems and other currency balances
- 🔢 Change whole numbers such as item levels, item copies and the death count
- ✅ Flip true/false values (tutorial flags, unlocked slots, chests opened, ...)
- 🌳 Make trees and other spawners **respawn** whenever you want
- ⏱ Reset or move other timers (cooldowns, quest respawns, daily resets)

> [!WARNING]
> Use this only on your own save files, and for single-player use. Always keep a backup of the original save. Values the game does not expect (for example an item level above the game's maximum) can crash the game or corrupt the save.

---

## 📑 Table of contents

- [Quick start](#-quick-start)
- [Termux guide (Android)](#-termux-guide-android)
- [save_tool.py commands](#-save_toolpy-commands)
- [Editing values](#-editing-values)
- [Timers and respawning](#-timers-and-respawning)
- [resign.py (hash only)](#-resignpy-hash-only)
- [Troubleshooting](#-troubleshooting)
- [How it works](#-how-it-works)

---

## ⚡ Quick start

**Change a value and re-sign (`save_tool.py`):**

```bash
python save_tool.py game_data.bin --list gems                  # find a value
python save_tool.py game_data.bin new.bin gems=100000          # change it and re-sign
python save_tool.py new.bin --verify                           # should print: hash valid: True
```

**Only fix the hash of a file you edited by hand (`resign.py`):**

```bash
python resign.py game_data.bin fixed.bin
```

Then copy the result over the game's `game_data.bin` (see the Termux guide below).

---

## 📱 Termux guide (Android)

### 1️⃣ Install Termux

Install Termux from **[F-Droid](https://f-droid.org/packages/com.termux/)** or the [GitHub releases](https://github.com/termux/termux-app/releases).

> [!IMPORTANT]
> Do **not** use the Play Store version. It is outdated and package installs often fail.

### 2️⃣ Set up Termux

Run these one at a time:

```bash
pkg update -y
pkg install python -y
termux-setup-storage
```

Tap **Allow** when Android asks for storage permission. This creates a `~/storage` folder linked to your phone's storage.

### 3️⃣ Put the script on your phone

1. Download `save_tool.py` and/or `resign.py` from this repository to your phone (they usually land in `Download`).
2. Copy them into Termux's home folder:

```bash
cp ~/storage/downloads/save_tool.py ~/
cp ~/storage/downloads/resign.py ~/
```

### 4️⃣ Get the save file out of the game

On Android 11 and newer, Termux cannot read the game's private data folders directly. Pick one of these:

| Method | Notes |
| --- | --- |
| **File manager that can open `Android/data`** | For example MiXplorer or Solid Explorer. Look in `Android/data/<game package>/files/` |
| **Shizuku or ADB from a PC** | Gives access to the folder without root |
| **Root** | Termux can read the data folder directly |

Search your file manager for `game_data.bin`, then copy it to your `Download` folder.

### 5️⃣ Edit the save

```bash
cp ~/storage/downloads/game_data.bin ~/
cd ~
python save_tool.py game_data.bin --verify
python save_tool.py game_data.bin edited.bin gems=100000
python save_tool.py edited.bin --verify
```

The last command should print `hash valid: True`.

> [!TIP]
> Edited the file yourself in a hex editor instead? Skip `save_tool.py` and run `python resign.py game_data.bin fixed.bin` (see [resign.py](#-resignpy-hash-only)).

### 6️⃣ Put it back in the game

1. Copy the result to `Download`:

   ```bash
   cp ~/edited.bin ~/storage/downloads/game_data.bin
   ```

2. **Close the game completely** (swipe it away from recent apps).
3. In your file manager, **back up the original** `game_data.bin`, then replace it in the game's folder with the edited file. The name must be exactly `game_data.bin`.
4. Open the game.

> [!TIP]
> Always edit a **fresh** save: close the game, copy the save out, edit it, copy it back, then open the game. Using an old copy may get it overwritten.

---

## 📖 save_tool.py commands

| Command | What it does |
| --- | --- |
| `save_tool.py IN --verify` | Checks the hash. Prints `hash valid: True/False` |
| `save_tool.py IN --list [filter]` | Lists every editable value, optionally filtered by text |
| `save_tool.py IN --timers [filter]` | Shows spawner, respawn and cooldown timers |
| `save_tool.py IN OUT PATH=VALUE ...` | Changes one or more values and re-signs |
| `save_tool.py IN OUT --respawn [filter] [--in 30m] [--all]` | Makes depleted spawners ready again |
| `save_tool.py IN OUT --refill [filter]` | *(Experimental)* Tops up spawner charges |
| `save_tool.py IN [OUT] --resign` | Only recomputes the hash and changes **no** values (same as `resign.py`) |

`IN` is the input save, `OUT` is the new file to write. The input file is never modified.

---

## 📝 Editing values

Use `--list` to find the path of a value, then set it with `PATH=VALUE`:

```bash
python save_tool.py game_data.bin --list gems
python save_tool.py game_data.bin --list knife
```

```bash
python save_tool.py game_data.bin new.bin \
    gems=100000 \
    deaths_count=0 \
    seen_blacksmith_sharpening_tutorial=true \
    player/items/knife/level=10 \
    player/items/pick/copies=70000 \
    currency/balances/soul.common=99999
```

| Rule | Example |
| --- | --- |
| Levels are separated by `/` | `player/items/knife/level=10` |
| A bare name means `player/...` | `gems=100000` is `player/gems=100000` |
| Items in a list are addressed by name | `player/items/pike/evolved=false` |
| True/false fields take `true` or `false` | `player/player_in_dungeon=false` |
| Whole-number fields reject decimals | `deaths_count=1.5` gives an error |
| Decimal fields (like gems) take any number | `gems=99999.5` |

> [!NOTE]
> Each value keeps its original type. The tool never changes other values, only the ones you name, and then re-signs the file.

---

## 🌳 Timers and respawning

Trees, ice and other resources are stored as **spawners**. When you harvest one, the game stores that it is depleted until the next **daily reset at 00:00 UTC**. The tool can clear that wait.

### See what is waiting

```bash
python save_tool.py game_data.bin --timers
python save_tool.py game_data.bin --timers tree
```

### Make depleted spawners respawn

```bash
python save_tool.py game_data.bin new.bin --respawn                # all depleted spawners, ready now
python save_tool.py game_data.bin new.bin --respawn tree           # only names containing "tree"
python save_tool.py game_data.bin new.bin --respawn tree --in 10m  # ready in 10 minutes
python save_tool.py game_data.bin new.bin --respawn --all          # also rewrite spawners with no timer running
```

The filter matches the spawner's name, for example `tree`, `ice`, `dragon` or `Spawner_1`.

**Workflow:** harvest what you want, close the game, run `--respawn` on the save the game just wrote, copy the result back, and start the game.

> [!NOTE]
> If the tool prints `0 spawner(s) updated`, nothing was waiting. That is normal if the daily reset has already passed, or if you used an old save.

### Other timers

Timer fields accept time expressions, relative to the **real current time**:

| Value | Meaning |
| --- | --- |
| `0` | Ready now |
| `now` | The current time |
| `+30m`, `+2h`, `+1d`, `+90s` | That long from now |
| `-1d` | One day ago |

```bash
python save_tool.py game_data.bin new.bin \
    vip/daily_chest_cooldown_timestamp=0 \
    boss_tower/last_tickets_restore_timestamp=-1d \
    quests/steps/quest_c1_step_1/respawn_at_unix_seconds=0
```

Seconds, milliseconds and .NET ticks are detected automatically. Run `--timers` to see all of these fields.

### Secret chests

Chests use a true/false flag instead of a timer. Set `is_opened` back to `false` to make one reappear:

```bash
python save_tool.py game_data.bin --list secret_chests
python save_tool.py game_data.bin new.bin secret_chests/chests/<id>/is_opened=false
```

### Spawner fields

You can also edit a single spawner by name. Each spawner has 7 values:

| Field | Meaning |
| --- | --- |
| `last_spawn_time` | When it last spawned (Unix seconds) |
| `saved_count` | How many currently exist |
| `remaining_charges` | Charges left in reserve |
| `next_big_spawn_time` | When it refills (Unix seconds, `0` = ready) |
| `cleared_once` | Whether it has been cleared before |
| `charges_sync_period` | The day number of its last sync |
| `known_max_charges` | Its maximum charges |

```bash
python save_tool.py game_data.bin new.bin "spawners/spawners_v3/tree_1 (1)_cab298/next_big_spawn_time=0"
```

> [!CAUTION]
> `--refill` is a best guess at "make everything present" and has not been verified in the game. Try it on a single spawner (for example `--refill "tree_1 (1)"`) before using it widely.

---

## 🔏 resign.py (hash only)

`resign.py` is a much smaller script that does one thing: it recomputes the hash of a save and **changes no values** (no gems, items, timers or anything else). Use it after you edit `game_data.bin` yourself, for example in a hex editor.

```bash
python resign.py game_data.bin              # writes game_data_resigned.bin
python resign.py game_data.bin out.bin      # writes out.bin
python resign.py game_data.bin --verify     # only checks if the hash is valid
```

| Command | What it does |
| --- | --- |
| `resign.py FILE` | Re-signs `FILE` and writes `<name>_resigned.bin` |
| `resign.py FILE OUT` | Re-signs `FILE` and writes `OUT` |
| `resign.py FILE --verify` | Prints `hash valid: True/False` and writes nothing |

> [!NOTE]
> Running it on a save the game wrote itself gives back an identical copy, because that hash is already valid. Your original file is never overwritten unless you choose the same name for the output.

---

## 🛠 Troubleshooting

<details>
<summary><b>The game ignores my edit or loads the old progress</b></summary>

- Run `python save_tool.py yourfile.bin --verify` and make sure it prints `hash valid: True`.
- The game keeps `game_data_backup.bin` and `game_data_temp.bin` in the same folder. If the main file is rejected, it may load the backup.
- If the game uses a cloud save, it can overwrite local changes.
- Make sure you edited a save that the game wrote recently.

</details>

<details>
<summary><b>Trees do not respawn</b></summary>

- Run `--timers` first. If it shows `0 on a respawn timer`, nothing was waiting.
- Harvest first, close the game, then run `--respawn` on the fresh save.
- Respawn again after the daily reset only if you harvested again.

</details>

<details>
<summary><b><code>error: no such field</code></b></summary>

The path is wrong. Run `--list <text>` to find the exact path. Paths with spaces or brackets must be in quotes.

</details>

<details>
<summary><b><code>command not found: python</code></b></summary>

Run `pkg install python -y` again, then reopen Termux.

</details>

<details>
<summary><b><code>No such file or directory</code></b></summary>

You are probably not in the folder that holds the file. Run `ls` to see the current folder, or use the full path, for example `~/storage/downloads/game_data.bin`.

</details>

<details>
<summary><b>I edited the file by hand in a hex editor</b></summary>

Run `python resign.py yourfile.bin fixed.bin` afterwards. It recomputes only the hash and changes no values.

</details>

---

## 🔍 How it works

The save is a [MessagePack](https://msgpack.org) map with the fields `version`, `salt`, `time`, `data` and `hash`. The tool changes values inside `data` by editing the exact bytes, then recomputes the hash:

```text
hash = MD5( data_bytes + msgpack_str(HASH_SALT) + msgpack_int(salt) )
```

- `data_bytes` is the serialized `data` section exactly as stored in the file.
- `HASH_SALT` is a constant string embedded in the game.
- `salt` is a random number the game picks on every save, encoded as a **minimal-width** MessagePack integer (so positive and negative salts hash differently).
- The result is written as uppercase hex pairs separated by dashes (`AA-BB-CC-...`).

`resign.py` performs only the hash step. `save_tool.py` first edits values by changing the exact bytes, then does the same hash step. Whole numbers use the smallest MessagePack width that fits, so the file can grow or shrink slightly when you change them. The hash always covers the final bytes.

---

## ⚖️ Disclaimer

This project is not affiliated with the game's developers. It is provided as-is for personal, offline use on your own save files. Back up your saves before using it.
