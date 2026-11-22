"""Wave progression, combat, economy, and upgrade rules."""

import random
from math import hypot

from .config import (
    ALL_PADS, BASE, BASE_RADIUS, BLUE, BOSS_ENTRANCE, BOSS_KIND, BOSS_PHASE_COUNT,
    BOSS_PHASE_SPEED_MULTIPLIERS,
    BOSS_WAVE, DEFENSES, DOG_EFFECT_DURATION, DOG_KNOCKBACK_DISTANCE,
    DOG_KNOCKBACK_EFFECT_DURATION, DROP_ATTRACT_RANGE, DROP_ATTRACT_SPEED,
    DROP_COLLECT_RANGE,
    EGG_PROJECTILE_SPEED, ENEMY_KINDS, ENTRANCES,
    FIELD, HARD_PAD_COSTS, HARD_SPAWN_INTERVALS, HARD_WAVES, MAX_BASE_HP,
    PADS, PLAYER_MELEE_COOLDOWN,
    PLAYER_MELEE_FLASH_DURATION, PLAYER_MELEE_RANGE, PLAYER_RANGED_INTERVAL,
    PLAYER_RANGED_RANGE, REPAIR_COST, REPAIR_HP, SPAWN_INTERVALS,
    STARTING_PLAYER_HP, UPGRADE_COSTS, WAVES,
)
from .geometry import distance
from .models import Drop, Enemy, Projectile, Shot, Tower


class Game:
    def __init__(self):
        self.reset()
        self.phase = 'title'

    def reset(self, difficulty='normal'):
        self.difficulty = difficulty
        self.waves = HARD_WAVES if difficulty == 'hard' else WAVES
        self.spawn_intervals = HARD_SPAWN_INTERVALS if difficulty == 'hard' else SPAWN_INTERVALS
        self.phase = 'combat'
        self.wave = 0
        self.spawned = 0
        self.rng = random.Random()
        self.wave_queue = list(self.waves[self.wave])
        self.rng.shuffle(self.wave_queue)
        self.route_queue = list(ENTRANCES)
        self.rng.shuffle(self.route_queue)
        self.spawn_wait = 0.75
        self.boss_spawned = False
        self.boss_encounters = 0
        self.boss_preparation = False
        self.boss_phase = 0
        self.player_x, self.player_y = 425.0, 467.0
        self.player_hp = self.max_player_hp = STARTING_PLAYER_HP
        self.base_hp = MAX_BASE_HP
        self.player_speed, self.damage = 240, 24
        self.attack_wait = self.hurt_wait = 0.0
        self.melee_wait = self.melee_flash = 0.0
        self.parts = self.energy = self.kills = self.xp = 0
        self.level, self.next_xp = 1, 100
        self.elapsed = 0.0
        self.selected_pad = 0
        self.enemies = []
        self.projectiles = []
        self.drops = []
        self.shots = []
        self.towers = [None] * len(ALL_PADS)
        self.unlocked_pads = [True] * len(PADS) + [difficulty != 'hard'] * len(HARD_PAD_COSTS)
        self.notice = ('', '')
        self.notice_left = 0.0
        self.loss_reason = ('', '')
        self.tutorial_active = False
        self.tutorial_moved = False
        self.tutorial_hit = False

    def begin_tutorial(self):
        """Set up a safe, hands-on practice round before the real game."""
        self.reset()
        self.tutorial_active = True

    def spawn_tutorial_target(self):
        """Place a stationary, low-health target within melee range."""
        if not self.enemies:
            x, y = self.player_x + 54, self.player_y
            self.enemies.append(Enemy(0, x, y, 32, 32))

    def message(self, chinese, english):
        self.notice = chinese, english
        self.notice_left = 2.6

    def advance_wave(self):
        if self.phase != 'prepare':
            return
        self.clear_dog_effects()
        self.projectiles.clear()
        if self.boss_preparation:
            self.boss_preparation = False
            self.phase = 'combat'
            self.notice_left = 0.0
            self.spawn_boss()
            return
        if self.wave + 1 < len(self.waves):
            self.wave += 1
            self.spawned = 0
            self.wave_queue = list(self.waves[self.wave])
            self.rng.shuffle(self.wave_queue)
            self.route_queue = list(ENTRANCES)
            self.rng.shuffle(self.route_queue)
            self.spawn_wait = 0.75
            self.boss_spawned = False
            self.boss_preparation = False
            self.boss_phase = 0
            self.phase = 'combat'
            self.notice_left = 0.0

    def clear_dog_effects(self):
        """Discard bark animation timers when leaving combat."""
        for tower in self.towers:
            if tower is not None and DEFENSES[tower.kind].mode == 'dog':
                tower.effect = 0.0

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
        if not self.unlocked_pads[self.selected_pad]:
            self.unlock_pad(self.selected_pad)
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

    def unlock_pad(self, index):
        if (self.phase != 'prepare' or self.difficulty != 'hard'
                or index < len(PADS) or index >= len(ALL_PADS)):
            return
        if self.unlocked_pads[index]:
            self.message('這個建造點已解鎖', 'This pad is already unlocked')
            return
        cost = HARD_PAD_COSTS[index - len(PADS)]
        if self.spend(cost):
            self.unlocked_pads[index] = True
            self.selected_pad = index
            self.message('額外建造點已解鎖', 'Extra defense slot unlocked')

    def upgrade_tower(self):
        if self.phase != 'prepare':
            return
        tower = self.towers[self.selected_pad]
        if tower is None:
            self.message('請先在這裡建造防禦設施', 'Build a defense on this pad first')
        elif tower.upgrade_level >= 3:
            self.message('這個設施已達最高等級', 'This defense is fully upgraded')
        elif self.spend(UPGRADE_COSTS[tower.upgrade_level - 1]):
            tower.upgrade_level += 1
            if DEFENSES[tower.kind].mode == 'wall':
                tower.max_hp += 44 if tower.upgrade_level == 2 else 60
                tower.hp = tower.max_hp
            self.message('設施效果已提升', 'Defense upgraded')

    def choose_upgrade(self, choice):
        if self.phase != 'upgrade' or choice not in (0, 1, 2):
            return
        self.xp -= self.next_xp
        self.level += 1
        self.next_xp = 100 + (self.level - 1) * 60
        if choice == 0:
            self.damage += 8
        elif choice == 1:
            self.max_player_hp += 25
            self.player_hp += 25
        else:
            self.player_speed += 30
        if self.xp < self.next_xp:
            self.phase = 'prepare' if self.boss_preparation else 'combat'
            self.clear_dog_effects()

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
            if self.tutorial_active:
                self.tutorial_hit = True
        return True

    def move_player(self, dx, dy, dt):
        length = hypot(dx, dy)
        if length:
            if self.tutorial_active:
                self.tutorial_moved = True
            self.player_x += self.player_speed * dx / length * dt
            self.player_y += self.player_speed * dy / length * dt
        left, top, width, height = FIELD
        self.player_x = max(left + 18, min(left + width - 18, self.player_x))
        self.player_y = max(top + 18, min(top + height - 18, self.player_y))

    def collect_drops(self, dt):
        travel = max(DROP_ATTRACT_SPEED, self.player_speed + 120) * dt
        remaining = []
        for drop in self.drops:
            dx, dy = self.player_x - drop.x, self.player_y - drop.y
            gap = hypot(dx, dy)
            if not drop.attracted and gap > DROP_ATTRACT_RANGE:
                remaining.append(drop)
                continue
            if gap <= DROP_COLLECT_RANGE + travel:
                if drop.energy:
                    self.energy += 1
                else:
                    self.parts += 1
            else:
                drop.attracted = True
                drop.x += dx / gap * travel
                drop.y += dy / gap * travel
                remaining.append(drop)
        self.drops = remaining

    def spawn_enemy(self):
        kind_index = self.wave_queue[self.spawned]
        kind = ENEMY_KINDS[kind_index]
        x, y = self.route_queue[self.spawned % len(self.route_queue)]
        hard_hp = 1.35 if self.difficulty == 'hard' else 1.0
        hp = round((kind.hp + 6 * self.wave) * hard_hp)
        self.enemies.append(Enemy(kind_index, x, y, hp, hp, dash_wait=kind.dash_interval))
        self.spawned += 1

    def spawn_boss(self):
        kind = ENEMY_KINDS[BOSS_KIND]
        x, _ = BOSS_ENTRANCE
        top = FIELD[1] + kind.radius
        bottom = FIELD[1] + FIELD[3] - kind.radius
        y = self.rng.uniform(top, bottom)
        hp = kind.hp + 120 * self.wave
        if self.difficulty == 'hard':
            hp = round(hp * (1.35 if self.boss_encounters == 0 else 1.7))
        self.boss_phase = 0
        self.boss_preparation = False
        self.enemies.append(Enemy(BOSS_KIND, x, y, hp, hp))
        self.boss_spawned = True
        self.boss_encounters += 1
        for tower in self.towers:
            if tower:
                tower.locked = False
        encounter = self.boss_encounters
        if self.difficulty == 'hard':
            self.message(f'困難模式第 {encounter} 場 Boss 出現！',
                         f'Hard mode boss encounter {encounter} has arrived!')
        else:
            self.message('最終 Boss 出現！', 'The final boss has arrived!')

    def advance_boss_phase(self):
        """Respawn a defeated boss phase from alternating field edges."""
        locked_count = 0
        for index, enemy in enumerate(self.enemies):
            if enemy.kind != BOSS_KIND or enemy.hp > 0:
                continue
            if self.boss_phase + 1 >= BOSS_PHASE_COUNT:
                for tower in self.towers:
                    if tower:
                        tower.locked = False
                return

            if self.difficulty == 'hard':
                lock_count = 1 if self.boss_phase == 0 else 2
                eligible = [tower for tower in self.towers
                            if tower is not None and not tower.locked]
                self.rng.shuffle(eligible)
                selected = eligible[:lock_count]
                for tower in selected:
                    tower.locked = True
                locked_count = len(selected)

            self.boss_phase += 1
            entrance_index = 1 if self.boss_phase % 2 else 0
            x, _ = ENTRANCES[entrance_index]
            kind = ENEMY_KINDS[BOSS_KIND]
            top = FIELD[1] + kind.radius
            bottom = FIELD[1] + FIELD[3] - kind.radius
            y = self.rng.uniform(top, bottom)
            hp = kind.hp + 120 * self.wave
            if self.difficulty == 'hard':
                hp = round(hp * (1.35 if self.boss_encounters == 1 else 1.7))
            self.enemies[index] = Enemy(BOSS_KIND, x, y, hp, hp)
            phase_number = self.boss_phase + 1
            if self.difficulty == 'hard':
                self.message(
                    f'Boss 第 {phase_number} 條血量！隨機鎖定 {locked_count} 座防禦塔！',
                    f'Boss phase {phase_number}! {locked_count} random defense tower(s) locked!',
                )
            else:
                self.message(
                    f'Boss 第 {phase_number} 條血量！從另一側出現！',
                    f'Boss phase {phase_number}! It has returned from the other side!',
                )
            return

    def wall_on_route(self, enemy, kind, dx, dy, length):
        """Return the first wall intersecting an enemy's straight route to base."""
        squared_length = dx * dx + dy * dy
        if squared_length == 0:
            return None
        nearest = None
        nearest_projection = 1.0
        blocking_radius = kind.radius + 24
        for index, tower in enumerate(self.towers):
            if not self.unlocked_pads[index]:
                continue
            if tower is None or tower.locked or DEFENSES[tower.kind].mode != 'wall':
                continue
            wall_x, wall_y = ALL_PADS[index]
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
        if self.difficulty == 'hard':
            speed *= 1.2
        if kind.boss:
            phase_index = min(self.boss_phase, len(BOSS_PHASE_SPEED_MULTIPLIERS) - 1)
            speed *= BOSS_PHASE_SPEED_MULTIPLIERS[phase_index]
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
            if enemy.stun_duration > 0:
                enemy.stun_elapsed += dt
                if enemy.stun_elapsed >= enemy.stun_duration * 1.15:
                    enemy.stun_duration = 0.0
                    enemy.stun_elapsed = 0.0
            if enemy.stunned > 0:
                enemy.stunned = max(0.0, enemy.stunned - dt)
                continue

            if kind.targets_player:
                dx, dy = self.player_x - enemy.x, self.player_y - enemy.y
                length = hypot(dx, dy)
                attack_distance = kind.radius + 15
                if length > attack_distance:
                    speed = self.enemy_speed(enemy, kind)
                    travel = min(length - attack_distance, speed * dt)
                    enemy.x += dx * travel / length
                    enemy.y += dy * travel / length
                else:
                    enemy.base_wait -= dt
                    if enemy.base_wait <= 0 and self.hurt_wait <= 0:
                        damage = round(kind.player_damage * (1.25 if self.difficulty == 'hard' else 1))
                        self.player_hp = max(0, self.player_hp - damage)
                        self.hurt_wait = 0.62
                        enemy.base_wait = kind.attack_interval * (0.8 if self.difficulty == 'hard' else 1)
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
                            damage = round(kind.base_damage * (1.25 if self.difficulty == 'hard' else 1))
                            tower.hp = max(0, tower.hp - damage)
                            enemy.wall_wait = max(0.45, kind.attack_interval * (0.8 if self.difficulty == 'hard' else 1))
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
                    enemy.base_wait = kind.attack_interval * (0.8 if self.difficulty == 'hard' else 1)
                    if kind.ranged:
                        dx, dy = BASE[0] - enemy.x, BASE[1] - enemy.y
                        length = max(1.0, hypot(dx, dy))
                        self.projectiles.append(Projectile(
                            enemy.x, enemy.y, dx / length * 350, dy / length * 350,
                            round(kind.base_damage * (1.25 if self.difficulty == 'hard' else 1)),
                            0, 0, radius=7, artwork=None, target_type='base', color=kind.color,
                        ))
                    else:
                        damage = round(kind.base_damage * (1.25 if self.difficulty == 'hard' else 1))
                        self.base_hp = max(0, self.base_hp - damage)

            if (enemy.stunned <= 0 and self.hurt_wait <= 0
                    and distance(enemy.x, enemy.y, self.player_x, self.player_y) < kind.radius + 13):
                damage = round(kind.player_damage * (1.25 if self.difficulty == 'hard' else 1))
                self.player_hp = max(0, self.player_hp - damage)
                self.hurt_wait = 0.62

    def nearest_target_at(self, x, y, reach, include_enemy_radius=False):
        """Return the living in-range enemy closest to the firing point."""
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
            target = self.nearest_target_at(
                self.player_x, self.player_y, PLAYER_RANGED_RANGE,
                include_enemy_radius=True,
            )
            if target is not None:
                dx, dy = target.x - self.player_x, target.y - self.player_y
                length = max(1.0, hypot(dx, dy))
                self.projectiles.append(Projectile(
                    self.player_x, self.player_y, dx / length * 600, dy / length * 600,
                    self.damage, 0, 0, radius=7, artwork=None,
                    target_type='enemies', color=BLUE,
                ))
                self.attack_wait = PLAYER_RANGED_INTERVAL

        for index, (pad, tower) in enumerate(zip(ALL_PADS, self.towers)):
            if tower is None or tower.locked or not self.unlocked_pads[index]:
                continue
            defense = DEFENSES[tower.kind]
            tower.wait = max(0.0, tower.wait - dt)
            tower.effect = max(0.0, tower.effect - dt)

            if defense.mode == 'wall' or tower.wait > 0:
                continue

            level = tower.upgrade_level
            reach = defense.reach + (22 if level >= 2 else 0) + (18 if level >= 3 else 0)
            if defense.mode == 'dog':
                targets = [
                    enemy for enemy in self.enemies
                    if enemy.hp > 0
                    and distance(*pad, enemy.x, enemy.y)
                    <= reach + ENEMY_KINDS[enemy.kind].radius
                ]
                if not targets:
                    continue

                damage = (defense.damage * 2 if level >= 3 else
                          defense.damage * 3 // 2 if level == 2 else defense.damage)
                knockback = DOG_KNOCKBACK_DISTANCE + (6 if level >= 2 else 0) + (6 if level >= 3 else 0)
                for enemy in targets:
                    enemy.hp -= damage
                    enemy.knockback_effect = DOG_KNOCKBACK_EFFECT_DURATION
                    enemy_knockback = (knockback * 0.5
                                       if ENEMY_KINDS[enemy.kind].boss else knockback)
                    dx, dy = enemy.x - pad[0], enemy.y - pad[1]
                    length = hypot(dx, dy)
                    if length < 1:
                        dx, dy = enemy.x - BASE[0], enemy.y - BASE[1]
                        length = hypot(dx, dy)
                    if length < 1:
                        dx, dy, length = 0, -1, 1
                    enemy_radius = ENEMY_KINDS[enemy.kind].radius
                    min_x, max_x = FIELD[0] + enemy_radius, FIELD[0] + FIELD[2] - enemy_radius
                    min_y, max_y = FIELD[1] + enemy_radius, FIELD[1] + FIELD[3] - enemy_radius
                    enemy.x = min(max_x, max(min_x, enemy.x + dx / length * enemy_knockback))
                    enemy.y = min(max_y, max(min_y, enemy.y + dy / length * enemy_knockback))

                tower.wait = defense.interval * (0.8 if level == 2 else 0.65 if level >= 3 else 1)
                tower.wait_total = tower.wait
                tower.effect = DOG_EFFECT_DURATION
                continue

            if defense.mode == 'stun':
                targets = [
                    enemy for enemy in self.enemies
                    if enemy.hp > 0 and distance(*pad, enemy.x, enemy.y) <= reach
                ]
                if not targets:
                    continue
                duration = defense.stun_duration + (0.7 if level >= 2 else 0) + (0.8 if level >= 3 else 0)
                for enemy in targets:
                    if duration >= enemy.stunned:
                        enemy.stunned = duration
                        enemy.stun_duration = duration
                        enemy.stun_elapsed = 0.0
                tower.wait = defense.interval * (0.8 if level == 2 else 0.65 if level >= 3 else 1)
                tower.wait_total = tower.wait
                for enemy in targets:
                    if not any(target is enemy for target in tower.stun_targets):
                        tower.stun_targets.append(enemy)
                tower.effect = max(
                    (enemy.stunned for enemy in tower.stun_targets), default=0.0
                )
                continue

            target = self.nearest_target_at(*pad, reach)
            if target is None:
                continue

            if defense.mode == 'egg':
                dx, dy = target.x - pad[0], target.y - pad[1]
                length = hypot(dx, dy)
                if length:
                    vx = dx / length * EGG_PROJECTILE_SPEED
                    vy = dy / length * EGG_PROJECTILE_SPEED
                else:
                    vx = vy = 0.0
                damage = (defense.damage * 2 if level >= 3 else
                          defense.damage * 3 // 2 if level == 2 else defense.damage)
                splash = defense.splash_radius + (12 if level >= 2 else 0) + (10 if level >= 3 else 0)
                self.projectiles.append(Projectile(
                    pad[0], pad[1], vx, vy, damage, damage // 2, splash,
                ))
                tower.wait = defense.interval * (0.8 if level == 2 else 0.65 if level >= 3 else 1)
                tower.wait_total = tower.wait
                continue

            if defense.mode == 'trap':
                if ENEMY_KINDS[target.kind].boss:
                    target.hp -= 180 if level == 1 else 240 if level == 2 else 320
                else:
                    target.hp = 0
                tower.wait = defense.interval * (0.8 if level == 2 else 0.65 if level >= 3 else 1)
                tower.wait_total = tower.wait
                tower.effect = 0.5
                self.shots.append(Shot(pad, (target.x, target.y), defense.color))
                continue

            damage = (defense.damage * 2 if level >= 3 else
                      defense.damage * 3 // 2 if level == 2 else defense.damage)
            target.hp -= damage
            self.shots.append(Shot(pad, (target.x, target.y), defense.color))
            tower.wait = defense.interval * (0.8 if level == 2 else 0.65 if level >= 3 else 1)
            tower.wait_total = tower.wait

    def update_projectiles(self, dt):
        """Move straight shots and apply damage only when their path collides."""
        remaining = []
        for projectile in self.projectiles:
            start_x, start_y = projectile.x, projectile.y
            end_x = start_x + projectile.vx * dt
            end_y = start_y + projectile.vy * dt
            dx, dy = end_x - start_x, end_y - start_y
            segment_length_squared = dx * dx + dy * dy
            def segment_hit(cx, cy, radius):
                if segment_length_squared:
                    t = max(0.0, min(1.0, ((cx - start_x) * dx + (cy - start_y) * dy)
                                          / segment_length_squared))
                else:
                    t = 0.0
                px, py = start_x + t * dx, start_y + t * dy
                return t, distance(px, py, cx, cy) <= radius + projectile.radius

            if projectile.target_type == 'base':
                base_t, base_hit = segment_hit(*BASE, BASE_RADIUS)
                first_wall = None
                first_wall_t = 2.0
                for index, tower in enumerate(self.towers):
                    if (tower is None or tower.locked or not self.unlocked_pads[index]
                            or DEFENSES[tower.kind].mode != 'wall'):
                        continue
                    wall_x, wall_y = ALL_PADS[index]
                    wall_t, wall_hit = segment_hit(wall_x, wall_y, 24)
                    if wall_hit and wall_t < first_wall_t:
                        first_wall, first_wall_t = index, wall_t
                if first_wall is not None and (not base_hit or first_wall_t < base_t):
                    wall = self.towers[first_wall]
                    wall.hp = max(0, wall.hp - projectile.damage)
                    if wall.hp == 0:
                        self.towers[first_wall] = None
                    continue
                if base_hit:
                    self.base_hp = max(0, self.base_hp - projectile.damage)
                    continue
            elif projectile.target_type == 'player':
                t, hit = segment_hit(self.player_x, self.player_y, 16)
                if hit:
                    if self.hurt_wait <= 0:
                        self.player_hp = max(0, self.player_hp - projectile.damage)
                        self.hurt_wait = 0.62
                    continue
            else:
                first_hit = None
                first_hit_t = 2.0
                for enemy in self.enemies:
                    if enemy.hp <= 0:
                        continue
                    t, hit = segment_hit(enemy.x, enemy.y, ENEMY_KINDS[enemy.kind].radius)
                    if hit and t < first_hit_t:
                        first_hit, first_hit_t = enemy, t
                if first_hit is not None:
                    impact_x, impact_y = start_x + first_hit_t * dx, start_y + first_hit_t * dy
                    first_hit.hp -= projectile.damage
                    if projectile.splash_radius:
                        for enemy in self.enemies:
                            if enemy is not first_hit and enemy.hp > 0 and distance(
                                enemy.x, enemy.y, impact_x, impact_y
                            ) <= projectile.splash_radius:
                                enemy.hp -= projectile.splash_damage
                    continue

            projectile.x, projectile.y = end_x, end_y
            field_left, field_top, field_width, field_height = FIELD
            if (field_left + projectile.radius <= end_x <= field_left + field_width - projectile.radius
                    and field_top + projectile.radius <= end_y <= field_top + field_height - projectile.radius):
                remaining.append(projectile)

        self.projectiles = remaining

    def remove_defeated(self):
        survivors = []
        for enemy in self.enemies:
            if enemy.hp > 0:
                survivors.append(enemy)
                continue
            self.kills += 1
            xp_gain = ENEMY_KINDS[enemy.kind].xp_reward
            if self.difficulty == 'hard':
                xp_gain = round(xp_gain * 1.5)
            self.xp += xp_gain
            if self.difficulty == 'hard':
                self.drops.extend((Drop(enemy.x - 9, enemy.y), Drop(enemy.x + 9, enemy.y)))
                self.drops.append(Drop(enemy.x, enemy.y - 9, energy=True))
            else:
                self.drops.append(Drop(enemy.x - 8, enemy.y))
            if self.difficulty != 'hard' and (self.kills % 2 == 0 or ENEMY_KINDS[enemy.kind].boss):
                self.drops.append(Drop(enemy.x + 8, enemy.y, energy=True))
        self.enemies = survivors
        living_stunned = {id(enemy) for enemy in survivors if enemy.stunned > 0}
        for tower in self.towers:
            if tower is None or DEFENSES[tower.kind].mode != 'stun':
                continue
            tower.stun_targets = [
                enemy for enemy in tower.stun_targets
                if id(enemy) in living_stunned
            ]
            tower.effect = max(
                (enemy.stunned for enemy in tower.stun_targets), default=0.0
            )

    def update(self, dt, dx, dy, time_scale=1.0):
        """Advance all movement, attacks, and cooldowns on scaled game time."""
        dt *= time_scale
        if self.phase not in ('combat', 'prepare'):
            return
        for enemy in self.enemies:
            enemy.knockback_effect = max(0.0, enemy.knockback_effect - dt)
        self.notice_left = max(0.0, self.notice_left - dt)
        self.melee_wait = max(0.0, self.melee_wait - dt)
        self.melee_flash = max(0.0, self.melee_flash - dt)
        self.move_player(dx, dy, dt)
        for shot in self.shots:
            shot.remaining -= dt
        self.shots = [shot for shot in self.shots if shot.remaining > 0]
        if self.tutorial_active:
            if self.phase == 'combat':
                self.remove_defeated()
            self.collect_drops(dt)
            return
        if self.phase == 'prepare':
            self.collect_drops(dt)
            self.update_projectiles(dt)
            return

        self.elapsed += dt
        self.hurt_wait = max(0.0, self.hurt_wait - dt)
        self.spawn_wait -= dt
        if self.spawn_wait <= 0 and self.spawned < len(self.waves[self.wave]):
            self.spawn_enemy()
            interval = self.spawn_intervals[self.wave]
            self.spawn_wait = interval * self.rng.uniform(0.85, 1.15)

        self.move_enemies(dt)
        if self.player_hp == 0 or self.base_hp == 0:
            self.phase = 'loss'
            self.loss_reason = ('禮堂耐久已歸零', 'The auditorium fell') if self.base_hp == 0 else (
                '守衛的生命已歸零', 'The defender fell')
            return

        self.attack(dt)
        self.update_projectiles(dt)
        self.advance_boss_phase()
        self.remove_defeated()
        self.collect_drops(dt)

        # Pause after boss-gate waves so the player can prepare for the boss.
        boss_due = (
            (self.wave == BOSS_WAVE and self.boss_encounters == 0)
            or (self.difficulty == 'hard' and self.wave == len(self.waves) - 1
                and self.boss_encounters == 1)
        )
        if (boss_due and self.spawned == len(self.waves[self.wave])
                and not self.enemies and not self.boss_preparation):
            self.boss_preparation = True
            self.phase = 'prepare'
            self.message(f'第 {self.wave + 1} 波敵人已清除，可建塔或升級後再迎戰 Boss',
                         f'Wave {self.wave + 1} cleared. Prepare for the boss.')

        if self.xp >= self.next_xp:
            self.phase = 'upgrade'
        elif self.boss_preparation:
            self.phase = 'prepare'
        elif self.spawned == len(self.waves[self.wave]) and not self.enemies:
            if (self.wave == len(self.waves) - 1 and self.boss_spawned
                    and (self.difficulty != 'hard' or self.boss_encounters >= 2)):
                self.phase = 'win'
            elif self.wave < len(self.waves) - 1:
                self.phase = 'prepare'
                self.message('可以拾取資源，再決定如何備戰', 'Collect resources, then prepare for the next wave')

        if self.phase == 'prepare':
            self.clear_dog_effects()
