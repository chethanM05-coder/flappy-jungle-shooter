import wx
import random
import time
import os
import math

# Improved Flappy Jungle Shooter (wxPython)
# Features:
# - integer drawing to avoid deprecation warnings
# - capped dt
# - pause (P) / restart (R)
# - shooting cooldown and bullet limit
# - multiple enemy types (snake, eagle)
# - image loading from assets/ with graceful fallback to rectangles

WINDOW_W = 480
WINDOW_H = 640
MAX_BULLETS = 4
SHOOT_COOLDOWN = 0.28


def load_bitmap(path, expected_w=None, expected_h=None):
    if not os.path.isfile(path):
        return None
    try:
        img = wx.Image(path, wx.BITMAP_TYPE_ANY)
        if expected_w and expected_h:
            img = img.Scale(expected_w, expected_h, wx.IMAGE_QUALITY_HIGH)
        return wx.Bitmap(img)
    except Exception:
        return None


class Sprite:
    def __init__(self, x, y, w, h, vx=0, vy=0, color=wx.Colour(255, 255, 255), bmp=None):
        self.x = float(x)
        self.y = float(y)
        self.w = int(w)
        self.h = int(h)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.alive = True
        self.bmp = bmp
        # preserve original bitmap for potential per-frame effects
        self._orig_bmp = bmp
        # visual niceties
        self.shadow = True
        # bobbing parameters (for enemies)
        self.base_y = float(y)
        self.bob_phase = 0.0
        self.bob_amp = 0.0
        self.bob_speed = 1.0

    def rect(self):
        return (int(self.x), int(self.y), self.w, self.h)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, dc):
        ix = int(self.x)
        iy = int(self.y)

        # shadow
        if self.shadow:
            try:
                sh_brush = wx.Brush(wx.Colour(0, 0, 0, 100))
                dc.SetBrush(sh_brush)
                dc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 0)))
                dc.DrawEllipse(ix + 6, iy + self.h - 6, int(self.w - 8), 8)
            except Exception:
                # some backends may not support alpha brushes; fallback
                dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))
                dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
                dc.DrawEllipse(ix + 6, iy + self.h - 6, int(self.w - 8), 8)

        if self.bmp:
            # Draw bitmap (already scaled during load)
            dc.DrawBitmap(self.bmp, ix, iy, True)
            return

        # Check if this is a venom bullet (special rendering)
        bullet_type = getattr(self, 'bullet_type', None)
        if bullet_type == 'venom':
            # Draw venom pellet with glow effect
            try:
                # outer glow (dimmer green)
                glow_color = wx.Colour(80, 200, 60, 100)
                dc.SetBrush(wx.Brush(glow_color))
                dc.SetPen(wx.Pen(glow_color))
                dc.DrawEllipse(ix - 2, iy - 2, self.w + 4, self.h + 4)
            except Exception:
                pass
            # inner bright pellet
            dc.SetBrush(wx.Brush(self.color))
            dc.SetPen(wx.Pen(wx.Colour(80, 180, 60)))
            dc.DrawEllipse(ix, iy, self.w, self.h)
            return

        elif bullet_type == 'special':
            # Bird's special: orange burst bullet
            try:
                glow_color = wx.Colour(255, 150, 50, 120)
                dc.SetBrush(wx.Brush(glow_color))
                dc.SetPen(wx.Pen(glow_color))
                dc.DrawEllipse(ix - 3, iy - 3, self.w + 6, self.h + 6)
            except Exception:
                pass
            dc.SetBrush(wx.Brush(self.color))
            dc.SetPen(wx.Pen(wx.Colour(255, 200, 100)))
            dc.DrawEllipse(ix, iy, self.w, self.h)
            return

        elif bullet_type == 'special_venom':
            # Snake's special: bright yellow-green venom
            try:
                glow_color = wx.Colour(200, 255, 100, 140)
                dc.SetBrush(wx.Brush(glow_color))
                dc.SetPen(wx.Pen(glow_color))
                dc.DrawEllipse(ix - 3, iy - 3, self.w + 6, self.h + 6)
            except Exception:
                pass
            dc.SetBrush(wx.Brush(self.color))
            dc.SetPen(wx.Pen(wx.Colour(120, 200, 80)))
            dc.DrawEllipse(ix, iy, self.w, self.h)
            return

        # Check if this is a snake character
        is_snake = getattr(self, 'character_type', None) == 'snake'

        if is_snake:
            # Draw snake body (segmented)
            segments = getattr(self, 'snake_segments', 3)
            segment_w = int(self.w // segments)
            squash = getattr(self, 'squash', 1.0)
            draw_h = max(2, int(self.h * squash))
            draw_y = iy + (self.h - draw_h)

            for i in range(segments):
                seg_x = ix + i * segment_w
                seg_y = draw_y + (i % 2) * 2  # wavy motion
                dc.SetBrush(wx.Brush(wx.Colour(50 + i * 20, 180, 80)))
                dc.SetPen(wx.Pen(wx.Colour(30, 140, 50)))
                dc.DrawRoundedRectangle(seg_x, seg_y, segment_w, draw_h, 3)

            # snake head (front segment)
            head_x = ix
            head_y = draw_y
            dc.SetBrush(wx.Brush(wx.Colour(60, 200, 90)))
            dc.DrawRoundedRectangle(head_x, head_y, segment_w, draw_h, 3)

            # snake eyes
            eye_x = head_x + int(segment_w * 0.6)
            eye_y = head_y + int(draw_h * 0.3)
            dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
            dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
            dc.DrawCircle(eye_x, eye_y, max(1, int(draw_h // 6)))
            dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))
            dc.DrawCircle(eye_x + 1, eye_y - 1, max(1, int(draw_h // 12)))

            # snake tongue
            tongue_x = head_x + segment_w
            tongue_y = head_y + int(draw_h // 2)
            dc.SetPen(wx.Pen(wx.Colour(255, 100, 100), 2))
            dc.DrawLine(tongue_x, tongue_y, tongue_x + 6, tongue_y - 2)
            dc.DrawLine(tongue_x, tongue_y, tongue_x + 6, tongue_y + 2)
            return

        # rectangle fallback with bird-like details
        # compute tilt and squash if present (attributes set by GamePanel)
        tilt = getattr(self, 'tilt', 0.0)
        squash = getattr(self, 'squash', 1.0)

        # apply squash vertically by adjusting height
        draw_h = max(2, int(self.h * squash))
        draw_y = iy + (self.h - draw_h)

        dc.SetBrush(wx.Brush(self.color))
        dc.SetPen(wx.Pen(self.color))
        # main body
        dc.DrawRoundedRectangle(ix, draw_y, self.w, draw_h, 4)

        # eye (position moves slightly with tilt)
        eye_x = ix + int(self.w * 0.58) + int(tilt * 4)
        eye_y = draw_y + int(draw_h * 0.3) - int(tilt * 2)
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0)))
        dc.DrawCircle(eye_x, eye_y, max(1, int(draw_h // 8)))
        # eye shine (highlight)
        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))
        dc.DrawCircle(eye_x + 1, eye_y - 1, max(1, int(draw_h // 16)))

        # beak as a small triangle that tilts
        beak_dx = int(6 + tilt * 6)
        beak = [(ix + self.w, draw_y + draw_h // 2), (ix + self.w + beak_dx, draw_y + draw_h // 2 - 4),
                (ix + self.w + beak_dx, draw_y + draw_h // 2 + 4)]
        dc.SetBrush(wx.Brush(wx.Colour(255, 180, 40)))
        dc.SetPen(wx.Pen(wx.Colour(200, 120, 20)))
        dc.DrawPolygon(beak)

        # wing: simple polygon that 'flaps' by using bird_frame attribute
        wing_offset = getattr(self, 'wing_offset', 0)
        wing = [(ix + int(self.w * 0.2), draw_y + int(draw_h * 0.5)),
                (ix + int(self.w * 0.4) + wing_offset, draw_y + int(draw_h * 0.2)),
                (ix + int(self.w * 0.6) + wing_offset, draw_y + int(draw_h * 0.6))]
        dc.SetBrush(wx.Brush(wx.Colour(230, 160, 40)))
        dc.SetPen(wx.Pen(wx.Colour(200, 120, 20)))
        dc.DrawPolygon(wing)

        # tail feathers
        tail_x = ix - 4
        tail = [(tail_x, draw_y + int(draw_h * 0.3)),
                (tail_x - 8, draw_y),
                (tail_x - 6, draw_y + draw_h)]
        dc.SetBrush(wx.Brush(wx.Colour(200, 140, 30)))
        dc.SetPen(wx.Pen(wx.Colour(150, 100, 20)))
        dc.DrawPolygon(tail)

    def intersects(self, other):
        return not (self.x + self.w < other.x or self.x > other.x + other.w or
                    self.y + self.h < other.y or self.y > other.y + other.h)


class Particle:
    """Simple particle for visual effects (explosions, impacts)."""

    def __init__(self, x, y, vx, vy, color, lifetime=0.6):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.lifetime = float(lifetime)
        self.age = 0.0
        self.size = 4

    def update(self, dt):
        """Move particle and return True if still alive."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt
        return self.age < self.lifetime

    def draw(self, dc):
        """Draw particle with alpha fade."""
        if self.age >= self.lifetime:
            return
        alpha = int(255 * (1.0 - self.age / self.lifetime))
        try:
            c = wx.Colour(self.color.Red(), self.color.Green(), self.color.Blue(), alpha)
            dc.SetBrush(wx.Brush(c))
            dc.SetPen(wx.Pen(c))
        except Exception:
            dc.SetBrush(wx.Brush(self.color))
            dc.SetPen(wx.Pen(self.color))
        dc.DrawCircle(int(self.x), int(self.y), self.size)


class GamePanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        assets = os.path.join(os.path.dirname(__file__), 'assets')

        # load bitmaps if available; note sizes chosen to fit rectangle defaults
        self.bird_bmps = []
        for i in range(3):
            bmp = load_bitmap(os.path.join(assets, f'bird_{i}.png'), 34, 24)
            self.bird_bmps.append(bmp)
        # Fallback: if no bird images, fill with None
        if not any(self.bird_bmps):
            self.bird_bmps = [None] * 3
        self.snake_bmp = load_bitmap(os.path.join(assets, 'snake.png'), 48, 32)
        self.eagle_bmp = load_bitmap(os.path.join(assets, 'eagle.png'), 52, 36)
        self.crocodile_bmp = load_bitmap(os.path.join(assets, 'crocodile.png'), 56, 28)
        self.owl_bmp = load_bitmap(os.path.join(assets, 'owl.png'), 44, 40)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_SET_FOCUS, lambda evt: self.SetFocus())
        self.SetFocus()

        self.last_time = time.time()
        self.dt = 0.0

        # Character selection: 'bird' or 'snake'
        self.current_character = 'bird'

        bird_bmp = next((b for b in self.bird_bmps if b), None)
        # If no bitmap, use color fallback
        bird_color = wx.Colour(255, 200, 0)
        self.bird = Sprite(60, WINDOW_H // 2, 34, 24, color=bird_color, bmp=bird_bmp)
        self.bird_frame = 0
        self.bird_anim_timer = 0.0

        # Snake character (alternative player)
        snake_color = wx.Colour(50, 180, 80)
        self.snake = Sprite(60, WINDOW_H // 2, 40, 20, color=snake_color, bmp=None)
        self.snake.character_type = 'snake'
        self.snake.snake_segments = 3
        self.snake_frame = 0
        self.snake_anim_timer = 0.0

        # Select active player
        self.player = self.bird

        self.gravity = 900.0
        self.flap_strength = -320.0
        self.bullets = []
        self.enemies = []
        self.particles = []
        self.spawn_timer = 0.0
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.keys = set()
        self.running = True
        self.paused = False
        self.last_shot = -10.0
        self.last_special = -10.0  # cooldown for special attacks
        self.special_cooldown = 3.0  # 3 second cooldown
        self.timer.Start(16)

        # difficulty and progression
        # discrete difficulty presets (name, base multiplier, spawn rate multiplier, enemy speed multiplier, gravity multiplier)
        self.difficulty_presets = [
            {'name': 'Easy', 'mult': 0.8, 'spawn_rate': 0.8, 'enemy_speed': 0.85, 'gravity': 0.9},
            {'name': 'Normal', 'mult': 1.0, 'spawn_rate': 1.0, 'enemy_speed': 1.0, 'gravity': 1.0},
            {'name': 'Hard', 'mult': 1.2, 'spawn_rate': 1.2, 'enemy_speed': 1.15, 'gravity': 1.05},
            {'name': 'Insane', 'mult': 1.5, 'spawn_rate': 1.5, 'enemy_speed': 1.4, 'gravity': 1.1},
        ]
        self.difficulty_index = 1  # start at Normal
        self.difficulty = self.difficulty_presets[self.difficulty_index]['mult']
        self.high_score = self.load_high_score()
        self.camera_shake = 0.0  # camera shake timer

        # health/shield system
        self.health = 1  # one-hit death currently
        self.shield = False
        self.shield_timer = 0.0

        # clouds: list of dicts {x, y, w, h, vx, alpha}
        self.clouds = []
        for i in range(6):
            cw = random.randint(80, 180)
            ch = random.randint(30, 60)
            cx = random.randint(0, WINDOW_W)
            cy = random.randint(30, WINDOW_H // 2)
            cvx = random.uniform(-10.0, -40.0)
            ca = random.randint(140, 255)
            self.clouds.append({'x': float(cx), 'y': float(cy), 'w': cw, 'h': ch, 'vx': cvx, 'a': ca})

        # background clouds (slower, larger, more distant)
        self.bg_clouds = []
        for i in range(3):
            cw = random.randint(150, 280)
            ch = random.randint(50, 100)
            cx = random.randint(0, WINDOW_W)
            cy = random.randint(10, WINDOW_H // 3)
            cvx = random.uniform(-2.0, -10.0)
            ca = random.randint(80, 140)
            self.bg_clouds.append({'x': float(cx), 'y': float(cy), 'w': cw, 'h': ch, 'vx': cvx, 'a': ca})

        # Pre-render a smooth sky gradient to a bitmap to avoid per-frame banding seams
        try:
            self.sky_bmp = wx.Bitmap(WINDOW_W, WINDOW_H)
            mdc = wx.MemoryDC(self.sky_bmp)
            top = wx.Colour(135, 206, 250)
            bot = wx.Colour(60, 150, 210)
            for y in range(WINDOW_H):
                t = y / float(WINDOW_H - 1)
                r = int(top.Red() * (1 - t) + bot.Red() * t)
                g = int(top.Green() * (1 - t) + bot.Green() * t)
                b = int(top.Blue() * (1 - t) + bot.Blue() * t)
                mdc.SetPen(wx.Pen(wx.Colour(r, g, b)))
                mdc.DrawLine(0, y, WINDOW_W, y)
            mdc.SelectObject(wx.NullBitmap)
        except Exception:
            self.sky_bmp = None

        # Theme and dynamic background modes
        # Sequence of theme changes: at score thresholds switch theme and increase difficulty
        self.theme_sequence = [('rainy', 500), ('sunny', 1500)]
        self.theme_stage = 0
        self.theme = 'sunny'
        # theme difficulty multipliers
        self.theme_spawn_boost = 1.0
        self.theme_enemy_speed_boost = 1.0
        # raindrops used in rainy theme
        self.raindrops = []
        # generate initial sky for current theme (sunny)
        try:
            # regenerate sky to ensure theme can modify it later
            pass
        except Exception:
            pass

    def on_key_down(self, event):
        key = event.GetKeyCode()
        self.keys.add(key)
        if key == wx.WXK_SPACE:
            self.player.vy = self.flap_strength
            self.play_sound('flap')
        elif key in (ord('P'), ord('p')):
            self.paused = not self.paused
        elif key in (ord('R'), ord('r')):
            self.reset()
        elif key == wx.WXK_CONTROL or key == ord('Z'):
            self.try_shoot()
        elif key in (ord('C'), ord('c')):
            # Toggle character
            self.toggle_character()
        elif key in (ord('X'), ord('x')):
            # Special attack
            self.try_special_attack()
        elif key in (ord('D'), ord('d')):
            # cycle difficulty presets
            self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_presets)
            preset = self.difficulty_presets[self.difficulty_index]
            self.difficulty = preset['mult']
            # small feedback
            self.play_sound('special')
        elif key == wx.WXK_ESCAPE:
            wx.GetApp().Exit()

    def on_key_up(self, event):
        key = event.GetKeyCode()
        if key in self.keys:
            self.keys.remove(key)

    def try_shoot(self):
        now = time.time()
        if now - self.last_shot < SHOOT_COOLDOWN:
            return
        if len(self.bullets) >= MAX_BULLETS:
            return
        self.shoot()
        self.last_shot = now

    def shoot(self):
        """Fire weapon based on current character."""
        if self.current_character == 'bird':
            self.shoot_bird()
        else:
            self.shoot_snake()
        self.play_sound('shoot')

    def shoot_bird(self):
        """Bird fires a single straight red projectile."""
        bx = self.bird.x + self.bird.w
        by = self.bird.y + self.bird.h // 2 - 4
        bullet = Sprite(bx, by, 8, 8, vx=420, color=wx.Colour(255, 50, 50))
        bullet.bullet_type = 'normal'
        self.bullets.append(bullet)

    def shoot_snake(self):
        """Snake fires a cone of 3 venom pellets (green) at different angles."""
        bx = self.snake.x + self.snake.w
        by = self.snake.y + self.snake.h // 2

        # Cone spread: center, up, down
        angles = [0, -0.3, 0.3]  # radians (straight, up-angled, down-angled)

        for angle in angles:
            # Create velocity components
            speed = 380
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)

            # Create venom pellet (slightly smaller, green)
            pellet = Sprite(bx, by, 6, 6, vx=vx, vy=vy, color=wx.Colour(100, 220, 80))
            pellet.bullet_type = 'venom'
            pellet.lifetime = 3.0  # venom pellets disappear after 3 seconds
            pellet.age = 0.0
            self.bullets.append(pellet)

    def try_special_attack(self):
        """Attempt to use character's special attack (cooldown-based)."""
        now = time.time()
        if now - self.last_special < self.special_cooldown:
            return
        self.special_attack()
        self.last_special = now

    def special_attack(self):
        """Character-specific special attack."""
        if self.current_character == 'bird':
            self.special_bird_attack()
        else:
            self.special_snake_attack()
        self.play_sound('special')
        self.trigger_shake(6.0)

    def special_bird_attack(self):
        """Bird: Rapid spread of 5 bullets in a fan pattern."""
        bx = self.bird.x + self.bird.w
        by = self.bird.y + self.bird.h // 2

        # Fan pattern: spread across 3 angles
        angles = [-0.4, -0.2, 0, 0.2, 0.4]
        for angle in angles:
            speed = 450
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)

            bullet = Sprite(bx, by, 8, 8, vx=vx, vy=vy, color=wx.Colour(255, 100, 50))
            bullet.bullet_type = 'special'
            self.bullets.append(bullet)

    def special_snake_attack(self):
        """Snake: Venom cloud explosion - creates ring of projectiles around snake."""
        cx = self.snake.x + self.snake.w // 2
        cy = self.snake.y + self.snake.h // 2

        # Create 8 venom projectiles in a circle
        num_pellets = 8
        for i in range(num_pellets):
            angle = (2 * math.pi * i) / num_pellets
            speed = 250
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)

            pellet = Sprite(cx, cy, 7, 7, vx=vx, vy=vy, color=wx.Colour(150, 255, 100))
            pellet.bullet_type = 'special_venom'
            pellet.lifetime = 2.0
            pellet.age = 0.0
            self.bullets.append(pellet)

    def spawn_enemy(self):
        t = random.random()
        preset_speed = self.difficulty_presets[self.difficulty_index].get('enemy_speed', 1.0)
        speed_factor = (1.0 + (self.difficulty - 1.0) * 0.3) * preset_speed * self.theme_enemy_speed_boost

        if t < 0.25:
            # Snake (ground level)
            h = random.randint(20, 36)
            y = WINDOW_H - 60 - h
            bmp = self.snake_bmp
            enemy = Sprite(WINDOW_W, y, 48, h, vx=-(150 + random.random() * 40) * speed_factor,
                           color=wx.Colour(10, 150, 20), bmp=bmp)
            enemy.bob_amp = random.uniform(2.0, 6.0)
            enemy.bob_speed = random.uniform(1.0, 2.0)
            enemy.enemy_type = 'snake'
        elif t < 0.50:
            # Eagle (air, fast)
            h = random.randint(28, 44)
            y = random.randint(20, WINDOW_H - 160)
            bmp = self.eagle_bmp
            enemy = Sprite(WINDOW_W, y, 52, h, vx=-(200 + random.random() * 80) * speed_factor,
                           color=wx.Colour(120, 80, 40), bmp=bmp)
            enemy.bob_amp = random.uniform(6.0, 14.0)
            enemy.bob_speed = random.uniform(0.8, 1.6)
            enemy.enemy_type = 'eagle'
        elif t < 0.75:
            # Crocodile (ground, slower, wider)
            h = random.randint(22, 32)
            y = WINDOW_H - 60 - h
            bmp = self.crocodile_bmp
            enemy = Sprite(WINDOW_W, y, 56, h, vx=-(100 + random.random() * 30) * speed_factor,
                           color=wx.Colour(40, 120, 50), bmp=bmp)
            enemy.bob_amp = random.uniform(1.0, 3.0)
            enemy.bob_speed = random.uniform(0.6, 1.2)
            enemy.enemy_type = 'crocodile'
        else:
            # Owl (air, medium speed, weaves)
            h = random.randint(30, 42)
            y = random.randint(40, WINDOW_H - 140)
            bmp = self.owl_bmp
            enemy = Sprite(WINDOW_W, y, 44, h, vx=-(120 + random.random() * 50) * speed_factor,
                           color=wx.Colour(80, 60, 40), bmp=bmp)
            enemy.bob_amp = random.uniform(8.0, 16.0)
            enemy.bob_speed = random.uniform(1.5, 2.5)
            enemy.enemy_type = 'owl'
        self.enemies.append(enemy)

    def reset(self):
        self.bullets.clear()
        self.enemies.clear()
        self.particles.clear()
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.bird.x = 60
        self.bird.y = WINDOW_H // 2
        self.bird.vx = 0
        self.bird.vy = 0
        self.snake.x = 60
        self.snake.y = WINDOW_H // 2
        self.snake.vx = 0
        self.snake.vy = 0
        self.running = True
        self.paused = False
        self.camera_shake = 0.0
        self.difficulty = 1.0

    def spawn_particles(self, x, y, color, count=8):
        """Spawn particle burst on impact."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 200)
            vx = speed * math.cos(angle)
            vy = speed * math.sin(angle)
            # random particle color variation
            if random.random() < 0.3:
                # sparkle particles (brighter)
                p_color = wx.Colour(255, 255, 200)
            else:
                p_color = color
            p = Particle(x, y, vx, vy, p_color, lifetime=0.5)
            self.particles.append(p)

    def load_high_score(self):
        """Load high score from file if it exists."""
        try:
            with open('highscore.txt', 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        """Save current high score to file."""
        try:
            with open('highscore.txt', 'w') as f:
                f.write(str(self.high_score))
        except Exception:
            pass

    def trigger_shake(self, intensity=5.0):
        """Trigger camera shake for impact feedback."""
        self.camera_shake = intensity

    def play_sound(self, sound_name):
        """Placeholder for sound effects."""
        # TODO: Integrate pygame.mixer or winsound for actual audio
        pass

    def toggle_character(self):
        """Switch between bird and snake characters."""
        if self.current_character == 'bird':
            self.current_character = 'snake'
            self.player = self.snake
        else:
            self.current_character = 'bird'
            self.player = self.bird
        # Reset player position and velocity
        self.player.x = 60
        self.player.y = WINDOW_H // 2
        self.player.vy = 0

    def on_timer(self, _):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        if dt > 0.05:
            dt = 0.05
        self.dt = dt

        if not self.running or self.paused:
            self.Refresh()
            return
        # physics (gravity scaled by difficulty preset)
        gravity_scale = self.difficulty_presets[self.difficulty_index].get('gravity', 1.0)
        self.player.vy += self.gravity * gravity_scale * dt
        self.player.y += self.player.vy * dt
        if self.player.y < 0:
            self.player.y = 0
            self.player.vy = 0
        if self.player.y + self.player.h > WINDOW_H - 60:
            self.player.y = WINDOW_H - 60 - self.player.h
            self.player.vy = 0

        # update bullets
        for b in list(self.bullets):
            b.update(dt)
            # Check venom/special pellet lifetime
            bullet_type = getattr(b, 'bullet_type', None)
            if bullet_type in ('venom', 'special_venom'):
                b.age = getattr(b, 'age', 0) + dt
                if b.age >= getattr(b, 'lifetime', 3.0):
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    continue
            if b.x > WINDOW_W:
                try:
                    self.bullets.remove(b)
                except ValueError:
                    pass

        # spawn enemies (spawn rate affected by difficulty preset)
        self.spawn_timer += dt
        base_spawn = max(0.6, 1.2 - (self.score / 1000.0))
        spawn_rate_mul = self.difficulty_presets[self.difficulty_index].get('spawn_rate', 1.0) * self.theme_spawn_boost
        spawn_interval = max(0.18, base_spawn / spawn_rate_mul)
        if self.spawn_timer > spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_enemy()

        # update difficulty based on score
        self.difficulty = 1.0 + (self.score / 5000.0)

        # check theme transitions based on score thresholds
        if self.theme_stage < len(self.theme_sequence):
            next_theme, threshold = self.theme_sequence[self.theme_stage]
            if self.score >= threshold:
                self.theme = next_theme
                # apply simple boosts depending on theme
                if self.theme == 'rainy':
                    self.theme_spawn_boost = 1.25
                    self.theme_enemy_speed_boost = 1.15
                    # spawn raindrops
                    for _ in range(120):
                        rx = random.randint(0, WINDOW_W)
                        ry = random.randint(-WINDOW_H, 0)
                        rv = random.uniform(200, 400)
                        self.raindrops.append({'x': float(rx), 'y': float(ry), 'v': rv})
                elif self.theme == 'sunny':
                    self.theme_spawn_boost = 1.0
                    self.theme_enemy_speed_boost = 1.0
                    self.raindrops.clear()
                self.theme_stage += 1

        # update enemies and collisions
        for e in list(self.enemies):
            # advance bobbing phase
            if e.bob_amp and e.bob_speed:
                e.bob_phase += e.bob_speed * dt
                e.y = e.base_y + math.sin(e.bob_phase) * e.bob_amp
            e.update(dt)
            if e.x + e.w < 0:
                try:
                    self.enemies.remove(e)
                except ValueError:
                    pass
                continue
            if e.intersects(self.player):
                self.running = False
                self.combo = 0
                self.trigger_shake(8.0)
                self.play_sound('hit')
            for b in list(self.bullets):
                if e.intersects(b):
                    try:
                        self.enemies.remove(e)
                    except ValueError:
                        pass
                    try:
                        self.bullets.remove(b)
                    except ValueError:
                        pass
                    # Score with combo multiplier
                    self.combo += 1
                    self.combo_timer = 3.0  # reset combo timer
                    base_score = 100
                    multiplier = 1 + (self.combo - 1) * 0.2  # 1.0, 1.2, 1.4, etc.
                    self.score += int(base_score * multiplier)
                    # Spawn particles at enemy center
                    ex = e.x + e.w // 2
                    ey = e.y + e.h // 2
                    self.spawn_particles(ex, ey, e.color, count=6)
                    self.trigger_shake(3.0)
                    self.play_sound('hit')

        # bird animation frame (if bird is active player)
        if self.current_character == 'bird':
            self.bird_anim_timer += dt
            if self.bird_anim_timer > 0.12 and any(self.bird_bmps):
                self.bird_anim_timer = 0.0
                self.bird_frame = (self.bird_frame + 1) % len(self.bird_bmps)
                bmp = self.bird_bmps[self.bird_frame]
                if bmp:
                    self.bird.bmp = bmp

            # Bird visual effects (tilt, squash, wing) independent of bitmap presence
            # Tilt: based on vertical velocity (upwards tilt when vy < 0)
            max_tilt = 1.0
            tilt = max(-max_tilt, min(max_tilt, -self.bird.vy / 300.0))
            # Squash: briefly squash when flapping (using bird_anim_timer proximity)
            flap_phase = (self.bird_anim_timer % 0.12) / 0.12
            squash = 1.0 - max(0.0, (0.12 - min(self.bird_anim_timer, 0.12)) / 0.12) * 0.12
            # wing offset based on animation frame (if no bitmap, still show wing motion)
            wing_offset = 0
            if not any(self.bird_bmps):
                # emulate wing motion from bird_frame
                wing_offset = -6 if (self.bird_frame % 2 == 0) else 4

            self.bird.tilt = tilt
            self.bird.squash = squash
            self.bird.wing_offset = wing_offset
        else:
            # Snake animation (wavy motion)
            self.snake_anim_timer += dt
            if self.snake_anim_timer > 0.15:
                self.snake_anim_timer = 0.0
                self.snake_frame = (self.snake_frame + 1) % 4

            # Snake squash and tilt
            squash = 1.0 - abs(math.sin(self.snake_anim_timer * math.pi)) * 0.1
            tilt = math.sin(self.snake_anim_timer * math.pi * 2) * 0.5
            self.snake.squash = squash
            self.snake.tilt = tilt

        # update clouds
        for c in self.clouds:
            c['x'] += c['vx'] * dt
            if c['x'] + c['w'] < -20:
                # wrap to right
                c['x'] = WINDOW_W + random.randint(10, 120)
                c['y'] = random.randint(20, WINDOW_H // 2)
                c['w'] = random.randint(80, 180)
                c['h'] = random.randint(30, 60)

        # update background clouds
        for c in self.bg_clouds:
            c['x'] += c['vx'] * dt
            if c['x'] + c['w'] < -20:
                c['x'] = WINDOW_W + random.randint(20, 200)
                c['y'] = random.randint(10, WINDOW_H // 3)
                c['w'] = random.randint(150, 280)
                c['h'] = random.randint(50, 100)

        # update combo timer (reset combo if too long without a hit)
        self.combo_timer -= dt
        if self.combo_timer <= 0:
            self.combo = 0

        # update particles
        for p in list(self.particles):
            if not p.update(dt):
                try:
                    self.particles.remove(p)
                except ValueError:
                    pass

        # update camera shake
        self.camera_shake = max(0, self.camera_shake - dt * 15)

        # update raindrops when in rainy theme
        if self.theme == 'rainy':
            for rd in list(self.raindrops):
                rd['y'] += rd['v'] * dt
                if rd['y'] > WINDOW_H:
                    # recycle raindrop to top
                    rd['y'] = random.uniform(-WINDOW_H * 0.5, -5)
                    rd['x'] = random.uniform(0, WINDOW_W)

        self.Refresh()

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.Clear()

        # compute shake offset
        shake_x = int(random.uniform(-self.camera_shake, self.camera_shake)) if self.camera_shake > 0 else 0
        shake_y = int(random.uniform(-self.camera_shake, self.camera_shake)) if self.camera_shake > 0 else 0

        # sky gradient (use cached bitmap to avoid banding seams)
        if getattr(self, 'sky_bmp', None):
            try:
                dc.DrawBitmap(self.sky_bmp, 0, 0)
            except Exception:
                dc.SetBrush(wx.Brush(wx.Colour(135, 206, 250)))
                dc.DrawRectangle(0, 0, WINDOW_W, WINDOW_H)
        else:
            try:
                # fallback: create several horizontal bands
                top = wx.Colour(135, 206, 250)  # light sky
                bot = wx.Colour(60, 150, 210)
                band_count = 12
                for i in range(band_count):
                    t = i / (band_count - 1)
                    r = int(top.Red() * (1 - t) + bot.Red() * t)
                    g = int(top.Green() * (1 - t) + bot.Green() * t)
                    b = int(top.Blue() * (1 - t) + bot.Blue() * t)
                    dc.SetBrush(wx.Brush(wx.Colour(r, g, b)))
                    y0 = int(i * WINDOW_H / band_count)
                    y1 = int((i + 1) * WINDOW_H / band_count)
                    dc.DrawRectangle(0, y0, WINDOW_W, y1 - y0)
            except Exception:
                dc.SetBrush(wx.Brush(wx.Colour(135, 206, 250)))
                dc.DrawRectangle(0, 0, WINDOW_W, WINDOW_H)

        # draw background clouds (distant, dimmer)
        for c in self.bg_clouds:
            cx = int(c['x'])
            cy = int(c['y'])
            cw = int(c['w'])
            ch = int(c['h'])
            ca = int(c.get('a', 100))
            try:
                cloud_brush = wx.Brush(wx.Colour(200, 220, 255, ca))
                dc.SetBrush(cloud_brush)
                dc.SetPen(wx.Pen(wx.Colour(200, 220, 255, ca)))
                dc.DrawEllipse(cx, cy, int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.25), cy - int(ch * 0.2), int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.45), cy, int(cw * 0.5), ch)
            except Exception:
                dc.SetBrush(wx.Brush(wx.Colour(200, 220, 255)))
                dc.SetPen(wx.Pen(wx.Colour(200, 220, 255)))
                dc.DrawEllipse(cx, cy, int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.25), cy - int(ch * 0.2), int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.45), cy, int(cw * 0.5), ch)

        # softer ground: layered foreground with a slight gradient and small texture
        try:
            grad_steps = 6
            top_col = wx.Colour(40, 110, 55)
            bot_col = wx.Colour(18, 75, 30)
            band_h = 48 // grad_steps
            for i in range(grad_steps):
                t = i / max(1, grad_steps - 1)
                r = int(top_col.Red() * (1 - t) + bot_col.Red() * t)
                g = int(top_col.Green() * (1 - t) + bot_col.Green() * t)
                b = int(top_col.Blue() * (1 - t) + bot_col.Blue() * t)
                dc.SetBrush(wx.Brush(wx.Colour(r, g, b)))
                dc.SetPen(wx.Pen(wx.Colour(r, g, b)))
                y = WINDOW_H - 48 + i * band_h
                dc.DrawRectangle(0, y, WINDOW_W, band_h + 1)
        except Exception:
            dc.SetBrush(wx.Brush(wx.Colour(18, 75, 30)))
            dc.DrawRectangle(0, WINDOW_H - 48, WINDOW_W, 48)

        # small foreground texture: scattered darker/ lighter dots to avoid a hard line
        for x in range(0, WINDOW_W, 24):
            h = random.randint(2, 6)
            col = wx.Colour(20 + random.randint(0, 20), 60 + random.randint(0, 40), 18 + random.randint(0, 20))
            dc.SetBrush(wx.Brush(col))
            dc.SetPen(wx.Pen(col))
            dc.DrawEllipse(x + (random.randint(-6, 6)), WINDOW_H - 12 - random.randint(0, 6), 8, h)

        # draw player (bird or snake)
        self.player.draw(dc)

        # rainy overlay / raindrops
        if self.theme == 'rainy' and self.raindrops:
            try:
                # subtle dark tint already applied earlier; draw raindrops as thin lines
                dc.SetPen(wx.Pen(wx.Colour(180, 200, 230, 180)))
                for rd in self.raindrops:
                    x = int(rd['x'])
                    y = int(rd['y'])
                    dc.DrawLine(x, y, x + 2, y + 10)
            except Exception:
                pass

        # draw bullets
        for b in self.bullets:
            b.draw(dc)

        # draw enemies
        for e in self.enemies:
            e.draw(dc)

        # draw particles
        for p in self.particles:
            p.draw(dc)

        # draw clouds (behind everything else?) draw before foreground to create parallax
        # small clouds drawn slightly above
        for c in self.clouds:
            cx = int(c['x'])
            cy = int(c['y'])
            cw = int(c['w'])
            ch = int(c['h'])
            ca = int(c.get('a', 220))
            try:
                cloud_brush = wx.Brush(wx.Colour(255, 255, 255, ca))
                dc.SetBrush(cloud_brush)
                dc.SetPen(wx.Pen(wx.Colour(255, 255, 255, ca)))
                # draw a few overlapping ellipses to look like a cloud
                dc.DrawEllipse(cx, cy, int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.25), cy - int(ch * 0.2), int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.45), cy, int(cw * 0.5), ch)
            except Exception:
                # fallback: solid white ellipses without alpha
                dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                dc.SetPen(wx.Pen(wx.Colour(255, 255, 255)))
                dc.DrawEllipse(cx, cy, int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.25), cy - int(ch * 0.2), int(cw * 0.6), ch)
                dc.DrawEllipse(cx + int(cw * 0.45), cy, int(cw * 0.5), ch)

        # HUD
        dc.SetTextForeground(wx.BLACK)
        dc.SetFont(wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dc.DrawText(f"Score: {self.score}", 10, 10)
        dc.DrawText(f"High: {self.high_score}", 10, 28)
        char_text = "🐦 Bird" if self.current_character == 'bird' else "🐍 Snake"
        dc.DrawText(f"Char: {char_text}", 10, 46)
        dc.DrawText(f"Theme: {self.theme}", 10, 64)

        if self.combo > 0:
            dc.SetTextForeground(wx.Colour(255, 200, 0))
            dc.DrawText(f"Combo: {self.combo}x", WINDOW_W - 180, 28)
            dc.SetTextForeground(wx.BLACK)
        dc.DrawText(f"Difficulty: {self.difficulty:.1f}x", WINDOW_W - 180, 10)

        # Show weapon type and ammo (moved down because Theme occupies y=64)
        if self.current_character == 'bird':
            dc.DrawText("Weapon: Bullets", 10, 82)
            dc.DrawText(f"Ammo: {len(self.bullets)}/{MAX_BULLETS}", 10, 100)
        else:
            dc.DrawText("Weapon: Venom Cone", 10, 82)
            dc.DrawText(f"Projectiles: {len(self.bullets)}", 10, 100)

        # Show special attack cooldown
        now = time.time()
        special_cooldown_remaining = self.special_cooldown - (now - self.last_special)
        if special_cooldown_remaining <= 0:
            dc.SetTextForeground(wx.Colour(255, 200, 0))
            dc.DrawText("Special: READY!", WINDOW_W - 200, 46)
        else:
            dc.SetTextForeground(wx.Colour(200, 100, 0))
            dc.DrawText(f"Special: {special_cooldown_remaining:.1f}s", WINDOW_W - 200, 46)

        dc.SetTextForeground(wx.BLACK)
        dc.DrawText("P: pause  R: restart  C: char  Space: flap  Ctrl/Z: shoot  X: special", 10, 118)

        if self.paused:
            dc.DrawText("Paused", WINDOW_W // 2 - 30, WINDOW_H // 2)
        if not self.running:
            dc.DrawText("Game Over - Press R to restart", 80, WINDOW_H // 2) 
class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Flappy Jungle Shooter", size=(WINDOW_W, WINDOW_H))
        self.panel = GamePanel(self)
        self.Centre()
def main():
    app = wx.App(False)
    frame = MainFrame()
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
