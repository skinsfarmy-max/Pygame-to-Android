import pygame
import math
import random


# ============================================================
# DARK ACID BACKYARD
# One-file pygame top-down survival / base defense
# ============================================================

pygame.init()
pygame.display.set_caption("DARK ACID // LAST YARD")

INFO = pygame.display.Info()
WIDTH = INFO.current_w
HEIGHT = INFO.current_h

if WIDTH < 900:
    WIDTH = 1280
if HEIGHT < 600:
    HEIGHT = 720

SCREEN = pygame.display.set_mode(
    (WIDTH, HEIGHT),
    pygame.FULLSCREEN | pygame.DOUBLEBUF
)

CLOCK = pygame.time.Clock()

# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------

BLACK = (5, 7, 5)
NIGHT = (9, 13, 9)

GRASS = (31, 51, 28)
GRASS_DARK = (21, 37, 20)
GRASS_LIGHT = (45, 68, 37)

DIRT = (57, 43, 29)
DIRT_LIGHT = (75, 54, 35)

WOOD = (79, 53, 34)
WOOD_DARK = (48, 34, 24)
WOOD_LIGHT = (105, 71, 44)

METAL = (68, 73, 67)
METAL_DARK = (35, 39, 35)

WHITE = (225, 230, 217)
GREY = (150, 155, 143)

GREEN = (99, 255, 91)
ACID = (137, 255, 44)
PURPLE = (183, 79, 255)

RED = (225, 65, 51)
ORANGE = (240, 156, 48)

BLOOD = (118, 28, 21)

# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------

WORLD_W = 4200
WORLD_H = 3200

FPS = 144

PLAYER_SPEED = 340
PLAYER_RADIUS = 17

BULLET_SPEED = 1100
BULLET_DAMAGE = 34
FIRE_DELAY = 0.105

ZOMBIE_BASE_SPEED = 65

MAX_PARTICLES = 1100

GRID_SIZE = 80

# ------------------------------------------------------------
# FONTS
# ------------------------------------------------------------

FONT_CACHE = {}


def font(size, bold=False):
    key = (size, bold)

    if key not in FONT_CACHE:
        FONT_CACHE[key] = pygame.font.SysFont(
            "consolas",
            size,
            bold=bold
        )

    return FONT_CACHE[key]


# ============================================================
# UTILITY
# ============================================================

def clamp(v, a, b):
    return max(a, min(b, v))


def dist2(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def distance(ax, ay, bx, by):
    return math.sqrt(dist2(ax, ay, bx, by))


def normalize(dx, dy):
    d = math.sqrt(dx * dx + dy * dy)

    if d <= 0.0001:
        return 0.0, 0.0

    return dx / d, dy / d


def world_to_screen(camera, x, y):
    return (
        int(x - camera.x),
        int(y - camera.y)
    )


def screen_to_world(camera, x, y):
    return (
        x + camera.x,
        y + camera.y
    )


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# ============================================================
# CAMERA
# ============================================================

class Camera:

    def __init__(self):
        self.x = 0
        self.y = 0

        self.target_x = 0
        self.target_y = 0

        self.shake = 0
        self.shake_x = 0
        self.shake_y = 0

    def follow(self, x, y, territory):

        self.target_x = x - WIDTH / 2
        self.target_y = y - HEIGHT / 2

        # Camera may only show unlocked territory.
        min_x = territory.left - 180
        max_x = territory.right - WIDTH + 180

        min_y = territory.top - 180
        max_y = territory.bottom - HEIGHT + 180

        if max_x < min_x:
            min_x = max_x = (territory.left + territory.right) / 2 - WIDTH / 2

        if max_y < min_y:
            min_y = max_y = (territory.top + territory.bottom) / 2 - HEIGHT / 2

        self.target_x = clamp(self.target_x, min_x, max_x)
        self.target_y = clamp(self.target_y, min_y, max_y)

    def update(self, dt):

        smoothing = 1.0 - math.pow(0.001, dt)

        self.x += (self.target_x - self.x) * smoothing
        self.y += (self.target_y - self.y) * smoothing

        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 35)

            power = self.shake

            self.shake_x = random.uniform(-power, power)
            self.shake_y = random.uniform(-power, power)
        else:
            self.shake_x = 0
            self.shake_y = 0

    def kick(self, amount):
        self.shake = min(25, self.shake + amount)


# ============================================================
# PARTICLES
# ============================================================

class Particle:

    __slots__ = (
        "x", "y",
        "vx", "vy",
        "life", "max_life",
        "size",
        "color",
        "kind",
        "gravity"
    )

    def __init__(
        self,
        x,
        y,
        vx,
        vy,
        life,
        size,
        color,
        kind="normal",
        gravity=0
    ):

        self.x = x
        self.y = y

        self.vx = vx
        self.vy = vy

        self.life = life
        self.max_life = life

        self.size = size
        self.color = color

        self.kind = kind
        self.gravity = gravity

    def update(self, dt):

        self.life -= dt

        if self.life <= 0:
            return False

        self.vx *= math.pow(0.05, dt)
        self.vy *= math.pow(0.05, dt)

        self.vy += self.gravity * dt

        self.x += self.vx * dt
        self.y += self.vy * dt

        return True

    def draw(self, screen, camera):

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        alpha = clamp(
            self.life / self.max_life,
            0,
            1
        )

        size = max(
            1,
            int(self.size * alpha)
        )

        pygame.draw.circle(
            screen,
            self.color,
            (sx, sy),
            size
        )


# ============================================================
# ACID
# ============================================================

class AcidPool:

    __slots__ = (
        "x",
        "y",
        "radius",
        "points",
        "life"
    )

    def __init__(self, x, y, radius):

        self.x = x
        self.y = y
        self.radius = radius

        self.life = 45.0

        self.points = []

        count = random.randint(12, 19)

        for i in range(count):

            angle = math.pi * 2 * i / count

            r = radius * random.uniform(
                0.65,
                1.12
            )

            self.points.append(
                (
                    math.cos(angle) * r,
                    math.sin(angle) * r
                )
            )

    def contains(self, x, y):

        if self.life <= 0:
            return False

        return dist2(
            self.x,
            self.y,
            x,
            y
        ) <= self.radius * self.radius

    def draw(self, screen, camera):

        pts = []

        for px, py in self.points:

            sx, sy = world_to_screen(
                camera,
                self.x + px,
                self.y + py
            )

            pts.append((sx, sy))

        if len(pts) >= 3:

            pygame.draw.polygon(
                screen,
                (61, 95, 24),
                pts
            )

            inner = []

            for px, py in self.points:

                px *= 0.78
                py *= 0.78

                sx, sy = world_to_screen(
                    camera,
                    self.x + px,
                    self.y + py
                )

                inner.append((sx, sy))

            pygame.draw.polygon(
                screen,
                (89, 143, 27),
                inner
            )

        # acid bubbles
        for i in range(5):

            a = pygame.time.get_ticks() * 0.001

            bx = self.x + math.cos(a * (0.7 + i * 0.1) + i) * self.radius * 0.45
            by = self.y + math.sin(a * (0.9 + i * 0.08) + i * 2) * self.radius * 0.35

            sx, sy = world_to_screen(
                camera,
                bx,
                by
            )

            pygame.draw.circle(
                screen,
                ACID,
                (sx, sy),
                2
            )


# ============================================================
# BULLET
# ============================================================

class Bullet:

    __slots__ = (
        "x",
        "y",
        "vx",
        "vy",
        "life",
        "damage"
    )

    def __init__(self, x, y, vx, vy, damage=BULLET_DAMAGE):

        self.x = x
        self.y = y

        self.vx = vx
        self.vy = vy

        self.life = 1.25
        self.damage = damage

    def update(self, dt):

        self.life -= dt

        if self.life <= 0:
            return False

        self.x += self.vx * dt
        self.y += self.vy * dt

        return True

    def draw(self, screen, camera):

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        dx, dy = normalize(
            self.vx,
            self.vy
        )

        tail_x = sx - dx * 15
        tail_y = sy - dy * 15

        pygame.draw.line(
            screen,
            (245, 246, 205),
            (tail_x, tail_y),
            (sx, sy),
            3
        )

        pygame.draw.circle(
            screen,
            WHITE,
            (sx, sy),
            3
        )


# ============================================================
# POWER NODE
# ============================================================

class PowerNode:

    __slots__ = (
        "id",
        "x",
        "y",
        "kind"
    )

    def __init__(self, node_id, x, y, kind="normal"):

        self.id = node_id
        self.x = x
        self.y = y
        self.kind = kind

    def draw(self, screen, camera, powered=False, selected=False):

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        if powered:
            color = GREEN
        else:
            color = RED

        if selected:

            pygame.draw.circle(
                screen,
                WHITE,
                (sx, sy),
                12,
                2
            )

        pygame.draw.circle(
            screen,
            WOOD_DARK,
            (sx, sy),
            8
        )

        pygame.draw.circle(
            screen,
            color,
            (sx, sy),
            4
        )


# ============================================================
# POWER CABLE
# ============================================================

class PowerCable:

    __slots__ = (
        "a",
        "b",
        "health",
        "broken",
        "repair"
    )

    def __init__(self, a, b):

        self.a = a
        self.b = b

        self.health = 100
        self.broken = False
        self.repair = 0

    def get_points(self):

        return self.a.x, self.a.y, self.b.x, self.b.y

    def distance_to(self, x, y):

        ax, ay = self.a.x, self.a.y
        bx, by = self.b.x, self.b.y

        dx = bx - ax
        dy = by - ay

        length2 = dx * dx + dy * dy

        if length2 <= 0.001:
            return distance(
                x,
                y,
                ax,
                ay
            )

        t = (
            (x - ax) * dx +
            (y - ay) * dy
        ) / length2

        t = clamp(
            t,
            0,
            1
        )

        px = ax + dx * t
        py = ay + dy * t

        return distance(
            x,
            y,
            px,
            py
        )

    def break_cable(self):

        self.broken = True
        self.health = 0

    def repair_step(self, amount):

        if not self.broken:
            return False

        self.repair += amount

        if self.repair >= 100:

            self.repair = 0
            self.health = 100
            self.broken = False

            return True

        return False

    def draw(self, screen, camera):

        ax, ay, bx, by = self.get_points()

        sx1, sy1 = world_to_screen(
            camera,
            ax,
            ay
        )

        sx2, sy2 = world_to_screen(
            camera,
            bx,
            by
        )

        if self.broken:

            pygame.draw.line(
                screen,
                (91, 42, 32),
                (sx1, sy1),
                (sx2, sy2),
                5
            )

            # broken sparks
            mx = (sx1 + sx2) // 2
            my = (sy1 + sy2) // 2

            pygame.draw.circle(
                screen,
                RED,
                (mx, my),
                4
            )

        else:

            pygame.draw.line(
                screen,
                (26, 28, 23),
                (sx1, sy1),
                (sx2, sy2),
                6
            )

            pygame.draw.line(
                screen,
                (74, 83, 65),
                (sx1, sy1),
                (sx2, sy2),
                2
            )


# ============================================================
# POWER GRID
# ============================================================

class PowerGrid:

    def __init__(self):

        self.nodes = []
        self.cables = []

        self.next_id = 0

        self.generator_node = None

        self.powered_ids = set()

    def create_node(
        self,
        x,
        y,
        kind="normal"
    ):

        node = PowerNode(
            self.next_id,
            x,
            y,
            kind
        )

        self.next_id += 1

        self.nodes.append(node)

        if kind == "generator":
            self.generator_node = node

        return node

    def connect(self, a, b):

        if a is b:
            return None

        for cable in self.cables:

            if (
                (cable.a is a and cable.b is b) or
                (cable.a is b and cable.b is a)
            ):
                return cable

        cable = PowerCable(
            a,
            b
        )

        self.cables.append(cable)

        self.recalculate()

        return cable

    def disconnect(self, cable):

        if cable in self.cables:
            self.cables.remove(cable)

        self.recalculate()

    def recalculate(self):

        self.powered_ids.clear()

        if self.generator_node is None:
            return

        queue = [
            self.generator_node
        ]

        self.powered_ids.add(
            self.generator_node.id
        )

        while queue:

            node = queue.pop(0)

            for cable in self.cables:

                if cable.broken:
                    continue

                next_node = None

                if cable.a is node:
                    next_node = cable.b

                elif cable.b is node:
                    next_node = cable.a

                if next_node is not None:

                    if next_node.id not in self.powered_ids:

                        self.powered_ids.add(
                            next_node.id
                        )

                        queue.append(
                            next_node
                        )

    def is_powered(self, node):

        return node is not None and node.id in self.powered_ids

    def nearest_node(self, x, y, radius=42):

        best = None
        best_d = radius * radius

        for node in self.nodes:

            d = dist2(
                x,
                y,
                node.x,
                node.y
            )

            if d < best_d:

                best_d = d
                best = node

        return best

    def nearest_broken_cable(self, x, y, radius=65):

        best = None
        best_d = radius

        for cable in self.cables:

            if not cable.broken:
                continue

            d = cable.distance_to(
                x,
                y
            )

            if d < best_d:

                best_d = d
                best = cable

        return best

    def cable_near(self, x, y, radius=24):

        for cable in self.cables:

            if cable.distance_to(x, y) <= radius:
                return cable

        return None

    def draw(self, screen, camera):

        for cable in self.cables:

            cable.draw(
                screen,
                camera
            )

        for node in self.nodes:

            node.draw(
                screen,
                camera,
                self.is_powered(node)
            )


# ============================================================
# BUILDINGS
# ============================================================

class Building:

    __slots__ = (
        "x",
        "y",
        "node",
        "health",
        "max_health",
        "kind",
        "radius",
        "cost"
    )

    def __init__(
        self,
        x,
        y,
        kind,
        grid,
        cost
    ):

        self.x = x
        self.y = y

        self.kind = kind

        self.radius = 28
        self.health = 100
        self.max_health = 100

        self.cost = cost

        self.node = grid.create_node(
            x,
            y,
            "building"
        )

    def powered(self, grid):

        return grid.is_powered(
            self.node
        )

    def update(self, game, dt):
        pass

    def draw_base(self, screen, camera, game):

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        if self.kind == "turret":

            pygame.draw.rect(
                screen,
                (48, 48, 41),
                (
                    sx - 20,
                    sy - 15,
                    40,
                    30
                )
            )

            pygame.draw.rect(
                screen,
                METAL,
                (
                    sx - 16,
                    sy - 12,
                    32,
                    24
                )
            )

            pygame.draw.circle(
                screen,
                (53, 57, 49),
                (sx, sy),
                13
            )

            pygame.draw.line(
                screen,
                (23, 25, 22),
                (sx, sy),
                (
                    sx + 27,
                    sy - 3
                ),
                8
            )

            pygame.draw.line(
                screen,
                METAL,
                (sx, sy),
                (
                    sx + 27,
                    sy - 3
                ),
                4
            )

        elif self.kind == "spotlight":

            # tripod
            pygame.draw.line(
                screen,
                METAL_DARK,
                (sx, sy + 2),
                (sx - 16, sy + 30),
                4
            )

            pygame.draw.line(
                screen,
                METAL_DARK,
                (sx, sy + 2),
                (sx + 16, sy + 30),
                4
            )

            pygame.draw.line(
                screen,
                METAL_DARK,
                (sx, sy + 2),
                (sx, sy + 30),
                4
            )

            pygame.draw.rect(
                screen,
                METAL,
                (
                    sx - 13,
                    sy - 18,
                    26,
                    20
                )
            )

            pygame.draw.circle(
                screen,
                ACID,
                (sx, sy - 8),
                7
            )

        # power indicator
        if self.powered(game.power_grid):

            pygame.draw.circle(
                screen,
                GREEN,
                (
                    sx + self.radius - 3,
                    sy - self.radius + 3
                ),
                3
            )

        else:

            pygame.draw.circle(
                screen,
                RED,
                (
                    sx + self.radius - 3,
                    sy - self.radius + 3
                ),
                3
            )


class Turret(Building):

    __slots__ = (
        "cooldown",
        "angle"
    )

    def __init__(
        self,
        x,
        y,
        grid
    ):

        super().__init__(
            x,
            y,
            "turret",
            grid,
            150
        )

        self.cooldown = 0
        self.angle = 0

    def update(self, game, dt):

        if not self.powered(game.power_grid):
            return

        self.cooldown -= dt

        best = None
        best_d = 360 * 360

        for zombie in game.zombies:

            d = dist2(
                self.x,
                self.y,
                zombie.x,
                zombie.y
            )

            if d < best_d:

                best_d = d
                best = zombie

        if best is None:
            return

        self.angle = math.atan2(
            best.y - self.y,
            best.x - self.x
        )

        # acid bonus
        fire_rate = 1.0

        if game.on_acid(
            self.x,
            self.y
        ):
            fire_rate = 1.5

        if self.cooldown <= 0:

            self.cooldown = 0.42 / fire_rate

            vx = math.cos(self.angle) * BULLET_SPEED
            vy = math.sin(self.angle) * BULLET_SPEED

            game.bullets.append(
                Bullet(
                    self.x,
                    self.y,
                    vx,
                    vy
                )
            )

            game.camera.kick(1)

    def draw(self, screen, camera, game):

        self.draw_base(
            screen,
            camera,
            game
        )

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        # Visible effective firing radius.
        pygame.draw.circle(
            screen,
            (72, 92, 55),
            (sx, sy),
            360,
            1
        )

        if not self.powered(game.power_grid):
            return

        ex = sx + math.cos(self.angle) * 34
        ey = sy + math.sin(self.angle) * 34

        pygame.draw.line(
            screen,
            (31, 33, 29),
            (sx, sy),
            (ex, ey),
            8
        )

        pygame.draw.line(
            screen,
            METAL,
            (sx, sy),
            (ex, ey),
            4
        )


class Spotlight(Building):

    __slots__ = (
        "angle",
        "sweep"
    )

    def __init__(
        self,
        x,
        y,
        grid
    ):

        super().__init__(
            x,
            y,
            "spotlight",
            grid,
            110
        )

        self.angle = 0
        self.sweep = random.uniform(
            0,
            math.pi * 2
        )

    def update(self, game, dt):

        if not self.powered(game.power_grid):
            return

        self.sweep += dt * 0.35

        self.angle = math.sin(
            self.sweep
        ) * 0.65

    def draw(self, screen, camera, game):

        self.draw_base(
            screen,
            camera,
            game
        )

        if not self.powered(game.power_grid):
            return

        # Actual world light beam.
        # It is not a screen overlay.

        length = 430
        spread = 0.28

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        a = self.angle

        p1 = (
            sx + math.cos(a - spread) * length,
            sy + math.sin(a - spread) * length
        )

        p2 = (
            sx + math.cos(a + spread) * length,
            sy + math.sin(a + spread) * length
        )

        pygame.draw.polygon(
            screen,
            (43, 70, 32),
            [
                (sx, sy),
                p1,
                p2
            ]
        )


# ============================================================
# PLAYER
# ============================================================

class Player:

    def __init__(self, x, y):

        self.x = x
        self.y = y

        self.health = 100
        self.max_health = 100

        self.angle = 0

        self.fire_timer = 0

        self.walk_time = 0

        self.invulnerable = 0

        # XP is a spendable currency now — no levels or automatic weapon scaling.
        self.xp = 0
        self.weapon_damage = BULLET_DAMAGE
        self.weapon_fire_delay = FIRE_DELAY

    def add_xp(self, amount, game):
        self.xp += amount

    def upgrade_weapon_damage(self, game):
        cost = 80 + max(0, (self.weapon_damage - BULLET_DAMAGE) // 10) * 45
        if self.xp < cost:
            game.message(f"DAMAGE NEEDS {cost} XP")
            return
        self.xp -= cost
        self.weapon_damage += 10
        game.message(f"DAMAGE +10 — {self.weapon_damage} DMG")

    def upgrade_fire_rate(self, game):
        upgrades = max(0, int(round((FIRE_DELAY - self.weapon_fire_delay) / 0.012)))
        cost = 100 + upgrades * 55
        if self.xp < cost:
            game.message(f"FIRE RATE NEEDS {cost} XP")
            return
        self.xp -= cost
        self.weapon_fire_delay = max(0.045, self.weapon_fire_delay - 0.012)
        game.message("FIRE RATE UPGRADED")

    def upgrade_health(self, game):
        upgrades = max(0, (self.max_health - 100) // 15)
        cost = 120 + upgrades * 60
        if self.xp < cost:
            game.message(f"MAX HP NEEDS {cost} XP")
            return
        self.xp -= cost
        self.max_health += 15
        self.health = self.max_health
        game.message(f"MAX HEALTH +15 — {self.max_health}")

    def update(self, game, dt):

        if game.in_house:
            game.update_house_player(dt)
            return

        keys = pygame.key.get_pressed()

        dx = 0
        dy = 0

        if keys[pygame.K_w]:
            dy -= 1

        if keys[pygame.K_s]:
            dy += 1

        if keys[pygame.K_a]:
            dx -= 1

        if keys[pygame.K_d]:
            dx += 1

        dx, dy = normalize(
            dx,
            dy
        )

        speed = PLAYER_SPEED

        if keys[pygame.K_LSHIFT]:
            speed *= 1.25

        old_x = self.x
        old_y = self.y

        if dx or dy:

            self.walk_time += dt * 10

            self.x += dx * speed * dt
            self.y += dy * speed * dt

            # Fences are the hard boundary of every unlocked plot.
            # Never allow the player to step into the white-noise fog.
            if not game.territory.contains(self.x, self.y):
                self.x = old_x
                self.y = old_y

        else:

            self.walk_time += dt * 2

        # Territory/fence collision is handled above by the union of unlocked plots.
        # This prevents entering white-noise areas while still allowing movement
        # through the one-tile-wide connections between expanded plots.
        game.resolve_actor_collision(self, 18)

        # A structure collision can push the player slightly outside a plot;
        # put them back on the safe side of the fence.
        if not game.territory.contains(self.x, self.y):
            self.x = old_x
            self.y = old_y

        mx, my = pygame.mouse.get_pos()

        wx, wy = screen_to_world(
            game.camera,
            mx,
            my
        )

        self.angle = math.atan2(
            wy - self.y,
            wx - self.x
        )

        self.fire_timer -= dt

        if (
            pygame.mouse.get_pressed()[0]
            and game.build_mode is None
            and game.wire_mode is False
        ):

            if self.fire_timer <= 0:

                self.fire_timer = self.weapon_fire_delay

                vx = math.cos(self.angle) * BULLET_SPEED
                vy = math.sin(self.angle) * BULLET_SPEED

                game.bullets.append(
                    Bullet(
                        self.x + math.cos(self.angle) * 25,
                        self.y + math.sin(self.angle) * 25,
                        vx,
                        vy,
                        self.weapon_damage
                    )
                )

                game.camera.kick(1.5)

        if self.invulnerable > 0:
            self.invulnerable -= dt

    def hurt(self, amount, game):

        if self.invulnerable > 0:
            return

        self.health -= amount
        self.invulnerable = 0.35

        game.camera.kick(7)

        game.spawn_burst(
            self.x,
            self.y,
            RED,
            8
        )

        if self.health <= 0:

            self.health = self.max_health

            self.x = game.territory.centerx
            self.y = game.territory.centery

            game.cash = max(
                0,
                game.cash - 50
            )

    def draw(self, screen, camera):

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        bob = math.sin(
            self.walk_time
        ) * 2

        # shadow
        pygame.draw.ellipse(
            screen,
            (9, 12, 8),
            (
                sx - 17,
                sy + 11,
                34,
                10
            )
        )

        # body
        pygame.draw.circle(
            screen,
            (55, 67, 54),
            (
                sx,
                int(sy + bob)
            ),
            13
        )

        # head
        pygame.draw.circle(
            screen,
            (158, 130, 94),
            (
                sx,
                int(sy - 15 + bob)
            ),
            9
        )

        # weapon
        ex = sx + math.cos(self.angle) * 29
        ey = sy + math.sin(self.angle) * 29

        pygame.draw.line(
            screen,
            (31, 32, 29),
            (sx, sy),
            (ex, ey),
            7
        )

        pygame.draw.line(
            screen,
            METAL,
            (sx, sy),
            (ex, ey),
            3
        )


# ============================================================
# ZOMBIE
# ============================================================

class Zombie:

    __slots__ = (
        "x",
        "y",
        "health",
        "max_health",
        "speed",
        "attack_timer",
        "attack_delay",
        "anim",
        "target_cable",
        "is_boss",
        "special_timer",
        "shield_timer"
    )

    def __init__(
        self,
        x,
        y,
        wave
    ):

        self.x = x
        self.y = y

        hp = 60 + wave * 9

        self.health = hp
        self.max_health = hp

        self.speed = ZOMBIE_BASE_SPEED + wave * 3

        self.attack_timer = 0
        self.attack_delay = 0.65

        self.anim = random.uniform(
            0,
            math.pi * 2
        )

        self.target_cable = None
        self.is_boss = False
        self.special_timer = 0.0
        self.shield_timer = 0.0

    def is_in_fog(self, game):

        # Fog is physically outside territory.
        if not game.territory.contains(
            self.x,
            self.y
        ):
            return True

        # Dark areas inside territory are still dangerous,
        # but not hidden by a global camera overlay.
        if distance(
            self.x,
            self.y,
            game.player.x,
            game.player.y
        ) < 300:
            return False

        for building in game.buildings:

            if (
                building.kind == "spotlight"
                and building.powered(game.power_grid)
            ):

                if distance(
                    self.x,
                    self.y,
                    building.x,
                    building.y
                ) < 430:

                    return False

        return True

    def update(self, game, dt):

        self.anim += dt * 6

        # ----------------------------------------------------
        # Choose between player, building or cable
        # ----------------------------------------------------

        target_x = game.player.x
        target_y = game.player.y

        # Sometimes attack buildings
        nearest_building = None
        nearest_building_d = 500 * 500

        for building in game.buildings:

            d = dist2(
                self.x,
                self.y,
                building.x,
                building.y
            )

            if d < nearest_building_d:

                nearest_building_d = d
                nearest_building = building

        # Find cables when close enough.
        self.target_cable = None

        nearest_cable = None
        nearest_cable_d = 110 * 110

        for cable in game.power_grid.cables:

            if cable.broken:
                continue

            d = cable.distance_to(
                self.x,
                self.y
            )

            if d < math.sqrt(nearest_cable_d):

                nearest_cable_d = d * d
                nearest_cable = cable

        # If cable is nearby, zombies can bite it.
        if nearest_cable is not None and random.random() < 0.12:

            self.target_cable = nearest_cable

            mx = (
                nearest_cable.a.x +
                nearest_cable.b.x
            ) * 0.5

            my = (
                nearest_cable.a.y +
                nearest_cable.b.y
            ) * 0.5

            target_x = mx
            target_y = my

        elif nearest_building is not None and nearest_building_d < 260 * 260:

            target_x = nearest_building.x
            target_y = nearest_building.y

        # ----------------------------------------------------
        # Fog speed
        # ----------------------------------------------------

        speed = self.speed

        if self.is_in_fog(game):

            speed *= 1.45

        dx, dy = normalize(
            target_x - self.x,
            target_y - self.y
        )

        self.x += dx * speed * dt
        self.y += dy * speed * dt

        # Zombies are incorporeal: fences, props and buildings do not block them.
        # They can walk straight through world geometry and the white-noise fog.

        self.attack_timer -= dt

        # ----------------------------------------------------
        # Cable bite
        # ----------------------------------------------------

        if self.target_cable is not None:

            d = self.target_cable.distance_to(
                self.x,
                self.y
            )

            if d < 25:

                if self.attack_timer <= 0:

                    self.attack_timer = self.attack_delay

                    self.target_cable.health -= 30

                    if self.target_cable.health <= 0:

                        self.target_cable.break_cable()

                        game.power_grid.recalculate()

                        game.camera.kick(3)

                        game.spawn_burst(
                            self.x,
                            self.y,
                            RED,
                            14
                        )

                return

        # ----------------------------------------------------
        # Player attack
        # ----------------------------------------------------

        d_player = distance(
            self.x,
            self.y,
            game.player.x,
            game.player.y
        )

        if d_player < 29:

            if self.attack_timer <= 0:

                self.attack_timer = self.attack_delay

                game.player.hurt(
                    10,
                    game
                )

        # ----------------------------------------------------
        # Building attack
        # ----------------------------------------------------

        if nearest_building is not None:

            d = distance(
                self.x,
                self.y,
                nearest_building.x,
                nearest_building.y
            )

            if d < 34:

                if self.attack_timer <= 0:

                    self.attack_timer = self.attack_delay

                    nearest_building.health -= 7

                    game.spawn_burst(
                        nearest_building.x,
                        nearest_building.y,
                        BLOOD,
                        3
                    )

    def hit(self, damage, game):

        self.health -= damage

        game.spawn_burst(
            self.x,
            self.y,
            BLOOD,
            3
        )

        if self.health <= 0:

            game.kill_zombie(
                self
            )

            return True

        return False

    def draw(self, screen, camera, game):

        # Zombies are always rendered. Fog still affects their movement
        # speed, but never makes them disappear.

        sx, sy = world_to_screen(
            camera,
            self.x,
            self.y
        )

        wobble = math.sin(
            self.anim
        ) * 2

        # shadow
        pygame.draw.ellipse(
            screen,
            (11, 12, 8),
            (
                sx - 16,
                sy + 12,
                32,
                9
            )
        )

        # body
        pygame.draw.circle(
            screen,
            (83, 83, 66),
            (
                sx,
                int(sy + wobble)
            ),
            14
        )

        # head
        pygame.draw.circle(
            screen,
            (111, 94, 69),
            (
                sx,
                int(sy - 13 + wobble)
            ),
            10
        )

        # eyes
        pygame.draw.circle(
            screen,
            ACID,
            (
                sx - 4,
                int(sy - 15 + wobble)
            ),
            2
        )

        pygame.draw.circle(
            screen,
            ACID,
            (
                sx + 4,
                int(sy - 15 + wobble)
            ),
            2
        )

        # health
        ratio = clamp(
            self.health / self.max_health,
            0,
            1
        )

        pygame.draw.rect(
            screen,
            (35, 25, 22),
            (
                sx - 17,
                sy - 28,
                34,
                4
            )
        )

        pygame.draw.rect(
            screen,
            RED,
            (
                sx - 17,
                sy - 28,
                int(34 * ratio),
                4
            )
        )


# ============================================================
# TERRITORY
# ============================================================

class Territory:

    def __init__(self):

        # Starting plot.
        self.left = 1050
        self.top = 850

        self.width = 1100
        self.height = 800

        self.centerx = (
            self.left +
            self.width / 2
        )

        self.centery = (
            self.top +
            self.height / 2
        )

        self.expansions = 0
        self.direction_counts = {"left": 0, "right": 0, "up": 0, "down": 0}
        self.max_per_direction = 1

        self.plots = [
            pygame.Rect(
                self.left,
                self.top,
                self.width,
                self.height
            )
        ]

        self.costs = [
            350,
            550,
            800,
            1100
        ]

        self.static_w = max(160, WIDTH // 6)
        self.static_h = max(90, HEIGHT // 6)
        self.static_surface = pygame.Surface((self.static_w, self.static_h))

    def update_bounds(self):

        left = min(
            p.left
            for p in self.plots
        )

        top = min(
            p.top
            for p in self.plots
        )

        right = max(
            p.right
            for p in self.plots
        )

        bottom = max(
            p.bottom
            for p in self.plots
        )

        self.left = left
        self.top = top

        self.width = right - left
        self.height = bottom - top

        self.centerx = (
            left + right
        ) / 2

        self.centery = (
            top + bottom
        ) / 2

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    def contains(self, x, y):

        for plot in self.plots:

            if plot.collidepoint(
                int(x),
                int(y)
            ):
                return True

        return False

    def can_expand(self, direction):

        if direction not in self.direction_counts:
            return False
        if self.direction_counts[direction] >= self.max_per_direction:
            return False

        # Expansions are a clean plus-shaped grid: every direction grows
        # directly from the original plot, so there are no accidental gaps.
        return True

    def expand(self, direction):

        if not self.can_expand(direction):
            return None

        base = self.plots[0]
        n = self.direction_counts[direction] + 1
        dx, dy = {
            "left": (-1, 0),
            "right": (1, 0),
            "up": (0, -1),
            "down": (0, 1)
        }[direction]

        new_rect = pygame.Rect(
            base.left + dx * base.width * n,
            base.top + dy * base.height * n,
            base.width,
            base.height
        )

        self.plots.append(new_rect)
        self.direction_counts[direction] += 1
        self.expansions += 1
        self.update_bounds()
        return new_rect

    def cost(self):

        index = min(
            self.expansions,
            len(self.costs) - 1
        )

        return self.costs[index]

    def draw_fog_static(self, screen, rects):
        # Generate TV static only a few times per second instead of every frame.
        # This keeps the fog visual while removing the expansion-related FPS hit.
        now = pygame.time.get_ticks()
        if not hasattr(self, "static_noise"):
            self.static_noise = pygame.Surface((self.static_w, self.static_h))
            self.static_scaled = pygame.Surface((WIDTH, HEIGHT))
            self.static_noise_time = -9999

        if now - self.static_noise_time >= 90:
            surf = self.static_noise
            surf.fill((38, 38, 38))
            grain_count = max(500, (self.static_w * self.static_h) // 28)
            for _ in range(grain_count):
                gx = random.randrange(self.static_w)
                gy = random.randrange(self.static_h)
                v = random.randrange(25, 230)
                surf.set_at((gx, gy), (v, v, v))
            self.static_scaled = pygame.transform.scale(surf, (WIDTH, HEIGHT))
            self.static_noise_time = now

        old_clip = screen.get_clip()
        screen_rect = screen.get_rect()
        for r in rects:
            clip = r.clip(screen_rect)
            if clip.width > 0 and clip.height > 0:
                screen.set_clip(clip)
                screen.blit(self.static_scaled, (0, 0))
        screen.set_clip(old_clip)

    def draw_ground(self, screen, camera):

        # ----------------------------------------------------
        # Large dark world
        # ----------------------------------------------------

        screen.fill(
            (8, 11, 8)
        )

        # ----------------------------------------------------
        # FOG OUTSIDE TERRITORY
        #
        # World-space rectangles.
        # This is intentionally NOT a screen overlay.
        # ----------------------------------------------------

        huge = 5000

        # top
        top_rect = pygame.Rect(
            int(self.left - camera.x - huge),
            int(-huge),
            int(self.width + huge * 2),
            int(self.top + huge)
        )

        pygame.draw.rect(
            screen,
            (6, 9, 7),
            top_rect
        )

        # bottom
        bottom_rect = pygame.Rect(
            int(self.left - camera.x - huge),
            int(self.bottom - camera.y),
            int(self.width + huge * 2),
            int(huge)
        )

        pygame.draw.rect(
            screen,
            (6, 9, 7),
            bottom_rect
        )

        # left
        left_rect = pygame.Rect(
            int(-huge),
            int(self.top - camera.y),
            int(self.left + huge),
            int(self.height)
        )

        pygame.draw.rect(
            screen,
            (6, 9, 7),
            left_rect
        )

        # right
        right_rect = pygame.Rect(
            int(self.right - camera.x),
            int(self.top - camera.y),
            int(huge),
            int(self.height)
        )

        pygame.draw.rect(
            screen,
            (6, 9, 7),
            right_rect
        )

        self.draw_fog_static(
            screen,
            [top_rect, bottom_rect, left_rect, right_rect]
        )

        # ----------------------------------------------------
        # Fog in every locked grid cell inside the expanded bounds.
        # This removes the old black corner/gap artifacts.
        # ----------------------------------------------------
        locked_rects = []
        for gx in range(self.left, self.right, self.plots[0].width):
            for gy in range(self.top, self.bottom, self.plots[0].height):
                if not self.contains(gx + self.plots[0].width // 2, gy + self.plots[0].height // 2):
                    rr = pygame.Rect(int(gx - camera.x), int(gy - camera.y), self.plots[0].width, self.plots[0].height)
                    pygame.draw.rect(screen, (6, 9, 7), rr)
                    locked_rects.append(rr)
        if locked_rects:
            self.draw_fog_static(screen, locked_rects)

        # ----------------------------------------------------
        # Ground plots
        # ----------------------------------------------------

        for plot in self.plots:

            r = pygame.Rect(
                int(plot.left - camera.x),
                int(plot.top - camera.y),
                int(plot.width),
                int(plot.height)
            )

            pygame.draw.rect(
                screen,
                GRASS_DARK,
                r
            )

            pygame.draw.rect(
                screen,
                GRASS,
                r.inflate(-8, -8)
            )

        # ----------------------------------------------------
        # Grass noise
        # ----------------------------------------------------

        # Deterministic-ish sparse patches around camera.
        start_x = int(
            math.floor(
                camera.x / GRID_SIZE
            ) * GRID_SIZE
        )

        start_y = int(
            math.floor(
                camera.y / GRID_SIZE
            ) * GRID_SIZE
        )

        for gx in range(
            start_x - GRID_SIZE * 2,
            start_x + WIDTH + GRID_SIZE * 2,
            GRID_SIZE
        ):

            for gy in range(
                start_y - GRID_SIZE * 2,
                start_y + HEIGHT + GRID_SIZE * 2,
                GRID_SIZE
            ):

                wx = gx + 23
                wy = gy + 37

                if not self.contains(
                    wx,
                    wy
                ):
                    continue

                sx, sy = world_to_screen(
                    camera,
                    wx,
                    wy
                )

                pygame.draw.line(
                    screen,
                    GRASS_LIGHT,
                    (sx, sy),
                    (
                        sx + 7,
                        sy - 3
                    ),
                    1
                )

        # ----------------------------------------------------
        # Dirt paths
        # ----------------------------------------------------

        for plot in self.plots:

            px = plot.centerx
            py = plot.centery

            sx, sy = world_to_screen(
                camera,
                px,
                py
            )

            pygame.draw.rect(
                screen,
                DIRT,
                (
                    sx - 60,
                    int(plot.top - camera.y),
                    120,
                    plot.height
                )
            )

            pygame.draw.rect(
                screen,
                DIRT,
                (
                    int(plot.left - camera.x),
                    sy - 48,
                    plot.width,
                    96
                )
            )

        # ----------------------------------------------------
        # FENCES
        # ----------------------------------------------------

        self.draw_fences(
            screen,
            camera
        )

    def draw_fences(self, screen, camera):

        # Each unlocked plot gets fences on sides where
        # there isn't another unlocked plot.
        occupied = set(
            (
                p.left,
                p.top
            )
            for p in self.plots
        )

        for plot in self.plots:

            neighbors = {
                "left": (
                    plot.left - plot.width,
                    plot.top
                ),
                "right": (
                    plot.left + plot.width,
                    plot.top
                ),
                "up": (
                    plot.left,
                    plot.top - plot.height
                ),
                "down": (
                    plot.left,
                    plot.top + plot.height
                )
            }

            # left
            if neighbors["left"] not in occupied:

                self.draw_fence_line(
                    screen,
                    camera,
                    plot.left,
                    plot.top,
                    plot.left,
                    plot.bottom
                )

            # right
            if neighbors["right"] not in occupied:

                self.draw_fence_line(
                    screen,
                    camera,
                    plot.right,
                    plot.top,
                    plot.right,
                    plot.bottom
                )

            # top
            if neighbors["up"] not in occupied:

                self.draw_fence_line(
                    screen,
                    camera,
                    plot.left,
                    plot.top,
                    plot.right,
                    plot.top
                )

            # bottom
            if neighbors["down"] not in occupied:

                self.draw_fence_line(
                    screen,
                    camera,
                    plot.left,
                    plot.bottom,
                    plot.right,
                    plot.bottom
                )

    def draw_fence_line(
        self,
        screen,
        camera,
        x1,
        y1,
        x2,
        y2
    ):

        sx1, sy1 = world_to_screen(
            camera,
            x1,
            y1
        )

        sx2, sy2 = world_to_screen(
            camera,
            x2,
            y2
        )

        pygame.draw.line(
            screen,
            WOOD_DARK,
            (sx1, sy1),
            (sx2, sy2),
            10
        )

        pygame.draw.line(
            screen,
            WOOD,
            (sx1, sy1),
            (sx2, sy2),
            6
        )

        length = distance(
            x1,
            y1,
            x2,
            y2
        )

        count = int(
            length / 90
        )

        for i in range(
            count + 1
        ):

            t = (
                i /
                max(1, count)
            )

            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t

            sx, sy = world_to_screen(
                camera,
                x,
                y
            )

            pygame.draw.rect(
                screen,
                WOOD_DARK,
                (
                    sx - 5,
                    sy - 14,
                    10,
                    28
                )
            )

            pygame.draw.rect(
                screen,
                WOOD_LIGHT,
                (
                    sx - 3,
                    sy - 12,
                    6,
                    24
                )
            )


# ============================================================
# BACKYARD DECOR
# ============================================================

class Backyard:

    def __init__(self):

        self.objects = []

        # Trees
        for i in range(55):

            self.objects.append(
                (
                    "tree",
                    random.randint(
                        200,
                        WORLD_W - 200
                    ),
                    random.randint(
                        200,
                        WORLD_H - 200
                    ),
                    random.randint(
                        24,
                        44
                    )
                )
            )

        # Bushes
        for i in range(70):

            self.objects.append(
                (
                    "bush",
                    random.randint(
                        150,
                        WORLD_W - 150
                    ),
                    random.randint(
                        150,
                        WORLD_H - 150
                    ),
                    random.randint(
                        14,
                        30
                    )
                )
            )

        # Rocks
        for i in range(65):

            self.objects.append(
                (
                    "rock",
                    random.randint(
                        100,
                        WORLD_W - 100
                    ),
                    random.randint(
                        100,
                        WORLD_H - 100
                    ),
                    random.randint(
                        5,
                        13
                    )
                )
            )

        # Junk
        for i in range(28):

            self.objects.append(
                (
                    "junk",
                    random.randint(
                        100,
                        WORLD_W - 100
                    ),
                    random.randint(
                        100,
                        WORLD_H - 100
                    ),
                    random.randint(
                        8,
                        18
                    )
                )
            )

        # Fixed structures
        self.structures = [
            (
                "house",
                850,
                580,
                350,
                250
            ),
            (
                "shed",
                2500,
                920,
                230,
                170
            ),
            (
                "shed",
                2800,
                2100,
                210,
                150
            )
        ]

    def draw(self, screen, camera, territory):

        # Trees etc.
        for kind, x, y, size in self.objects:

            if (
                x < camera.x - 100 or
                x > camera.x + WIDTH + 100 or
                y < camera.y - 100 or
                y > camera.y + HEIGHT + 100
            ):
                continue

            # Objects outside unlocked territory are hidden in fog.
            if not territory.contains(x, y):
                continue

            sx, sy = world_to_screen(
                camera,
                x,
                y
            )

            if kind == "tree":

                pygame.draw.ellipse(
                    screen,
                    (18, 27, 16),
                    (
                        sx - size * 0.8,
                        sy + size * 0.45,
                        size * 1.6,
                        size * 0.45
                    )
                )

                pygame.draw.rect(
                    screen,
                    (64, 47, 30),
                    (
                        sx - 6,
                        sy - 2,
                        12,
                        size
                    )
                )

                pygame.draw.circle(
                    screen,
                    (27, 54, 28),
                    (
                        sx - 12,
                        sy - 10
                    ),
                    size
                )

                pygame.draw.circle(
                    screen,
                    (32, 65, 31),
                    (
                        sx + 10,
                        sy - 17
                    ),
                    int(size * 0.9)
                )

                pygame.draw.circle(
                    screen,
                    (38, 72, 34),
                    (
                        sx,
                        sy - 29
                    ),
                    int(size * 0.8)
                )

            elif kind == "bush":

                pygame.draw.circle(
                    screen,
                    (25, 52, 27),
                    (
                        sx - 8,
                        sy
                    ),
                    size
                )

                pygame.draw.circle(
                    screen,
                    (31, 64, 31),
                    (
                        sx + 8,
                        sy - 4
                    ),
                    int(size * 0.85)
                )

            elif kind == "rock":

                pygame.draw.ellipse(
                    screen,
                    (56, 60, 49),
                    (
                        sx - size,
                        sy - size * 0.5,
                        size * 2,
                        size
                    )
                )

            elif kind == "junk":

                pygame.draw.rect(
                    screen,
                    (57, 60, 51),
                    (
                        sx - size,
                        sy - size,
                        size * 2,
                        size * 2
                    )
                )

                pygame.draw.line(
                    screen,
                    WOOD_DARK,
                    (
                        sx - size,
                        sy - size
                    ),
                    (
                        sx + size,
                        sy + size
                    ),
                    2
                )

        # structures
        for kind, x, y, w, h in self.structures:

            if not territory.contains(
                x,
                y
            ):
                continue

            sx, sy = world_to_screen(
                camera,
                x,
                y
            )

            if kind == "house":

                pygame.draw.rect(
                    screen,
                    (76, 67, 55),
                    (
                        sx,
                        sy,
                        w,
                        h
                    )
                )

                # roof
                pygame.draw.polygon(
                    screen,
                    (48, 39, 33),
                    [
                        (sx - 25, sy),
                        (sx + w // 2, sy - 110),
                        (sx + w + 25, sy)
                    ]
                )

                # door
                pygame.draw.rect(
                    screen,
                    (43, 32, 25),
                    (
                        sx + w // 2 - 25,
                        sy + h - 95,
                        50,
                        95
                    )
                )

                # windows
                for wx in (
                    sx + 55,
                    sx + w - 95
                ):

                    pygame.draw.rect(
                        screen,
                        (35, 53, 39),
                        (
                            wx,
                            sy + 60,
                            40,
                            45
                        )
                    )

                # Visible backyard-house contents: shelves, table, radio and boxes.
                pygame.draw.rect(
                    screen,
                    (49, 39, 29),
                    (sx + 28, sy + 125, 72, 16)
                )
                pygame.draw.rect(
                    screen,
                    (43, 34, 26),
                    (sx + 42, sy + 141, 9, 45)
                )
                pygame.draw.rect(
                    screen,
                    (43, 34, 26),
                    (sx + 78, sy + 141, 9, 45)
                )

                pygame.draw.rect(
                    screen,
                    (91, 72, 48),
                    (sx + w - 125, sy + h - 68, 82, 45)
                )
                pygame.draw.rect(
                    screen,
                    (56, 44, 32),
                    (sx + w - 118, sy + h - 23, 8, 28)
                )
                pygame.draw.rect(
                    screen,
                    (56, 44, 32),
                    (sx + w - 55, sy + h - 23, 8, 28)
                )

                pygame.draw.rect(
                    screen,
                    (26, 31, 26),
                    (sx + 132, sy + 150, 42, 25)
                )
                pygame.draw.circle(
                    screen,
                    ACID,
                    (sx + 153, sy + 162),
                    5
                )

                for bx, by in (
                    (sx + 38, sy + h - 45),
                    (sx + 82, sy + h - 42),
                    (sx + 235, sy + h - 48)
                ):
                    pygame.draw.rect(
                        screen,
                        (100, 75, 42),
                        (bx, by, 30, 26)
                    )
                    pygame.draw.line(
                        screen,
                        (55, 42, 29),
                        (bx, by),
                        (bx + 30, by + 26),
                        2
                    )

            else:

                pygame.draw.rect(
                    screen,
                    (81, 57, 37),
                    (
                        sx,
                        sy,
                        w,
                        h
                    )
                )

                pygame.draw.polygon(
                    screen,
                    (53, 38, 27),
                    [
                        (sx - 15, sy),
                        (sx + w // 2, sy - 55),
                        (sx + w + 15, sy)
                    ]
                )

                pygame.draw.rect(
                    screen,
                    (43, 30, 22),
                    (
                        sx + w // 2 - 35,
                        sy + h - 80,
                        70,
                        80
                    )
                )

                # The right-side shed is the actual enterable house.
                if x == 2500 and y == 920:
                    pygame.draw.rect(
                        screen,
                        (35, 52, 38),
                        (sx + 28, sy + 48, 42, 32)
                    )
                    pygame.draw.rect(
                        screen,
                        (35, 52, 38),
                        (sx + w - 70, sy + 48, 42, 32)
                    )
                    pygame.draw.rect(
                        screen,
                        ACID,
                        (sx + w // 2 - 28, sy + h - 8, 56, 4)
                    )


class BossZombie(Zombie):

    def __init__(self, x, y, wave):
        super().__init__(x, y, wave)
        self.is_boss = True
        self.max_health = 4200 + wave * 500
        self.health = self.max_health
        self.speed = 66 + wave * 2.5
        self.special_timer = 4.0
        self.shield_timer = 0.0

    def update(self, game, dt):
        super().update(game, dt)
        self.special_timer -= dt
        if self.shield_timer > 0:
            self.shield_timer -= dt
        if self.special_timer <= 0:
            self.special_timer = 6.0
            self.shield_timer = 3.5
            game.message("BOSS ROAR — GRID BLACKOUT!")
            game.camera.kick(10)
            for cable in game.power_grid.cables:
                if not cable.broken:
                    mx = (cable.a.x + cable.b.x) * 0.5
                    my = (cable.a.y + cable.b.y) * 0.5
                    if distance(self.x, self.y, mx, my) < 280:
                        cable.health -= 90
                        if cable.health <= 0:
                            cable.break_cable()
            for building in game.buildings:
                if distance(self.x, self.y, building.x, building.y) < 240:
                    building.health = max(0, building.health - 70)
            game.power_grid.recalculate()
            game.spawn_burst(self.x, self.y, PURPLE, 28)

    def draw(self, screen, camera, game):
        sx, sy = world_to_screen(camera, self.x, self.y)
        bob = math.sin(self.anim) * 3
        pygame.draw.ellipse(screen, (9, 8, 8), (sx-32, sy+22, 64, 16))
        pygame.draw.circle(screen, (91, 35, 76), (sx, int(sy+bob)), 28)
        pygame.draw.circle(screen, (132, 48, 48), (sx, int(sy-27+bob)), 20)
        pygame.draw.circle(screen, PURPLE, (sx-8, int(sy-30+bob)), 4)
        pygame.draw.circle(screen, PURPLE, (sx+8, int(sy-30+bob)), 4)
        if self.shield_timer > 0:
            pygame.draw.circle(screen, PURPLE, (sx, int(sy+bob)), 38, 3)
        bar_w = 70
        pygame.draw.rect(screen, (25, 20, 20), (sx-bar_w//2, sy-58, bar_w, 7))
        pygame.draw.rect(screen, RED, (sx-bar_w//2, sy-58, int(bar_w * clamp(self.health/self.max_health, 0, 1)), 7))


# ============================================================
# WAVE MANAGER
# ============================================================

class WaveManager:

    def __init__(self):
        self.wave = 0
        self.active = False
        self.intermission = 12.0
        self.spawn_left = 0
        self.spawn_timer = 0.0
        self.spawn_delay = 0.25
        self.clear_timer = 0.0
        self.total_count = 0
        self.spawned_count = 0

    def remaining(self, game):
        # Exact amount still belonging to this wave: not spawned + alive.
        return max(0, self.spawn_left) + len(game.zombies)

    def update(self, game, dt):
        if not self.active:
            self.intermission -= dt
            if self.intermission <= 0:
                self.start_wave(game)
            return

        # Spawn the planned amount. A successful spawn ALWAYS consumes one
        # slot, so the wave can never wait forever on a stale counter.
        if self.spawn_left > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self.spawn_timer = self.spawn_delay
                spawned = game.spawn_zombie()
                if spawned:
                    self.spawn_left -= 1
                    self.spawned_count += 1
            return

        # No pending spawns and no living zombies = wave really cleared.
        if not game.zombies:
            self.clear_timer += dt
            if self.clear_timer >= 0.15:
                self.finish_wave(game)
        else:
            self.clear_timer = 0.0

    def finish_wave(self, game):
        self.active = False
        self.intermission = 15.0
        self.spawn_left = 0
        self.clear_timer = 0.0
        reward = 100 + self.wave * 30
        game.cash += reward
        game.message(f"WAVE {self.wave} CLEARED +${reward} — NEXT IN 15")

    def start_wave(self, game):
        self.wave += 1
        self.active = True
        self.clear_timer = 0.0
        self.total_count = 7 + self.wave * 4
        self.spawn_left = self.total_count
        self.spawned_count = 0
        self.spawn_delay = max(0.11, 0.42 - self.wave * 0.012)
        self.spawn_timer = 0.0
        if self.wave % 5 == 0:
            game.message(f"BOSS WAVE {self.wave}")
        else:
            game.message(f"WAVE {self.wave}")


# ============================================================
# GAME
# ============================================================

class Game:

    def __init__(self):

        self.camera = Camera()

        self.territory = Territory()

        self.backyard = Backyard()

        self.player = Player(
            self.territory.centerx,
            self.territory.centery
        )

        self.power_grid = PowerGrid()

        self.buildings = []

        self.bullets = []

        self.zombies = []

        self.particles = []

        self.acid = []

        self.cash = 700

        self.kills = 0

        self.build_mode = None

        self.wire_mode = False

        self.wire_start = None

        self.message_text = ""
        self.message_timer = 0

        self.game_time = 0
        self.in_house = False
        self.house_x = 0.5
        self.house_y = 0.82

        # Final extraction after all 4 expansion territories are unlocked.
        self.game_won = False
        self.end_timer = 0.0
        self.extraction_phase = 0  # 0 off, 1 car arriving, 2 player seated, 3 leaving
        self.car_x = 0.0
        self.car_y = 0.0
        self.car_arrived = False
        self.menu = True
        self.menu_static = None
        self.menu_static_timer = 0.0
        self.menu_static_w = 220
        self.menu_static_h = 125

        # ----------------------------------------------------
        # Wave manager
        # ----------------------------------------------------

        self.wave = WaveManager()

        # ----------------------------------------------------
        # Generator is now built manually.
        # ----------------------------------------------------
        self.generator = None

        self.seed_world()

    # ========================================================
    # WORLD SETUP
    # ========================================================

    def seed_world(self):

        # A small sign near the base.
        pass

    # ========================================================
    # MESSAGE
    # ========================================================

    def message(self, text):

        self.message_text = text
        self.message_timer = 3

    # ========================================================
    # ACID
    # ========================================================

    def on_acid(self, x, y):

        for pool in self.acid:

            if pool.contains(x, y):
                return True

        return False

    def spawn_acid(self, x, y):

        radius = random.randint(
            38,
            70
        )

        self.acid.append(
            AcidPool(
                x,
                y,
                radius
            )
        )

    # ========================================================
    # PARTICLES
    # ========================================================

    def add_particle(self, particle):

        if len(self.particles) >= MAX_PARTICLES:
            self.particles.pop(0)

        self.particles.append(
            particle
        )

    def spawn_burst(
        self,
        x,
        y,
        color,
        count
    ):

        for _ in range(count):

            angle = random.uniform(
                0,
                math.pi * 2
            )

            speed = random.uniform(
                40,
                230
            )

            self.add_particle(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    random.uniform(
                        0.25,
                        0.7
                    ),
                    random.randint(
                        2,
                        5
                    ),
                    color
                )
            )

    # ========================================================
    # WORLD COLLISIONS
    # ========================================================

    def collides_world(self, x, y, radius=20):

        # Backyard props and structures are solid.
        for kind, ox, oy, size in self.backyard.objects:
            if distance(x, y, ox, oy) < radius + size * 0.75:
                return True

        for kind, ox, oy, w, h in self.backyard.structures:
            # Leave a real doorway in the right-side shed (the building
            # unlocked by pressing R). The player can walk up to it.
            if kind == "shed" and ox == 2500 and oy == 920:
                door_x = ox + w / 2
                door_y = oy + h
                if distance(x, y, door_x, door_y) < 52 + radius:
                    continue
            if (
                ox - radius < x < ox + w + radius and
                oy - radius < y < oy + h + radius
            ):
                return True

        return False

    def resolve_actor_collision(self, actor, radius):

        # Keep actors inside the actual world.
        actor.x = clamp(actor.x, radius, WORLD_W - radius)
        actor.y = clamp(actor.y, radius, WORLD_H - radius)

        # Push out of solid backyard objects.
        for kind, ox, oy, size in self.backyard.objects:
            rr = radius + size * 0.72
            dx = actor.x - ox
            dy = actor.y - oy
            d2 = dx * dx + dy * dy

            if d2 < rr * rr and d2 > 0.0001:
                d = math.sqrt(d2)
                actor.x = ox + dx / d * rr
                actor.y = oy + dy / d * rr

        # Rectangular structures.
        for kind, ox, oy, w, h in self.backyard.structures:
            # Door opening for the right-side house.
            if kind == "shed" and ox == 2500 and oy == 920:
                door_x = ox + w / 2
                door_y = oy + h
                if distance(actor.x, actor.y, door_x, door_y) < 52 + radius:
                    continue

            cx = clamp(actor.x, ox, ox + w)
            cy = clamp(actor.y, oy, oy + h)
            dx = actor.x - cx
            dy = actor.y - cy
            d2 = dx * dx + dy * dy

            if d2 < radius * radius:
                if d2 > 0.0001:
                    d = math.sqrt(d2)
                    actor.x += dx / d * (radius - d)
                    actor.y += dy / d * (radius - d)
                else:
                    # Actor is inside the rectangle: push toward nearest edge.
                    options = [
                        (abs(actor.x - ox), ox - radius, actor.y),
                        (abs(actor.x - (ox + w)), ox + w + radius, actor.y),
                        (abs(actor.y - oy), actor.x, oy - radius),
                        (abs(actor.y - (oy + h)), actor.x, oy + h + radius)
                    ]
                    _, nx, ny = min(options, key=lambda v: v[0])
                    actor.x, actor.y = nx, ny

        # Buildings are also solid.
        for building in self.buildings:
            rr = radius + building.radius
            dx = actor.x - building.x
            dy = actor.y - building.y
            d2 = dx * dx + dy * dy

            if d2 < rr * rr and d2 > 0.0001:
                d = math.sqrt(d2)
                actor.x = building.x + dx / d * rr
                actor.y = building.y + dy / d * rr

    # ========================================================
    # ZOMBIES
    # ========================================================

    def spawn_zombie(self):

        min_distance = 650
        max_distance = 1750
        margin = 70
        candidates = []

        for _ in range(220):
            angle = random.uniform(0, math.pi * 2)
            radius = random.uniform(min_distance, max_distance)
            x = self.player.x + math.cos(angle) * radius
            y = self.player.y + math.sin(angle) * radius
            if not (margin <= x <= WORLD_W - margin and margin <= y <= WORLD_H - margin):
                continue
            if self.collides_world(x, y, 18):
                continue
            outside = not self.territory.contains(x, y)
            candidates.append((0 if outside else 1, random.random(), x, y))

        if candidates:
            candidates.sort(key=lambda p: (p[0], p[1]))
            _, _, x, y = candidates[0]
        else:
            # Coarse world-wide fallback, still bounded and never absurdly far.
            best = None
            for x in range(margin, WORLD_W - margin, 100):
                for y in range(margin, WORLD_H - margin, 100):
                    d = distance(x, y, self.player.x, self.player.y)
                    if min_distance <= d <= max_distance and not self.collides_world(x, y, 18):
                        score = (0 if not self.territory.contains(x, y) else 1, -d)
                        if best is None or score < best[0]:
                            best = (score, x, y)
            if best is None:
                return False
            _, x, y = best

        if (self.wave.wave > 0 and self.wave.wave % 5 == 0
                and not any(getattr(z, "is_boss", False) for z in self.zombies)):
            self.zombies.append(BossZombie(x, y, self.wave.wave))
            self.message(f"BOSS WAVE {self.wave.wave} — THE WARDEN ARRIVED")
        else:
            self.zombies.append(Zombie(x, y, self.wave.wave))
        return True

    def kill_zombie(self, zombie):

        if zombie not in self.zombies:
            return

        self.zombies.remove(
            zombie
        )

        self.kills += 1

        if getattr(zombie, "is_boss", False):
            reward = 350 + self.wave.wave * 25
            xp_reward = 180 + self.wave.wave * 20
            self.message(f"BOSS DESTROYED +${reward} +{xp_reward} XP")
        else:
            reward = random.randint(8, 15)
            xp_reward = 18 + min(35, self.wave.wave * 2)

        self.cash += reward
        self.player.add_xp(xp_reward, self)

        self.spawn_burst(
            zombie.x,
            zombie.y,
            BLOOD,
            18
        )

        # Permanent acid pool.
        self.spawn_acid(
            zombie.x,
            zombie.y
        )

        # XP/money particles.
        for _ in range(4):

            self.add_particle(
                Particle(
                    zombie.x,
                    zombie.y,
                    random.uniform(-30, 30),
                    random.uniform(-100, -30),
                    1.0,
                    3,
                    ACID,
                    "xp"
                )
            )

    # ========================================================
    # GENERATOR
    # ========================================================

    def can_place_generator(self, x, y):

        if not self.territory.contains(x, y):
            return False

        if self.on_acid(x, y):
            return False

        if self.generator is not None:
            return False

        for building in self.buildings:
            if distance(x, y, building.x, building.y) < 75:
                return False

        if self.collides_world(x, y, 42):
            return False

        return True

    def place_generator(self, x, y):

        cost = 300

        if self.generator is not None:
            self.message("GENERATOR ALREADY BUILT")
            return

        if self.cash < cost:
            self.message("GENERATOR COST $300")
            return

        if not self.can_place_generator(x, y):
            self.message("CAN'T PLACE GENERATOR HERE")
            return

        self.generator = self.power_grid.create_node(
            x, y, "generator"
        )

        self.cash -= cost
        self.power_grid.recalculate()
        self.message("GENERATOR BUILT — CONNECT YOUR GRID")

    # ========================================================
    # BUILDING
    # ========================================================

    def can_build_here(self, x, y):

        if not self.territory.contains(
            x,
            y
        ):
            return False

        if self.collides_world(x, y, 34):
            return False

        # Do not build on acid.
        if self.on_acid(
            x,
            y
        ):
            return False

        # Don't stack buildings.
        for building in self.buildings:

            if distance(
                x,
                y,
                building.x,
                building.y
            ) < 65:

                return False

        # Don't put building on generator.
        if (
            self.generator is not None and
            distance(
                x,
                y,
                self.generator.x,
                self.generator.y
            ) < 65
        ):

            return False

        return True

    def build(self, kind, x, y):

        if kind == "turret":
            cost = 150
        else:
            cost = 110

        if self.cash < cost:

            self.message(
                "NOT ENOUGH MONEY"
            )

            return

        if not self.can_build_here(
            x,
            y
        ):

            self.message(
                "CAN'T BUILD HERE"
            )

            return

        if kind == "turret":

            building = Turret(
                x,
                y,
                self.power_grid
            )

        else:

            building = Spotlight(
                x,
                y,
                self.power_grid
            )

        self.buildings.append(
            building
        )

        self.cash -= cost

        self.message(
            f"{kind.upper()} BUILT — CONNECT A CABLE"
        )

    # ========================================================
    # WIRING
    # ========================================================

    def wire_click(self, x, y):

        # First click chooses existing node or creates node.
        node = self.power_grid.nearest_node(
            x,
            y,
            44
        )

        if node is None:

            node = self.power_grid.create_node(
                x,
                y
            )

        if self.wire_start is None:

            self.wire_start = node

            self.message(
                "WIRE: SELECT NEXT NODE"
            )

            return

        if node is self.wire_start:
            return

        self.power_grid.connect(
            self.wire_start,
            node
        )

        self.power_grid.recalculate()

        self.wire_start = node

        self.message(
            "CABLE CONNECTED"
        )

    def cancel_wire(self):

        self.wire_mode = False
        self.wire_start = None

    # ========================================================
    # REPAIR
    # ========================================================

    def repair(self):

        cable = self.power_grid.nearest_broken_cable(
            self.player.x,
            self.player.y,
            65
        )

        if cable is None:
            return

        finished = cable.repair_step(
            100
        )

        if finished:

            self.power_grid.recalculate()

            self.message(
                "CABLE REPAIRED"
            )

            self.spawn_burst(
                self.player.x,
                self.player.y,
                GREEN,
                10
            )

        else:

            self.message(
                "REPAIRING..."
            )

    # ========================================================
    # EXPANSION
    # ========================================================

    def try_expand(self, direction):

        cost = self.territory.cost()

        if self.cash < cost:

            self.message(
                f"EXPANSION COST ${cost}"
            )

            return

        rect = self.territory.expand(direction)

        if rect is None:
            self.message(f"{direction.upper()} IS MAXED — ONE EXPANSION PER SIDE")
            return

        self.cash -= cost

        self.message(
            f"TERRITORY EXPANDED {direction.upper()} -${cost}"
        )

        if self.territory.expansions >= 4 and self.extraction_phase == 0:
            self.game_won = True
            self.end_timer = 0.0
            self.extraction_phase = 2  # car is already waiting at base
            self.car_arrived = False
            base = self.territory.plots[0]
            self.car_x = base.centerx
            self.car_y = base.centery
            self.message("ALL TERRITORIES SECURED — GET TO THE CAR")

        # Put a few particles at new area.
        for _ in range(30):

            x = random.uniform(
                rect.left,
                rect.right
            )

            y = random.uniform(
                rect.top,
                rect.bottom
            )

            self.add_particle(
                Particle(
                    x,
                    y,
                    random.uniform(-20, 20),
                    random.uniform(-40, 10),
                    random.uniform(0.5, 1.2),
                    3,
                    GREEN
                )
            )

    # ========================================================
    # HOUSE INTERIOR
    # ========================================================

    def update_house_player(self, dt):
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        dy = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        dx, dy = normalize(dx, dy)
        speed = 0.62 * dt
        self.house_x = clamp(self.house_x + dx * speed, 0.10, 0.90)
        self.house_y = clamp(self.house_y + dy * speed, 0.16, 0.88)

    def near_house_door(self):
        # The enterable house is the shed on the RIGHT plot unlocked with R.
        # Its door is centered on the bottom wall: x=2615, y=1090.
        return distance(self.player.x, self.player.y, 2615, 1090) < 125

    def enter_house(self):
        if self.in_house:
            self.in_house = False
            # Put the player just outside the RIGHT-PLOT house door.
            self.player.x = 2615
            self.player.y = 1118
            self.message("BACKYARD — LEFT THE HOUSE")
            return

        if self.near_house_door():
            self.in_house = True
            self.house_x = 0.5
            self.house_y = 0.82
            self.cancel_wire()
            self.build_mode = None
            self.wire_mode = False
            self.wire_start = None
            self.message("HOUSE — H TO EXIT")
        else:
            self.message("GET CLOSER TO THE FRONT DOOR")

    def draw_house_interior(self):
        SCREEN.fill((31, 28, 24))

        # walls / floor
        pygame.draw.rect(SCREEN, (91, 78, 62), (70, 70, WIDTH - 140, HEIGHT - 140))
        pygame.draw.rect(SCREEN, (57, 48, 39), (100, 100, WIDTH - 200, HEIGHT - 200))

        # floor boards
        for y in range(180, HEIGHT - 130, 34):
            pygame.draw.line(SCREEN, (73, 59, 45), (110, y), (WIDTH - 110, y), 2)

        # windows
        for x in (180, WIDTH - 300):
            pygame.draw.rect(SCREEN, (27, 43, 37), (x, 135, 120, 85))
            pygame.draw.line(SCREEN, (105, 91, 70), (x + 60, 135), (x + 60, 220), 5)
            pygame.draw.line(SCREEN, (105, 91, 70), (x, 177), (x + 120, 177), 5)

        # table
        pygame.draw.rect(SCREEN, (104, 72, 43), (WIDTH // 2 - 170, 360, 340, 38))
        pygame.draw.rect(SCREEN, (68, 48, 31), (WIDTH // 2 - 145, 398, 25, 150))
        pygame.draw.rect(SCREEN, (68, 48, 31), (WIDTH // 2 + 120, 398, 25, 150))

        # radio + tools
        pygame.draw.rect(SCREEN, (35, 35, 31), (WIDTH // 2 - 80, 325, 90, 35))
        pygame.draw.circle(SCREEN, ACID, (WIDTH // 2 - 48, 342), 7)
        pygame.draw.line(SCREEN, METAL, (WIDTH // 2 + 20, 333), (WIDTH // 2 + 45, 315), 3)

        # shelves
        pygame.draw.rect(SCREEN, (74, 50, 31), (160, 285, 230, 18))
        pygame.draw.rect(SCREEN, (74, 50, 31), (160, 390, 230, 18))
        for x in (180, 225, 275, 325):
            pygame.draw.rect(SCREEN, (110, 79, 43), (x, 305, 25, 60))
            pygame.draw.rect(SCREEN, (100, 70, 38), (x, 410, 28, 60))

        # bed/couch
        pygame.draw.rect(SCREEN, (52, 65, 52), (WIDTH - 390, 430, 230, 100))
        pygame.draw.rect(SCREEN, (85, 68, 49), (WIDTH - 390, 405, 230, 35))

        # exit door
        pygame.draw.rect(SCREEN, (40, 29, 22), (WIDTH // 2 - 55, HEIGHT - 210, 110, 150))
        pygame.draw.rect(SCREEN, (137, 111, 68), (WIDTH // 2 + 25, HEIGHT - 140, 8, 8))

        px = int(100 + self.house_x * (WIDTH - 200))
        py = int(100 + self.house_y * (HEIGHT - 200))
        pygame.draw.ellipse(SCREEN, (18, 15, 12), (px - 15, py + 10, 30, 9))
        pygame.draw.circle(SCREEN, (55, 67, 54), (px, py), 13)
        pygame.draw.circle(SCREEN, (158, 130, 94), (px, py - 15), 9)

        title = font(30, True).render("HOUSE // ARMORY", True, WHITE)
        SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 24))

        # XP is a currency: show the raw amount and spend it here.
        panel = pygame.Rect(WIDTH - 365, 115, 300, 250)
        pygame.draw.rect(SCREEN, (18, 19, 16), panel)
        pygame.draw.rect(SCREEN, (78, 89, 65), panel, 2)
        xp = self.player.xp
        dmg_cost = 80 + max(0, (self.player.weapon_damage - BULLET_DAMAGE) // 10) * 45
        rate_upgrades = max(0, int(round((FIRE_DELAY - self.player.weapon_fire_delay) / 0.012)))
        rate_cost = 100 + rate_upgrades * 55
        hp_upgrades = max(0, (self.player.max_health - 100) // 15)
        hp_cost = 120 + hp_upgrades * 60
        lines = [
            f"XP {xp}",
            f"U  DAMAGE +10   [{dmg_cost} XP]",
            f"I  FIRE RATE    [{rate_cost} XP]",
            f"O  MAX HP +15   [{hp_cost} XP]",
        ]
        for i, line in enumerate(lines):
            col = ACID if i == 0 else WHITE
            SCREEN.blit(font(16, i == 0).render(line, True, col), (panel.x + 18, panel.y + 18 + i * 42))

        hint = font(18, True).render("WASD — WALK    U DAMAGE    I FIRE RATE    O MAX HP    X EXIT", True, ACID)
        SCREEN.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 45))

    # ========================================================
    # INPUT
    # ========================================================

    def menu_buttons(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        return {
            "start": pygame.Rect(cx - 190, cy + 20, 260, 76),
            "exit": pygame.Rect(cx + 95, cy + 105, 190, 60),
        }

    def handle_event(self, event):

        if self.menu:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.__init__()
                    self.menu = False
                    self.message("BACKYARD ONLINE — SECURE THE YARD")
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    raise SystemExit
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                buttons = self.menu_buttons()
                if buttons["start"].collidepoint(event.pos):
                    self.__init__()
                    self.menu = False
                    self.message("BACKYARD ONLINE — SECURE THE YARD")
                elif buttons["exit"].collidepoint(event.pos):
                    pygame.quit()
                    raise SystemExit
            return

        # Finished game: any left click returns to the main menu.
        if self.game_won and self.extraction_phase == 3 and self.car_arrived:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.__init__()
                self.menu = True
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit
            return

        if event.type == pygame.KEYDOWN:

            # ------------------------------------------------
            # HOUSE / WEAPON WORKBENCH
            # ------------------------------------------------
            if self.in_house:
                if event.key == pygame.K_x:
                    self.enter_house()
                    return
                if event.key == pygame.K_u:
                    self.player.upgrade_weapon_damage(self)
                    return
                if event.key == pygame.K_i:
                    self.player.upgrade_fire_rate(self)
                    return
                if event.key == pygame.K_o:
                    self.player.upgrade_health(self)
                    return
                # Don't allow outdoor construction while inside.
                return

            # ------------------------------------------------
            # BUILD
            # ------------------------------------------------

            if event.key == pygame.K_b:

                self.build_mode = None
                self.cancel_wire()

                self.message(
                    "BUILD: 4 GENERATOR / 1 TURRET / 2 SPOTLIGHT"
                )

            elif event.key == pygame.K_4:

                self.build_mode = "generator"
                self.cancel_wire()

                self.message(
                    "GENERATOR MODE — LMB TO PLACE ($300)"
                )

            elif event.key == pygame.K_1:

                self.build_mode = "turret"
                self.cancel_wire()

                self.message(
                    "TURRET MODE — LMB TO PLACE"
                )

            elif event.key == pygame.K_2:

                self.build_mode = "spotlight"
                self.cancel_wire()

                self.message(
                    "SPOTLIGHT MODE — LMB TO PLACE"
                )

            # ------------------------------------------------
            # REAL WIRING
            # ------------------------------------------------

            elif event.key == pygame.K_3:

                self.build_mode = None

                self.wire_mode = not self.wire_mode

                self.wire_start = None

                if self.wire_mode:

                    self.message(
                        "WIRE MODE — CLICK GENERATOR/NODE → NODE"
                    )

                else:

                    self.message(
                        "WIRE MODE OFF"
                    )

            # ------------------------------------------------
            # REPAIR
            # ------------------------------------------------

            elif event.key == pygame.K_h:
                if self.game_won and self.extraction_phase == 2:
                    if distance(self.player.x, self.player.y, self.car_x, self.car_y) < 115:
                        self.extraction_phase = 3
                        self.car_arrived = False
                        self.message("EXTRACTION STARTED — GOODBYE")
                    else:
                        self.message("GET CLOSER TO THE CAR")
                elif not self.in_house:
                    if self.near_house_door():
                        self.enter_house()
                    else:
                        self.message("GET CLOSER TO THE HOUSE DOOR")

            elif event.key == pygame.K_x:
                if self.in_house:
                    self.enter_house()

            elif event.key == pygame.K_e:

                self.repair()

            # ------------------------------------------------
            # TERRITORY
            # ------------------------------------------------

            elif event.key == pygame.K_q:

                self.try_expand(
                    "left"
                )

            elif event.key == pygame.K_r:

                self.try_expand(
                    "right"
                )

            elif event.key == pygame.K_f:

                self.try_expand(
                    "up"
                )

            elif event.key == pygame.K_v:

                self.try_expand(
                    "down"
                )

            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

        # ----------------------------------------------------
        # Mouse
        # ----------------------------------------------------

        if event.type == pygame.MOUSEBUTTONDOWN:

            if event.button == 1:

                mx, my = pygame.mouse.get_pos()

                x, y = screen_to_world(
                    self.camera,
                    mx,
                    my
                )

                if self.wire_mode:

                    self.wire_click(
                        x,
                        y
                    )

                elif self.build_mode == "generator":

                    self.place_generator(
                        x,
                        y
                    )

                    self.build_mode = None

                elif self.build_mode:

                    self.build(
                        self.build_mode,
                        x,
                        y
                    )

            elif event.button == 3:

                self.build_mode = None
                self.cancel_wire()

    # ========================================================
    # BULLETS
    # ========================================================

    def update_bullets(self, dt):

        new_bullets = []

        for bullet in self.bullets:

            if not bullet.update(dt):
                continue

            hit = False

            for zombie in self.zombies:

                if dist2(
                    bullet.x,
                    bullet.y,
                    zombie.x,
                    zombie.y
                ) < 20 * 20:

                    zombie.hit(
                        bullet.damage,
                        self
                    )

                    hit = True

                    break

            if not hit:

                new_bullets.append(
                    bullet
                )

        self.bullets = new_bullets

    # ========================================================
    # PARTICLES
    # ========================================================

    def update_particles(self, dt):

        alive = []

        for particle in self.particles:

            if particle.kind == "xp":

                dx = self.player.x - particle.x
                dy = self.player.y - particle.y

                d = math.sqrt(
                    dx * dx +
                    dy * dy
                )

                if d < 280:

                    nx, ny = normalize(
                        dx,
                        dy
                    )

                    particle.vx += nx * 550 * dt
                    particle.vy += ny * 550 * dt

                    if d < 30:

                        continue

            if particle.update(dt):

                alive.append(
                    particle
                )

        self.particles = alive

    # ========================================================
    # UPDATE
    # ========================================================

    def update(self, dt):

        self.game_time += dt

        if self.menu:
            self.update_menu_static(dt)
            return

        if self.game_won:
            self.end_timer += dt
            base = self.territory.plots[0]
            center_x, center_y = base.centerx, base.centery

            if self.extraction_phase == 2:
                # The car is parked in the starting plot. The player must be able
                # to walk back to it normally and press H to enter. Only the
                # outdoor simulation is paused; player movement remains active.
                self.player.update(self, dt)
                self.camera.follow(self.player.x, self.player.y, self.territory)
                self.camera.update(dt)
                return

            if self.extraction_phase == 3:
                # Drive away from the backyard.
                dx = self.car_x - center_x
                dy = self.car_y - center_y
                d = math.hypot(dx, dy)
                if d < 1550:
                    if d < 1:
                        dx, dy, d = 1, 0, 1
                    step = 600 * dt
                    self.car_x += dx / d * step
                    self.car_y += dy / d * step
                else:
                    self.car_arrived = True
                return

        if self.message_timer > 0:

            self.message_timer -= dt

        if self.in_house:
            # The house is a separate management dimension: no outdoor
            # movement, shooting, construction, or wave simulation advances.
            self.update_house_player(dt)
            self.camera.update(dt)
            return

        self.player.update(
            self,
            dt
        )

        # Grid remains real graph.
        self.power_grid.recalculate()

        for building in self.buildings:

            building.update(
                self,
                dt
            )

        for zombie in list(
            self.zombies
        ):

            zombie.update(
                self,
                dt
            )

            # Keep zombies inside world.
            zombie.x = clamp(
                zombie.x,
                -100,
                WORLD_W + 100
            )

            zombie.y = clamp(
                zombie.y,
                -100,
                WORLD_H + 100
            )

        self.update_bullets(
            dt
        )

        # Acid pools slowly dissolve instead of remaining forever.
        alive_acid = []
        for pool in self.acid:
            pool.life -= dt
            if pool.life > 0:
                alive_acid.append(pool)
        self.acid = alive_acid

        self.update_particles(
            dt
        )

        self.wave.update(
            self,
            dt
        )

        self.camera.follow(
            self.player.x,
            self.player.y,
            self.territory
        )

        self.camera.update(
            dt
        )

    # ========================================================
    # DRAW BACKYARD FOG DETAILS
    # ========================================================

    def draw_world_fog_edges(self):

        # Mist strips are part of world geometry at fences.
        # Not a full-screen postprocess.

        t = self.territory

        strips = [
            pygame.Rect(
                int(t.left - self.camera.x - 15),
                int(t.top - self.camera.y - 20),
                35,
                int(t.height + 40)
            ),
            pygame.Rect(
                int(t.right - self.camera.x - 20),
                int(t.top - self.camera.y - 20),
                35,
                int(t.height + 40)
            ),
            pygame.Rect(
                int(t.left - self.camera.x - 20),
                int(t.top - self.camera.y - 20),
                int(t.width + 40),
                35
            ),
            pygame.Rect(
                int(t.left - self.camera.x - 20),
                int(t.bottom - self.camera.y - 15),
                int(t.width + 40),
                35
            )
        ]

        for r in strips:

            pygame.draw.rect(
                SCREEN,
                (11, 16, 11),
                r
            )

    # ========================================================
    # BUILD PREVIEW
    # ========================================================

    def draw_build_preview(self):

        if self.build_mode is None:
            return

        mx, my = pygame.mouse.get_pos()

        x, y = screen_to_world(
            self.camera,
            mx,
            my
        )

        sx, sy = world_to_screen(
            self.camera,
            x,
            y
        )

        valid = self.can_build_here(
            x,
            y
        )

        if valid:
            color = GREEN
        else:
            color = RED

        pygame.draw.circle(
            SCREEN,
            color,
            (
                sx,
                sy
            ),
            30,
            2
        )

        pygame.draw.line(
            SCREEN,
            color,
            (
                sx - 10,
                sy
            ),
            (
                sx + 10,
                sy
            ),
            2
        )

        pygame.draw.line(
            SCREEN,
            color,
            (
                sx,
                sy - 10
            ),
            (
                sx,
                sy + 10
            ),
            2
        )

    # ========================================================
    # WIRE PREVIEW
    # ========================================================

    def draw_wire_preview(self):

        if not self.wire_mode:
            return

        mx, my = pygame.mouse.get_pos()

        x, y = screen_to_world(
            self.camera,
            mx,
            my
        )

        sx, sy = world_to_screen(
            self.camera,
            x,
            y
        )

        if self.wire_start is not None:

            ax, ay = world_to_screen(
                self.camera,
                self.wire_start.x,
                self.wire_start.y
            )

            pygame.draw.line(
                SCREEN,
                ACID,
                (
                    ax,
                    ay
                ),
                (
                    sx,
                    sy
                ),
                3
            )

            pygame.draw.circle(
                SCREEN,
                ACID,
                (
                    sx,
                    sy
                ),
                6,
                2
            )

        else:

            pygame.draw.circle(
                SCREEN,
                WHITE,
                (
                    sx,
                    sy
                ),
                7,
                2
            )

    # ========================================================
    # HUD
    # ========================================================

    def draw_hud(self):

        # top left
        pygame.draw.rect(
            SCREEN,
            (11, 15, 11),
            (
                18,
                18,
                310,
                142
            )
        )

        pygame.draw.rect(
            SCREEN,
            (42, 51, 38),
            (
                18,
                18,
                310,
                142
            ),
            2
        )

        txt = font(
            20,
            True
        )

        SCREEN.blit(
            txt.render(
                f"${self.cash}",
                True,
                ACID
            ),
            (
                32,
                30
            )
        )

        SCREEN.blit(
            txt.render(
                f"KILLS {self.kills}",
                True,
                WHITE
            ),
            (
                32,
                58
            )
        )

        SCREEN.blit(
            txt.render(
                f"XP {self.player.xp}",
                True,
                ORANGE
            ),
            (32, 82)
        )

        SCREEN.blit(
            txt.render(
                f"POWER {len(self.power_grid.powered_ids)}/{len(self.power_grid.nodes)}",
                True,
                GREEN if self.generator is not None else RED
            ),
            (32, 108)
        )

        # health
        pygame.draw.rect(
            SCREEN,
            (40, 25, 22),
            (
                32,
                129,
                250,
                8
            )
        )

        pygame.draw.rect(
            SCREEN,
            RED,
            (
                32,
                129,
                int(
                    250 *
                    self.player.health /
                    self.player.max_health
                ),
                8
            )
        )

        # ----------------------------------------------------
        # WAVE PANEL
        # ----------------------------------------------------

        panel_w = 310

        pygame.draw.rect(
            SCREEN,
            (11, 15, 11),
            (
                WIDTH - panel_w - 18,
                18,
                panel_w,
                112
            )
        )

        pygame.draw.rect(
            SCREEN,
            (42, 51, 38),
            (
                WIDTH - panel_w - 18,
                18,
                panel_w,
                112
            ),
            2
        )

        if self.wave.active:

            wave_text = (
                f"WAVE {self.wave.wave}"
            )

            state_text = (
                f"ZOMBIES LEFT {self.wave.remaining(self)}"
            )

            timer_text = (
                "ACTIVE"
            )

        else:

            wave_text = (
                f"NEXT WAVE"
            )

            state_text = (
                "PREPARE"
            )

            timer_text = format_time(
                self.wave.intermission
            )

        SCREEN.blit(
            txt.render(
                wave_text,
                True,
                WHITE
            ),
            (
                WIDTH - panel_w,
                30
            )
        )

        SCREEN.blit(
            txt.render(
                state_text,
                True,
                ORANGE
            ),
            (
                WIDTH - panel_w,
                58
            )
        )

        SCREEN.blit(
            font(
                25,
                True
            ).render(
                timer_text,
                True,
                ACID
            ),
            (
                WIDTH - 95,
                48
            )
        )

        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        small = font(
            15
        )

        controls = (
            "WASD MOVE   LMB SHOOT   E REPAIR   H HOUSE / ENTER CAR   "
            "1 TURRET $150   2 LIGHT $110   3 WIRES   4 GENERATOR $300"
        )

        SCREEN.blit(
            small.render(
                controls,
                True,
                GREY
            ),
            (
                20,
                HEIGHT - 29
            )
        )

        # Context hints
        if self.near_house_door():
            house_hint = font(18, True).render(
                "H — ENTER HOUSE",
                True,
                ACID
            )
            SCREEN.blit(
                house_hint,
                (
                    WIDTH // 2 - house_hint.get_width() // 2,
                    HEIGHT - 58
                )
            )

        expand_text = (
            "EXPAND: Q LEFT   R RIGHT   F UP   V DOWN   (1 EACH — THEN EXTRACTION)"
        )

        SCREEN.blit(
            small.render(
                expand_text,
                True,
                GREY
            ),
            (
                WIDTH - 390,
                HEIGHT - 29
            )
        )

        # ----------------------------------------------------
        # BUILD MODE
        # ----------------------------------------------------

        if self.build_mode:

            costs = {
                "generator": 300,
                "turret": 150,
                "spotlight": 110
            }
            label = (
                f"BUILDING: {self.build_mode.upper()} "
                f"${costs.get(self.build_mode, 0)} | LMB PLACE | RMB CANCEL"
            )

            surf = font(
                18,
                True
            ).render(
                label,
                True,
                ACID
            )

            SCREEN.blit(
                surf,
                (
                    WIDTH // 2 - surf.get_width() // 2,
                    HEIGHT - 65
                )
            )

        if self.wire_mode:

            label = (
                "WIRE MODE — CLICK NODE → NODE | RMB CANCEL"
            )

            surf = font(
                18,
                True
            ).render(
                label,
                True,
                ACID
            )

            SCREEN.blit(
                surf,
                (
                    WIDTH // 2 - surf.get_width() // 2,
                    HEIGHT - 65
                )
            )

        # ----------------------------------------------------
        # MESSAGE
        # ----------------------------------------------------

        if self.message_timer > 0:

            surf = font(
                23,
                True
            ).render(
                self.message_text,
                True,
                WHITE
            )

            pygame.draw.rect(
                SCREEN,
                (10, 14, 10),
                (
                    WIDTH // 2 - surf.get_width() // 2 - 15,
                    150,
                    surf.get_width() + 30,
                    42
                )
            )

            SCREEN.blit(
                surf,
                (
                    WIDTH // 2 -
                    surf.get_width() // 2,
                    158
                )
            )

    # ========================================================
    # EXTRACTION CAR
    # ========================================================

    def draw_car(self):
        sx, sy = world_to_screen(self.camera, self.car_x, self.car_y)
        # shadow
        pygame.draw.ellipse(SCREEN, (8, 8, 7), (sx - 58, sy + 18, 116, 24))
        body = pygame.Rect(sx - 55, sy - 24, 110, 42)
        pygame.draw.rect(SCREEN, (185, 185, 175), body, border_radius=10)
        pygame.draw.rect(SCREEN, (42, 48, 43), (sx - 30, sy - 18, 28, 18), border_radius=4)
        pygame.draw.rect(SCREEN, (42, 48, 43), (sx + 3, sy - 18, 28, 18), border_radius=4)
        pygame.draw.rect(SCREEN, (215, 205, 165), (sx - 47, sy - 4, 94, 18), border_radius=4)
        pygame.draw.circle(SCREEN, (20, 20, 18), (sx - 34, sy + 19), 12)
        pygame.draw.circle(SCREEN, (20, 20, 18), (sx + 34, sy + 19), 12)
        pygame.draw.circle(SCREEN, WHITE, (sx + 50, sy - 5), 5)

    # ========================================================
    # MENU
    # ========================================================

    def update_menu_static(self, dt):
        self.menu_static_timer -= dt
        if self.menu_static is not None and self.menu_static_timer > 0:
            return
        self.menu_static_timer = 0.075
        surf = pygame.Surface((self.menu_static_w, self.menu_static_h))
        for y in range(self.menu_static_h):
            for x in range(self.menu_static_w):
                v = random.randint(105, 225)
                surf.set_at((x, y), (v, v, v))
        self.menu_static = pygame.transform.scale(surf, (WIDTH, HEIGHT))

    def draw_menu(self):
        if self.menu_static is None:
            self.update_menu_static(0)
        SCREEN.blit(self.menu_static, (0, 0))

        # Dark veil + offset panels make the static feel like an old field monitor.
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 9, 7, 205))
        SCREEN.blit(overlay, (0, 0))

        cx, cy = WIDTH // 2, HEIGHT // 2
        # Misaligned geometric menu frame.
        frame = pygame.Rect(cx - 390, cy - 250, 780, 470)
        pygame.draw.rect(SCREEN, (14, 17, 13), frame, border_radius=3)
        pygame.draw.rect(SCREEN, (125, 138, 105), frame, 2, border_radius=3)
        pygame.draw.line(SCREEN, ACID, (frame.left + 35, frame.top + 78), (frame.right - 110, frame.top + 78), 2)
        pygame.draw.line(SCREEN, GREY, (frame.left + 510, frame.top + 25), (frame.left + 735, frame.top + 250), 1)

        title = font(72, True).render("LAST YARD", True, WHITE)
        sub = font(18, True).render("SURVIVE  /  EXPAND  /  EXTRACT", True, ACID)
        SCREEN.blit(title, (frame.left + 34, frame.top + 25))
        SCREEN.blit(sub, (frame.left + 39, frame.top + 91))

        buttons = self.menu_buttons()
        mouse = pygame.mouse.get_pos()

        def button(rect, label, accent=False, skew=0):
            hover = rect.collidepoint(mouse)
            pts = [
                (rect.left + skew, rect.top),
                (rect.right, rect.top),
                (rect.right - skew, rect.bottom),
                (rect.left, rect.bottom)
            ]
            pygame.draw.polygon(SCREEN, (24, 29, 23) if not hover else (39, 49, 35), pts)
            pygame.draw.polygon(SCREEN, ACID if accent or hover else (88, 98, 77), pts, 2)
            txt = font(22, True).render(label, True, WHITE if not hover else ACID)
            SCREEN.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        button(buttons["start"], "START GAME", True, 18)
        button(buttons["exit"], "EXIT [ESC]", False, -10)

        hint = font(13, True).render("LAST YARD", True, GREY)
        SCREEN.blit(hint, (frame.left + 42, frame.bottom - 55))

    # ========================================================
    # DRAW
    # ========================================================

    def draw(self):

        if self.menu:
            self.draw_menu()
            return

        if self.in_house:
            self.draw_house_interior()
            return

        # Camera shake is added only during rendering.
        old_x = self.camera.x
        old_y = self.camera.y

        self.camera.x += self.camera.shake_x
        self.camera.y += self.camera.shake_y

        self.territory.draw_ground(
            SCREEN,
            self.camera
        )

        self.backyard.draw(
            SCREEN,
            self.camera,
            self.territory
        )

        # acid
        for pool in self.acid:

            pool.draw(
                SCREEN,
                self.camera
            )

        # power cables behind buildings
        self.power_grid.draw(
            SCREEN,
            self.camera
        )

        # buildings
        for building in self.buildings:

            if isinstance(
                building,
                Turret
            ):

                building.draw(
                    SCREEN,
                    self.camera,
                    self
                )

            else:

                building.draw(
                    SCREEN,
                    self.camera,
                    self
                )

        # zombies
        for zombie in self.zombies:

            zombie.draw(
                SCREEN,
                self.camera,
                self
            )

        # bullets
        for bullet in self.bullets:

            bullet.draw(
                SCREEN,
                self.camera
            )

        # particles
        for particle in self.particles:

            particle.draw(
                SCREEN,
                self.camera
            )

        # extraction car
        if self.game_won:
            self.draw_car()

        # player
        if self.extraction_phase != 3:
            self.player.draw(SCREEN, self.camera)

        # world-space fog boundary
        self.draw_world_fog_edges()

        # build/wire preview
        self.draw_build_preview()
        self.draw_wire_preview()

        # HUD
        self.draw_hud()

        if self.game_won:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 105))
            SCREEN.blit(shade, (0, 0))
            if self.car_arrived:
                title = font(48, True).render("EXTRACTION COMPLETE", True, WHITE)
                sub = font(22, True).render("THE BACKYARD IS SECURED", True, ACID)
                prompt = font(17, True).render("CLICK TO RETURN TO MAIN MENU", True, WHITE)
                SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 70))
                SCREEN.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 - 10))
                SCREEN.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 38))
            elif self.extraction_phase == 2:
                title = font(34, True).render("VEHICLE READY — H TO ENTER", True, WHITE)
                SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 110))
            else:
                title = font(34, True).render("EXTRACTION IN PROGRESS", True, WHITE)
                SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 110))

        self.camera.x = old_x
        self.camera.y = old_y


# ============================================================
# MAIN
# ============================================================

def main():

    game = Game()

    running = True

    # Start directly with first preparation period.
    game.message(
        "BACKYARD ONLINE — 4 GENERATOR / 1 TURRET / 2 SPOTLIGHT"
    )

    while running:

        dt = CLOCK.tick(
            FPS
        ) / 1000.0

        dt = min(
            dt,
            0.033
        )

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False

            game.handle_event(
                event
            )

        game.update(
            dt
        )

        game.draw()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()