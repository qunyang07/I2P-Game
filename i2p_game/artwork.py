"""Artwork paths and display sizes for the supplied image assets."""

from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"
NEW_IMAGE_DIR = ASSET_DIR / "images(new)"

# All runtime artwork is kept together in assets/images(new).
ARTWORK_FILES = {
    "field1": NEW_IMAGE_DIR / "field1_bg.png",
    "field2": NEW_IMAGE_DIR / "field2_bg.png",
    "auditorium_logo": NEW_IMAGE_DIR / "auditorium_logo.png",
    "auditorium_title": NEW_IMAGE_DIR / "auditorium.jpg",
    "defender": NEW_IMAGE_DIR / "NaiFrog.png",
    "bear": NEW_IMAGE_DIR / "Bear.png",
    "small_bear": NEW_IMAGE_DIR / "small_bear.png",
    "niulai": NEW_IMAGE_DIR / "Niulai.png",
    "nailong": NEW_IMAGE_DIR / "nailong.png",
    "boss": NEW_IMAGE_DIR / "TungtungtungSahur.png",
    "traffic_light": NEW_IMAGE_DIR / "Traffic_light.png",
    "wall": NEW_IMAGE_DIR / "Wall.jpg",
    "lake": NEW_IMAGE_DIR / "Lake.png",
    "dog": NEW_IMAGE_DIR / "dog.png",
    "egg_launcher": NEW_IMAGE_DIR / "naiEgg_launcher.png",
    "egg": NEW_IMAGE_DIR / "naiEgg.png",
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
    "nailong": (36, 48),
    "boss": (104, 140),
    "traffic_light": (24, 58),
    "wall": (68, 52),
    "lake": (64, 42),
    "dog": (42, 50),
    "egg_launcher": (52, 46),
    "egg": (19, 21),
}
