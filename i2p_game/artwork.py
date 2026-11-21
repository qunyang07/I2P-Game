"""Artwork paths and display sizes for the supplied image assets."""

from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
IMAGE_DIR = ASSET_DIR / "images"

# Runtime images are all stored in assets/images. The *_sprite and *_bg PNGs
# are display-sized versions of the supplied artwork; no other image directory
# is loaded by the game.
ARTWORK_FILES = {
    "field1": IMAGE_DIR / "field1_bg.png",
    "field2": IMAGE_DIR / "field2_bg.png",
    "auditorium_logo": IMAGE_DIR / "auditorium_logo.png",
    "auditorium_title": IMAGE_DIR / "auditorium_title.png",
    "defender": IMAGE_DIR / "NaiFrog_sprite.png",
    "bear": IMAGE_DIR / "Bear_sprite.png",
    "small_bear": IMAGE_DIR / "small_bear_sprite.png",
    "niulai": IMAGE_DIR / "Niulai_sprite.png",
    "boss": IMAGE_DIR / "TungtungtungSahur_sprite.png",
    "traffic_light": IMAGE_DIR / "Traffic_light_sprite.png",
    "wall": IMAGE_DIR / "Wall_sprite.png",
    "lake": IMAGE_DIR / "Lake_sprite.png",
    "dog": IMAGE_DIR / "dog_sprite.png",
    "egg_launcher": IMAGE_DIR / "naiEgg_launcher_sprite.png",
    "egg": IMAGE_DIR / "naiEgg_sprite.png",
}

SPRITE_SIZES = {
    "field1": (810, 553),
    "field2": (810, 553),
    "auditorium_logo": (120, 80),
    "auditorium_title": (240, 160),
    "defender": (42, 84),
    "bear": (42, 61),
    "small_bear": (42, 56),
    "niulai": (56, 56),
    "boss": (104, 140),
    "traffic_light": (24, 58),
    "wall": (68, 52),
    "lake": (64, 42),
    "dog": (42, 50),
    "egg_launcher": (52, 46),
    "egg": (19, 21),
}
