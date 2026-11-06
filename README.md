# Butcher Hero Save Editor

Single-file, client-side save editor for Butcher Hero `game_data.bin`.

## What it does
- Opens a `.bin` save locally in your browser — nothing is uploaded.
- Lists editable int / float / bool fields inside `data`.
- Lets you edit values, including timer/timestamp helpers.
- Re-signs the save (MD5 + salt) so the game accepts it.
- Downloads the edited `game_data.bin`.

## Use it
1. Open the GitHub Pages link for this repo.
2. Click **Open save** / choose your `game_data.bin`.
3. Edit, then click **Save game_data.bin**.
4. Back up your original save first.

## Files
- `index.html` — the whole editor (HTML + CSS + JS, no build step).
- `.nojekyll` — tells GitHub Pages to serve the file as-is.

## Privacy
All parsing/editing happens in the browser. No save data leaves your device.
