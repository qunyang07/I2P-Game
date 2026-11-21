"""Shared game configuration and balance data."""

from dataclasses import dataclass

WIDTH, HEIGHT = 1152, 720
FIELD = (20, 108, 812, 555)
SIDE = (850, 108, 282, 555)
BASE = (425, 379)
BASE_RADIUS = 68

# Eight locations are arranged around the auditorium so each defense type has
# room to matter without crowding the original three locations.
PADS = (
    (284, 374), (567, 374), (425, 516),
    (337, 260), (513, 260), (337, 498), (513, 498), (425, 235),
)

# Each entrance extends one pad's straight route toward the field edge.
ENTRANCES = (
    (35, 365), (817, 365), (425, 648), (236, 123),
    (614, 123), (226, 648), (624, 648), (425, 123),
)
BOSS_ENTRANCE = ENTRANCES[0]

MAX_BASE_HP = 180
REPAIR_COST, REPAIR_HP = 4, 38
UPGRADE_COST = (5, 2)
STARTING_PLAYER_HP = 100
PLAYER_MELEE_RANGE = 78
PLAYER_MELEE_COOLDOWN = 1.05
PLAYER_MELEE_FLASH_DURATION = 0.22
PLAYER_RANGED_RANGE = 153
PLAYER_RANGED_INTERVAL = 0.37

BG = '#0c1621'
PANEL = '#162534'
BORDER = '#2d4558'
TEXT = '#ffffff'
MUTED = '#d3e1eb'
GREEN = '#8ee5ae'
BLUE = '#78d7ff'
GOLD = '#ffd181'
PURPLE = '#c9b3ff'
RED = '#ff8580'


@dataclass(frozen=True)
class EnemyKind:
    name: tuple
    artwork: str
    hp: int
    speed: int
    base_damage: int
    player_damage: int
    radius: int
    color: str
    attack_interval: float = 0.9
    attack_range: int = 0
    ranged: bool = False
    boss: bool = False
    dash_interval: float = 0.0
    dash_duration: float = 0.0


# Three ordinary enemy classes use different health, speed, attack timing, and
# attack style. The fourth entry is reserved for the final-wave boss.
ENEMY_KINDS = (
    EnemyKind(('熊', 'Bear'), 'bear', 64, 43, 10, 12, 15, RED, 1.0),
    EnemyKind(('小熊', 'Small bear'), 'small_bear', 32, 92, 5, 7, 11, '#ffac66', 0.68,
              dash_interval=3.8, dash_duration=0.65),
    EnemyKind(('牛來', 'Niulai'), 'niulai', 58, 46, 8, 9, 15, PURPLE, 1.2, 118, True),
    EnemyKind(('最終 Boss', 'Final boss'), 'boss', 1250, 24, 24, 25, 31, RED, 1.15, boss=True),
)
BOSS_KIND = 3
BOSS_WAVE = 4
FIELD2_START_WAVE = 3

WAVES = (
    (0, 0, 1, 0, 1, 0, 0, 1),
    (0, 1, 2, 0, 1, 0, 2, 1, 0, 1, 2, 0),
    (1, 2, 0, 1, 2, 0, 1, 0, 2, 1, 0, 2, 0, 1, 2, 0),
    (2, 1, 0, 1, 2, 0, 1, 2, 0, 1, 0, 2, 1, 2, 0, 1, 2, 0, 1, 2),
    (1, 2, 0, 1, 2, 0, 2, 1, 0, 2, 1, 0, 1, 2, 0, 2, 1, 2, 0, 1, 2, 0, 1, 2),
)

# Longer gaps make each wave last longer and leave more time to react.
SPAWN_INTERVALS = (1.45, 1.3, 1.18, 1.08, 0.98)


@dataclass(frozen=True)
class DefenseKind:
    name: tuple
    description: tuple
    cost: tuple
    reach: int
    damage: int
    interval: float
    color: str
    artwork: str
    mode: str
    durability: int = 0
    stun_duration: float = 0.0
    splash_radius: int = 0


DEFENSES = (
    DefenseKind(('紅綠燈', 'Traffic light'), ('大範圍暫停敵人', 'Stuns groups of enemies'),
                (6, 3), 220, 0, 6.0, GREEN, 'traffic_light', 'stun', stun_duration=1.7),
    DefenseKind(('施工圍牆', 'Construction wall'), ('便宜、脆弱，可阻擋路線', 'Cheap, fragile path blocker'),
                (2, 0), 0, 0, 0.0, MUTED, 'wall', 'wall', durability=88),
    DefenseKind(('小湖', 'Small lake'), ('淹沒單一敵人，冷卻較久', 'Drowns one enemy; long cooldown'),
                (5, 2), 66, 0, 6.5, BLUE, 'lake', 'trap'),
    DefenseKind(('校狗', 'Campus dog'), ('近距離快速攻擊', 'Fast close-range attack'),
                (6, 2), 98, 22, 0.72, GOLD, 'dog', 'shot'),
    DefenseKind(('奶蛋發射器', 'Egg launcher'), ('遠程蛋彈，可波及附近敵人', 'Long-range egg with splash damage'),
                (8, 4), 300, 34, 1.25, PURPLE, 'egg_launcher', 'egg', splash_radius=38),
)

UPGRADES = (
    (('攻擊強化', 'Power'), ('玩家攻擊傷害 +8', 'Player damage +8'), GOLD),
    (('生命強化', 'Vitality'), ('最大生命與目前生命 +25', 'Maximum and current HP +25'), GREEN),
    (('移動強化', 'Agility'), ('移動速度 +30', 'Movement speed +30'), BLUE),
)
