"""Wave progression, combat, economy, and upgrade rules."""

import random
from math import hypot

from .config import (
    BASE, BASE_RADIUS, BLUE, BOSS_ENTRANCE, BOSS_KIND, BOSS_WAVE, DEFENSES,
    ENEMY_KINDS, ENTRANCES, FIELD, MAX_BASE_HP, PADS, PLAYER_MELEE_COOLDOWN,
    PLAYER_MELEE_FLASH_DURATION, PLAYER_MELEE_RANGE, PLAYER_RANGED_INTERVAL,
    PLAYER_RANGED_RANGE, REPAIR_COST, REPAIR_HP, SPAWN_INTERVALS,
    STARTING_PLAYER_HP, UPGRADE_COST, WAVES,
)
from .geometry import distance
from .models import Drop, Enemy, Shot, Tower


class Game:
    def __init__(self):
        self.reset()
        self.phase = 'title'

    def reset(self):
        self.phase = 'combat'
        self.wave = 0
        self.spawned = 0
        self.rng = random.Random()
        self.wave_queue = list(WAVES[self.wave])
        self.rng.shuffle(self.wave_queue)
        self.route_queue = list(ENTRANCES)
        self.rng.shuffle(self.route_queue)
        self.spawn_wait = 0.75
        self.boss_spawned = False
        self.player_x, self.player_y = 425.0, 467.0
        self.player_hp = self.max_player_hp = STARTING_PLAYER_HP
        self.base_hp = MAX_BASE_HP
        self.player_speed, self.damage = 240, 24
        self.attack_wait = self.hurt_wait = 0.0
        self.melee_wait = self.melee_flash = 0.0
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
            self.wave_queue = list(WAVES[self.wave])
            self.rng.shuffle(self.wave_queue)
            self.route_queue = list(ENTRANCES)
            self.rng.shuffle(self.route_queue)
            self.spawn_wait = 0.75
            self.boss_spawned = False
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
        if self.phase != 'prepare' or not 0 <= kind < len(DEFENSES):
            return
        if self.towers[self.selected_pad] is not None:
            self.message('這個建造點已有防禦設施', 'This pad is already occupied')
            return
        defense = DEFENSES[kind]
        if self.spend(defense.cost):
            self.towers[self.selected_pad] = Tower(
                kind, hp=defense.durability, max_hp=defense.durability
            )
            self.message(f'已建造{defense.name[0]}', f'{defense.name[1]} built')

    def upgrade_tower(self):
        if self.phase != 'prepare':
            return
        tower = self.towers[self.selected_pad]
        if tower is None:
            self.message('請先在這裡建造防禦設施', 'Build a defense on this pad first')
        elif tower.upgraded:
            self.message('這個設施已達最高等級', 'This defense is fully upgraded')
        elif self.spend(UPGRADE_COST):
            tower.upgraded = True
            if DEFENSES[tower.kind].mode == 'wall':
                tower.max_hp += 44
                tower.hp = tower.max_hp
            self.message('設施效果已提升', 'Defense upgraded')

    def choose_upgrade(self, choice):
        if self.phase != 'upgrade' or choice not in (0, 1, 2):
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

    def manual_attack(self):
        """Damage every enemy in the defender's circular melee radius."""
        if self.phase != 'combat' or self.melee_wait > 0:
            return False
        self.melee_wait = PLAYER_MELEE_COOLDOWN
        self.melee_flash = PLAYER_MELEE_FLASH_DURATION
        damage = self.damage + 16
        hit_count = 0
        for enemy in self.enemies:
            if enemy.hp <= 0:
                continue
            dx, dy = enemy.x - self.player_x, enemy.y - self.player_y
            gap = hypot(dx, dy)
            if gap > PLAYER_MELEE_RANGE + ENEMY_KINDS[enemy.kind].radius:
                continue
            enemy.hp -= damage
            hit_count += 1
        if hit_count:
            self.message('近戰命中敵人', 'Melee strike hit')
        return True

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
        kind_index = self.wave_queue[self.spawned]
        kind = ENEMY_KINDS[kind_index]
        x, y = self.route_queue[self.spawned % len(self.route_queue)]
        hp = kind.hp + 6 * self.wave
        self.enemies.append(Enemy(kind_index, x, y, hp, hp, dash_wait=kind.dash_interval))
        self.spawned += 1

    def spawn_boss(self):
        kind = ENEMY_KINDS[BOSS_KIND]
        x, y = BOSS_ENTRANCE
        hp = kind.hp + 120 * self.wave
        self.enemies.append(Enemy(BOSS_KIND, x, y, hp, hp))
        self.boss_spawned = True
        self.message('最終 Boss 出現！', 'The final boss has arrived!')

    def wall_on_route(self, enemy, kind, dx, dy, length):
        """Return the first wall intersecting an enemy's straight route to base."""
        squared_length = dx * dx + dy * dy
        if squared_length == 0:
            return None
        nearest = None
        nearest_projection = 1.0
        blocking_radius = kind.radius + 24
        for index, tower in enumerate(self.towers):
            if tower is None or DEFENSES[tower.kind].mode != 'wall':
                continue
            wall_x, wall_y = PADS[index]
            projection = (
                (wall_x - enemy.x) * dx + (wall_y - enemy.y) * dy
            ) / squared_length
            if not 0 < projection < 1 or projection >= nearest_projection:
                continue
            closest_x = enemy.x + projection * dx
            closest_y = enemy.y + projection * dy
            if distance(closest_x, closest_y, wall_x, wall_y) > blocking_radius:
                continue
            nearest_projection = projection
            nearest = (index, max(0.0, projection * length - blocking_radius))
        return nearest

    def enemy_speed(self, enemy, kind):
        speed = kind.speed * (1 + 0.08 * self.wave)
        if enemy.slowed:
            speed *= 0.54
        if enemy.dash_left > 0:
            speed *= 2.0
        return speed

    def move_enemies(self, dt):
        for enemy in self.enemies:
            kind = ENEMY_KINDS[enemy.kind]
            enemy.slowed = max(0.0, enemy.slowed - dt)
            enemy.dash_wait = max(0.0, enemy.dash_wait - dt)
            enemy.dash_left = max(0.0, enemy.dash_left - dt)
            if kind.dash_interval and enemy.dash_wait == 0 and enemy.dash_left == 0:
                enemy.dash_left = kind.dash_duration
                enemy.dash_wait = kind.dash_interval
            if enemy.stunned > 0:
                enemy.stunned = max(0.0, enemy.stunned - dt)
                continue

            dx, dy = BASE[0] - enemy.x, BASE[1] - enemy.y
            length = hypot(dx, dy)
            if length <= 0:
                continue

            wall = self.wall_on_route(enemy, kind, dx, dy, length)
            target_distance = BASE_RADIUS + kind.radius + (kind.attack_range if kind.ranged else 0)
            room_to_base = max(0.0, length - target_distance)
            if wall is not None and wall[1] < room_to_base:
                wall_index, distance_to_wall = wall
                if distance_to_wall <= 0.01:
                    enemy.wall_wait -= dt
                    if enemy.wall_wait <= 0:
                        tower = self.towers[wall_index]
                        if tower is not None:
                            tower.hp = max(0, tower.hp - kind.base_damage)
                            enemy.wall_wait = max(0.45, kind.attack_interval)
                            if tower.hp == 0:
                                self.towers[wall_index] = None
                else:
                    speed = self.enemy_speed(enemy, kind)
                    travel = min(distance_to_wall, speed * dt)
                    enemy.x += dx * travel / length
                    enemy.y += dy * travel / length
            elif room_to_base > 0.01:
                speed = self.enemy_speed(enemy, kind)
                travel = min(room_to_base, speed * dt)
                enemy.x += dx * travel / length
                enemy.y += dy * travel / length
            else:
                enemy.base_wait -= dt
                if enemy.base_wait <= 0:
                    self.base_hp = max(0, self.base_hp - kind.base_damage)
                    enemy.base_wait = kind.attack_interval
                    if kind.ranged:
                        self.shots.append(Shot((enemy.x, enemy.y), BASE, kind.color))

            if (enemy.stunned <= 0 and self.hurt_wait <= 0
                    and distance(enemy.x, enemy.y, self.player_x, self.player_y) < kind.radius + 13):
                self.player_hp = max(0, self.player_hp - kind.player_damage)
                self.hurt_wait = 0.62

    def target_at(self, x, y, reach, include_enemy_radius=False):
        nearest = None
        nearest_gap = float('inf')
        for enemy in self.enemies:
            gap = distance(x, y, enemy.x, enemy.y)
            enemy_radius = ENEMY_KINDS[enemy.kind].radius if include_enemy_radius else 0
            target_reach = reach + enemy_radius
            if enemy.hp > 0 and gap <= target_reach and gap < nearest_gap:
                nearest_gap, nearest = gap, enemy
        return nearest

    def attack(self, dt):
        self.attack_wait -= dt
        if self.attack_wait <= 0:
            target = self.target_at(
                self.player_x, self.player_y, PLAYER_RANGED_RANGE,
                include_enemy_radius=True,
            )
            if target is not None:
                target.hp -= self.damage
                self.shots.append(Shot(
                    (self.player_x, self.player_y), (target.x, target.y), BLUE
                ))
                self.attack_wait = PLAYER_RANGED_INTERVAL

        for pad, tower in zip(PADS, self.towers):
            if tower is None:
                continue
            defense = DEFENSES[tower.kind]
            tower.wait = max(0.0, tower.wait - dt)
            tower.effect = max(0.0, tower.effect - dt)

            if defense.mode == 'wall' or tower.wait > 0:
                continue

            reach = defense.reach + (22 if tower.upgraded else 0)
            if defense.mode == 'stun':
                targets = [
                    enemy for enemy in self.enemies
                    if enemy.hp > 0 and distance(*pad, enemy.x, enemy.y) <= reach
                ]
                if not targets:
                    continue
                duration = defense.stun_duration + (0.7 if tower.upgraded else 0)
                for enemy in targets:
                    enemy.stunned = max(enemy.stunned, duration)
                tower.wait = defense.interval * (0.8 if tower.upgraded else 1)
                tower.effect = 0.42
                continue

            target = self.target_at(*pad, reach)
            if target is None:
                continue

            if defense.mode == 'trap':
                if ENEMY_KINDS[target.kind].boss:
                    target.hp -= 240 if tower.upgraded else 180
                else:
                    target.hp = 0
                tower.wait = defense.interval * (0.8 if tower.upgraded else 1)
                tower.effect = 0.5
                self.shots.append(Shot(pad, (target.x, target.y), defense.color))
                continue

            damage = defense.damage * 3 // 2 if tower.upgraded else defense.damage
            target.hp -= damage
            if defense.mode == 'egg':
                splash = defense.splash_radius + (12 if tower.upgraded else 0)
                for enemy in self.enemies:
                    if enemy is not target and enemy.hp > 0 and distance(
                        enemy.x, enemy.y, target.x, target.y
                    ) <= splash:
                        enemy.hp -= damage // 2
                self.shots.append(Shot(pad, (target.x, target.y), defense.color, artwork='egg'))
            else:
                self.shots.append(Shot(pad, (target.x, target.y), defense.color))
            tower.wait = defense.interval

    def remove_defeated(self):
        survivors = []
        for enemy in self.enemies:
            if enemy.hp > 0:
                survivors.append(enemy)
                continue
            self.kills += 1
            self.xp += 3 if ENEMY_KINDS[enemy.kind].boss else 1
            self.drops.append(Drop(enemy.x - 8, enemy.y))
            if self.kills % 2 == 0 or ENEMY_KINDS[enemy.kind].boss:
                self.drops.append(Drop(enemy.x + 8, enemy.y, energy=True))
        self.enemies = survivors

    def update(self, dt, dx, dy):
        if self.phase not in ('combat', 'prepare'):
            return
        self.notice_left = max(0.0, self.notice_left - dt)
        self.melee_wait = max(0.0, self.melee_wait - dt)
        self.melee_flash = max(0.0, self.melee_flash - dt)
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
            self.spawn_wait = SPAWN_INTERVALS[self.wave] * self.rng.uniform(0.85, 1.15)

        self.move_enemies(dt)
        if self.player_hp == 0 or self.base_hp == 0:
            self.phase = 'loss'
            self.loss_reason = ('禮堂耐久已歸零', 'The auditorium fell') if self.base_hp == 0 else (
                '守衛的生命已歸零', 'The defender fell')
            return

        self.attack(dt)
        self.remove_defeated()
        self.collect_drops()

        # The boss arrives only after the regular enemies of the final wave
        # have been cleared, so the wave cannot finish before the boss fight.
        if (self.wave == BOSS_WAVE and self.spawned == len(WAVES[self.wave])
                and not self.enemies and not self.boss_spawned):
            self.spawn_boss()

        if self.xp >= self.next_xp:
            self.phase = 'upgrade'
        elif self.spawned == len(WAVES[self.wave]) and not self.enemies:
            if self.wave == len(WAVES) - 1 and self.boss_spawned:
                self.phase = 'win'
            elif self.wave < len(WAVES) - 1:
                self.phase = 'prepare'
                self.message('可以拾取資源，再決定如何備戰', 'Collect resources, then prepare for the next wave')
