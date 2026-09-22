"""Snakerson: Snake clasico para escritorio, implementado con Pygame."""

import json
import math
import os
import random
import sqlite3
import sys
from datetime import datetime
import pygame

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
pygame.init()

GAME_WIDTH, GAME_HEIGHT = 800, 800
MENU_WIDTH, MENU_HEIGHT = 640, 420
WIDTH, HEIGHT = MENU_WIDTH, MENU_HEIGHT
BOARD = 704
CELL = 44
GRID = 16
FPS = 60
BOARD_X, BOARD_Y = (GAME_WIDTH - BOARD) // 2, (GAME_HEIGHT - BOARD) // 2
FOOD_COUNT = 4
FOOD_LIFETIME = 8.0
PROGRESS_FILE = os.path.join(os.path.expanduser("~"), ".snakerson_progress.json")
DATABASE_FILE = os.path.join(os.path.expanduser("~"), ".snakerson_stats.db")

BG = (5, 8, 20)
PANEL = (18, 29, 42)
PANEL_LIGHT = (28, 45, 61)
GRID_COLOR = (31, 53, 68)
WHITE = (242, 247, 250)
MUTED = (143, 161, 178)
GREEN = (101, 229, 114)
RED = (224, 84, 92)
GOLD = (255, 210, 63)
COLORS = {"GREEN": (50, 205, 50), "CYAN": (0, 217, 255), "YELLOW": GOLD, "RED": (255, 92, 92), "MAGENTA": (255, 79, 216), "BLUE": (79, 140, 255), "WHITE": WHITE}

LEVELS = [
    {"color": "GREEN", "speed": 1.0, "target": 4, "time": 60, "obstacles": [], "cycle": ["GREEN", "CYAN", "YELLOW", "MAGENTA"]},
    {"color": "CYAN", "speed": 1.15, "target": 5, "time": 65, "obstacles": [(2, 2), (13, 2), (2, 13), (13, 13)], "cycle": ["CYAN", "GREEN", "BLUE", "RED"]},
    {"color": "YELLOW", "speed": 1.3, "target": 6, "time": 70, "obstacles": [(5, 2), (10, 2), (5, 13), (10, 13), (2, 5), (13, 5), (2, 10), (13, 10)], "cycle": ["YELLOW", "MAGENTA", "CYAN", "GREEN"]},
    {"color": "RED", "speed": 1.45, "target": 7, "time": 75, "obstacles": [(3, 4), (4, 4), (5, 4), (10, 4), (11, 4), (12, 4), (3, 11), (4, 11), (5, 11), (10, 11), (11, 11), (12, 11)], "cycle": ["RED", "BLUE", "YELLOW", "CYAN"]},
    {"color": "MAGENTA", "speed": 1.6, "target": 8, "time": 80, "obstacles": [(6, 2), (7, 2), (8, 2), (9, 2), (6, 13), (7, 13), (8, 13), (9, 13), (2, 4), (2, 5), (13, 10), (13, 11), (2, 11), (13, 4)], "cycle": ["MAGENTA", "RED", "GREEN", "YELLOW"]},
    {"color": "BLUE", "speed": 1.8, "target": 9, "time": 85, "obstacles": [(4, 2), (4, 3), (4, 4), (4, 5), (11, 10), (11, 11), (11, 12), (11, 13), (9, 4), (10, 4), (2, 11), (3, 11), (7, 2), (8, 13)], "cycle": ["BLUE", "YELLOW", "MAGENTA", "CYAN"]},
    {"color": "WHITE", "speed": 2.0, "target": 10, "time": 90, "obstacles": [(6, 2), (7, 2), (8, 2), (9, 2), (6, 13), (7, 13), (8, 13), (9, 13), (2, 4), (2, 5), (13, 10), (13, 11), (2, 11), (13, 4), (4, 2), (4, 3), (4, 4), (4, 5), (11, 10), (11, 11), (11, 12), (11, 13), (9, 4), (10, 4), (2, 11), (3, 11), (7, 2), (8, 13), (2, 2), (13, 2), (2, 13), (13, 13), (8, 5), (7, 10)], "cycle": ["WHITE", "MAGENTA", "YELLOW", "GREEN"]},
]

ADDITIONAL_OBSTACLES = [
    [(3, 3), (12, 12)],
    [(6, 3), (9, 12)],
    [(3, 12), (12, 3)],
    [(7, 3), (8, 12)],
    [(3, 7), (12, 8)],
    [(6, 7), (9, 8)],
    [(3, 3), (12, 12)],
]


def expand_obstacles(level_index, obstacles):
    """Convierte cada punto de obstaculo en una barrera de tres bloques."""
    anchors = list(obstacles) + ADDITIONAL_OBSTACLES[level_index]
    expanded = set()
    for x, y in anchors:
        candidates = [(x, y), (x + 1, y), (x + 2, y)]
        if x + 2 >= GRID:
            candidates = [(x, y), (x - 1, y), (x - 2, y)]
        expanded.update(cell for cell in candidates if 0 <= cell[0] < GRID and 0 <= cell[1] < GRID)
    return sorted(expanded)


for level_index, level in enumerate(LEVELS):
    level["obstacles"] = expand_obstacles(level_index, level["obstacles"])

DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
KEY_TO_DIRECTION = {pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right", pygame.K_w: "up", pygame.K_s: "down", pygame.K_a: "left", pygame.K_d: "right"}


def load_progress():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return {"best": {int(k): int(v) for k, v in data.get("best", {}).items()}}
    except (OSError, ValueError, TypeError):
        return {"best": {}}


def save_progress(progress):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as file:
            json.dump(progress, file)
    except OSError:
        pass


def initialize_database():
    with sqlite3.connect(DATABASE_FILE) as database:
        database.execute(
            """CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                played_at TEXT NOT NULL,
                mode TEXT NOT NULL,
                level INTEGER,
                won INTEGER NOT NULL,
                score INTEGER NOT NULL,
                food_count INTEGER NOT NULL,
                duration REAL NOT NULL,
                reason TEXT NOT NULL
            )"""
        )


def record_game(mode, level_id, won, score, food_count, duration, reason):
    with sqlite3.connect(DATABASE_FILE) as database:
        database.execute(
            """INSERT INTO games
            (played_at, mode, level, won, score, food_count, duration, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(timespec="seconds"), mode, level_id, int(won), score, food_count, duration, reason),
        )


def database_summary():
    with sqlite3.connect(DATABASE_FILE) as database:
        total, wins, score, average = database.execute(
            "SELECT COUNT(*), COALESCE(SUM(won), 0), COALESCE(SUM(score), 0), COALESCE(AVG(score), 0) FROM games"
        ).fetchone()
        recent = database.execute(
            "SELECT mode, level, won, score, played_at FROM games ORDER BY id DESC LIMIT 8"
        ).fetchall()
    return total, wins, score, average, recent


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snakerson - 7 niveles")
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont("segoeuisemibold", 56)
        self.font_heading = pygame.font.SysFont("segoeuisemibold", 32)
        self.font_body = pygame.font.SysFont("segoeui", 22)
        self.font_small = pygame.font.SysFont("segoeui", 17)
        self.progress = load_progress()
        initialize_database()
        self.state = "menu"
        self.selected_level = 1
        self.running = True
        self.last_move = 0
        self.animation_time = 0.0
        self.hover_amount = {}

    def resize_window(self, width, height):
        global WIDTH, HEIGHT
        WIDTH, HEIGHT = width, height
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    def show_menu(self):
        self.resize_window(MENU_WIDTH, MENU_HEIGHT)
        self.state = "menu"

    def text(self, value, font, color, position, center=False):
        surface = font.render(value, True, color)
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rect)
        return rect

    def button(self, rect, label, accent=GREEN):
        mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse)
        target = 1.0 if hovered else 0.0
        progress = self.hover_amount.get(label, 0.0)
        progress += (target - progress) * 0.18
        self.hover_amount[label] = progress
        lift = int(progress * 3)
        animated_rect = rect.move(0, -lift)
        color = tuple(min(255, channel + int(18 * progress)) for channel in PANEL_LIGHT)
        pygame.draw.rect(self.screen, color, animated_rect, border_radius=8)
        pygame.draw.rect(self.screen, accent if progress > 0.05 else (45, 70, 88), animated_rect, 2 if hovered else 1, border_radius=8)
        self.text(label, self.font_body, WHITE, animated_rect.center, True)
        return hovered

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            self.animation_time += dt
            self.events()
            if self.state == "playing":
                self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.key_event(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.click(event.pos)

    def key_event(self, key):
        if self.state == "playing":
            if key == pygame.K_ESCAPE:
                self.show_menu()
                return
            if key in KEY_TO_DIRECTION:
                new_direction = KEY_TO_DIRECTION[key]
                if not self.started:
                    self.direction = self.pending_direction = new_direction
                    self.started = True
                elif OPPOSITE[new_direction] != self.direction:
                    self.pending_direction = new_direction
        elif self.state == "menu":
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_level(self.selected_level)
            elif key == pygame.K_1:
                self.state = "levels"
            elif key == pygame.K_2:
                self.state = "howto"
            elif key == pygame.K_3:
                self.start_free_mode()
            elif key == pygame.K_4:
                self.state = "stats"
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif self.state in ("levels", "howto", "stats", "result") and key == pygame.K_ESCAPE:
            self.state = "menu"

    def click(self, position):
        x, y = position
        if self.state == "menu":
            if pygame.Rect(330, 78, 290, 42).collidepoint(position):
                self.start_level(self.selected_level)
            elif pygame.Rect(330, 126, 290, 42).collidepoint(position):
                self.start_free_mode()
            elif pygame.Rect(330, 174, 290, 42).collidepoint(position):
                self.state = "levels"
            elif pygame.Rect(330, 222, 290, 42).collidepoint(position):
                self.state = "stats"
            elif pygame.Rect(330, 270, 290, 42).collidepoint(position):
                self.state = "howto"
            elif pygame.Rect(330, 318, 290, 42).collidepoint(position):
                self.running = False
        elif self.state == "levels":
            for index in range(7):
                col, row = index % 4, index // 4
                rect = pygame.Rect(70 + col * 285, 170 + row * 170, 250, 130)
                if rect.collidepoint(position):
                    self.selected_level = index + 1
                    self.start_level(self.selected_level)
                    return
            if pygame.Rect(40, 760, 190, 54).collidepoint(position):
                self.state = "menu"
        elif self.state == "howto" and pygame.Rect(40, 760, 190, 54).collidepoint(position):
            self.state = "menu"
        elif self.state == "stats" and pygame.Rect(40, 760, 190, 54).collidepoint(position):
            self.state = "menu"
        elif self.state == "result":
            if pygame.Rect(200, 500, 400, 56).collidepoint(position):
                if self.mode == "free":
                    self.start_free_mode()
                else:
                    self.start_level(self.level_id)
            elif pygame.Rect(200, 565, 400, 56).collidepoint(position):
                self.show_menu()
            elif self.next_level and pygame.Rect(200, 630, 400, 56).collidepoint(position):
                self.start_level(self.next_level)

    def start_level(self, level_id):
        self.resize_window(GAME_WIDTH, GAME_HEIGHT)
        self.mode = "levels"
        self.level_id = level_id
        self.level = LEVELS[level_id - 1]
        self.snake = [(4, 8), (3, 8), (2, 8), (1, 8)]
        self.direction = self.pending_direction = "right"
        self.obstacles = set(self.level["obstacles"])
        self.food_count = 0
        self.color_index = 0
        self.snake_color = self.level["cycle"][0]
        self.time_left = float(self.level["time"])
        self.foods = self.spawn_foods()
        self.state = "playing"
        self.last_move = 0
        self.started = False

    def start_free_mode(self):
        self.resize_window(GAME_WIDTH, GAME_HEIGHT)
        self.mode = "free"
        self.level_id = None
        self.level = {"speed": 1.0, "time": None, "obstacles": [], "cycle": ["GREEN", "CYAN", "YELLOW", "MAGENTA"], "color": "GREEN"}
        self.snake = [(4, 8), (3, 8), (2, 8), (1, 8)]
        self.direction = self.pending_direction = "right"
        self.obstacles = set()
        self.food_count = 0
        self.color_index = 0
        self.snake_color = self.level["cycle"][0]
        self.time_left = None
        self.foods = self.spawn_foods()
        self.state = "playing"
        self.last_move = 0
        self.started = False

    def spawn_food(self):
        occupied_food = {item["position"] for item in getattr(self, "foods", [])}
        free = [(x, y) for x in range(GRID) for y in range(GRID) if (x, y) not in self.snake and (x, y) not in self.obstacles and (x, y) not in occupied_food]
        return random.choice(free)

    def spawn_foods(self):
        self.foods = []
        for _ in range(FOOD_COUNT):
            self.foods.append({"position": self.spawn_food(), "time": FOOD_LIFETIME})
        return self.foods

    def refill_foods(self):
        while len(self.foods) < FOOD_COUNT:
            free = [(x, y) for x in range(GRID) for y in range(GRID) if (x, y) not in self.snake and (x, y) not in self.obstacles and all(item["position"] != (x, y) for item in self.foods)]
            if not free:
                return
            self.foods.append({"position": random.choice(free), "time": FOOD_LIFETIME})

    def update(self, dt):
        if not self.started:
            return
        if self.time_left is not None:
            self.time_left -= dt
            if self.time_left <= 0:
                self.finish(False, "Se acabo el tiempo")
                return
        for food in self.foods:
            food["time"] -= dt
        self.foods = [food for food in self.foods if food["time"] > 0]
        self.refill_foods()
        self.last_move += dt
        interval = 0.22 / self.level["speed"]
        if self.last_move < interval:
            return
        self.last_move -= interval
        self.direction = self.pending_direction
        dx, dy = DIRECTIONS[self.direction]
        head = self.snake[0]
        new_head = (head[0] + dx, head[1] + dy)
        eaten_food = next((food for food in self.foods if food["position"] == new_head), None)
        eating = eaten_food is not None
        body = self.snake if eating else self.snake[:-1]
        outside = not (0 <= new_head[0] < GRID and 0 <= new_head[1] < GRID)
        if outside or new_head in body or new_head in self.obstacles:
            self.finish(False, "Colision detectada")
            return
        self.snake.insert(0, new_head)
        if eating:
            self.foods.remove(eaten_food)
            self.food_count += 1
            if self.food_count % 3 == 0:
                self.color_index = (self.color_index + 1) % len(self.level["cycle"])
                self.snake_color = self.level["cycle"][self.color_index]
            if self.mode == "free" and len(self.snake) >= GRID * GRID:
                self.finish(True, "Pantalla completada")
                return
            if self.mode == "levels" and self.food_count >= self.level["target"]:
                self.finish(True, "Nivel superado")
                return
            self.refill_foods()
        else:
            self.snake.pop()

    def finish(self, won, reason):
        multiplier = self.level_id or 1
        self.score = self.food_count * 10 * multiplier
        if self.mode == "levels":
            self.progress["best"][self.level_id] = max(self.score, self.progress["best"].get(self.level_id, 0))
            save_progress(self.progress)
        duration = self.level["time"] - self.time_left if self.time_left is not None else 0
        record_game(self.mode, self.level_id, won, self.score, self.food_count, duration, reason)
        self.result_won = won
        self.result_reason = reason
        self.next_level = self.level_id + 1 if won and self.mode == "levels" and self.level_id < len(LEVELS) else None
        self.state = "result"

    def draw(self):
        self.draw_space_background()
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "levels":
            self.draw_levels()
        elif self.state == "howto":
            self.draw_howto()
        elif self.state == "stats":
            self.draw_stats()
        elif self.state == "playing":
            self.draw_game()
        else:
            self.draw_game()
            self.draw_result()

    def draw_space_background(self):
        """Dibuja un cielo espacial estable para que no parpadeen las estrellas."""
        self.screen.fill(BG)
        random.seed(704)
        for _ in range(150):
            x = random.randrange(WIDTH)
            y = random.randrange(HEIGHT)
            radius = random.choice((1, 1, 1, 2))
            brightness = random.randrange(90, 220)
            color = (brightness // 2, brightness // 2, brightness)
            pygame.draw.circle(self.screen, color, (x, y), radius)
        for x, y, width, color in ((150, 205, 260, (31, 24, 74)), (690, 150, 230, (24, 38, 78)), (770, 570, 280, (44, 21, 67))):
            pygame.draw.line(self.screen, color, (x - width, y + 75), (x + width, y - 75), 34)
            pygame.draw.line(self.screen, tuple(min(255, channel + 12) for channel in color), (x - width, y + 50), (x + width, y - 100), 3)
        random.seed()

    def draw_menu(self):
        pygame.draw.rect(self.screen, (14, 28, 39), (18, 18, 290, 384), border_radius=12)
        self.draw_animated_logo()
        self.text("SNAKE / 7 NIVELES", self.font_small, MUTED, (40, 82))
        self.text("COME / CRECE / EVOLUCIONA", self.font_small, MUTED, (38, 360))
        self.text("Tu partida", self.font_small, MUTED, (330, 30))
        self.text("7 niveles disponibles", self.font_body, WHITE, (330, 48))
        self.button(pygame.Rect(330, 78, 290, 42), "JUGAR AHORA", GREEN)
        self.button(pygame.Rect(330, 126, 290, 42), "SNAKE FREE", COLORS["CYAN"])
        self.button(pygame.Rect(330, 174, 290, 42), "SELECCIONAR NIVEL", COLORS["CYAN"])
        self.button(pygame.Rect(330, 222, 290, 42), "DESEMPENO Y PARTIDAS", GOLD)
        self.button(pygame.Rect(330, 270, 290, 42), "COMO JUGAR", GOLD)
        self.button(pygame.Rect(330, 318, 290, 42), "SALIR", RED)
        self.text("ENTER jugar | 3 Snake Free | ESC salir", self.font_small, MUTED, (330, 382))

    def draw_animated_logo(self):
        """Anima la serpiente hasta convertirla en la S del nombre."""
        self.text("NAKERSON", self.font_heading, GREEN, (66, 42))
        phase = (self.animation_time % 4.2) / 4.2
        if phase < 0.72:
            progress = phase / 0.72
            start_x, start_y = 45, 265
            target_x, target_y = 43, 57
            offset_x = start_x + (target_x - start_x) * progress
            offset_y = start_y + (target_y - start_y) * progress
        else:
            offset_x, offset_y = 43, 57
        points = [(offset_x + 14, offset_y + 24), (offset_x + 28, offset_y + 24), (offset_x + 42, offset_y + 24), (offset_x + 56, offset_y + 18), (offset_x + 66, offset_y + 6)]
        for index, (x, y) in enumerate(points):
            radius = 12 if index == len(points) - 1 else 9
            pulse = 1.0 + 0.06 * math.sin(self.animation_time * 4.0 + index)
            pygame.draw.circle(self.screen, (12, 52, 35), (int(x + 2), int(y + 3)), int(radius * pulse))
            pygame.draw.circle(self.screen, (35, 137, 85), (int(x), int(y)), int(radius * pulse))
        head_x, head_y = points[-1]
        pygame.draw.circle(self.screen, WHITE, (int(head_x + 4), int(head_y - 3)), 2)
        pygame.draw.circle(self.screen, WHITE, (int(head_x + 4), int(head_y + 3)), 2)

    def draw_levels(self):
        self.text("SELECCION DE NIVEL", self.font_heading, WHITE, (40, 40))
        self.text("Todos los niveles estan disponibles desde el inicio.", self.font_body, MUTED, (40, 82))
        for index, level in enumerate(LEVELS):
            col, row = index % 4, index // 4
            rect = pygame.Rect(70 + col * 285, 170 + row * 170, 250, 130)
            color = COLORS[level["color"]]
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            self.text(f"NIVEL {index + 1}", self.font_heading, color, (rect.x + 16, rect.y + 14))
            self.text(f"{level['target']} alimentos", self.font_small, WHITE, (rect.x + 16, rect.y + 65))
            self.text(f"Velocidad {level['speed']:.2f}x", self.font_small, MUTED, (rect.x + 16, rect.y + 92))
            self.text(f"{len(level['obstacles'])} bloques", self.font_small, MUTED, (rect.x + 16, rect.y + 113))
        self.button(pygame.Rect(40, 760, 190, 54), "VOLVER", MUTED)

    def draw_howto(self):
        self.text("COMO JUGAR", self.font_heading, GOLD, (40, 40))
        lines = ["Flechas o W/A/S/D: mover la serpiente", "La serpiente avanza automaticamente por la cuadricula", "Come alimentos para crecer y sumar puntos", "Cada 3 alimentos, cambia el color de la serpiente", "Chocar contra borde, cuerpo u obstaculo termina la partida", "Completa el objetivo antes de que termine el tiempo", "Snake Free solo se gana al llenar toda la pantalla", "ESC: volver al menu durante una partida"]
        for index, line in enumerate(lines):
            pygame.draw.circle(self.screen, GREEN, (65, 150 + index * 52), 5)
            self.text(line, self.font_body, WHITE, (85, 140 + index * 58))
        self.button(pygame.Rect(40, 760, 190, 54), "VOLVER", MUTED)

    def draw_clock(self, center, seconds, color=GOLD, radius=18):
        pygame.draw.circle(self.screen, (8, 16, 24), center, radius + 3)
        pygame.draw.circle(self.screen, color, center, radius, 2)
        pygame.draw.line(self.screen, color, center, (center[0], center[1] - radius + 6), 3)
        pygame.draw.line(self.screen, color, center, (center[0] + 8, center[1] + 5), 3)
        self.text(f"{max(0, int(seconds))}s", self.font_small, WHITE, (center[0] + radius + 8, center[1] - 8))

    def draw_game(self):
        board_rect = pygame.Rect(BOARD_X, BOARD_Y, BOARD, BOARD)
        pygame.draw.rect(self.screen, (16, 31, 41), board_rect)
        for x in range(GRID + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (BOARD_X + x * CELL, BOARD_Y), (BOARD_X + x * CELL, BOARD_Y + BOARD))
        for y in range(GRID + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (BOARD_X, BOARD_Y + y * CELL), (BOARD_X + BOARD, BOARD_Y + y * CELL))
        for x, y in self.obstacles:
            rect = pygame.Rect(BOARD_X + x * CELL + 5, BOARD_Y + y * CELL + 5, CELL - 10, CELL - 10)
            pygame.draw.rect(self.screen, (90, 108, 121), rect, border_radius=5)
            pygame.draw.line(self.screen, (185, 199, 208), rect.topleft, (rect.right - 4, rect.top), 2)
        for food in self.foods:
            fx, fy = food["position"]
            center = (BOARD_X + fx * CELL + CELL // 2, BOARD_Y + fy * CELL + CELL // 2)
            food_color = RED if food["time"] <= 3 else GOLD
            pulse = 1.0 + 0.14 * math.sin(self.animation_time * 5.0 + fx + fy)
            glow_radius = int(18 * pulse)
            glow = pygame.Surface((glow_radius * 2 + 8, glow_radius * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*food_color, 38), (glow.get_width() // 2, glow.get_height() // 2), glow_radius)
            self.screen.blit(glow, (center[0] - glow.get_width() // 2, center[1] - glow.get_height() // 2))
            pygame.draw.circle(self.screen, (117, 82, 18), (center[0], center[1] + 2), int(15 * pulse))
            pygame.draw.circle(self.screen, food_color, center, int(11 * pulse))
            pygame.draw.arc(self.screen, WHITE, pygame.Rect(center[0] - 16, center[1] - 16, 32, 32), -1.57, -1.57 + 6.28 * food["time"] / FOOD_LIFETIME, 2)
        for index, (x, y) in enumerate(self.snake):
            rect = pygame.Rect(BOARD_X + x * CELL + 4, BOARD_Y + y * CELL + 4, CELL - 8, CELL - 8)
            base_color = COLORS[self.snake_color]
            dark_color = tuple(max(0, channel - 72) for channel in base_color)
            light_color = tuple(min(255, channel + 46) for channel in base_color)
            if index == 0:
                head_pulse = int(3 + 2 * math.sin(self.animation_time * 4.0))
                pygame.draw.ellipse(self.screen, (*base_color, 55), rect.inflate(head_pulse * 2, head_pulse * 2))
            pygame.draw.ellipse(self.screen, (5, 12, 9), rect.move(3, 4))
            pygame.draw.ellipse(self.screen, dark_color, rect)
            pygame.draw.ellipse(self.screen, base_color, rect.inflate(-3, -3))
            pygame.draw.arc(self.screen, light_color, rect.inflate(-6, -6), 3.4, 5.9, 2)
            pygame.draw.arc(self.screen, (235, 255, 235), rect.inflate(-9, -9), 3.7, 5.1, 1)
            if index == 0:
                pygame.draw.circle(self.screen, WHITE, (rect.centerx + (7 if self.direction == "right" else -7), rect.centery - 5), 3)
                pygame.draw.circle(self.screen, WHITE, (rect.centerx + (7 if self.direction == "right" else -7), rect.centery + 5), 3)
        hud = pygame.Surface((300, 142), pygame.SRCALPHA)
        hud.fill((5, 12, 20, 190))
        self.screen.blit(hud, (BOARD_X + BOARD - 320, BOARD_Y + 18))
        hud_x = BOARD_X + BOARD - 300
        title = "SNAKE FREE" if self.mode == "free" else f"NIVEL {self.level_id}"
        title_color = COLORS["CYAN"] if self.mode == "free" else COLORS[self.level["color"]]
        self.text(title, self.font_heading, title_color, (hud_x, BOARD_Y + 30))
        score = self.food_count * 10 * (self.level_id or 1)
        self.text(f"Puntaje  {score}", self.font_body, WHITE, (hud_x, BOARD_Y + 72))
        food_label = f"Comida  {self.food_count}"
        if self.mode == "free":
            food_label = f"Pantalla  {len(self.snake)}/{GRID * GRID}"
        self.text(food_label, self.font_body, WHITE, (hud_x, BOARD_Y + 100))
        if self.time_left is None:
            self.text("Sin limite de nivel", self.font_small, GOLD, (hud_x + 148, BOARD_Y + 75))
        else:
            self.draw_clock((hud_x + 205, BOARD_Y + 116), self.time_left)
        self.text("Alimentos: 8s cada uno", self.font_small, MUTED, (BOARD_X + 18, BOARD_Y + BOARD - 28))
        instruction = "PRESIONA UNA FLECHA" if not self.started else "Flechas / WASD"
        instruction_color = GOLD if not self.started else MUTED
        self.text(instruction, self.font_small, instruction_color, (BOARD_X + 18, BOARD_Y + BOARD - 66))
        self.text("ESC  volver al menu", self.font_small, MUTED, (BOARD_X + 18, BOARD_Y + BOARD - 38))

    def draw_stats(self):
        total, wins, score, average, recent = database_summary()
        self.text("DESEMPENO Y PARTIDAS", self.font_heading, WHITE, (40, 40))
        self.text("Historial guardado en la base de datos local", self.font_body, MUTED, (40, 82))
        self.text(f"Partidas: {total}", self.font_body, GREEN, (40, 140))
        self.text(f"Victorias: {wins}", self.font_body, GOLD, (220, 140))
        self.text(f"Puntaje total: {score}", self.font_body, WHITE, (400, 140))
        self.text(f"Promedio: {average:.1f}", self.font_body, COLORS["CYAN"], (650, 140))
        self.text("ULTIMAS PARTIDAS", self.font_heading, COLORS["CYAN"], (40, 205))
        for x, label in ((40, "MODO"), (240, "RESULTADO"), (410, "PUNTOS"), (560, "FECHA")):
            self.text(label, self.font_small, MUTED, (x, 250))
        for index, (mode, level, won, game_score, played_at) in enumerate(recent):
            y = 285 + index * 34
            mode_label = "SNAKE FREE" if mode == "free" else f"NIVEL {level}"
            result_label = "VICTORIA" if won else "DERROTA"
            self.text(mode_label, self.font_small, WHITE, (40, y))
            self.text(result_label, self.font_small, GREEN if won else RED, (240, y))
            self.text(str(game_score), self.font_small, WHITE, (410, y))
            self.text(played_at.replace("T", " "), self.font_small, MUTED, (560, y))
        self.button(pygame.Rect(40, 760, 190, 54), "VOLVER", MUTED)

    def draw_result(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 9, 14, 185))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(160, 75, 480, 650)
        pygame.draw.rect(self.screen, PANEL, box, border_radius=12)
        color = GREEN if self.result_won else RED
        result_title = "SNAKE FREE COMPLETADO" if self.result_won and self.mode == "free" else "NIVEL SUPERADO" if self.result_won else "GAME OVER"
        self.text(result_title, self.font_heading, color, (190, 125))
        self.text(self.result_reason, self.font_body, WHITE, (190, 195))
        self.text(f"Alimentos: {self.food_count}", self.font_body, MUTED, (190, 245))
        self.text(f"Puntaje: {self.score}", self.font_body, WHITE, (190, 285))
        self.button(pygame.Rect(200, 500, 400, 56), "REPETIR PARTIDA", color)
        self.button(pygame.Rect(200, 565, 400, 56), "MENU PRINCIPAL", PANEL_LIGHT)
        if self.next_level:
            self.button(pygame.Rect(200, 630, 400, 56), "SIGUIENTE NIVEL", GOLD)


def main():
    Game().run()


if __name__ == "__main__":
    main()