# Auditorium Defense

A bilingual defense game set at the NTHU Auditorium. Protect the auditorium through five increasingly difficult waves, collect parts and energy, place defenses, and defeat the final boss. The background changes at Wave 4. Pygame is preferred; Tkinter is used if Pygame is unavailable.

## Run

```bash
python auditorium_defense.py
```

You can also run `python main.py`. The Traditional Chinese interface uses the bundled font at `assets/fonts/NotoSansTC.ttf`.

## Controls

- Arrow keys or WASD: move
- Space or click inside the battlefield: manual melee attack
- Between waves: click a pad or press Tab to select one, then press 1–5 to build
- R: repair the auditorium
- U: upgrade the selected defense
- Enter: start the next wave
- Esc: pause or return to the title screen
- H on the title screen: open the new player guide

## Project layout

- `i2p_game/config.py`: field layout, enemy and boss balance, waves, defenses, and upgrades
- `i2p_game/models.py`: enemy, tower, drop, shot, and button data objects
- `i2p_game/game.py`: movement, combat, building, resources, wave transitions, and boss logic
- `i2p_game/interface.py`: input handling, tutorial, HUD, menus, and battlefield drawing
- `i2p_game/canvas.py`: Pygame and Tkinter drawing backends
- `i2p_game/artwork.py`: image paths and in-game sprite sizes
- `assets/images/`: supplied characters, defenses, projectiles, and backgrounds, plus display-sized PNG versions used at runtime
- `i2p_game/launcher.py`: application startup and event loops
