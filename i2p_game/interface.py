"""Input handling and game screen drawing."""

from .config import (
    BASE, BG, BLUE, BORDER, BOSS_KIND, BOSS_PHASE_COUNT, BOSS_WAVE,
    DEFENSES, ENEMY_KINDS, FIELD, GOLD, GREEN, HEIGHT, MAX_BASE_HP, MUTED,
    ALL_PADS, HARD_PAD_COSTS, PADS, PANEL, FIELD2_START_WAVE, PLAYER_MELEE_COOLDOWN,
    PLAYER_MELEE_FLASH_DURATION, PLAYER_MELEE_RANGE, PLAYER_RANGED_INTERVAL,
    PLAYER_RANGED_RANGE,
    PURPLE, RED, SIDE, TEXT, WIDTH,
    UPGRADE_COSTS, UPGRADES,
)
from .models import Button
from .game import Game
from .geometry import distance, inside

class Interface:
    def __init__(self, canvas):
        self.canvas = canvas
        self.game = Game()
        self.game.phase = 'help'
        self.keys = set()
        self.buttons = []
        self.pointer = (-1, -1)
        self.before_pause = 'combat'
        self.drawn_phase = None
        self.focus_paused = False
        self.tutorial_step = None
        self.game_speed = 1.0
        self.game_speeds = (1.0, 1.5, 2.0)
        self.encyclopedia_return_phase = 'title'
        self.encyclopedia_category = 0
        self.encyclopedia_index = 0

    def word(self, chinese, english):
        return chinese if self.canvas.chinese else english

    def text(self, x, y, value, size=18, color=TEXT, anchor='w'):
        self.canvas.text(x, y, value, size, color, anchor)

    def label(self, x, y, chinese, english, size=18, color=TEXT, anchor='w'):
        self.text(x, y, self.word(chinese, english), size, color, anchor)

    def button(self, x, y, width, height, title, action, accent=BLUE, primary=False,
               size=16):
        bounds = (x, y, width, height)
        hover = inside(*self.pointer, bounds)
        fill = accent if primary else ('#294355' if hover else '#203345')
        self.canvas.rect(*bounds, fill, outline=accent if hover or primary else BORDER)
        self.text(x + width / 2, y + height / 2, self.word(*title), size,
                  BG if primary else TEXT, 'center')
        self.buttons.append(Button(bounds, action))

    def speed_button(self, x, y, width, height):
        bounds = (x, y, width, height)
        hover = inside(*self.pointer, bounds)
        fill = '#294355' if hover else '#203345'
        self.canvas.rect(*bounds, fill, outline=BLUE if hover else BORDER)
        self.text(x + width / 2, y + height / 2, f'{self.game_speed:g}×', 14, TEXT, 'center')
        self.text(x + width / 2, y + 36, 'Q', 10, MUTED, 'center')
        self.buttons.append(Button(bounds, self.cycle_game_speed))

    def pause_button(self, x, y, width, height):
        """Draw a pause icon as a square with its middle third removed."""
        bounds = (x, y, width, height)
        hover = inside(*self.pointer, bounds)
        fill = '#294355' if hover else '#203345'
        self.canvas.rect(*bounds, fill, outline=BLUE if hover else BORDER)
        icon_size = 24
        icon_x = x + (width - icon_size) / 2
        icon_y = y + (height - icon_size) / 2
        self.canvas.rect(icon_x, icon_y, icon_size, icon_size, TEXT)
        self.canvas.rect(icon_x + icon_size / 3, icon_y, icon_size / 3, icon_size, fill)
        self.buttons.append(Button(bounds, self.pause))

    def cycle_game_speed(self):
        current = self.game_speeds.index(self.game_speed)
        self.game_speed = self.game_speeds[(current + 1) % len(self.game_speeds)]

    def start(self, difficulty='normal'):
        self.keys.clear()
        self.focus_paused = False
        self.game.reset(difficulty)
        self.tutorial_step = None

    def start_hard(self):
        self.keys.clear()
        self.focus_paused = False
        self.game.reset('hard')
        self.tutorial_step = None

    def start_tutorial(self):
        self.keys.clear()
        self.focus_paused = False
        self.game.begin_tutorial()
        self.tutorial_step = 0

    def advance_tutorial(self):
        """Advance the contextual tutorial after a player action."""
        if not self.game.tutorial_active:
            return
        if self.tutorial_step == 0 and self.game.tutorial_moved:
            self.tutorial_step = 1
            self.game.spawn_tutorial_target()
            self.game.message('靠近熊後施展近戰', 'Approach the bear, then melee')
        elif self.tutorial_step == 1 and self.game.tutorial_hit:
            self.tutorial_step = 2
            self.game.message('走到金色方塊上收集零件', 'Walk over the gold square to collect parts')
        elif self.tutorial_step == 2 and self.game.parts:
            self.game.parts = max(self.game.parts, 2)
            self.game.phase = 'prepare'
            self.tutorial_step = 3
            self.game.message('選擇建造點並建造施工圍牆', 'Select a pad and build a construction wall')
        elif self.tutorial_step == 3 and any(self.game.towers):
            self.tutorial_step = 4
            self.game.message('教學完成！按 Enter 開始第一波', 'Tutorial complete! Press Enter for Wave 1')

    def start_next_wave(self):
        if self.game.tutorial_active:
            if self.tutorial_step != 4:
                self.game.message('請先完成目前的教學步驟', 'Finish the current tutorial step first')
                return
            self.game.tutorial_active = False
            self.tutorial_step = None
        self.game.advance_wave()

    def title(self):
        self.keys.clear()
        self.game.phase = 'title'

    def help(self):
        self.game.phase = 'help'

    def open_encyclopedia(self):
        self.encyclopedia_return_phase = self.game.phase
        self.encyclopedia_category = 0
        self.encyclopedia_index = 0
        self.game.phase = 'encyclopedia'

    def close_encyclopedia(self):
        self.game.phase = self.encyclopedia_return_phase

    def set_encyclopedia_category(self, category):
        self.encyclopedia_category = category
        self.encyclopedia_index = 0

    def move_encyclopedia_selection(self, direction):
        count = len(self.encyclopedia_profiles())
        self.encyclopedia_index = (self.encyclopedia_index + direction) % count

    def pause(self):
        if self.game.phase in ('combat', 'prepare'):
            self.before_pause = self.game.phase
            self.game.phase = 'pause'
            self.focus_paused = False

    def focus_lost(self):
        if self.game.phase in ('combat', 'prepare'):
            self.before_pause = self.game.phase
            self.game.phase = 'pause'
            self.focus_paused = True
        self.keys.clear()

    def resume(self):
        self.game.phase = self.before_pause
        self.focus_paused = False

    def focus_gained(self):
        if self.focus_paused:
            self.resume()

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
        elif phase == 'help':
            if key == 'escape':
                self.title()
            elif key == 'enter':
                self.start()
        elif phase == 'encyclopedia':
            if key == 'escape':
                self.close_encyclopedia()
            elif key == 'left':
                self.move_encyclopedia_selection(-1)
            elif key == 'right':
                self.move_encyclopedia_selection(1)
            elif key in ('1', '2', '3'):
                self.set_encyclopedia_category(int(key) - 1)
        elif phase in ('combat', 'prepare'):
            if key == 'escape':
                self.pause()
            elif key == 'q':
                self.cycle_game_speed()
            elif phase == 'combat' and key == 'space':
                self.game.manual_attack()
            elif phase == 'prepare':
                if key == 'enter':
                    self.start_next_wave()
                elif key == 'r':
                    self.game.repair()
                elif key == 'u':
                    self.game.upgrade_tower()
                elif key == 'tab':
                    count = len(ALL_PADS) if self.game.difficulty == 'hard' else len(PADS)
                    self.game.selected_pad = (self.game.selected_pad + 1) % count
                elif key in ('1', '2', '3', '4', '5'):
                    self.game.build(int(key) - 1)
            self.advance_tutorial()
        elif phase == 'upgrade' and key in ('1', '2', '3'):
            self.game.choose_upgrade(int(key) - 1)
        elif phase == 'pause':
            if key in ('escape', 'enter'):
                self.resume()
            elif key == 'r':
                self.start(self.game.difficulty)
        elif phase in ('win', 'loss'):
            if key in ('r', 'enter'):
                self.start(self.game.difficulty)
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
                self.advance_tutorial()
                return
        if self.game.phase == 'combat':
            left, top, width, height = FIELD
            if left <= x < left + width and top <= y < top + height:
                self.game.manual_attack()
            return
        if self.game.phase == 'prepare':
            pad_list = ALL_PADS if self.game.difficulty == 'hard' else PADS
            for index, (px, py) in enumerate(pad_list):
                if distance(x, y, px, py) <= 30:
                    self.game.selected_pad = index
                    if not self.game.unlocked_pads[index]:
                        self.game.unlock_pad(index)
                    self.advance_tutorial()
                    return

    def tick(self, dt, movement_keys=None):
        keys = self.keys
        if movement_keys is not None:
            keys = self.keys | set(movement_keys)
        dx = int(bool(keys & {'right', 'd'})) - int(bool(keys & {'left', 'a'}))
        dy = int(bool(keys & {'down', 's'})) - int(bool(keys & {'up', 'w'}))
        self.game.update(min(dt, 0.05), dx, dy, time_scale=self.game_speed)
        self.advance_tutorial()

    def draw_field(self):
        draw = self.canvas
        draw.rect(*FIELD, '#132931', outline='#38535d')
        background = 'field2' if self.game.wave >= FIELD2_START_WAVE else 'field1'
        draw.image(background, FIELD[0] + 1, FIELD[1] + 1)
        draw.circle(*BASE, 108, '#1c373a')
        draw.circle(*BASE, 75, '#203e43', outline='#4b7275', width=2)
        draw.image('auditorium_logo', BASE[0] - 60, BASE[1] - 40)
        self.label(425, 434, '清大大禮堂', 'NTHU AUDITORIUM', 13, '#c8e4e6', 'center')
        pad_list = ALL_PADS if self.game.difficulty == 'hard' else PADS
        for index, (x, y) in enumerate(pad_list):
            tower = self.game.towers[index]
            selected = self.game.phase == 'prepare' and index == self.game.selected_pad
            unlocked = self.game.unlocked_pads[index]
            draw.circle(x, y, 26, '#233d45' if unlocked else '#17252b',
                        outline=BLUE if selected else ('#54727c' if unlocked else '#765d39'), width=2)
            if tower is None:
                if unlocked:
                    self.text(x, y, str(index + 1), 17, BLUE if selected else MUTED, 'center')
                elif self.game.difficulty == 'hard':
                    self.text(x, y - 5, str(index + 1), 13, GOLD, 'center')
                    cost = HARD_PAD_COSTS[index - len(PADS)]
                    self.text(x, y + 10, f'{cost[0]}P/{cost[1]}E', 8, MUTED, 'center')
            else:
                defense = DEFENSES[tower.kind]
                draw.sprite(defense.artwork, x, y + 22)
                draw.circle(x + 17, y - 17, 8, '#101d26', outline=TEXT)
                self.text(x + 17, y - 17, str(tower.upgrade_level), 10, TEXT, 'center')
                if tower.locked:
                    draw.circle(x, y, 30, '#141b20', outline=RED, width=3)
                    self.text(x, y, 'X', 21, RED, 'center')
                if defense.mode == 'wall' and tower.max_hp:
                    self.bar(x - 24, y + 23, 48, 4, tower.hp / tower.max_hp, RED)
                if tower.effect > 0 and defense.mode == 'stun':
                    draw.circle(x, y, 36, None, outline=defense.color, width=2)
                elif tower.effect > 0 and defense.mode == 'trap':
                    draw.circle(x, y, 34, None, outline=defense.color, width=2)

    def draw_entities(self):
        draw, game = self.canvas, self.game
        for drop in game.drops:
            x, y = round(drop.x), round(drop.y)
            if drop.energy:
                self.draw_energy_drop(x, y)
            else:
                draw.rect(x - 6, y - 6, 12, 12, '#000000')
                draw.rect(x - 4, y - 4, 8, 8, GOLD)
        for enemy in game.enemies:
            kind = ENEMY_KINDS[enemy.kind]
            x, y, radius = enemy.x, enemy.y, kind.radius
            if enemy.stunned:
                draw.circle(x, y, radius + 7, '#4e613c', outline=GOLD, width=2)
            elif enemy.slowed:
                draw.circle(x, y, radius + 4, '#427085', outline=BLUE)
            draw.circle(x, y, radius, '#63323c', outline=kind.color, width=2)
            sprite_top = draw.sprite(kind.artwork, x, y + (24 if kind.boss else 8))
            if not kind.boss:
                self.bar(x - 17, sprite_top - 6, 34, 4,
                         enemy.hp / enemy.max_hp, RED, border=1)
        for shot in game.shots:
            draw.line(shot.origin, shot.target, shot.color, width=2)
            draw.circle(*shot.target, 4, shot.color)
            if shot.artwork:
                draw.sprite(shot.artwork, shot.target[0], shot.target[1] + 8)
        for projectile in game.projectiles:
            if projectile.artwork:
                draw.sprite(projectile.artwork, projectile.x, projectile.y + 10)
            else:
                draw.circle(projectile.x, projectile.y, projectile.radius,
                            projectile.color, outline='#101820', width=1)
        x, y = game.player_x, game.player_y
        sprite_top = y - 77  # Defender sprite is 84 px tall and drawn with a 7 px foot offset.
        if game.hurt_wait <= 0 or int(game.hurt_wait * 24) % 2 == 0:
            draw.circle(x, y, 15, '#224e68', outline=BLUE, width=2)
            draw.sprite('defender', x, y + 7)
        self.bar(x - 21, sprite_top - 7, 42, 5,
                 game.player_hp / game.max_player_hp, BLUE, border=1)
        if game.melee_flash > 0:
            progress = 1 - game.melee_flash / PLAYER_MELEE_FLASH_DURATION
            reach = PLAYER_MELEE_RANGE * (0.58 + 0.42 * progress)
            draw.circle(x, y, reach, None, outline=GOLD, width=4)

    def cover_outside_field(self):
        """Cover any entity artwork drawn beyond the battlefield rectangle."""
        left, top, width, height = FIELD
        right, bottom = left + width, top + height
        self.canvas.rect(0, 0, WIDTH, top, BG)
        self.canvas.rect(0, bottom, WIDTH, HEIGHT - bottom, BG)
        self.canvas.rect(0, top, left, height, BG)
        self.canvas.rect(right, top, WIDTH - right, height, BG)

    def draw_energy_drop(self, x, y):
        """Draw energy as a purple circle inside a larger black circle."""
        outer_radius = 7
        border_width = 1.5
        self.canvas.circle(x, y, outer_radius, '#000000')
        self.canvas.circle(x, y, outer_radius - border_width, PURPLE)

    def bar(self, x, y, width, height, fraction, color, border=0):
        if border:
            self.canvas.rect(x - border, y - border,
                             width + border * 2, height + border * 2,
                             '#000000')
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
        self.text(783, 65, f'{game.wave + 1} / {len(game.waves)}', 20)
        self.label(836, 39, '零件', 'PARTS', 14, GOLD)
        self.text(836, 65, str(game.parts), 20, GOLD)
        self.label(916, 39, '能量', 'ENERGY', 14, PURPLE)
        self.text(916, 65, str(game.energy), 20, PURPLE)
        if game.phase in ('combat', 'prepare'):
            self.speed_button(990, 29, 68, 42)
            self.pause_button(1070, 29, 42, 42)

    def draw_boss_bar(self):
        boss = next((enemy for enemy in self.game.enemies
                     if ENEMY_KINDS[enemy.kind].boss and enemy.hp > 0), None)
        if boss is None:
            return
        x, y, width, height = FIELD[0] + 90, FIELD[1] + 14, FIELD[2] - 180, 8
        encounter = (f'  第 {self.game.boss_encounters} 場' if self.game.difficulty == 'hard'
                     else '')
        encounter_en = (f'  FIGHT {self.game.boss_encounters}'
                        if self.game.difficulty == 'hard' else '')
        self.label(x + width / 2, FIELD[1] + 5,
                   f'Boss{encounter}  {self.game.boss_phase + 1}/{BOSS_PHASE_COUNT}',
                   f'BOSS{encounter_en}  {self.game.boss_phase + 1}/{BOSS_PHASE_COUNT}',
                   10, TEXT, 'center')
        for row in range(BOSS_PHASE_COUNT):
            bar_y = y + row * 11
            self.canvas.rect(x, bar_y, width, height, '#08121b', outline='#75444a')
            phase = BOSS_PHASE_COUNT - 1 - row
            if phase < self.game.boss_phase:
                fraction = 0.0
            elif phase == self.game.boss_phase:
                fraction = max(0.0, boss.hp / boss.max_hp)
            else:
                fraction = 1.0
            filled = int((width - 4) * fraction)
            if filled:
                self.canvas.rect(x + 2, bar_y + 2, filled, height - 4, RED)

    def draw_side(self):
        draw, game = self.canvas, self.game
        draw.rect(*SIDE, PANEL, outline=BORDER)
        self.label(868, 135, '戰況', 'STATUS', 15, MUTED)
        if game.phase == 'prepare' or (game.phase == 'pause' and self.before_pause == 'prepare'):
            self.draw_preparation()
            return
        waiting_boss = int(
            (game.wave == BOSS_WAVE and game.boss_encounters == 0)
            or (game.difficulty == 'hard' and game.wave == len(game.waves) - 1
                and game.boss_encounters == 1)
        )
        left = len(game.waves[game.wave]) - game.spawned + len(game.enemies) + waiting_boss
        self.label(868, 158, '困難模式' if game.difficulty == 'hard' else '普通模式',
                   'HARD MODE' if game.difficulty == 'hard' else 'NORMAL', 12, GOLD)
        self.label(868, 184, f'第 {game.wave + 1} 波', f'Wave {game.wave + 1}', 26)
        self.label(868, 218, f'剩餘敵人   {left}', f'Enemies remaining   {left}', 17)
        self.label(868, 253, f'已擊倒   {game.kills}', f'Defeated   {game.kills}', 17)
        draw.line((869, 285), (1112, 285), BORDER)
        self.label(868, 318, f'等級 {game.level}', f'Level {game.level}', 20, GREEN)
        percent = min(100, round(100 * game.xp / game.next_xp))
        self.text(1111, 319, f'{percent}%', 15, MUTED, 'e')
        self.bar(868, 348, 244, 9, game.xp / game.next_xp, GREEN)
        self.label(868, 399, '自動遠程射擊；近戰需手動', 'Auto ranged; melee is manual', 14, MUTED)
        self.label(868, 430, 'Space / 點擊：圓形範圍近戰', 'Space / click: circular melee', 15, GOLD)
        self.label(868, 478, '方向鍵 / WASD 移動', 'Arrow keys / WASD to move', 15)
        self.label(868, 511, '走近金色、紫色物品撿取', 'Walk over gold / purple drops', 14, MUTED)
        self.label(868, 544, 'Esc 暫停', 'Esc to pause', 15)

    def draw_preparation(self):
        game = self.game
        heading = ('Boss 戰前備戰', 'Boss preparation') if game.boss_preparation else (
            '波次間備戰', 'Preparation'
        )
        self.label(868, 170, *heading, 27)
        percent = min(100, round(100 * game.xp / game.next_xp))
        self.label(868, 199, f'等級 {game.level}　經驗 {percent}%',
                   f'Level {game.level}　XP {percent}%', 13, GREEN)
        instructions = ('點選建造點；困難模式可花資源解鎖外圍空位',
                        'Click a pad; unlock outer slots in Hard mode')
        self.label(868, 216, *instructions, 11, MUTED)
        tower = game.towers[game.selected_pad]
        pad_status = self.word('空地', 'Empty') if tower is None else self.word(*DEFENSES[tower.kind].name)
        if tower is not None:
            pad_status += f' Lv.{tower.upgrade_level}'
            if tower.locked:
                pad_status += self.word('（已鎖定）', ' (Locked)')
        elif not game.unlocked_pads[game.selected_pad]:
            cost = HARD_PAD_COSTS[game.selected_pad - len(PADS)]
            pad_status = self.word(f'點擊解鎖 {cost[0]}零件/{cost[1]}能量',
                                   f'Click to unlock {cost[0]}P/{cost[1]}E')
        self.label(868, 237, f'建造點 {game.selected_pad + 1}   {pad_status}',
                   f'Pad {game.selected_pad + 1}   {pad_status}', 15, BLUE)
        for index, defense in enumerate(DEFENSES):
            y = 251 + index * 43
            cost = defense.cost
            zh, en = defense.name
            self.button(868, y, 246, 30, (f'{index + 1}  {zh}   {cost[0]}零件/{cost[1]}能量',
                                           f'{index + 1}  {en}   {cost[0]}P/{cost[1]}E'),
                        lambda kind=index: game.build(kind), defense.color, size=13)
            self.label(878, y + 32, *defense.description, 12, MUTED)
        self.button(868, 480, 246, 35, ('R  修理禮堂   4 零件', 'R  Repair auditorium   4P'), game.repair, size=13)
        next_cost = (UPGRADE_COSTS[tower.upgrade_level - 1]
                     if tower is not None and tower.upgrade_level < 3 else None)
        if next_cost:
            upgrade_title = (
                f'U  升級至 Lv.{tower.upgrade_level + 1}   {next_cost[0]}零件/{next_cost[1]}能量',
                f'U  Upgrade to Lv.{tower.upgrade_level + 1}   {next_cost[0]}P/{next_cost[1]}E',
            )
        else:
            upgrade_title = ('U  升級選取設施', 'U  Upgrade selected defense')
        self.button(868, 523, 246, 35, upgrade_title,
                    game.upgrade_tower, size=13)
        start_title = ('Enter  開始 Boss 戰', 'Enter  Start boss fight') if game.boss_preparation else (
            'Enter  開始下一波', 'Enter  Start next wave'
        )
        self.button(868, 585, 246, 43, start_title, self.start_next_wave,
                    GREEN, True, size=14)

    def overlay(self, x, y, width, height):
        self.buttons.clear()
        self.canvas.rect(x + 7, y + 8, width, height, '#09121b')
        self.canvas.rect(x, y, width, height, '#172a3a', outline='#52788b', line_width=2)

    def draw_title(self):
        self.overlay(308, 171, 536, 365)
        self.label(576, 195, '國立清華大學', 'NATIONAL TSING HUA UNIVERSITY', 15, BLUE, 'center')
        self.canvas.image('auditorium_title', 456, 204)
        self.label(576, 369, '大禮堂防衛戰', 'Auditorium Defense', 42, TEXT, 'center')
        self.label(576, 413, '普通模式五波；困難模式八波並迎戰兩次 Boss。',
                   'Normal: 5 waves. Hard: 8 waves and two boss fights.', 16, MUTED, 'center')
        self.button(350, 438, 202, 48, ('Enter  普通模式', 'Enter  Normal'), self.start, BLUE, True)
        self.button(600, 438, 202, 48, ('困難模式', 'Hard mode'), self.start_hard, RED, True)
        self.button(326, 494, 154, 32, ('H  操作說明', 'H  Controls'), self.help, size=12)
        self.button(499, 494, 154, 32, ('手把手教學', 'Guided tutorial'),
                    self.start_tutorial, GREEN, size=12)
        self.button(672, 494, 154, 32, ('圖鑑', 'Encyclopedia'),
                    self.open_encyclopedia, BLUE, size=12)

    def draw_help(self):
        self.overlay(176, 119, 800, 492)
        self.label(210, 162, '新手指引與操作說明', 'New player guide', 27)
        rows = (
            ('方向鍵 / WASD 移動；自動遠程射擊。Space 或點擊才會手動觸發圓形範圍近戰。', 'Move with arrows / WASD. Ranged shots are automatic; Space or click manually triggers circular melee.'),
            ('附近敵人會被自動攻擊；金色是零件，紫色是能量，走近即可拾取。', 'Nearby enemies are attacked automatically. Gold is parts; purple is energy.'),
            ('波次間點擊建造點或按 Tab 選位置，再用 1–5 建造五種設施。', 'Between waves, click a pad or press Tab, then press 1–5 to build.'),
            ('紅綠燈暈眩群敵；圍牆擋路但會被打壞；小湖淹一隻敵人。', 'Traffic light stuns groups; walls block and break; lakes drown one enemy.'),
            ('校狗近攻；奶蛋發射器遠攻並波及附近敵人。R 修禮堂，U 升級設施。', 'Dog attacks nearby; egg launcher fires far and splashes. R repairs; U upgrades.'),
            ('熊耐打近攻；小熊會衝刺；牛來會遠距攻擊。', 'Bear is tough and melee; small bears dash; Niulai attacks at range.'),
            ('奶龍血量中等、移動快，會追擊玩家並造成中高傷害；第二波開始出現。', 'Nailong has medium health, moves fast, and chases the player with hard-hitting attacks. It joins from Wave 2.'),
            ('守住禮堂並擊敗 Boss 獲勝；玩家或禮堂生命歸零則失敗。', 'Defeat the boss while keeping both HP bars above zero to win.'),
        )
        for index, row in enumerate(rows):
            self.label(210, 216 + index * 43, *row, 15, MUTED)
        self.button(252, 548, 200, 42, ('Enter  開始遊戲', 'Enter  Start game'), self.start, BLUE, True)
        self.button(476, 548, 200, 42, ('手把手教學', 'Guided tutorial'), self.start_tutorial, GREEN)
        self.button(700, 548, 200, 42, ('Esc  回標題', 'Esc  Back to title'), self.title)

    @staticmethod
    def relative_range(pixels):
        """Convert engine distance to a relative 0–200 scale in steps of five."""
        return min(200, int((pixels / 2 + 2.5) // 5) * 5)

    def encyclopedia_profiles(self):
        if self.encyclopedia_category == 0:
            damage = self.game.damage
            melee_damage = damage + 16
            return [(
                '守衛', 'Defender', 'defender', (
                    ('生命值', 'Health', f'{self.game.max_player_hp} HP', f'{self.game.max_player_hp} HP'),
                    ('移動速度', 'Move speed', f'{self.game.player_speed} /秒', f'{self.game.player_speed} /s'),
                    ('自動遠程傷害', 'Auto ranged damage', str(damage), str(damage)),
                    ('自動遠程射程', 'Auto ranged range', str(self.relative_range(PLAYER_RANGED_RANGE)),
                     str(self.relative_range(PLAYER_RANGED_RANGE))),
                    ('自動攻擊間隔', 'Auto attack interval', f'{PLAYER_RANGED_INTERVAL:.2f} 秒',
                     f'{PLAYER_RANGED_INTERVAL:.2f} s'),
                    ('索敵模式', 'Targeting', '遠程鎖定最近；近戰命中範圍內全部',
                     'Ranged targets nearest; melee hits all nearby'),
                    ('手動近戰', 'Manual melee',
                     f'{melee_damage} 傷害 / 射程 {self.relative_range(PLAYER_MELEE_RANGE)}',
                     f'{melee_damage} damage / range {self.relative_range(PLAYER_MELEE_RANGE)}'),
                    ('近戰冷卻', 'Melee cooldown', f'{PLAYER_MELEE_COOLDOWN:.2f} 秒',
                     f'{PLAYER_MELEE_COOLDOWN:.2f} s'),
                ),
            )]

        if self.encyclopedia_category == 1:
            profiles = []
            for index, kind in enumerate(ENEMY_KINDS):
                boss = index == BOSS_KIND
                if boss:
                    phase_hp = kind.hp + 120 * BOSS_WAVE
                    health = f'{phase_hp} × {BOSS_PHASE_COUNT} 階'
                    health_en = f'{phase_hp} × {BOSS_PHASE_COUNT} phases'
                    target_zh, target_en = '朝基地前進', 'Advances toward the base'
                    special_zh, special_en = '三階段，左右交替重現', 'Three phases; alternates sides'
                else:
                    health = f'{kind.hp} HP'
                    health_en = f'{kind.hp} HP'
                    if kind.targets_player:
                        target_zh, target_en = '主動追擊玩家', 'Chases the player'
                        special_zh, special_en = '快速近戰追兵', 'Fast melee pursuer'
                    elif kind.ranged:
                        target_zh, target_en = '朝基地前進並在射程外攻擊', 'Approaches and attacks the base from range'
                        special_zh, special_en = '遠程攻擊', 'Ranged attacker'
                    else:
                        target_zh, target_en = '朝基地前進', 'Advances toward the base'
                        if kind.dash_interval:
                            special_zh = f'每 {kind.dash_interval:g} 秒衝刺 {kind.dash_duration:g} 秒'
                            special_en = f'Dashes for {kind.dash_duration:g}s every {kind.dash_interval:g}s'
                        else:
                            special_zh, special_en = '近戰攻擊', 'Melee attacker'

                attack_range = self.relative_range(kind.attack_range) if kind.ranged else None
                range_zh = f'{attack_range} 相對距離' if attack_range is not None else '接觸距離'
                range_en = str(attack_range) if attack_range is not None else 'Contact'
                if kind.targets_player:
                    damage_zh = f'玩家 {kind.player_damage}'
                    damage_en = f'{kind.player_damage} to player'
                else:
                    damage_zh = f'玩家 {kind.player_damage} / 禮堂 {kind.base_damage}'
                    damage_en = f'Player {kind.player_damage} / base {kind.base_damage}'
                profiles.append((kind.name[0], kind.name[1], kind.artwork, (
                    ('生命值', 'Health', health, health_en),
                    ('移動速度', 'Move speed', f'{kind.speed} /秒', f'{kind.speed} /s'),
                    ('攻擊傷害', 'Attack damage', damage_zh, damage_en),
                    ('攻擊射程', 'Attack range', range_zh, range_en),
                    ('攻擊間隔', 'Attack interval', f'{kind.attack_interval:g} 秒',
                     f'{kind.attack_interval:g} s'),
                    ('索敵模式', 'Targeting', target_zh, target_en),
                    ('特性', 'Special', special_zh, special_en),
                    ('波次成長', 'Wave scaling',
                     '速度每波 +8%；一般敵人生命每波 +6，Boss 每階 +120',
                     '+8% speed per wave; +6 regular HP or +120 boss HP per phase per wave'),
                )))
            return profiles

        profiles = []
        for defense in DEFENSES:
            attack_range = self.relative_range(defense.reach) if defense.reach else None
            range_zh = f'{attack_range} 相對距離' if attack_range is not None else '路線阻擋'
            range_en = str(attack_range) if attack_range is not None else 'Blocks a route'
            if defense.mode == 'stun':
                damage_zh, damage_en = '傷害 0；範圍暈眩', '0 damage; area stun'
                targeting_zh, targeting_en = '範圍內所有敵人', 'All enemies in range'
                special_zh = f'暈眩 {defense.stun_duration:g} 秒；Lv.2/3 射程 +10/+20、冷卻 -20%/-35%'
                special_en = f'Stun {defense.stun_duration:g}s; Lv2/3 range +10/+20, cooldown -20%/-35%'
            elif defense.mode == 'wall':
                damage_zh, damage_en = '不造成傷害', 'No damage'
                targeting_zh, targeting_en = '阻擋敵人前進路線', 'Blocks enemy paths'
                special_zh = f'耐久 {defense.durability}；Lv.2 +44，Lv.3 再 +60'
                special_en = f'{defense.durability} durability; Lv2 +44, Lv3 +60'
            elif defense.mode == 'trap':
                damage_zh, damage_en = '一般敵人秒殺；Boss 180/240/320', 'Kills regular enemies; 180/240/320 to boss'
                targeting_zh, targeting_en = '射程內最近敵人', 'Nearest enemy in range'
                special_zh = 'Lv.2/3 射程 +10/+20、冷卻 -20%/-35%'
                special_en = 'Lv2/3 range +10/+20, cooldown -20%/-35%'
            elif defense.mode == 'egg':
                damage_zh = f'{defense.damage}/{defense.damage * 3 // 2}/{defense.damage * 2} 單體'
                damage_en = f'{defense.damage}/{defense.damage * 3 // 2}/{defense.damage * 2} direct'
                targeting_zh, targeting_en = '射程內最近敵人；直線飛行可閃避', 'Nearest in range; projectile can miss'
                splash = self.relative_range(defense.splash_radius)
                special_zh = f'濺射半徑 {splash}；彈速 420/秒；最高等級傷害 ×2、射程 +20'
                special_en = f'Splash {splash}; shot 420/s; Lv3 ×2 damage, +20 range'
            else:
                damage_zh, damage_en = f'{defense.damage}', f'{defense.damage}'
                targeting_zh, targeting_en = '射程內最近敵人', 'Nearest enemy in range'
                special_zh = 'Lv.2 傷害 +50%；Lv.3 傷害 ×2、射程 +40'
                special_en = 'Lv2 +50% damage; Lv3 ×2 damage, +40 range'
            interval_zh = f'{defense.interval:g} 秒' if defense.interval else '—'
            interval_en = f'{defense.interval:g} s' if defense.interval else '—'
            durability_zh = f'{defense.durability} HP' if defense.durability else '—'
            durability_en = f'{defense.durability} HP' if defense.durability else '—'
            cost_zh = f'{defense.cost[0]} 零件 / {defense.cost[1]} 能量'
            cost_en = f'{defense.cost[0]} parts / {defense.cost[1]} energy'
            profiles.append((defense.name[0], defense.name[1], defense.artwork, (
                ('耐久', 'Durability', durability_zh, durability_en),
                ('攻擊射程', 'Attack range', range_zh, range_en),
                ('攻擊傷害', 'Attack damage', damage_zh, damage_en),
                ('攻擊間隔', 'Attack interval', interval_zh, interval_en),
                ('索敵模式', 'Targeting', targeting_zh, targeting_en),
                ('建造花費', 'Build cost', cost_zh, cost_en),
                ('特性 / 升級', 'Special / upgrade', special_zh, special_en),
            )))
        return profiles

    def draw_encyclopedia(self):
        self.overlay(48, 44, 1056, 632)
        self.label(576, 76, '角色與防禦圖鑑', 'Character & Defense Encyclopedia',
                   26, TEXT, 'center')
        category_names = (
            ('主角', 'Hero'), ('敵人', 'Enemies'), ('防禦塔', 'Defenses'),
        )
        for index, title in enumerate(category_names):
            self.button(185 + index * 261, 95, 235, 34, title,
                        lambda category=index: self.set_encyclopedia_category(category),
                        GREEN if index == self.encyclopedia_category else BLUE,
                        index == self.encyclopedia_category, size=14)

        profiles = self.encyclopedia_profiles()
        self.encyclopedia_index %= len(profiles)
        tab_gap = 8
        tab_width = (944 - tab_gap * (len(profiles) - 1)) / len(profiles)
        for index, profile in enumerate(profiles):
            x = 104 + index * (tab_width + tab_gap)
            self.button(x, 140, tab_width, 34, profile[:2],
                        lambda item=index: setattr(self, 'encyclopedia_index', item),
                        BLUE if index == self.encyclopedia_index else BORDER,
                        index == self.encyclopedia_index, size=12)

        name_zh, name_en, artwork, rows = profiles[self.encyclopedia_index]
        portrait_x, portrait_y, portrait_size = 133, 224, 176
        self.canvas.rect(portrait_x - 5, portrait_y - 5,
                         portrait_size + 10, portrait_size + 10,
                         '#203345', outline=BLUE, line_width=2)
        self.canvas.portrait(artwork, portrait_x, portrait_y, portrait_size)
        self.label(portrait_x + portrait_size / 2, 425, name_zh, name_en,
                   22, TEXT, 'center')
        self.label(921, 187, f'{self.encyclopedia_index + 1} / {len(profiles)}',
                   f'{self.encyclopedia_index + 1} / {len(profiles)}', 13, MUTED, 'e')

        stats_x, value_x = 360, 535
        for index, (label_zh, label_en, value_zh, value_en) in enumerate(rows):
            y = 218 + index * 43
            self.label(stats_x, y, label_zh, label_en, 14, BLUE)
            value_size = 12 if index == len(rows) - 1 else 14
            self.label(value_x, y, value_zh, value_en, value_size, TEXT)

        self.label(360, 570,
                   '射程採相對尺度：5 的倍數，最大 200；數值用來比較距離。',
                   'Ranges use a relative scale in steps of 5, capped at 200.',
                   12, MUTED)
        self.button(114, 614, 44, 34, ('‹', '‹'),
                    lambda: self.move_encyclopedia_selection(-1), BLUE, size=18)
        self.button(207, 614, 44, 34, ('›', '›'),
                    lambda: self.move_encyclopedia_selection(1), BLUE, size=18)
        self.label(182, 631, '← / → 切換', '← / → browse', 11, MUTED, 'center')
        self.button(870, 608, 164, 42, ('Esc  返回', 'Esc  Back'),
                    self.close_encyclopedia, GREEN, True, size=14)

    def draw_tutorial_hint(self):
        if not self.game.tutorial_active:
            return
        prompts = (
            ('第 1 步：按方向鍵或 WASD 走一步。', 'Step 1: Press an arrow key or WASD to move.'),
            ('第 2 步：靠近熊，按 Space 或點擊場地施展近戰。', 'Step 2: Approach the bear, then press Space or click to melee.'),
            ('第 3 步：走到金色方塊上收集零件。', 'Step 3: Walk over the gold square to collect parts.'),
            ('第 4 步：選空建造點，按 2 或點選「施工圍牆」。', 'Step 4: Select an empty pad, then press 2 or choose Construction wall.'),
            ('完成！按 Enter 開始正式的第一波。', 'Complete! Press Enter to begin the real first wave.'),
        )
        chinese, english = prompts[self.tutorial_step]
        self.canvas.rect(42, 604, 768, 43, '#183b46', outline=GREEN, line_width=2)
        self.label(426, 625, chinese, english, 16, TEXT, 'center')

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
            self.label(576, 321, '成功擊敗最終 Boss 並守住大禮堂。', 'The final boss is defeated; the auditorium is safe.', 17, MUTED, 'center')
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
        self.cover_outside_field()
        self.draw_hud()
        self.draw_boss_bar()
        self.draw_side()
        self.draw_tutorial_hint()
        if game.notice_left > 0 and game.phase in ('combat', 'prepare'):
            self.label(23, 690, *game.notice, 16, GOLD)
        elif game.phase in ('combat', 'prepare'):
            self.label(23, 690, '藍圈是守衛；敵人外觀表示種類，金圈表示暈眩。',
                       'Blue ring marks the defender; sprites show enemy types, gold means stunned.', 14, MUTED)
        if game.phase == 'title':
            self.draw_title()
        elif game.phase == 'help':
            self.draw_help()
        elif game.phase == 'encyclopedia':
            self.draw_encyclopedia()
        elif game.phase == 'upgrade':
            self.draw_upgrade()
        elif game.phase == 'pause':
            self.overlay(266, 234, 620, 250)
            self.label(576, 280, '已暫停', 'Paused', 34, TEXT, 'center')
            self.button(280, 380, 140, 44, ('繼續', 'Resume'), self.resume, BLUE, True)
            self.button(433, 380, 140, 44, ('重新開始', 'Reset'), self.start)
            self.button(586, 380, 140, 44, ('圖鑑', 'Encyclopedia'),
                        self.open_encyclopedia, GREEN)
            self.button(739, 380, 140, 44, ('回標題', 'Title'), self.title)
        elif game.phase in ('win', 'loss'):
            self.draw_result(game.phase == 'win')
