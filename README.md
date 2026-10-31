# 🔏 game_data.bin Re-Signer

![Python](https://img.shields.io/badge/python-3.x-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux%20%7C%20Windows%20%7C%20macOS-lightgrey)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)

A tiny, dependency-free Python script that recomputes the integrity hash of a `game_data.bin` save file.

If you edit a save (for example in a hex editor), the game rejects it because the stored hash no longer matches. `resign.py` fixes that. **It only rewrites the hash and never changes any value in the save.**

> [!WARNING]
> Use this only on your own save files, and for single-player use. Always keep a backup of the original save.

---

## 📑 Table of contents

- [Features](#-features)
- [Usage](#-usage)
- [Termux guide (Android)](#-termux-guide-android)
- [Troubleshooting](#-troubleshooting)
- [How it works](#-how-it-works)

---

## ✨ Features

- ✅ Re-signs a save so the game accepts it
- ✅ Leaves every value untouched (gems, items, timers, ...)
- ✅ Works whether the save's salt is positive or negative
- ✅ `--verify` mode to check a hash without writing anything
- ✅ Pure Python standard library, nothing to install

---

## 🚀 Usage

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
> Your original file is never overwritten unless you choose the same name for the output.

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

1. Download `resign.py` from this repository to your phone (it usually lands in `Download`).
2. Copy it into Termux's home folder:

```bash
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

### 5️⃣ Re-sign the file

```bash
cp ~/storage/downloads/game_data.bin ~/
cd ~
python resign.py game_data.bin --verify
python resign.py game_data.bin game_data_fixed.bin
python resign.py game_data_fixed.bin --verify
```

- The first `--verify` shows whether the current hash is valid.
- The second command writes `game_data_fixed.bin` with a fresh hash.
- The last `--verify` should print `hash valid: True`.

### 6️⃣ Put it back in the game

1. Copy the result to `Download`:

   ```bash
   cp ~/game_data_fixed.bin ~/storage/downloads/game_data.bin
   ```

2. **Close the game completely** (swipe it away from recent apps).
3. In your file manager, **back up the original** `game_data.bin`, then replace it in the game's folder with the fixed file. The name must be exactly `game_data.bin`.
4. Open the game.

> [!TIP]
> Always edit a **fresh** save: close the game, copy the save out, edit it, copy it back, then open the game. Using an old copy may get it overwritten.

---

## 🛠 Troubleshooting

<details>
<summary><b>The game ignores my edit or loads the old progress</b></summary>

- The game keeps `game_data_backup.bin` and `game_data_temp.bin` in the same folder. If the main file is rejected, it may load the backup.
- If the game uses a cloud save, it can overwrite local changes.
- Run `python resign.py yourfile.bin --verify` and make sure it prints `hash valid: True`.

</details>

<details>
<summary><b><code>command not found: python</code></b></summary>

Run `pkg install python -y` again, then reopen Termux.

</details>

<details>
<summary><b><code>No such file or directory</code></b></summary>

You are probably not in the folder that holds the file. Run `ls` to see what is in the current folder, or use the full path, for example `~/storage/downloads/game_data.bin`.

</details>

<details>
<summary><b>I edited the file by hand and the game rejects it</b></summary>

Run `python resign.py` on it **after every edit**. Any change to the data section invalidates the hash.

</details>

---

## 🔍 How it works

The save is a [MessagePack](https://msgpack.org) map with the fields `version`, `salt`, `time`, `data` and `hash`.

```text
hash = MD5( data_bytes + msgpack_str(HASH_SALT) + msgpack_int(salt) )
```

- `data_bytes` is the serialized `data` section exactly as stored in the file.
- `HASH_SALT` is a constant string embedded in the game.
- `salt` is a random number the game picks on every save, encoded as a **minimal-width** MessagePack integer.
- The result is written as uppercase hex pairs separated by dashes (`AA-BB-CC-...`).

---

## ⚖️ Disclaimer

This project is not affiliated with the game's developers. It is provided as-is for personal, offline use on your own save files. Back up your saves before using it.
