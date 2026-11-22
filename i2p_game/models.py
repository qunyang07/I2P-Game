"""Small data objects used by the game and interface."""

from dataclasses import dataclass
from typing import Callable

@dataclass
class Enemy:
    kind: int
    x: float
    y: float
    hp: int
    max_hp: int
    base_wait: float = 0.0
    slowed: float = 0.0
    stunned: float = 0.0
    stun_duration: float = 0.0
    stun_elapsed: float = 0.0
    wall_wait: float = 0.0
    dash_wait: float = 0.0
    dash_left: float = 0.0


@dataclass
class Tower:
    kind: int
    upgrade_level: int = 1
    wait: float = 0.0
    hp: int = 0
    max_hp: int = 0
    effect: float = 0.0
    locked: bool = False

    @property
    def upgraded(self):
        return self.upgrade_level > 1


@dataclass
class Drop:
    x: float
    y: float
    energy: bool = False


@dataclass
class Shot:
    origin: tuple
    target: tuple
    color: str
    remaining: float = 0.12
    artwork: str | None = None


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: int
    splash_damage: int
    splash_radius: int
    radius: int = 5
    artwork: str | None = 'egg'
    target_type: str = 'enemies'
    color: str = '#78d7ff'


@dataclass
class Button:
    bounds: tuple
    action: Callable[[], None]
