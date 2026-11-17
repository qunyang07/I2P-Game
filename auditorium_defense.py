"""大禮堂防衛戰。Run with `python auditorium_defense.py`.

Uses Pygame when installed and Tkinter otherwise. Art is drawn in code.
"""

from dataclasses import dataclass
from math import cos, hypot, sin, tau
from pathlib import Path
from time import perf_counter
from typing import Callable
import os


WIDTH, HEIGHT = 1152, 720
FIELD = (20, 108, 812, 555)
SIDE = (850, 108, 282, 555)
BASE = (425, 379)
BASE_RADIUS = 68
PADS = ((284, 374), (567, 374), (425, 516))
ENTRANCES = (
    (86, 178), (758, 583), (752, 172), (94, 591),
    (425, 142), (800, 371), (425, 628), (54, 371),
)
MAX_BASE_HP = 180
REPAIR_COST, REPAIR_HP = 4, 38
UPGRADE_COST = (5, 2)
STARTING_PLAYER_HP = 100

BG = '#0c1621'
PANEL = '#162534'
BORDER = '#2d4558'
TEXT = '#edf5fa'
MUTED = '#a8bdcd'
GREEN = '#8ee5ae'
BLUE = '#78d7ff'
GOLD = '#ffd181'
PURPLE = '#c9b3ff'
RED = '#ff8580'


@dataclass(frozen=True)
class EnemyKind:
    hp: int
    speed: int
    base_damage: int
    player_damage: int
    radius: int
    color: str


ENEMY_KINDS = (
    EnemyKind(48, 51, 6, 9, 14, RED),
    EnemyKind(29, 84, 4, 7, 10, '#ffac66'),
)

# Each tuple lists the enemy types that enter, in their spawn order.
WAVES = (
    (0,) * 8,
    (0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0),
    (1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1),
)
SPAWN_INTERVALS = (1.15, 0.94, 0.77)


@dataclass(frozen=True)
class DefenseKind:
    name: tuple
    description: tuple
    cost: tuple
    reach: int
    damage: int
    interval: float
    color: str


DEFENSES = (
    DefenseKind(('哨戒塔', 'Sentry'), ('快速攻擊單一敵人', 'Rapid single-target shots'),
                (5, 2), 185, 18, 0.55, GOLD),
    DefenseKind(('冰霜塔', 'Frost tower'), ('傷害並減緩敵人', 'Damages and slows enemies'),
                (5, 3), 170, 12, 0.62, BLUE),
    DefenseKind(('脈衝塔', 'Pulse tower'), ('同時打擊附近敵群', 'Hits groups near the target'),
                (7, 3), 171, 22, 0.90, PURPLE),
)

UPGRADES = (
    (('攻擊強化', 'Power'), ('每次攻擊傷害 +8', 'Attack damage +8'), GOLD),
    (('生命強化', 'Vitality'), ('最大生命與目前生命 +25', 'Maximum and current HP +25'), GREEN),
    (('移動強化', 'Agility'), ('移動速度 +30', 'Movement speed +30'), BLUE),
)


@dataclass
class Enemy:
    kind: int
    x: float
    y: float
    hp: int
    max_hp: int
    base_wait: float = 0.0
    slowed: float = 0.0


@dataclass
class Tower:
    kind: int
    upgraded: bool = False
    wait: float = 0.0


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


def distance(ax, ay, bx, by):
    return hypot(ax - bx, ay - by)


class Game:
    def __init__(self):
        self.reset()
        self.phase = 'title'

    def reset(self):
        self.phase = 'combat'
        self.wave = 0
        self.spawned = 0
        self.spawn_wait = 0.75
        self.player_x, self.player_y = 425.0, 467.0
        self.player_hp = self.max_player_hp = STARTING_PLAYER_HP
        self.base_hp = MAX_BASE_HP
        self.player_speed, self.damage, self.reach = 240, 24, 153
        self.attack_wait = self.hurt_wait = 0.0
        self.parts = self.energy = self.kills = self.xp = 0
        self.level, self.next_xp = 1, 5
        self.elapsed = 0.0
        self.selected_pad = 0
        self.enemies = []
        self.drops = []
        self.shots = []
        self.towers = [None] * len(PADS)
        self.notice = ('', '')
        self.notice_left = 0.0
        self.loss_reason = ('', '')

    def message(self, chinese, english):
        self.notice = chinese, english
        self.notice_left = 2.6

    def advance_wave(self):
        if self.phase == 'prepare' and self.wave + 1 < len(WAVES):
            self.wave += 1
            self.spawned = 0
            self.spawn_wait = 0.75
            self.phase = 'combat'
            self.notice_left = 0.0

    def can_afford(self, cost):
        return self.parts >= cost[0] and self.energy >= cost[1]

    def spend(self, cost):
        if not self.can_afford(cost):
            self.message('資源不足', 'Insufficient resources')
            return False
        self.parts -= cost[0]
        self.energy -= cost[1]
        return True

    def repair(self):
        if self.phase != 'prepare':
            return
        if self.base_hp == MAX_BASE_HP:
            self.message('禮堂耐久已滿', 'Auditorium durability is full')
            return
        if self.spend((REPAIR_COST, 0)):
            restored = min(REPAIR_HP, MAX_BASE_HP - self.base_hp)
            self.base_hp += restored
            self.message(f'禮堂耐久 +{restored}', f'Auditorium +{restored} HP')

    def build(self, kind):
        if self.phase != 'prepare':
            return
        if self.towers[self.selected_pad] is not None:
            self.message('這個建造點已有防禦塔', 'A tower already occupies this pad')
            return
        defense = DEFENSES[kind]
        if self.spend(defense.cost):
            self.towers[self.selected_pad] = Tower(kind)
            self.message(f'已建造{defense.name[0]}', f'{defense.name[1]} built')

    def upgrade_tower(self):
        if self.phase != 'prepare':
            return
        tower = self.towers[self.selected_pad]
        if tower is None:
            self.message('請先在這裡建塔', 'Build a tower on this pad first')
        elif tower.upgraded:
            self.message('這座塔已達最高等級', 'This tower is fully upgraded')
        elif self.spend(UPGRADE_COST):
            tower.upgraded = True
            self.message('砲塔攻擊與射程提升', 'Tower damage and range increased')

    def choose_upgrade(self, choice):
        if self.phase != 'upgrade':
            return
        self.xp -= self.next_xp
        self.level += 1
        self.next_xp += 3
        if choice == 0:
            self.damage += 8
        elif choice == 1:
            self.max_player_hp += 25
            self.player_hp += 25
        else:
            self.player_speed += 30
        if self.xp < self.next_xp:
            self.phase = 'combat'

    def move_player(self, dx, dy, dt):
        length = hypot(dx, dy)
        if length:
            self.player_x += self.player_speed * dx / length * dt
            self.player_y += self.player_speed * dy / length * dt
        left, top, width, height = FIELD
        self.player_x = max(left + 18, min(left + width - 18, self.player_x))
        self.player_y = max(top + 18, min(top + height - 18, self.player_y))

    def collect_drops(self):
        remaining = []
        for drop in self.drops:
            if distance(self.player_x, self.player_y, drop.x, drop.y) <= 30:
                if drop.energy:
                    self.energy += 1
                else:
                    self.parts += 1
            else:
                remaining.append(drop)
        self.drops = remaining

    def spawn_enemy(self):
        kind = WAVES[self.wave][self.spawned]
        x, y = ENTRANCES[(self.spawned + 2 * self.wave) % len(ENTRANCES)]
        hp = ENEMY_KINDS[kind].hp + 6 * self.wave
        self.enemies.append(Enemy(kind, x, y, hp, hp))
        self.spawned += 1

    def move_enemies(self, dt):
        for enemy in self.enemies:
            kind = ENEMY_KINDS[enemy.kind]
            enemy.slowed = max(0.0, enemy.slowed - dt)
            dx, dy = BASE[0] - enemy.x, BASE[1] - enemy.y
            length = hypot(dx, dy)
            room = length - BASE_RADIUS - kind.radius
            if room > 0.01:
                speed = kind.speed * (1 + 0.08 * self.wave)
                if enemy.slowed:
                    speed *= 0.54
                travel = min(room, speed * dt)
                enemy.x += dx * travel / length
                enemy.y += dy * travel / length
            else:
                enemy.base_wait -= dt
                if enemy.base_wait <= 0:
                    self.base_hp = max(0, self.base_hp - kind.base_damage)
                    enemy.base_wait = 0.9
            if self.hurt_wait <= 0 and distance(enemy.x, enemy.y, self.player_x, self.player_y) < kind.radius + 13:
                self.player_hp = max(0, self.player_hp - kind.player_damage)
                self.hurt_wait = 0.62

    def target_at(self, x, y, reach):
        nearest = None
        for enemy in self.enemies:
            gap = distance(x, y, enemy.x, enemy.y)
            if enemy.hp > 0 and gap <= reach:
                reach, nearest = gap, enemy
        return nearest

    def attack(self, dt):
        self.attack_wait -= dt
        if self.attack_wait <= 0:
            target = self.target_at(self.player_x, self.player_y, self.reach)
            if target is not None:
                target.hp -= self.damage
                self.shots.append(Shot((self.player_x, self.player_y), (target.x, target.y), BLUE))
                self.attack_wait = 0.37
        for pad, tower in zip(PADS, self.towers):
            if tower is None:
                continue
            tower.wait -= dt
            if tower.wait > 0:
                continue
            kind = DEFENSES[tower.kind]
            reach = kind.reach + (22 if tower.upgraded else 0)
            target = self.target_at(*pad, reach)
            if target is None:
                continue
            damage = kind.damage * 3 // 2 if tower.upgraded else kind.damage
            target.hp -= damage
            if tower.kind == 1:
                target.slowed = 1.08
            elif tower.kind == 2:
                for enemy in self.enemies:
                    if enemy is not target and enemy.hp > 0 and distance(enemy.x, enemy.y, target.x, target.y) <= 67:
                        enemy.hp -= damage
                        self.shots.append(Shot((target.x, target.y), (enemy.x, enemy.y), kind.color))
            self.shots.append(Shot(pad, (target.x, target.y), kind.color))
            tower.wait = kind.interval

    def remove_defeated(self):
        survivors = []
        for enemy in self.enemies:
            if enemy.hp > 0:
                survivors.append(enemy)
                continue
            self.kills += 1
            self.xp += 1
            self.drops.append(Drop(enemy.x - 8, enemy.y))
            if self.kills % 2 == 0:
                self.drops.append(Drop(enemy.x + 8, enemy.y, energy=True))
        self.enemies = survivors

    def update(self, dt, dx, dy):
        if self.phase not in ('combat', 'prepare'):
            return
        self.notice_left -= dt
        self.move_player(dx, dy, dt)
        self.collect_drops()
        for shot in self.shots:
            shot.remaining -= dt
        self.shots = [shot for shot in self.shots if shot.remaining > 0]
        if self.phase == 'prepare':
            return
        self.elapsed += dt
        self.hurt_wait = max(0.0, self.hurt_wait - dt)
        self.spawn_wait -= dt
        if self.spawn_wait <= 0 and self.spawned < len(WAVES[self.wave]):
            self.spawn_enemy()
            self.spawn_wait = SPAWN_INTERVALS[self.wave]
        self.move_enemies(dt)
        if self.player_hp == 0 or self.base_hp == 0:
            self.phase = 'loss'
            self.loss_reason = ('禮堂耐久已歸零', 'The auditorium fell') if self.base_hp == 0 else (
                '守衛的生命已歸零', 'The defender fell')
            return
        self.attack(dt)
        self.remove_defeated()
        self.collect_drops()
        if self.xp >= self.next_xp:
            self.phase = 'upgrade'
        elif self.spawned == len(WAVES[self.wave]) and not self.enemies:
            if self.wave + 1 == len(WAVES):
                self.phase = 'win'
            else:
                self.phase = 'prepare'
                self.message('可以拾取零件與能量，再決定如何備戰', 'Pick up drops, then repair or build')


@dataclass
class Button:
    bounds: tuple
    action: Callable[[], None]


def inside(x, y, bounds):
    left, top, width, height = bounds
    return left <= x < left + width and top <= y < top + height


class Interface:
    def __init__(self, canvas):
        self.canvas = canvas
        self.game = Game()
        self.keys = set()
        self.buttons = []
        self.pointer = (-1, -1)
        self.before_pause = 'combat'
        self.drawn_phase = None

    def word(self, chinese, english):
        return chinese if self.canvas.chinese else english

    def text(self, x, y, value, size=18, color=TEXT, anchor='w'):
        self.canvas.text(x, y, value, size, color, anchor)

    def label(self, x, y, chinese, english, size=18, color=TEXT, anchor='w'):
        self.text(x, y, self.word(chinese, english), size, color, anchor)

    def button(self, x, y, width, height, title, action, accent=BLUE, primary=False):
        bounds = (x, y, width, height)
        hover = inside(*self.pointer, bounds)
        fill = accent if primary else ('#294355' if hover else '#203345')
        self.canvas.rect(*bounds, fill, outline=accent if hover or primary else BORDER)
        self.text(x + width / 2, y + height / 2, self.word(*title), 16,
                  BG if primary else TEXT, 'center')
        self.buttons.append(Button(bounds, action))

    def start(self):
        self.keys.clear()
        self.game.reset()

    def title(self):
        self.keys.clear()
        self.game.phase = 'title'

    def help(self):
        self.game.phase = 'help'

    def pause(self):
        if self.game.phase in ('combat', 'prepare'):
            self.before_pause = self.game.phase
            self.game.phase = 'pause'

    def focus_lost(self):
        self.pause()
        self.keys.clear()

    def resume(self):
        self.game.phase = self.before_pause

    def key_down(self, key):
        if key in self.keys:
            return
        self.keys.add(key)
        phase = self.game.phase
        if phase == 'title':
            if key in ('enter', 'space'):
                self.start()
            elif key == 'h':
                self.help()
        elif phase == 'help' and key in ('escape', 'enter'):
            self.title()
        elif phase in ('combat', 'prepare'):
            if key == 'escape':
                self.pause()
            elif phase == 'prepare':
                if key == 'enter':
                    self.game.advance_wave()
                elif key == 'r':
                    self.game.repair()
                elif key == 'u':
                    self.game.upgrade_tower()
                elif key == 'tab':
                    self.game.selected_pad = (self.game.selected_pad + 1) % len(PADS)
                elif key in ('1', '2', '3'):
                    self.game.build(int(key) - 1)
        elif phase == 'upgrade' and key in ('1', '2', '3'):
            self.game.choose_upgrade(int(key) - 1)
        elif phase == 'pause':
            if key in ('escape', 'enter'):
                self.resume()
            elif key == 'r':
                self.start()
        elif phase in ('win', 'loss'):
            if key in ('r', 'enter'):
                self.start()
            elif key == 'escape':
                self.title()

    def key_up(self, key):
        self.keys.discard(key)

    def click(self, x, y):
        if self.drawn_phase != self.game.phase:
            return
        for button in reversed(self.buttons):
            if inside(x, y, button.bounds):
                button.action()
                return
        if self.game.phase == 'prepare':
            for index, (px, py) in enumerate(PADS):
                if distance(x, y, px, py) <= 30:
                    self.game.selected_pad = index
                    return

    def tick(self, dt):
        dx = int(bool(self.keys & {'right', 'd'})) - int(bool(self.keys & {'left', 'a'}))
        dy = int(bool(self.keys & {'down', 's'})) - int(bool(self.keys & {'up', 'w'}))
        self.game.update(min(dt, 0.05), dx, dy)

    def draw_field(self):
        draw = self.canvas
        draw.rect(*FIELD, '#132931', outline='#38535d')
        for x in range(41, 813, 32):
            draw.line((x, 109), (x, 661), '#193139')
        for y in range(125, 652, 32):
            draw.line((21, y), (831, y), '#193139')
        for entry in ENTRANCES:
            draw.line(entry, BASE, '#213c43', width=2)
            draw.circle(*entry, 8, '#422e36', outline='#9e5455')
        draw.circle(*BASE, 108, '#1c373a')
        draw.circle(*BASE, 75, '#203e43', outline='#4b7275', width=2)
        draw.rect(365, 344, 120, 63, '#314958', outline='#556f7c')
        draw.rect(365, 389, 120, 16, '#6f8895')
        for x in (376, 395, 445, 464):
            draw.rect(x, 349, 9, 39, '#a0bbc4')
        draw.rect(413, 359, 25, 30, '#172a38')
        draw.polygon(((356, 346), (425, 316), (494, 346)), '#a67364', outline='#d4a28a')
        draw.rect(361, 405, 128, 6, '#8ba3ad')
        draw.rect(356, 411, 138, 5, '#526c7b')
        self.label(425, 434, '清大大禮堂', 'NTHU AUDITORIUM', 13, '#c8e4e6', 'center')
        for index, (x, y) in enumerate(PADS):
            tower = self.game.towers[index]
            selected = self.game.phase == 'prepare' and index == self.game.selected_pad
            draw.circle(x, y, 26, '#233d45', outline=BLUE if selected else '#54727c', width=2)
            if tower is None:
                self.text(x, y, str(index + 1), 17, BLUE if selected else MUTED, 'center')
            else:
                defense = DEFENSES[tower.kind]
                draw.rect(x - 11, y - 9, 22, 20, defense.color, outline=TEXT if tower.upgraded else None)
                draw.line((x, y), (x + 12, y - 13), defense.color, width=6)
                if tower.upgraded:
                    draw.circle(x, y + 16, 3, TEXT)

    def draw_entities(self):
        draw, game = self.canvas, self.game
        for drop in game.drops:
            x, y = drop.x, drop.y
            if drop.energy:
                draw.polygon(((x, y - 6), (x + 5, y), (x, y + 6), (x - 5, y)), PURPLE)
            else:
                draw.rect(x - 4, y - 4, 8, 8, GOLD, outline='#ffe3aa')
        for enemy in game.enemies:
            kind = ENEMY_KINDS[enemy.kind]
            x, y, radius = enemy.x, enemy.y, kind.radius
            if enemy.slowed:
                draw.circle(x, y, radius + 4, '#427085', outline=BLUE)
            if enemy.kind == 0:
                draw.circle(x, y, radius, '#63323c', outline=RED, width=2)
            else:
                points = tuple((x + radius * cos(tau * i / 4), y + radius * sin(tau * i / 4)) for i in range(4))
                draw.polygon(points, '#794932', outline=kind.color)
            draw.circle(x, y, 4, kind.color)
            if enemy.hp < enemy.max_hp:
                self.bar(x - 13, y - radius - 8, 26, 3, enemy.hp / enemy.max_hp, RED)
        for shot in game.shots:
            draw.line(shot.origin, shot.target, shot.color, width=2)
            draw.circle(*shot.target, 4, shot.color)
        x, y = game.player_x, game.player_y
        if game.hurt_wait <= 0 or int(game.hurt_wait * 24) % 2 == 0:
            draw.circle(x, y, 15, '#224e68', outline=BLUE, width=2)
            draw.rect(x - 6, y - 5, 12, 10, '#e1f6ff')
            draw.circle(x, y + 1, 3, '#32768f')

    def bar(self, x, y, width, height, fraction, color):
        self.canvas.rect(x, y, width, height, '#0b1923')
        filled = int(width * min(1.0, max(0.0, fraction)))
        if filled:
            self.canvas.rect(x, y, filled, height, color)

    def draw_hud(self):
        draw, game = self.canvas, self.game
        draw.rect(20, 18, 1112, 72, PANEL, outline=BORDER)
        self.label(37, 42, '大禮堂防衛戰', 'AUDITORIUM DEFENSE', 22)
        self.label(38, 68, '國立清華大學', 'NATIONAL TSING HUA UNIVERSITY', 12, MUTED)
        self.label(338, 39, '守衛生命', 'DEFENDER HP', 14, BLUE)
        self.text(510, 39, f'{game.player_hp} / {game.max_player_hp}', 15, TEXT, 'e')
        self.bar(338, 59, 172, 8, game.player_hp / game.max_player_hp, BLUE)
        self.label(548, 39, '禮堂耐久', 'AUDITORIUM HP', 14, GREEN)
        self.text(742, 39, f'{game.base_hp} / {MAX_BASE_HP}', 15, TEXT, 'e')
        self.bar(548, 59, 194, 8, game.base_hp / MAX_BASE_HP, GREEN)
        self.label(783, 39, '波次', 'WAVE', 14, MUTED)
        self.text(783, 65, f'{game.wave + 1} / {len(WAVES)}', 20)
        self.label(907, 39, '零件', 'PARTS', 14, GOLD)
        self.text(907, 65, str(game.parts), 20, GOLD)
        self.label(1019, 39, '能量', 'ENERGY', 14, PURPLE)
        self.text(1019, 65, str(game.energy), 20, PURPLE)

    def draw_side(self):
        draw, game = self.canvas, self.game
        draw.rect(*SIDE, PANEL, outline=BORDER)
        self.label(868, 135, '戰況', 'STATUS', 15, MUTED)
        if game.phase == 'prepare' or (game.phase == 'pause' and self.before_pause == 'prepare'):
            self.draw_preparation()
            return
        left = len(WAVES[game.wave]) - game.spawned + len(game.enemies)
        self.label(868, 172, f'第 {game.wave + 1} 波', f'Wave {game.wave + 1}', 28)
        self.label(868, 218, f'剩餘敵人   {left}', f'Enemies remaining   {left}', 17)
        self.label(868, 253, f'已擊倒   {game.kills}', f'Defeated   {game.kills}', 17)
        draw.line((869, 285), (1112, 285), BORDER)
        self.label(868, 318, f'等級 {game.level}', f'Level {game.level}', 20, GREEN)
        self.text(1111, 319, f'{game.xp} / {game.next_xp} XP', 15, MUTED, 'e')
        self.bar(868, 348, 244, 9, game.xp / game.next_xp, GREEN)
        self.label(868, 399, '靠近敵人時自動攻擊', 'Attacks trigger near enemies', 16, MUTED)
        self.label(868, 430, '走到掉落物旁即可拾取', 'Walk over drops to collect them', 16, MUTED)
        self.label(868, 492, '方向鍵 / WASD 移動', 'Arrow keys / WASD to move', 16)
        self.label(868, 525, 'Esc 暫停', 'Esc to pause', 16)

    def draw_preparation(self):
        game = self.game
        self.label(868, 170, '波次間備戰', 'Preparation', 27)
        self.label(868, 201, '點地圖或按 Tab 選擇建造點', 'Click a pad or use Tab to select', 14, MUTED)
        tower = game.towers[game.selected_pad]
        pad_status = self.word('空地', 'Empty') if tower is None else self.word(*DEFENSES[tower.kind].name)
        if tower is not None and tower.upgraded:
            pad_status += ' Lv.2'
        self.label(868, 233, f'建造點 {game.selected_pad + 1}   {pad_status}',
                   f'Pad {game.selected_pad + 1}   {pad_status}', 16, BLUE)
        for index, defense in enumerate(DEFENSES):
            y = 255 + index * 66
            cost = defense.cost
            zh, en = defense.name
            self.button(868, y, 246, 36, (f'{index + 1}  {zh}   {cost[0]} 零件 / {cost[1]} 能量',
                                           f'{index + 1}  {en}   {cost[0]}P / {cost[1]}E'),
                        lambda kind=index: game.build(kind), defense.color)
            self.label(878, y + 49, *defense.description, 13, MUTED)
        self.button(868, 458, 246, 37, ('R  修理禮堂   4 零件', 'R  Repair auditorium   4P'), game.repair)
        self.button(868, 503, 246, 37, ('U  升級選取的塔   5 零件 / 2 能量', 'U  Upgrade selected tower   5P / 2E'),
                    game.upgrade_tower)
        self.button(868, 575, 246, 45, ('Enter  開始下一波', 'Enter  Start next wave'), game.advance_wave, GREEN, True)

    def overlay(self, x, y, width, height):
        self.buttons.clear()
        self.canvas.rect(x + 7, y + 8, width, height, '#09121b')
        self.canvas.rect(x, y, width, height, '#172a3a', outline='#52788b', line_width=2)

    def draw_title(self):
        self.overlay(308, 183, 536, 352)
        self.label(576, 228, '國立清華大學', 'NATIONAL TSING HUA UNIVERSITY', 15, BLUE, 'center')
        self.label(576, 296, '大禮堂防衛戰', 'Auditorium Defense', 46, TEXT, 'center')
        self.label(576, 361, '收集資源、配置防禦塔，守住三波敵襲。',
                   'Collect resources and protect the base for three waves.', 17, MUTED, 'center')
        self.button(378, 438, 190, 48, ('Enter  開始遊戲', 'Enter  Start'), self.start, BLUE, True)
        self.button(584, 438, 190, 48, ('H  操作說明', 'H  Controls'), self.help)

    def draw_help(self):
        self.overlay(289, 168, 574, 382)
        self.label(326, 217, '操作說明', 'How to play', 30)
        rows = (
            ('方向鍵或 WASD 移動，附近有敵人時自動攻擊。', 'Move with the arrow keys or WASD. Attacks are automatic.'),
            ('走近零件和能量即可拾取。升級用 1、2、3 三選一。', 'Walk over drops to collect them. Pick an upgrade with 1–3.'),
            ('波次間按 Tab 選建造點，按 1、2、3 選塔種。', 'Between waves, Tab selects a pad and 1–3 builds a tower.'),
            ('按 R 修禮堂、按 U 升級塔、按 Enter 開始下一波。', 'R repairs, U upgrades the tower, and Enter starts a wave.'),
            ('守衛和禮堂都撐過第三波，就能獲勝。', 'Win by keeping the defender and auditorium alive for three waves.'),
        )
        for index, row in enumerate(rows):
            self.label(326, 270 + index * 36, *row, 16, MUTED)
        self.button(469, 468, 215, 44, ('Esc  回標題', 'Esc  Back to title'), self.title)

    def draw_upgrade(self):
        self.overlay(230, 252, 692, 222)
        self.label(576, 294, '角色升級', 'Level up', 29, GREEN, 'center')
        self.label(576, 335, '選擇一項強化後繼續戰鬥', 'Choose an upgrade to resume combat', 16, MUTED, 'center')
        for index, (title, details, color) in enumerate(UPGRADES):
            x = 251 + 221 * index
            self.button(x, 370, 208, 40, (f'{index + 1}  {title[0]}', f'{index + 1}  {title[1]}'),
                        lambda choice=index: self.game.choose_upgrade(choice), color)
            self.label(x + 104, 434, *details, 15, color, 'center')

    def draw_result(self, victory):
        game = self.game
        self.overlay(307, 213, 538, 294)
        if victory:
            self.label(576, 271, '防守成功', 'Auditorium secured', 35, GREEN, 'center')
            self.label(576, 321, '成功守住第三波的最後一名敵人。', 'All three waves defeated.', 17, MUTED, 'center')
        else:
            self.label(576, 271, '防守失敗', 'Defense failed', 35, RED, 'center')
            self.label(576, 321, *game.loss_reason, 17, MUTED, 'center')
        elapsed = int(game.elapsed)
        self.label(576, 372, f'擊倒 {game.kills} 隻    戰鬥時間 {elapsed // 60}:{elapsed % 60:02d}',
                   f'{game.kills} defeated    Combat time {elapsed // 60}:{elapsed % 60:02d}', 17, TEXT, 'center')
        self.button(368, 425, 200, 46, ('R  再玩一局', 'R  Play again'), self.start, BLUE, True)
        self.button(584, 425, 200, 46, ('Esc  回標題', 'Esc  Back to title'), self.title)

    def draw(self):
        game = self.game
        self.drawn_phase = game.phase
        self.buttons.clear()
        self.canvas.clear(BG)
        self.draw_field()
        self.draw_entities()
        self.draw_hud()
        self.draw_side()
        if game.notice_left > 0 and game.phase in ('combat', 'prepare'):
            self.label(23, 690, *game.notice, 16, GOLD)
        elif game.phase in ('combat', 'prepare'):
            self.label(23, 690, '守衛為藍色，敵人為紅色或橘色。', 'Blue defender, red or orange enemies.', 14, MUTED)
        if game.phase == 'title':
            self.draw_title()
        elif game.phase == 'help':
            self.draw_help()
        elif game.phase == 'upgrade':
            self.draw_upgrade()
        elif game.phase == 'pause':
            self.overlay(311, 249, 530, 226)
            self.label(576, 307, '已暫停', 'Paused', 34, TEXT, 'center')
            self.button(341, 389, 150, 44, ('Enter  繼續', 'Enter  Resume'), self.resume, BLUE, True)
            self.button(501, 389, 150, 44, ('R  重新開始', 'R  Restart'), self.start)
            self.button(661, 389, 150, 44, ('回標題', 'Title'), self.title)
        elif game.phase in ('win', 'loss'):
            self.draw_result(game.phase == 'win')


class PygameCanvas:
    def __init__(self, pygame, screen):
        self.pg, self.screen = pygame, screen
        windows_font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'msjh.ttc'
        self.font_file = str(windows_font) if windows_font.is_file() else pygame.font.match_font(
            'microsoftjhenghei,pingfangtc,notosanscjktc,notosanscjk,wenquanyizenhei')
        self.chinese = self.font_file is not None
        self.fonts = {}

    def clear(self, color):
        self.screen.fill(color)

    def rect(self, x, y, width, height, color, outline=None, line_width=1):
        bounds = self.pg.Rect(int(x), int(y), int(width), int(height))
        self.pg.draw.rect(self.screen, color, bounds)
        if outline:
            self.pg.draw.rect(self.screen, outline, bounds, line_width)

    def circle(self, x, y, radius, color, outline=None, width=1):
        center = int(x), int(y)
        self.pg.draw.circle(self.screen, color, center, int(radius))
        if outline:
            self.pg.draw.circle(self.screen, outline, center, int(radius), width)

    def line(self, start, end, color, width=1):
        self.pg.draw.line(self.screen, color, start, end, width)

    def polygon(self, points, color, outline=None):
        self.pg.draw.polygon(self.screen, color, points)
        if outline:
            self.pg.draw.polygon(self.screen, outline, points, 1)

    def text(self, x, y, value, size, color, anchor):
        if size not in self.fonts:
            self.fonts[size] = self.pg.font.Font(self.font_file, size)
        surface = self.fonts[size].render(value, True, color)
        box = surface.get_rect()
        setattr(box, {'w': 'midleft', 'e': 'midright', 'center': 'center'}[anchor], (int(x), int(y)))
        self.screen.blit(surface, box)


class TkCanvas:
    def __init__(self, canvas, families):
        self.canvas = canvas
        available = set(families)
        preferred = ('Microsoft JhengHei UI', 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans CJK TC', 'WenQuanYi Zen Hei')
        self.family = next((name for name in preferred if name in available), None)
        self.chinese = self.family is not None
        if not self.family:
            self.family = 'TkDefaultFont'

    def clear(self, color):
        self.canvas.delete('all')
        self.canvas.configure(background=color)

    def rect(self, x, y, width, height, color, outline=None, line_width=1):
        self.canvas.create_rectangle(x, y, x + width, y + height, fill=color, outline=outline or '', width=line_width)

    def circle(self, x, y, radius, color, outline=None, width=1):
        self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=color,
                                outline=outline or '', width=width)

    def line(self, start, end, color, width=1):
        self.canvas.create_line(*start, *end, fill=color, width=width)

    def polygon(self, points, color, outline=None):
        coords = [coord for point in points for coord in point]
        self.canvas.create_polygon(*coords, fill=color, outline=outline or '')

    def text(self, x, y, value, size, color, anchor):
        self.canvas.create_text(x, y, text=value, anchor=anchor, fill=color, font=(self.family, -size))


KEY_NAMES = {'return': 'enter', 'kp_enter': 'enter', 'kp enter': 'enter',
             'kp_1': '1', 'kp_2': '2', 'kp_3': '3', '[1]': '1', '[2]': '2', '[3]': '3'}


def normalize_key(name):
    name = name.lower()
    return KEY_NAMES.get(name, name)


def run_pygame(pygame):
    pygame.display.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption('大禮堂防衛戰 | Auditorium Defense')
        clock = pygame.time.Clock()
        interface = Interface(PygameCanvas(pygame, screen))
        while True:
            dt = clock.tick(60) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    interface.key_down(normalize_key(pygame.key.name(event.key)))
                elif event.type == pygame.KEYUP:
                    interface.key_up(normalize_key(pygame.key.name(event.key)))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    interface.click(*event.pos)
                elif event.type == pygame.WINDOWFOCUSLOST:
                    interface.focus_lost()
            interface.pointer = pygame.mouse.get_pos()
            interface.tick(dt)
            interface.draw()
            pygame.display.flip()
    finally:
        pygame.quit()


def run_tkinter():
    import tkinter as tk
    from tkinter import font

    root = tk.Tk()
    root.title('大禮堂防衛戰 | Auditorium Defense')
    root.resizable(False, False)
    widget = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, background=BG)
    widget.pack()
    interface = Interface(TkCanvas(widget, font.families(root)))
    root.bind('<KeyPress>', lambda event: interface.key_down(normalize_key(event.keysym)))
    root.bind('<KeyRelease>', lambda event: interface.key_up(normalize_key(event.keysym)))
    root.bind('<FocusOut>', lambda event: interface.focus_lost())
    widget.bind('<Button-1>', lambda event: interface.click(event.x, event.y))
    widget.bind('<Motion>', lambda event: setattr(interface, 'pointer', (event.x, event.y)))
    widget.bind('<Leave>', lambda event: setattr(interface, 'pointer', (-1, -1)))
    previous = perf_counter()

    def frame():
        nonlocal previous
        now = perf_counter()
        interface.tick(now - previous)
        interface.draw()
        previous = now
        root.after(16, frame)

    frame()
    root.mainloop()


def main():
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    try:
        import pygame
    except ModuleNotFoundError as error:
        if error.name != 'pygame':
            raise
        run_tkinter()
    else:
        run_pygame(pygame)


if __name__ == '__main__':
    main()
