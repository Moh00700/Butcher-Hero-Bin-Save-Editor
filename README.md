Here is the whole process for Termux. You only need Python, because resign.py uses nothing beyond Python's built-in libraries.
1. Install Termux
Install it from F-Droid or GitHub, not the Play Store. The Play Store version is outdated and its package installs often fail.
2. Set up Termux
Open Termux and run these one at a time:
pkg update -y
pkg install python -y
termux-setup-storage
Tap Allow when Android asks for storage permission. This creates a ~/storage folder that links to your phone's storage.
3. Put the script on your phone
Download resign.py from this chat to your phone. It usually lands in the Download folder.
In Termux, copy it into your home folder:
cp ~/storage/downloads/resign.py ~/
4. Get your save file out of the game
This is the hardest step. On Android 11 and newer, Termux can't read the game's private data folders directly. You have three options:
A file manager that can open Android/data. Some, like MiXplorer or Solid Explorer, can. Look for game_data.bin inside the game's folder under Android/data/<game package name>/files/, and copy it to Download.
Shizuku or ADB from a PC. Both give access to those folders.
Root. If your phone is rooted, Termux can read the game's data folder directly.
I don't know your game's package name, so I can't give an exact path. Search for game_data.bin in your file manager.
5. Re-sign the file
Copy the save into Termux, run the script, then check the result:
cp ~/storage/downloads/game_data.bin ~/
cd ~
python resign.py game_data.bin --verify
python resign.py game_data.bin game_data_fixed.bin
python resign.py game_data_fixed.bin --verify
The first --verify shows whether the current hash is valid.
The second command writes game_data_fixed.bin with a new hash. It changes no values.
The last --verify should print hash valid: True.
6. Put it back in the game
Copy the result to Download:
cp ~/game_data_fixed.bin ~/storage/downloads/game_data.bin
Close the game completely (swipe it away from recent apps).
Using your file manager, back up the original game_data.bin, then replace it in the game's folder with the fixed file. The name must be exactly game_data.bin.
Open the game.
Tips
Edit a fresh save. Close the game, copy the save out, edit it, copy it back, and then open the game. If you use an old copy, the game may overwrite it.
Backup files. The game also keeps game_data_backup.bin and game_data_temp.bin in the same folder. If your edit is rejected, the game may load the backup instead.
Cloud save. If the game syncs a cloud save, it can overwrite your edit.
Hex edits. If you edit values yourself in a hex editor, run resign.py afterward, every time, or the game will reject the file.
Errors. If you see command not found: python, run pkg install python again. If you see No such file, check that you're in the folder holding the file by running ls.
