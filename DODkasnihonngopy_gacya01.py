import os
import math
import random
import pyxel


# ============================================================
# DEMOCRACY OF THE DEAD
# ULTIMATE GRAPHICS EDITION (BDF Font Integrated)
# ============================================================

WINDOW_W = 160
WINDOW_H = 120

UI_HEIGHT = 26

PLAYER_SPEED = 1.7
PLAYER_R = 5
ZOMBIE_R = 4

SANCTUARY_W = 18

MAX_STAGE_PLAY = 5
FINAL_STAGE = MAX_STAGE_PLAY + 1

ZOMBIE_COUNT_BASE = 6
FINAL_STAGE_ZOMBIES = 30

BASE_TIME_LIMIT = 18.0
BONUS_TIME_AFTER_CLEAR = 5.0
FINAL_STAGE_TIME_LIMIT_MIN = 4.5

TRANSFORM_DURATION = 240
GAMEOVER_HOLD_TIME = 150

FOLLOW_DISTANCE = 12
TRAIL_MAX_LENGTH = 200

CREDITS_SPEED = 0.42

# ------------------------------------------------------------
# タイトル画像設定
# ------------------------------------------------------------

TITLE_IMAGE = "dodtaitle.png"

TITLE_IMG_W = 70
TITLE_IMG_H = 83

TITLE_FRAME_W = TITLE_IMG_W
TITLE_FRAME_H = TITLE_IMG_H

TITLE_FRAME_X = (WINDOW_W - TITLE_FRAME_W) // 2
TITLE_FRAME_Y = 7

TITLE_IMG_X = TITLE_FRAME_X
TITLE_IMG_Y = TITLE_FRAME_Y


# ------------------------------------------------------------
# GAMEPAD (ASCII Controller Fixed Mapping)
# ------------------------------------------------------------

GAMEPAD_DPAD_UP = pyxel.GAMEPAD1_BUTTON_DPAD_UP
GAMEPAD_DPAD_DOWN = pyxel.GAMEPAD1_BUTTON_DPAD_DOWN
GAMEPAD_DPAD_LEFT = pyxel.GAMEPAD1_BUTTON_DPAD_LEFT
GAMEPAD_DPAD_RIGHT = pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT

# AボタンとCボタンのマッピングをスワップ
GAMEPAD_A_ID = pyxel.GAMEPAD1_BUTTON_B  
GAMEPAD_C_ID = pyxel.GAMEPAD1_BUTTON_A  
GAMEPAD_START_ID = pyxel.GAMEPAD1_BUTTON_START


# ============================================================
# BDF FONT PARSER
# ============================================================

class BDFParser:
    def __init__(self, filename):
        self.fonts = {}
        self.widths = {}
        self._load(filename)

    def _load(self, filename):
        if not os.path.exists(filename):
            return
        try:
            with open(filename, "r", encoding="utf-8", errors="ignore") as f:
                current_encoding = None
                current_dwidth = 12
                bitmap_mode = False
                bitmap_lines = []
                for line in f:
                    line = line.strip()
                    if line.startswith("ENCODING"):
                        current_encoding = int(line.split()[1])
                    elif line.startswith("DWIDTH"):
                        parts = line.split()
                        if len(parts) > 1:
                            current_dwidth = int(parts[1])
                    elif line == "BITMAP":
                        bitmap_mode = True
                        bitmap_lines = []
                    elif line == "ENDCHAR":
                        if current_encoding is not None and current_encoding != -1:
                            self.fonts[current_encoding] = bitmap_lines
                            self.widths[current_encoding] = current_dwidth
                        bitmap_mode = False
                        current_encoding = None
                        current_dwidth = 12
                    elif bitmap_mode:
                        bitmap_lines.append(line)
        except Exception:
            pass

    def draw_text(self, x, y, text, col):
        cx = x
        for char in text:
            code = ord(char)
            if code in self.fonts:
                bitmap = self.fonts[code]
                for row_idx, row_hex in enumerate(bitmap):
                    if not row_hex:
                        continue
                    val = int(row_hex, 16)
                    bit_len = len(row_hex) * 4
                    for col_idx in range(bit_len):
                        if val & (1 << (bit_len - 1 - col_idx)):
                            pyxel.pset(cx + col_idx, y + row_idx, col)
                cx += self.widths.get(code, 12)
            else:
                cx += 6


# ============================================================
# UTILITIES
# ============================================================

def clamp(v, a, b):
    return max(a, min(b, v))


def dist(ax, ay, bx, by):
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def safe_play(channel, sound_id, loop=False):
    try:
        pyxel.play(channel, sound_id, loop=loop)
    except Exception:
        pass


# ============================================================
# PARTICLE & EFFECTS
# ============================================================

class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=1, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1

    def draw(self):
        if self.life <= 0:
            return
        ratio = self.life / max(1, self.max_life)
        c = self.color if ratio > 0.66 else (7 if ratio > 0.33 else 1)
        x = int(self.x)
        y = int(self.y)
        if self.size <= 1:
            pyxel.pset(x, y, c)
        else:
            pyxel.rect(x - self.size // 2, y - self.size // 2, self.size, self.size, c)

class Shockwave:
    def __init__(self, x, y, color=8):
        self.x = x
        self.y = y
        self.radius = 1.0
        self.life = 25
        self.max_life = 25
        self.color = color

    def update(self):
        self.radius += 0.8
        self.life -= 1

    def draw(self):
        if self.life > 0:
            pyxel.circb(int(self.x), int(self.y), int(self.radius), self.color)

class Shake:
    def __init__(self):
        self.timer = 0
        self.intensity = 0

    def start(self, frames=10, intensity=2):
        self.timer = max(self.timer, frames)
        self.intensity = max(self.intensity, intensity)

    def update(self):
        if self.timer > 0:
            self.timer -= 1
        if self.timer == 0:
            self.intensity = 0

    def get_offset(self):
        if self.timer <= 0:
            return 0, 0
        return (random.randint(-self.intensity, self.intensity), random.randint(-self.intensity, self.intensity))

class Fade:
    def __init__(self):
        self.alpha = 0.0
        self.target = 0.0
        self.speed = 0.05
        self.active = False

    def to(self, target, speed=0.05):
        self.target = clamp(target, 0.0, 1.0)
        self.speed = speed
        self.active = True

    def update(self):
        if not self.active:
            return
        if self.alpha < self.target:
            self.alpha = min(self.target, self.alpha + self.speed)
        elif self.alpha > self.target:
            self.alpha = max(self.target, self.alpha - self.speed)
        if self.alpha == self.target:
            self.active = False

    def draw(self):
        if self.alpha <= 0:
            return
        count = int(self.alpha * 7)
        for _ in range(count):
            pyxel.rect(0, 0, WINDOW_W, WINDOW_H, 0)


# ============================================================
# PLAYER
# ============================================================

class Player:
    def __init__(self, x, y, is_main=True, color_override=None, char_type="heroine"):
        self.x = x
        self.y = y
        self.dir = 1
        self.walk_frame = 0
        self.color = color_override if color_override is not None else 11
        self.is_main = is_main
        self.is_zombified = False
        self.temp_color = None
        self.dust_particles = []
        self.transform_particles = []
        self.trail = []
        self.char_type = char_type

        if is_main:
            self.trail = [(x, y) for _ in range(TRAIL_MAX_LENGTH)]

    def update(self, obstacles, controllable=True):
        for p in self.transform_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[3] += 0.05
            p[5] -= 1
        self.transform_particles = [p for p in self.transform_particles if p[5] > 0]

        if not self.is_main:
            return

        dx, dy = 0, 0

        if controllable and not self.is_zombified:
            if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(GAMEPAD_DPAD_LEFT):
                dx = -PLAYER_SPEED
            elif pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(GAMEPAD_DPAD_RIGHT):
                dx = PLAYER_SPEED
            if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(GAMEPAD_DPAD_UP):
                dy = -PLAYER_SPEED
            elif pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(GAMEPAD_DPAD_DOWN):
                dy = PLAYER_SPEED

        if dx != 0 or dy != 0:
            if dx != 0 and dy != 0:
                f = 1 / math.sqrt(2)
                dx *= f
                dy *= f
            self.walk_frame = (self.walk_frame + 1) % 16
            self.x += dx
            self.y += dy
            if dx > 0: self.dir = 1
            elif dx < 0: self.dir = -1

            if pyxel.frame_count % 2 == 0:
                self.dust_particles.append(
                    [self.x + random.uniform(-2, 2), self.y + random.uniform(2, 4),
                     random.uniform(-0.6, 0.6), random.uniform(-0.6, -0.1),
                     random.choice([5, 6, 13]), 12]
                )

        self.x = clamp(self.x, PLAYER_R, WINDOW_W - SANCTUARY_W - PLAYER_R)
        self.y = clamp(self.y, UI_HEIGHT + PLAYER_R, WINDOW_H - PLAYER_R)

        if self.is_main and not self.is_zombified:
            self.trail.insert(0, (self.x, self.y))
            self.trail = self.trail[:TRAIL_MAX_LENGTH]

        for p in self.dust_particles:
            p[0] += p[2]
            p[1] += p[3]
            p[5] -= 1
        self.dust_particles = [p for p in self.dust_particles if p[5] > 0]

    def spawn_transform_particle(self, color):
        for _ in range(random.randint(2, 5)):
            self.transform_particles.append(
                [self.x + random.uniform(-7, 7), self.y + random.uniform(-10, 5),
                 random.uniform(-2.0, 2.0), random.uniform(-3.5, -1.0),
                 color, random.randint(20, 50)]
            )

    def draw(self):
        x = int(self.x)
        y = int(self.y)

        for p in self.dust_particles:
            pyxel.pset(int(p[0]), int(p[1]), p[4])

        for p in self.transform_particles:
            pyxel.rect(int(p[0]), int(p[1]), 2, 2, p[4])

        pyxel.circ(x, y + 5, 5, 0)
        pyxel.rect(x - 4, y + 4, 9, 2, 1)

        if self.is_zombified:
            pyxel.circ(x, y - 3, 5, 3)
            pyxel.rect(x - 5, y + 1, 10, 7, 3)
            pyxel.rect(x - 4, y + 2, 8, 5, 4)
            pyxel.pset(x - 2, y - 4, 8)
            pyxel.pset(x + 2, y - 4, 8)
            pyxel.line(x - 2, y - 1, x + 2, y - 1, 0)
            pyxel.line(x - 1, y, x + 1, y, 0)
            return

        c = self.temp_color if self.temp_color is not None else self.color
        foot = [0, 1, -1, 0][(self.walk_frame // 4) % 4]

        pyxel.rect(x - 4, y + 3 + foot, 3, 4, c)
        pyxel.rect(x + 1, y + 3 - foot, 3, 4, c)
        pyxel.rect(x - 5, y - 3, 10, 8, c)
        pyxel.rect(x - 4, y - 2, 8, 6, 7)
        pyxel.line(x - 3, y - 2, x + 2, y - 2, 13)

        arm_y = y - 1
        pyxel.line(x - 5, arm_y, x - 7, arm_y + 3, c)
        pyxel.line(x + 5, arm_y, x + 7, arm_y + 3, c)

        pyxel.circ(x, y - 7, 4, 6)
        pyxel.circ(x, y - 7, 3, 7)

        if self.char_type in ["heroine", "girl"]:
            hair_col = 5 if self.char_type == "heroine" else 4
            pyxel.rect(x - 4, y - 11, 9, 3, hair_col)
            pyxel.rect(x - 4, y - 8, 2, 5, hair_col)
            pyxel.rect(x + 3, y - 8, 2, 5, hair_col)
            pyxel.pset(x - 2, y - 7, 0)
            pyxel.pset(x + 1, y - 7, 0)
            if self.dir == -1:
                pyxel.pset(x - 3, y - 7, 0)
            elif self.dir == 1:
                pyxel.pset(x + 2, y - 7, 0)
        else:
            hair_col = 0
            pyxel.rect(x - 3, y - 11, 7, 2, hair_col)
            pyxel.pset(x - 3 * self.dir, y - 9, hair_col)
            pyxel.pset(x + self.dir * 2, y - 7, 0)


# ============================================================
# ZOMBIE
# ============================================================

class Zombie:
    def __init__(self, x, y, speed_factor=1.0, global_speed_multiplier=1.0):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-0.4, 0.4)
        self.dir = 1
        self.state = "wander"
        self.speed_factor = speed_factor * global_speed_multiplier
        self.base_color = random.choice([3, 4, 11])
        self.captured_particles = []
        self.attack_anim = random.random() * 10

    def update(self, player, obstacles, captured_zombies):
        self.attack_anim += 0.12
        px, py = player.x, player.y
        d = dist(self.x, self.y, px, py)

        if self.state == "captured":
            try:
                index = captured_zombies.index(self)
            except ValueError:
                index = 0

            target_index = min(len(player.trail) - 1, (index + 1) * FOLLOW_DISTANCE)
            tx, ty = player.trail[target_index]
            td = dist(self.x, self.y, tx, ty)
            sp = 1.0 * self.speed_factor

            if td > 1:
                self.vx = ((tx - self.x) / td) * sp
                self.vy = ((ty - self.y) / td) * sp
            else:
                self.vx, self.vy = 0, 0

            self.x += self.vx
            self.y += self.vy

            if self.vx > 0: self.dir = 1
            elif self.vx < 0: self.dir = -1

            self.x = clamp(self.x, ZOMBIE_R, WINDOW_W - 1 - ZOMBIE_R)
            self.y = clamp(self.y, UI_HEIGHT + ZOMBIE_R, WINDOW_H - 1 - ZOMBIE_R)

            for p in self.captured_particles:
                p[0] += p[2]
                p[1] += p[3]
                p[5] -= 1
            self.captured_particles = [p for p in self.captured_particles if p[5] > 0]
            return

        if d < PLAYER_R + ZOMBIE_R and not player.is_zombified:
            self.state = "captured"
            self.vx, self.vy = 0, 0
            safe_play(3, 8)
            return

        if not player.is_zombified:
            if d < 48:
                self.state = "follow"
                if d > 0:
                    self.vx += ((px - self.x) / d) * 0.10
                    self.vy += ((py - self.y) / d) * 0.10
            else:
                self.state = "wander"
                if random.random() < 0.02:
                    self.vx = random.uniform(-0.5, 0.5)
                    self.vy = random.uniform(-0.5, 0.5)

        v = dist(0, 0, self.vx, self.vy)
        max_v = 1.0 * self.speed_factor

        if v > max_v and v != 0:
            self.vx *= max_v / v
            self.vy *= max_v / v

        nx, ny = self.x + self.vx, self.y + self.vy
        sanctuary_boundary = WINDOW_W - SANCTUARY_W

        if nx > sanctuary_boundary - ZOMBIE_R:
            nx = self.x
            self.vx = 0

        self.x, self.y = nx, ny

        if self.vx > 0: self.dir = 1
        elif self.vx < 0: self.dir = -1

        self.x = clamp(self.x, ZOMBIE_R, WINDOW_W - 1 - ZOMBIE_R)
        self.y = clamp(self.y, UI_HEIGHT + ZOMBIE_R, WINDOW_H - 1 - ZOMBIE_R)

    def draw(self):
        x, y = int(self.x), int(self.y)

        for p in self.captured_particles:
            pyxel.pset(int(p[0]), int(p[1]), p[4])

        pyxel.circ(x, y + 5, 5, 0)
        c = 7 if self.state == "captured" else self.base_color
        step = 1 if int(self.attack_anim) % 2 == 0 else -1

        pyxel.rect(x - 3, y + 3 + step, 3, 4, c)
        pyxel.rect(x + 1, y + 3 - step, 3, 4, c)
        pyxel.rect(x - 5, y - 2, 10, 8, c)
        pyxel.rect(x - 4, y - 1, 8, 6, c + 1)
        pyxel.line(x - 2, y - 1, x, y + 3, 3)
        pyxel.line(x + 2, y - 1, x + 1, y + 2, 3)

        arm = int(math.sin(self.attack_anim))
        pyxel.line(x - 4, y - 1, x - 7, y + arm, c)
        pyxel.line(x + 4, y - 1, x + 7, y - arm, c)

        pyxel.circ(x, y - 6, 4, c)
        pyxel.circ(x, y - 6, 3, c + 1)
        pyxel.rect(x - 4, y - 10, 8, 2, 0)
        pyxel.pset(x - 2, y - 7, 8)
        pyxel.pset(x + 2, y - 7, 8)
        pyxel.line(x - 2, y - 4, x + 2, y - 4, 0)

        if self.state == "captured":
            pyxel.rectb(x - 6, y - 11, 12, 17, 13)


# ============================================================
# CREDITS
# ============================================================

CREDITS_CONTENT = [
    (18, "DEMOCRACY OF THE DEAD", 8),
    (8, "", 7),
    (16, "ゲームデザイン & コンセプト", 11),
    (14, "Y. K", 7),
    (10, "", 0),
    (16, "プログラム & サウンド", 11),
    (14, "M. T", 7),
    (10, "", 0),
    (16, "スペシャルサンクス", 11),
    (14, "チーム T.D", 7),
    (14, "すべてのプレイヤー", 7),
    (10, "", 0),
    (16, "テストプレイ", 11),
    (14, "ゲームチューニング", 7),
    (14, "M. T", 7),
    (12, "", 0),
    (18, "最後までのプレイありがとう!", 13),
    (8, "", 7),
    (16, "制作著作 MIRAI WORK 2026", 13),
    (8, "", 7),
    (18, "また会いましょう！", 8),
]


# ============================================================
# MAIN GAME
# ============================================================

class GameApp:
    def __init__(self):
        pyxel.init(WINDOW_W, WINDOW_H, title="DEMOCRACY OF THE DEAD")
        self.bdf = BDFParser("umplus_j10r.bdf")
        self.title_image_loaded = False

        if os.path.exists(TITLE_IMAGE):
            try:
                pyxel.images[0].load(0, 0, TITLE_IMAGE)
                self.title_image_loaded = True
            except Exception:
                self.title_image_loaded = False

        self.setup_sound()

        self.state = "TITLE"
        self.stage = -1
        self.stage_start_frame = 0
        self.stage_time_limit = BASE_TIME_LIMIT
        self.time_remaining_next_stage = BASE_TIME_LIMIT
        self.last_stage_remaining_time = 0.0
        self.start_time_total = 0.0
        self.total_clear_time = 0.0
        self.zombie_speed_multiplier = 1.0

        self.player = None
        self.players = []
        self.dummy_players = []
        self.zombies = []
        self.captured_zombies = []
        self.obstacles = []
        self.particles = []
        self.shockwaves = []
        
        self.ash_particles = [
            [random.uniform(0, WINDOW_W), random.uniform(0, WINDOW_H), random.uniform(0.1, 0.4)]
            for _ in range(40)
        ]

        self.fade = Fade()
        self.shake = Shake()

        self.next_state_called = False
        self.marching = False
        self.fade_outting = False
        self.time_up_zombified = False
        self.time_up_frame = 0
        self.time_up_warning_played = False

        self.ending_timer = 0
        self.sunset_timer = 0
        self.title_logo_alpha_timer = 0
        self.credits_y = WINDOW_H
        self.credits_duration = sum(h for h, _, _ in CREDITS_CONTENT)
        self.credits_finished = False
        self.show_final_score = False
        self.result_timer = 0
        
        # 動画自動選択（ガチャ）用変数
        self.video_timer = 0

        self.title_particles = []
        for _ in range(55):
            self.title_particles.append(
                [random.randint(0, WINDOW_W - 1), random.randint(0, WINDOW_H - 1),
                 random.uniform(0.2, 1.2), random.choice([5, 6, 7, 13])]
            )

        self.play_music_safe("TITLE")

        try:
            import js
            js.pyxel_app = self
        except Exception:
            pass

        pyxel.run(self.update, self.draw)

    def get_text_width(self, text):
        width = 0
        for c in text:
            code = ord(c)
            width += self.bdf.widths.get(code, 6 if code > 127 else 4)
        return width

    def center_text_x(self, text):
        return max(0, (WINDOW_W - self.get_text_width(text)) // 2)

    def get_stage_theme(self):
        themes = {
            1: (2, 1, 9, 10), 2: (1, 5, 13, 4), 3: (9, 2, 10, 8),
            4: (0, 1, 5, 2), 5: (13, 1, 6, 3), FINAL_STAGE: (3, 0, 8, 2),
        }
        return themes.get(self.stage, (2, 1, 9, 10))

    def setup_sound(self):
        try:
            pyxel.sounds[0].set("c2e2g2 c2e2g2 d2f2a2 d2f2a2", "t", "55445544", "nnnnnnnn", 18)
            pyxel.sounds[1].set("c2 c2 g1 g1 a1 a1 f1 f1", "s", "55443322", "nnnnnnnn", 20)
            pyxel.sounds[2].set("c1e1g1 c1e1g1 f1a1c2 f1a1c2", "p", "55443322", "nnnnnnnn", 26)
            pyxel.sounds[3].set("c1 r c1 r g0 r g0 r", "n", "76543210", "nnnnnnnn", 22)
            pyxel.sounds[4].set("c2e2g2c3", "p", "7777", "nnnn", 5)
            pyxel.sounds[5].set("c3g2c2", "s", "754", "sss", 5)
            pyxel.sounds[6].set("c3", "s", "7", "n", 6)
            pyxel.sounds[7].set("c2", "p", "4", "n", 4)
            pyxel.sounds[8].set("c3e3g3c4", "p", "7777", "sfsf", 10)
            pyxel.sounds[9].set("c1g0c1", "n", "765", "fff", 8)
            pyxel.sounds[10].set("g2c3g2c3g2c3c1", "s", "76547654", "nnnnnnnn", 18)
            pyxel.sounds[11].set("c2a1f1d1", "n", "7654", "ffff", 14)
            pyxel.sounds[12].set("c1 c1 d1 e1 f1", "n", "76543", "fffff", 12)
            pyxel.sounds[12+1].set("c2e2g2c3", "t", "7777", "nnnn", 8)
            pyxel.sounds[13].set("c2g1e1", "p", "543", "fff", 30)
            pyxel.sounds[14].set("e1a1c2", "p", "543", "fff", 30)
            pyxel.sounds[15].set("a0c1e1", "p", "432", "fff", 40)
            pyxel.sounds[16].set("c2e2g2 c2e2g2 c2 c2", "s", "55445544", "nnnnnnnn", 20)
            pyxel.sounds[17].set("e2g2b2 e2g2b2 e2 e2", "p", "55445544", "nnnnnnnn", 20)
            pyxel.sounds[18].set("d2f2a2 d2f2a2 d2 d2", "t", "55445544", "nnnnnnnn", 18)
            pyxel.sounds[19].set("f2a2c3 f2a2c3 f2 f2", "s", "66556655", "nnnnnnnn", 18)
            pyxel.sounds[20].set("g2b2d3 g2b2d3 g2 g2", "p", "66556655", "nnnnnnnn", 16)
            pyxel.sounds[21].set("a2c3e3 a2c3e3 a2 a2", "t", "77667766", "nnnnnnnn", 14)
            
            pyxel.musics[0].set([0], [0], [1], [])
            pyxel.musics[1].set([16], [16], [1], [])
            pyxel.musics[2].set([17], [17], [1], [])
            pyxel.musics[3].set([18], [18], [1], [])
            pyxel.musics[4].set([19], [19], [1], [])
            pyxel.musics[5].set([20], [20], [1], [])
            pyxel.musics[6].set([21], [21], [1], [])
            pyxel.musics[7].set([2], [2], [3], [])
        except Exception:
            pass

    def play_music_safe(self, mode):
        try:
            pyxel.stop()
            if mode == "TITLE": 
                pyxel.playm(0, loop=True)
            elif mode == "PLAYING":
                music_id = self.stage if 1 <= self.stage <= 5 else (6 if self.stage == FINAL_STAGE else 1)
                pyxel.playm(music_id, loop=True)
            elif mode == "ENDING": 
                pyxel.playm(7, loop=True)
            elif mode == "GAMEOVER":
                safe_play(0, 13, loop=True)
                safe_play(1, 14, loop=True)
                safe_play(2, 15, loop=True)
        except Exception:
            pass

    def burst(self, x, y, count=25, colors=None):
        if colors is None: colors = [7, 8, 11, 13]
        for _ in range(count):
            angle = random.random() * math.pi * 2
            speed = random.uniform(0.5, 3.0)
            self.particles.append(
                Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                         random.choice(colors), random.randint(20, 45), random.choice([1, 1, 2]), 0.05)
            )

    def update_effects(self):
        for p in self.particles: p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for s in self.shockwaves: s.update()
        self.shockwaves = [s for s in self.shockwaves if s.life > 0]
        for ash in self.ash_particles:
            ash[0] -= ash[2]
            ash[1] += ash[2] * 2.5
            if ash[1] > WINDOW_H:
                ash[1] = -5
                ash[0] = random.uniform(0, WINDOW_W + 50)

    def spawn_stage(self):
        self.stage += 1
        if self.stage < 1: self.stage = 1
        if self.stage > FINAL_STAGE: self.stage = FINAL_STAGE

        self.time_up_zombified = False
        self.time_up_frame = 0
        self.time_up_warning_played = False
        self.fade_outting = False

        self.players = []
        self.dummy_players = []
        self.zombies = []
        self.captured_zombies = []
        self.particles = []
        self.shockwaves = []

        if self.stage == FINAL_STAGE:
            spawn_x = WINDOW_W // 4
            spawn_y = WINDOW_H // 2
            self.player = Player(spawn_x, spawn_y, True, char_type="heroine")
            self.players.append(self.player)

            sanctuary_x = (WINDOW_W - SANCTUARY_W + 5)
            self.dummy_players = [
                Player(sanctuary_x, WINDOW_H // 2 - 20, False, 11, char_type="boy"),
                Player(sanctuary_x + 4, WINDOW_H // 2, False, 7, char_type="boy"),
                Player(sanctuary_x, WINDOW_H // 2 + 20, False, 8, char_type="girl")
            ]
            self.players.extend(self.dummy_players)

            count = FINAL_STAGE_ZOMBIES
            self.stage_time_limit = max(FINAL_STAGE_TIME_LIMIT_MIN, self.time_remaining_next_stage)
        else:
            self.player = Player(WINDOW_W // 4, WINDOW_H // 2, True, char_type="heroine")
            self.players.append(self.player)
            count = (ZOMBIE_COUNT_BASE + (self.stage - 1) * 2)
            self.stage_time_limit = self.time_remaining_next_stage

        for _ in range(count):
            zx = random.randint(8, WINDOW_W - SANCTUARY_W - 8)
            zy = random.randint(UI_HEIGHT + 5, WINDOW_H - 8)
            sf = random.choice([0.8, 1.0, 1.15, 1.3])
            self.zombies.append(Zombie(zx, zy, sf, self.zombie_speed_multiplier))

        if self.start_time_total == 0:
            self.start_time_total = (pyxel.frame_count / 60.0)

        self.stage_start_frame = pyxel.frame_count
        self.state = "PLAYING"
        self.marching = False
        self.fade.to(0.0, 0.08)
        self.play_music_safe("PLAYING")

    def start_march(self):
        self.marching = True
        for p in self.players:
            p.walk_frame = 0

    def update_march(self):
        if not self.marching: return
        target_x = (WINDOW_W - SANCTUARY_W + 2)
        speed = PLAYER_SPEED * 1.5

        for e in ([self.player] + self.captured_zombies):
            if e.x < target_x:
                e.x += min(speed, target_x - e.x)
                e.dir = 1
                if isinstance(e, Player):
                    e.walk_frame = (e.walk_frame + 1) % 16
        self.player.trail = [(self.player.x, self.player.y)] * TRAIL_MAX_LENGTH

    def start_ending(self):
        self.total_clear_time = (pyxel.frame_count / 60.0 - self.start_time_total)
        self.last_stage_remaining_time = self.time_remaining_next_stage
        self.time_remaining_next_stage += BONUS_TIME_AFTER_CLEAR
        self.state = "ENDING"
        self.ending_timer = 0
        self.sunset_timer = 0
        self.fade.to(0.0, 0.08)
        self.show_final_score = False
        self.play_music_safe("ENDING")

    def reset_to_title(self):
        self.state = "TITLE"
        self.stage = -1
        self.time_remaining_next_stage = BASE_TIME_LIMIT
        self.start_time_total = 0
        self.play_music_safe("TITLE")
        self.fade.to(0, 0.06)

    def movie_finished(self):
        self.reset_to_title()

    def update(self):
        self.fade.update()
        self.shake.update()
        self.update_effects()

        enter = (
            pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(GAMEPAD_A_ID) or 
            pyxel.btnp(GAMEPAD_C_ID) or pyxel.btnp(GAMEPAD_START_ID)
        )

        if self.state == "TITLE":
            if enter:
                safe_play(3, 4)
                self.fade.to(1.0, 0.06)
                self.next_state_called = True
            if (self.next_state_called and not self.fade.active and self.fade.alpha >= 0.99):
                self.next_state_called = False
                self.state = "TUTORIAL"
                self.fade.to(0.0, 0.06)

        elif self.state == "TUTORIAL":
            if enter:
                safe_play(3, 4)
                self.fade.to(1.0, 0.06)
                self.next_state_called = True
            if (self.next_state_called and not self.fade.active and self.fade.alpha >= 0.99):
                self.next_state_called = False
                self.stage = 0
                self.time_remaining_next_stage = BASE_TIME_LIMIT
                self.start_time_total = 0
                self.spawn_stage()

        elif self.state == "PLAYING":
            self.player.update(self.obstacles, True)
            for z in self.zombies:
                z.update(self.player, self.obstacles, self.captured_zombies)

            newly = [z for z in self.zombies if (z.state == "captured" and z not in self.captured_zombies)]
            for z in newly:
                self.captured_zombies.append(z)
                self.shockwaves.append(Shockwave(z.x, z.y, 8))
                self.burst(z.x, z.y, count=10, colors=[8, 9, 13])
                self.shake.start(4, 1)

            elapsed = (pyxel.frame_count - self.stage_start_frame) / 60.0
            time_left = max(0, self.stage_time_limit - elapsed)

            if time_left < 10 and not self.time_up_zombified and time_left > 0:
                if not self.time_up_warning_played:
                    safe_play(3, 6, loop=True)
                    self.time_up_warning_played = True
            else:
                if self.time_up_warning_played and time_left <= 0:
                    pyxel.stop(3) 

            if (time_left <= 0 and not self.time_up_zombified):
                self.time_up_zombified = True
                self.player.is_zombified = True
                self.time_up_frame = pyxel.frame_count
                self.shockwaves.append(Shockwave(self.player.x, self.player.y, 8))
                self.shake.start(20, 4)
                safe_play(3, 10) 
                self.play_music_safe("GAMEOVER")

            if self.time_up_zombified:
                if (pyxel.frame_count - self.time_up_frame > GAMEOVER_HOLD_TIME):
                    self.fade.to(1.0, 0.05)
                    self.next_state_called = True

            if (self.next_state_called and self.fade.alpha >= 0.99):
                self.next_state_called = False
                self.reset_to_title()

            if (len(self.zombies) > 0 and len(self.captured_zombies) == len(self.zombies) and not self.time_up_zombified):
                pyxel.stop(3)
                self.time_remaining_next_stage = time_left
                self.state = "GO_TO_SANCT"
                self.start_march()
                pyxel.stop()
                safe_play(0, 8)
                safe_play(1, 8)
                self.shockwaves.append(Shockwave(self.player.x, self.player.y, 9))

        elif self.state == "GO_TO_SANCT":
            self.update_march()
            sanctuary_x = (WINDOW_W - SANCTUARY_W)

            if (self.player.x >= sanctuary_x and all(z.x >= sanctuary_x for z in self.captured_zombies)):
                if not self.fade_outting:
                    self.marching = False
                    self.fade.to(1, 0.025)
                    self.fade_outting = True

            if (self.fade_outting and not self.fade.active and self.fade.alpha >= 0.99):
                self.fade_outting = False
                if self.stage == FINAL_STAGE:
                    self.start_ending()
                else:
                    self.spawn_stage()

        elif self.state == "ENDING":
            self.ending_timer += 1
            if self.ending_timer == 1: self.fade.to(0, 0.08)

            if (self.ending_timer < TRANSFORM_DURATION):
                if (self.ending_timer % 8 == 0): safe_play(3, 11)
                if (self.ending_timer % 10 == 0):
                    for p in self.dummy_players:
                        p.spawn_transform_particle(random.choice([3, 8, 13]))
                if (self.ending_timer % 5 < 2): self.shake.start(3, 2)
                for p in self.dummy_players:
                    if (self.ending_timer % 6 < 3): p.temp_color = random.choice([3, 8, 13])
                    else: p.temp_color = p.color

            if (self.ending_timer == TRANSFORM_DURATION):
                self.shake.start(25, 6)
                safe_play(3, 9)
                self.burst(self.player.x, self.player.y, count=40, colors=[8, 13, 3])
                for p in self.dummy_players:
                    p.is_zombified = True
                    p.temp_color = None

            if (self.ending_timer > TRANSFORM_DURATION + 60 and self.state == "ENDING"):
                self.state = "SUNSET_VIEW"
                self.sunset_timer = 0

        elif self.state == "SUNSET_VIEW":
            self.sunset_timer += 1
            self.player.dir = 0

            if self.sunset_timer > 240:
                self.state = "CREDITS_ROLL"
                self.credits_y = WINDOW_H + 10
                self.credits_finished = False
                self.fade_outting = False
                self.title_logo_alpha_timer = 0
                self.fade.to(0, 0.02)
                self.play_music_safe("ENDING")

        elif self.state == "CREDITS_ROLL":
            self.credits_y -= CREDITS_SPEED
            final_credit_bottom = (self.credits_y + self.credits_duration)

            if (final_credit_bottom < -10 and not self.fade_outting):
                self.fade_outting = True
                self.fade.to(1.0, 0.015) 

            if (self.fade_outting and not self.fade.active and self.fade.alpha >= 0.99):
                self.fade_outting = False
                self.state = "FINAL_LOGO"
                self.title_logo_alpha_timer = 0
                pyxel.stop()

        elif self.state == "FINAL_LOGO":
            self.title_logo_alpha_timer += 1
            if self.title_logo_alpha_timer == 30:
                self.fade.to(0.0, 0.02)
            elif self.title_logo_alpha_timer == 180:
                self.fade.to(1.0, 0.02)
            elif self.title_logo_alpha_timer > 180 and not self.fade.active and self.fade.alpha >= 0.99:
                self.state = "MOVIE_GACHA"
                self.video_timer = 0
                self.fade.alpha = 0.0
                self.fade.target = 0.0
                pyxel.stop()

        # ========= 動画自動選択（確率：80%, 15%, 5%） =========
        elif self.state == "MOVIE_GACHA":
            if self.video_timer == 0:
                rand_val = random.random()
                if rand_val < 0.80:
                    selected_movie = "rea1gumono.mp4"
                elif rand_val < 0.95:
                    selected_movie = "rea2seigi.mp4"
                else:
                    selected_movie = "rea3kenjya.mp4"

                try:
                    import js
                    js.showEndingMovie(selected_movie)
                except Exception:
                    print(f"Movie Gacha [Local Test]: {selected_movie}")

            self.video_timer += 1
            
            # 動画終了判定（例：約10秒 = 600フレーム）
            if self.video_timer > 600:
                self.reset_to_title()

    def draw(self):
        ox, oy = self.shake.get_offset()
        pyxel.cls(0)

        if self.state == "TITLE": self.draw_title()
        elif self.state == "TUTORIAL": self.draw_tutorial()
        elif self.state in ("PLAYING", "GO_TO_SANCT"):
            pyxel.camera(ox, oy)
            pyxel.clip(0, UI_HEIGHT, WINDOW_W, WINDOW_H - UI_HEIGHT)
            self.draw_playing()
            pyxel.camera(0, 0)
            pyxel.clip()
            self.draw_ui()
            if self.time_up_zombified:
                self.draw_gameover()
        elif self.state == "ENDING": self.draw_ending()
        elif self.state == "SUNSET_VIEW": self.draw_sunset_view()
        elif self.state == "CREDITS_ROLL": self.draw_credits()
        elif self.state == "FINAL_LOGO": self.draw_final_logo()
        elif self.state == "MOVIE_GACHA":
            pyxel.cls(0)
            text = ""
            self.bdf.draw_text(self.center_text_x(text), 55, text, 8)

        for ash in self.ash_particles:
            pyxel.pset(int(ash[0]), int(ash[1]), 5 if ash[2] < 0.25 else 13)

        self.fade.draw()

    def draw_title(self):
        pyxel.cls(12)

        pyxel.circ(25, 50, 18, 6)
        pyxel.circ(45, 42, 22, 6)
        pyxel.circ(65, 46, 16, 6)
        pyxel.rect(15, 48, 58, 22, 6)
        
        pyxel.circ(20, 42, 15, 7)
        pyxel.circ(35, 33, 19, 7)
        pyxel.circ(52, 35, 17, 7)
        pyxel.circ(64, 40, 12, 7)
        pyxel.rect(20, 38, 48, 15, 7)

        pyxel.circ(115, 45, 20, 6)
        pyxel.circ(135, 38, 22, 6)
        pyxel.rect(105, 45, 45, 25, 6)
        
        pyxel.circ(110, 38, 16, 7)
        pyxel.circ(128, 28, 21, 7)
        pyxel.circ(142, 34, 15, 7)
        pyxel.rect(112, 32, 35, 18, 7)

        store_y = WINDOW_H - 42
        pyxel.rect(8, store_y, 144, 42, 1)
        pyxel.rect(70, store_y + 14, 20, 28, 0)
        pyxel.line(80, store_y + 14, 80, store_y + 41, 13)
        for wx in range(16, 62, 11):
            pyxel.rect(wx, store_y + 16, 8, 16, 0)
            pyxel.line(wx + 4, store_y + 16, wx + 4, store_y + 31, 13)
        for wx in range(98, 144, 11):
            pyxel.rect(wx, store_y + 16, 8, 16, 0)
            pyxel.line(wx + 4, store_y + 16, wx + 4, store_y + 31, 13)

        pyxel.rect(46, store_y - 12, 68, 14, 0)
        pyxel.rectb(46, store_y - 12, 68, 14, 7)
        neon_color = 8 if (pyxel.frame_count // 15) % 2 == 0 else 2
        self.bdf.draw_text(48, store_y - 9, "CAMERA SHOP", neon_color)

        frame_x, frame_y = TITLE_FRAME_X, TITLE_FRAME_Y
        pyxel.rect(frame_x - 1, frame_y - 1, TITLE_FRAME_W + 2, TITLE_FRAME_H + 2, 7)
        pyxel.rect(frame_x, frame_y, TITLE_FRAME_W, TITLE_FRAME_H, 0)

        if self.title_image_loaded:
            pyxel.blt(TITLE_IMG_X, TITLE_IMG_Y, 0, 0, 0, TITLE_IMG_W, TITLE_IMG_H, None)
        else:
            pyxel.rect(TITLE_IMG_X, TITLE_IMG_Y, TITLE_IMG_W, TITLE_IMG_H, 1)
            title = "DEMOCRACY"
            self.bdf.draw_text(self.center_text_x(title), 35, title, 8)
            self.bdf.draw_text(self.center_text_x("OF THE DEAD"), 45, "OF THE DEAD", 7)

        if (pyxel.frame_count // 8) % 2 == 0:
            pyxel.line(frame_x, frame_y, frame_x + TITLE_FRAME_W - 1, frame_y, 13)

        pyxel.rect(1, 92, 158, 24, 0)
        pyxel.rectb(1, 92, 158, 24, 7)
        if (pyxel.frame_count // 30) % 2 == 0:
            prompt = "エンターキー/Aボタンを押してね"
            self.bdf.draw_text(self.center_text_x(prompt), 94, prompt, 8)

        copy_text = "(C)MIRAI WORK/Y.K/M.T 2026"
        self.bdf.draw_text(self.center_text_x(copy_text), 104, copy_text, 7)

    def draw_tutorial(self):
        pyxel.cls(0)
        for x in range(0, WINDOW_W, 8): pyxel.line(x, 0, x, WINDOW_H, 1)
        for y in range(0, WINDOW_H, 8): pyxel.line(0, y, WINDOW_W, y, 1)

        self.bdf.draw_text(self.center_text_x("DEMOCRACY OF THE DEAD"), 7, "DEMOCRACY OF THE DEAD", 8)
        tut_title = "操作方法"
        self.bdf.draw_text(self.center_text_x(tut_title), 19, tut_title, 13)

        instructions = [
            ("01", "移動", "方向キー/DPAD"),
            ("02", "捕獲", "ゾンビに接触"),
            ("03", "目的", "ゾンビを聖域へ"),
            ("04", "生存", "制限時間内聖域へ")
        ]
        for i, (n, head, body) in enumerate(instructions):
            y = 34 + i * 15
            pyxel.rect(12, y - 2, 12, 10, 1)
            self.bdf.draw_text(14, y, n, 13)
            self.bdf.draw_text(28, y, head, 11)
            self.bdf.draw_text(72, y, body, 7)

        if (pyxel.frame_count // 20) % 2 == 0:
            start_msg = "- エンターキーでスタート -"
            self.bdf.draw_text(self.center_text_x(start_msg), 108, start_msg, 8)

    def draw_playing(self):
        bg_col, line_col, grid_col, sanc_col = self.get_stage_theme()
        sanctuary_x = (WINDOW_W - SANCTUARY_W)
        
        pyxel.rect(0, UI_HEIGHT, WINDOW_W, WINDOW_H - UI_HEIGHT, bg_col)
        for y in range(UI_HEIGHT, WINDOW_H, 8): pyxel.line(0, y, WINDOW_W, y, 1)
        for x in range(0, sanctuary_x, 8): pyxel.line(x, UI_HEIGHT, x, WINDOW_H, line_col)
        for y in range(UI_HEIGHT + 4, WINDOW_H, 16): pyxel.line(0, y, sanctuary_x, y, grid_col)

        pyxel.rect(sanctuary_x, UI_HEIGHT, SANCTUARY_W, WINDOW_H - UI_HEIGHT, sanc_col)
        pyxel.rectb(sanctuary_x, UI_HEIGHT, SANCTUARY_W, WINDOW_H - UI_HEIGHT, 13)
        for y in range(UI_HEIGHT + 3, WINDOW_H, 7): pyxel.line(sanctuary_x + 2, y, WINDOW_W - 3, y, 12)

        entities = (list(self.players) + list(self.zombies))
        entities.sort(key=lambda e: e.y)
        for e in entities: e.draw()
        for s in self.shockwaves: s.draw()
        for p in self.particles: p.draw()

        if self.state == "GO_TO_SANCT":
            box_w, box_h = 128, 16
            box_x, box_y = (WINDOW_W - box_w) // 2, WINDOW_H - 20
            pyxel.rect(box_x, box_y, box_w, box_h, 0)
            pyxel.rectb(box_x, box_y, box_w, box_h, 13)
            text = "シェルターへむかえ!"
            self.bdf.draw_text(self.center_text_x(text), box_y + 3, text, 8)

    def draw_ui(self):
        pyxel.rect(0, 0, WINDOW_W, UI_HEIGHT, 0)
        pyxel.line(0, UI_HEIGHT - 1, WINDOW_W, UI_HEIGHT - 1, 13)

        stage_text = "STAGE: FINAL" if self.stage == FINAL_STAGE else f"STAGE: {self.stage}/{MAX_STAGE_PLAY}"
        self.bdf.draw_text(4, 2, stage_text, 7)

        elapsed = (pyxel.frame_count - self.stage_start_frame) / 60.0
        time_left = max(0, self.stage_time_limit - elapsed)
        time_text = f"残:{time_left:04.1f}s"
        tx = (WINDOW_W - self.get_text_width(time_text) - 4)
        
        color = 7 if (time_left >= 10 and not self.time_up_zombified) else 8
        self.bdf.draw_text(tx, 2, time_text, color)

        captured, total = len(self.captured_zombies), len(self.zombies)
        self.bdf.draw_text(4, 14, f"捕獲: {captured}/{total}", 11)

    def draw_gameover(self):
        if (pyxel.frame_count // 5) % 2 == 0:
            pyxel.rect(0, UI_HEIGHT, WINDOW_W, WINDOW_H - UI_HEIGHT, 2)
        box_w, box_h = 130, 48
        bx, by = (WINDOW_W - box_w) // 2, (WINDOW_H - box_h) // 2

        pyxel.rect(bx, by, box_w, box_h, 0)
        pyxel.rectb(bx, by, box_w, box_h, 8)
        pyxel.rectb(bx + 2, by + 2, box_w - 4, box_h - 4, 3)

        t1, t2, t3 = "タイムアップ!", "ゲームオーバー", "モンスターたちの勝利"
        center_x = bx + box_w // 2
        self.bdf.draw_text(center_x - len(t1) * 4, by + 7, t1, 8)
        self.bdf.draw_text(center_x - len(t2) * 4, by + 19, t2, 7)
        self.bdf.draw_text(center_x - len(t3) * 4, by + 31, t3, 13)

    def draw_ending(self):
        pyxel.cls(0)
        pyxel.rect(WINDOW_W - SANCTUARY_W, 0, SANCTUARY_W, WINDOW_H, 10)
        if (self.ending_timer % 12 < 6): pyxel.rect(WINDOW_W - SANCTUARY_W, 0, SANCTUARY_W, WINDOW_H, 3)

        for p in self.players: p.draw()
        for s in self.shockwaves: s.draw()

        pyxel.rect(0, 0, WINDOW_W, 8, 0)
        pyxel.rect(0, WINDOW_H - 8, WINDOW_W, 8, 0)

        if (self.ending_timer < TRANSFORM_DURATION):
            text1, text2 = "シェルターが侵食されている...", "苦しい... 苦しい..."
            self.bdf.draw_text(self.center_text_x(text1), 11, text1, 8)
            self.bdf.draw_text(self.center_text_x(text2), 21, text2, 7)
        else:
            text1, text2 = "シェルターは侵食された。", "彼らはモンスターとなった。"
            self.bdf.draw_text(self.center_text_x(text1), 11, text1, 8)
            self.bdf.draw_text(self.center_text_x(text2), 21, text2, 7)

    def draw_sunset_view(self):
        pyxel.cls(9)
        
        for i in range(3):
            speed = 0.4 + i * 0.15
            c_x = int((pyxel.frame_count * speed + i * 55) % (WINDOW_W + 30)) - 15
            c_y = 22 + i * 10 + int(math.sin(pyxel.frame_count * 0.08 + i * 2) * 3)
            if (pyxel.frame_count // 10 + i) % 2 == 0:
                pyxel.line(c_x - 3, c_y - 2, c_x, c_y, 0)
                pyxel.line(c_x, c_y, c_x + 3, c_y - 2, 0)
            else:
                pyxel.line(c_x - 3, c_y + 1, c_x, c_y, 0)
                pyxel.line(c_x, c_y, c_x + 3, c_y + 1, 0)

        pyxel.rect(0, WINDOW_H // 3, WINDOW_W, WINDOW_H * 2 // 3, 10)
        pyxel.rect(0, WINDOW_H * 2 // 3, WINDOW_W, WINDOW_H // 3, 4)

        cycle = [9, 10, 8, 14]
        c_idx = (pyxel.frame_count // 8) % len(cycle)
        for i in range(8, 0, -1):
            color = cycle[(i + c_idx) % len(cycle)] if i > 3 else 9
            pyxel.circ(WINDOW_W // 2, 15, i * 8, color)

        store_y = WINDOW_H - 45
        pyxel.rect(10, store_y, 140, 45, 0)
        pyxel.rect(45, store_y - 12, 70, 12, 4)
        pyxel.rectb(45, store_y - 12, 70, 12, 0)
        self.bdf.draw_text(48, store_y - 9, "DRUG STORE", 2)
        
        pyxel.rect(70, store_y + 15, 20, 30, 4)
        for wx in range(20, 60, 10): pyxel.rect(wx, store_y + 18, 6, 16, 4)
        for wx in range(100, 140, 10): pyxel.rect(wx, store_y + 18, 6, 16, 4)

        px, py = WINDOW_W // 2, WINDOW_H - 26
        pyxel.circ(px, py + 8, 5, 0)
        pyxel.rect(px - 3, py - 1, 6, 9, 0)
        pyxel.pset(px - 2, py + 2, 11)
        pyxel.circ(px, py - 6, 4, 6)
        pyxel.rect(px - 4, py - 10, 9, 3, 5)
        pyxel.rect(px - 4, py - 7, 2, 5, 5)
        pyxel.rect(px + 3, py - 7, 2, 5, 5)
        pyxel.line(px - 1, py - 2, px - 3, py + 3, 0)
        pyxel.line(px + 1, py - 2, px + 3, py + 3, 0)

        msg1, msg2 = "言われた通り、助けは呼びに行った", "それが民主主義ってヤツでしょう？"
        self.bdf.draw_text(self.center_text_x(msg1), 12, msg1, 7)
        self.bdf.draw_text(self.center_text_x(msg2), 22, msg2, 7)

    def draw_credits(self):
        pyxel.cls(0)
        progress = clamp((WINDOW_H - self.credits_y) / (self.credits_duration * 0.75), 0.0, 1.0)
        
        sky1 = 9 if progress < 0.3 else (1 if progress < 0.7 else 0)
        sky2 = 10 if progress < 0.3 else (2 if progress < 0.7 else 1)
        ground = 4 if progress < 0.3 else (3 if progress < 0.7 else 0)
        
        if sky1 != 0: pyxel.rect(0, 0, WINDOW_W, WINDOW_H // 3, sky1)
        pyxel.rect(0, WINDOW_H // 3, WINDOW_W, WINDOW_H * 2 // 3, sky2)
        pyxel.rect(0, WINDOW_H * 2 // 3, WINDOW_W, WINDOW_H // 3, ground)

        if progress < 0.8:
            cycle = [9, 10, 8, 14]
            c_idx = (pyxel.frame_count // 8) % len(cycle)
            sun_y = 15 + int(progress * 70)
            
            for i in range(8, 0, -1):
                color = cycle[(i + c_idx) % len(cycle)] if i > 3 else (9 if progress < 0.4 else 8)
                r = i * 8
                for dy in range(-r, r):
                    dx = int(math.sqrt(max(0, r**2 - dy**2)))
                    distort = int(math.sin(dy * 0.5 + pyxel.frame_count * 0.1) * (progress * 5))
                    pyxel.line(WINDOW_W // 2 - dx + distort, sun_y + dy, WINDOW_W // 2 + dx + distort, sun_y + dy, color)

        for i in range(3):
            speed = 0.4 + i * 0.15
            c_x = int((pyxel.frame_count * speed + i * 55) % (WINDOW_W + 30)) - 15
            c_y = 22 + i * 10 + int(math.sin(pyxel.frame_count * 0.08 + i * 2) * 3) - int(progress * 5)
            crow_col = 0 if progress < 0.6 else 1
            if (pyxel.frame_count // 10 + i) % 2 == 0:
                pyxel.line(c_x - 3, c_y - 2, c_x, c_y, crow_col)
                pyxel.line(c_x, c_y, c_x + 3, c_y - 2, crow_col)
            else:
                pyxel.line(c_x - 3, c_y + 1, c_x, c_y, crow_col)
                pyxel.line(c_x, c_y, c_x + 3, c_y + 1, crow_col)

        bldg_col, bldg_hl = 0, (4 if progress < 0.5 else 0)
        scroll_offset = max(0, WINDOW_H - self.credits_y) * 0.25
        store_y = int(WINDOW_H - 40 - scroll_offset)
        if store_y < WINDOW_H + 20:
            pyxel.rect(10, store_y, 140, 60, bldg_col)
            pyxel.rect(45, store_y - 10, 70, 10, bldg_hl)

        y = self.credits_y
        for height, text, color in CREDITS_CONTENT:
            if text:
                x = self.center_text_x(text)
                for dx, dy in [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]:
                    self.bdf.draw_text(x + dx, int(y) + dy, text, 0)
                txt_col = color if progress < 0.7 else 7
                self.bdf.draw_text(x, int(y), text, txt_col)
            y += height

    def draw_final_logo(self):
        pyxel.cls(0)
        title_text1 = "DEMOCRACY"
        title_text2 = "OF THE DEAD"
        tx1 = self.center_text_x(title_text1)
        tx2 = self.center_text_x(title_text2)
        
        self.bdf.draw_text(tx1, WINDOW_H // 2 - 12, title_text1, 8)
        self.bdf.draw_text(tx2, WINDOW_H // 2 + 2, title_text2, 7)

GameApp()
