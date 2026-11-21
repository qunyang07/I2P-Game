"""Input handling and game screen drawing."""

from .config import (
    BASE, BG, BLUE, BORDER, BOSS_WAVE, DEFENSES, ENEMY_KINDS,
    FIELD, GOLD, GREEN, MAX_BASE_HP, MUTED, PADS, PANEL,
    FIELD2_START_WAVE, PLAYER_MELEE_FLASH_DURATION, PLAYER_MELEE_RANGE,
    PURPLE, RED, SIDE, TEXT,
    UPGRADES, WAVES,
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

    def word(self, chinese, english):
        return chinese if self.canvas.chinese else english

    def text(self, x, y, value, size=18, color=TEXT, anchor='w'):
        self.canvas.text(x, y, value, size, color, anchor)

    def label(self, x, y, chinese, english, size=18, color=TEXT, anchor='w'):
        self.text(x, y, self.word(chinese, english), size, color, anchor)

    def button(self, x, y, width, height, title, action, accent=BLUE, primary=False, size=16):
        bounds = (x, y, width, height)
        hover = inside(*self.pointer, bounds)
        fill = accent if primary else ('#294355' if hover else '#203345')
        self.canvas.rect(*bounds, fill, outline=accent if hover or primary else BORDER)
        self.text(x + width / 2, y + height / 2, self.word(*title), size,
                  BG if primary else TEXT, 'center')
        self.buttons.append(Button(bounds, action))

    def start(self):
        self.keys.clear()
        self.focus_paused = False
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
        elif phase in ('combat', 'prepare'):
            if key == 'escape':
                self.pause()
            elif phase == 'combat' and key == 'space':
                self.game.manual_attack()
            elif phase == 'prepare':
                if key == 'enter':
                    self.game.advance_wave()
                elif key == 'r':
                    self.game.repair()
                elif key == 'u':
                    self.game.upgrade_tower()
                elif key == 'tab':
                    self.game.selected_pad = (self.game.selected_pad + 1) % len(PADS)
                elif key in ('1', '2', '3', '4', '5'):
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
        if self.game.phase == 'combat':
            left, top, width, height = FIELD
            if left <= x < left + width and top <= y < top + height:
                self.game.manual_attack()
            return
        if self.game.phase == 'prepare':
            for index, (px, py) in enumerate(PADS):
                if distance(x, y, px, py) <= 30:
                    self.game.selected_pad = index
                    return

    def tick(self, dt, movement_keys=None):
        keys = self.keys
        if movement_keys is not None:
            keys = self.keys | set(movement_keys)
        dx = int(bool(keys & {'right', 'd'})) - int(bool(keys & {'left', 'a'}))
        dy = int(bool(keys & {'down', 's'})) - int(bool(keys & {'up', 'w'}))
        self.game.update(min(dt, 0.05), dx, dy)

    def draw_field(self):
        draw = self.canvas
        draw.rect(*FIELD, '#132931', outline='#38535d')
        background = 'field2' if self.game.wave >= FIELD2_START_WAVE else 'field1'
        draw.image(background, FIELD[0] + 1, FIELD[1] + 1)
        draw.circle(*BASE, 108, '#1c373a')
        draw.circle(*BASE, 75, '#203e43', outline='#4b7275', width=2)
        draw.image('auditorium_logo', BASE[0] - 60, BASE[1] - 40)
        self.label(425, 434, '清大大禮堂', 'NTHU AUDITORIUM', 13, '#c8e4e6', 'center')
        for index, (x, y) in enumerate(PADS):
            tower = self.game.towers[index]
            selected = self.game.phase == 'prepare' and index == self.game.selected_pad
            draw.circle(x, y, 26, '#233d45', outline=BLUE if selected else '#54727c', width=2)
            if tower is None:
                self.text(x, y, str(index + 1), 17, BLUE if selected else MUTED, 'center')
            else:
                defense = DEFENSES[tower.kind]
                draw.sprite(defense.artwork, x, y + 22)
                if tower.upgraded:
                    draw.circle(x, y + 17, 3, TEXT)
<<<<<<< HEAD
                if tower.max_hp and (defense.mode == 'wall' or tower.hp < tower.max_hp):
=======
                if defense.mode == 'wall' and tower.max_hp:
>>>>>>> eb3320bcaea2b5f08323efcc69ac7c7417d1d56e
                    self.bar(x - 24, y + 23, 48, 4, tower.hp / tower.max_hp, RED)
                if tower.effect > 0 and defense.mode == 'stun':
                    draw.circle(x, y, 36, None, outline=defense.color, width=2)
                elif tower.effect > 0 and defense.mode == 'trap':
                    draw.circle(x, y, 34, None, outline=defense.color, width=2)

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
            if enemy.stunned:
                draw.circle(x, y, radius + 7, '#4e613c', outline=GOLD, width=2)
            elif enemy.slowed:
                draw.circle(x, y, radius + 4, '#427085', outline=BLUE)
            draw.circle(x, y, radius, '#63323c', outline=kind.color, width=2)
            sprite_top = draw.sprite(kind.artwork, x, y + (24 if kind.boss else 8))
            if enemy.hp < enemy.max_hp and not kind.boss:
                self.bar(x - 13, sprite_top - 5, 26, 3, enemy.hp / enemy.max_hp, RED)
        for shot in game.shots:
            draw.line(shot.origin, shot.target, shot.color, width=2)
            draw.circle(*shot.target, 4, shot.color)
            if shot.artwork:
                draw.sprite(shot.artwork, shot.target[0], shot.target[1] + 8)
<<<<<<< HEAD
        for egg in game.boss_eggs:
            draw.circle(egg.x, egg.y, 12, '#4a375b', outline=PURPLE, width=2)
            draw.sprite('egg', egg.x, egg.y + 10)
=======
>>>>>>> eb3320bcaea2b5f08323efcc69ac7c7417d1d56e
        x, y = game.player_x, game.player_y
        if game.hurt_wait <= 0 or int(game.hurt_wait * 24) % 2 == 0:
            draw.circle(x, y, 15, '#224e68', outline=BLUE, width=2)
            draw.sprite('defender', x, y + 7)
        if game.melee_flash > 0:
            progress = 1 - game.melee_flash / PLAYER_MELEE_FLASH_DURATION
            reach = PLAYER_MELEE_RANGE * (0.58 + 0.42 * progress)
            draw.circle(x, y, reach, None, outline=GOLD, width=4)

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

    def draw_boss_bar(self):
        boss = next((enemy for enemy in self.game.enemies
                     if ENEMY_KINDS[enemy.kind].boss and enemy.hp > 0), None)
        if boss is None:
            return
<<<<<<< HEAD
        x, y, width = FIELD[0] + 90, FIELD[1] + 10, FIELD[2] - 180
        phase = max(1, self.game.boss_phase)
        self.label(x + width / 2, y, f'最終 Boss・階段 {phase}/3',
                   f'FINAL BOSS · PHASE {phase}/3', 11, TEXT, 'center')
        colors = (RED, '#ffb46e', GOLD)
        for index, color in enumerate(colors, start=1):
            if index < phase:
                fraction = 0.0
            elif index == phase:
                fraction = boss.hp / boss.max_hp
            else:
                fraction = 1.0
            bar_y = y + 9 + (index - 1) * 9
            self.canvas.rect(x, bar_y, width, 7, '#08121b', outline=color)
            self.bar(x + 2, bar_y + 2, width - 4, 3, fraction, color)
=======
        x, y, width, height = FIELD[0] + 90, FIELD[1] + 10, FIELD[2] - 180, 14
        self.canvas.rect(x, y, width, height, '#08121b', outline=RED)
        filled = int((width - 4) * max(0.0, boss.hp / boss.max_hp))
        if filled:
            self.canvas.rect(x + 2, y + 2, filled, height - 4, RED)
        self.label(x + width / 2, y + height / 2,
                   '最終 Boss', 'FINAL BOSS', 11, TEXT, 'center')
>>>>>>> eb3320bcaea2b5f08323efcc69ac7c7417d1d56e

    def draw_side(self):
        draw, game = self.canvas, self.game
        draw.rect(*SIDE, PANEL, outline=BORDER)
        self.label(868, 135, '戰況', 'STATUS', 15, MUTED)
        if game.phase == 'prepare' or (game.phase == 'pause' and self.before_pause == 'prepare'):
            self.draw_preparation()
            return
        waiting_boss = int(game.wave == BOSS_WAVE and not game.boss_spawned)
        left = len(WAVES[game.wave]) - game.spawned + len(game.enemies) + waiting_boss
        self.label(868, 172, f'第 {game.wave + 1} 波', f'Wave {game.wave + 1}', 28)
        self.label(868, 218, f'剩餘敵人   {left}', f'Enemies remaining   {left}', 17)
        self.label(868, 253, f'已擊倒   {game.kills}', f'Defeated   {game.kills}', 17)
        draw.line((869, 285), (1112, 285), BORDER)
        self.label(868, 318, f'等級 {game.level}', f'Level {game.level}', 20, GREEN)
        self.text(1111, 319, f'{game.xp} / {game.next_xp} XP', 15, MUTED, 'e')
        self.bar(868, 348, 244, 9, game.xp / game.next_xp, GREEN)
        self.label(868, 399, '自動遠程射擊；近戰需手動', 'Auto ranged; melee is manual', 14, MUTED)
        self.label(868, 430, 'Space / 點擊：圓形範圍近戰', 'Space / click: circular melee', 15, GOLD)
        self.label(868, 478, '方向鍵 / WASD 移動', 'Arrow keys / WASD to move', 15)
        self.label(868, 511, '走近金色、紫色物品撿取', 'Walk over gold / purple drops', 14, MUTED)
        self.label(868, 544, 'Esc 暫停', 'Esc to pause', 15)

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
            y = 251 + index * 43
            cost = defense.cost
            zh, en = defense.name
            self.button(868, y, 246, 30, (f'{index + 1}  {zh}   {cost[0]}零件/{cost[1]}能量',
                                           f'{index + 1}  {en}   {cost[0]}P/{cost[1]}E'),
                        lambda kind=index: game.build(kind), defense.color, size=13)
            self.label(878, y + 32, *defense.description, 12, MUTED)
        self.button(868, 480, 246, 35, ('R  修理禮堂   4 零件', 'R  Repair auditorium   4P'), game.repair, size=13)
        self.button(868, 523, 246, 35, ('U  升級選取設施   5 零件 / 2 能量', 'U  Upgrade selected defense   5P / 2E'),
                    game.upgrade_tower, size=13)
        self.button(868, 585, 246, 43, ('Enter  開始下一波', 'Enter  Start next wave'), game.advance_wave, GREEN, True, size=14)

    def overlay(self, x, y, width, height):
        self.buttons.clear()
        self.canvas.rect(x + 7, y + 8, width, height, '#09121b')
        self.canvas.rect(x, y, width, height, '#172a3a', outline='#52788b', line_width=2)

    def draw_title(self):
        self.overlay(308, 171, 536, 365)
        self.label(576, 195, '國立清華大學', 'NATIONAL TSING HUA UNIVERSITY', 15, BLUE, 'center')
        self.canvas.image('auditorium_title', 456, 204)
        self.label(576, 369, '大禮堂防衛戰', 'Auditorium Defense', 42, TEXT, 'center')
        self.label(576, 413, '收集資源、配置防禦塔，守住五波敵襲。',
                   'Collect resources and protect the base for five waves.', 17, MUTED, 'center')
        self.button(378, 438, 190, 48, ('Enter  開始遊戲', 'Enter  Start'), self.start, BLUE, True)
        self.button(584, 438, 190, 48, ('H  操作說明', 'H  Controls'), self.help)

    def draw_help(self):
        self.overlay(176, 119, 800, 492)
        self.label(210, 162, '新手指引與操作說明', 'New player guide', 27)
        rows = (
            ('方向鍵 / WASD 移動；自動遠程射擊。Space 或點擊才會手動觸發圓形範圍近戰。', 'Move with arrows / WASD. Ranged shots are automatic; Space or click manually triggers circular melee.'),
            ('附近敵人會被自動攻擊；金色是零件，紫色是能量，走近即可拾取。', 'Nearby enemies are attacked automatically. Gold is parts; purple is energy.'),
            ('波次間點擊建造點或按 Tab 選位置，再用 1–5 建造五種設施。', 'Between waves, click a pad or press Tab, then press 1–5 to build.'),
            ('紅綠燈暈眩群敵；圍牆擋路但會被打壞；小湖淹一隻敵人。', 'Traffic light stuns groups; walls block and break; lakes drown one enemy.'),
            ('校狗近攻；奶蛋發射器遠攻並波及附近敵人。R 修禮堂，U 升級設施。', 'Dog attacks nearby; egg launcher fires far and splashes. R repairs; U upgrades.'),
            ('熊耐打近攻；小熊會衝刺；牛來會遠距攻擊。第五波一般敵人清完後出現 Boss。', 'Bear is tough and melee; small bears dash; Niulai attacks at range. The boss follows Wave 5.'),
<<<<<<< HEAD
            ('Boss 共三階段；每條血條耗盡會從不同入口重進。第 2、3 階段有奶蛋環繞，不會造成傷害。', 'Boss has three stages and re-enters from a new entrance after each bar. Eggs orbit in phases 2–3 without dealing damage.'),
=======
>>>>>>> eb3320bcaea2b5f08323efcc69ac7c7417d1d56e
            ('守住禮堂並擊敗 Boss 獲勝；玩家或禮堂生命歸零則失敗。', 'Defeat the boss while keeping both HP bars above zero to win.'),
        )
        for index, row in enumerate(rows):
            self.label(210, 216 + index * 43, *row, 15, MUTED)
        self.button(365, 548, 200, 42, ('Enter  開始遊戲', 'Enter  Start game'), self.start, BLUE, True)
        self.button(587, 548, 200, 42, ('Esc  回標題', 'Esc  Back to title'), self.title)

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
        self.draw_hud()
        self.draw_boss_bar()
        self.draw_side()
        if game.notice_left > 0 and game.phase in ('combat', 'prepare'):
            self.label(23, 690, *game.notice, 16, GOLD)
        elif game.phase in ('combat', 'prepare'):
            self.label(23, 690, '藍圈是守衛；敵人外觀表示種類，金圈表示暈眩。',
                       'Blue ring marks the defender; sprites show enemy types, gold means stunned.', 14, MUTED)
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
