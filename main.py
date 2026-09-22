"""Snakerson: Snake clasico para escritorio, implementado con Pygame."""

import json
import os
import random
import sqlite3
import sys
from datetime import datetime
import pygame

pygame.init()

WIDTH, HEIGHT = 960, 680
BOARD = 512
CELL = 32
GRID = 16
FPS = 60
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
        self.font_title = pygame.font.SysFont("segoeuisemibold", 44)
        self.font_heading = pygame.font.SysFont("segoeuisemibold", 26)
        self.font_body = pygame.font.SysFont("segoeui", 18)
        self.font_small = pygame.font.SysFont("segoeui", 14)
        self.progress = load_progress()
        initialize_database()
        self.state = "menu"
        self.selected_level = 1
        self.running = True
        self.last_move = 0

    def text(self, value, font, color, position, center=False):
        surface = font.render(value, True, color)
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rect)
        return rect

    def button(self, rect, label, accent=GREEN):
        mouse = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse)
        color = tuple(min(255, channel + 18) for channel in PANEL_LIGHT) if hovered else PANEL_LIGHT
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, accent if hovered else (45, 70, 88), rect, 1, border_radius=8)
        self.text(label, self.font_body, WHITE, rect.center, True)
        return hovered

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
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
                self.state = "menu"
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
            if pygame.Rect(585, 250, 300, 52).collidepoint(position):
                self.start_level(self.selected_level)
            elif pygame.Rect(585, 306, 300, 52).collidepoint(position):
                self.start_free_mode()
            elif pygame.Rect(585, 362, 300, 52).collidepoint(position):
                self.state = "levels"
            elif pygame.Rect(585, 418, 300, 52).collidepoint(position):
                self.state = "stats"
            elif pygame.Rect(585, 474, 300, 52).collidepoint(position):
                self.state = "howto"
            elif pygame.Rect(585, 530, 300, 52).collidepoint(position):
                self.running = False
        elif self.state == "levels":
            for index in range(7):
                col, row = index % 4, index // 4
                rect = pygame.Rect(90 + col * 200, 180 + row * 150, 170, 105)
                if rect.collidepoint(position):
                    self.selected_level = index + 1
                    self.start_level(self.selected_level)
                    return
            if pygame.Rect(40, 590, 150, 45).collidepoint(position):
                self.state = "menu"
        elif self.state == "howto" and pygame.Rect(40, 590, 150, 45).collidepoint(position):
            self.state = "menu"
        elif self.state == "stats" and pygame.Rect(40, 590, 150, 45).collidepoint(position):
            self.state = "menu"
        elif self.state == "result":
            if pygame.Rect(585, 420, 300, 48).collidepoint(position):
                if self.mode == "free":
                    self.start_free_mode()
                else:
                    self.start_level(self.level_id)
            elif pygame.Rect(585, 480, 300, 48).collidepoint(position):
                self.state = "menu"
            elif self.next_level and pygame.Rect(585, 540, 300, 48).collidepoint(position):
                self.start_level(self.next_level)

    def start_level(self, level_id):
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
        self.food = self.spawn_food()
        self.state = "playing"
        self.last_move = 0
        self.started = False

    def start_free_mode(self):
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
        self.food = self.spawn_food()
        self.state = "playing"
        self.last_move = 0
        self.started = False

    def spawn_food(self):
        free = [(x, y) for x in range(GRID) for y in range(GRID) if (x, y) not in self.snake and (x, y) not in self.obstacles]
        return random.choice(free)

    def update(self, dt):
        if not self.started:
            return
        if self.time_left is not None:
            self.time_left -= dt
            if self.time_left <= 0:
                self.finish(False, "Se acabo el tiempo")
                return
        self.last_move += dt
        interval = 0.22 / self.level["speed"]
        if self.last_move < interval:
            return
        self.last_move -= interval
        self.direction = self.pending_direction
        dx, dy = DIRECTIONS[self.direction]
        head = self.snake[0]
        new_head = (head[0] + dx, head[1] + dy)
        eating = new_head == self.food
        body = self.snake if eating else self.snake[:-1]
        outside = not (0 <= new_head[0] < GRID and 0 <= new_head[1] < GRID)
        if outside or new_head in body or new_head in self.obstacles:
            self.finish(False, "Colision detectada")
            return
        self.snake.insert(0, new_head)
        if eating:
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
            self.food = self.spawn_food()
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
        self.next_level = self.level_id + 1 if won and self.level_id < len(LEVELS) else None
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
        pygame.draw.rect(self.screen, (14, 28, 39), (40, 40, 470, 600), border_radius=12)
        self.text("SNAKERSON", self.font_title, GREEN, (78, 82))
        self.text("SNAKE ESPACIAL  /  7 NIVELES", self.font_small, MUTED, (82, 140))
        for index, (x, y) in enumerate([(100, 470), (140, 470), (180, 470), (220, 470), (260, 470), (300, 430), (340, 390), (380, 350)]):
            pygame.draw.circle(self.screen, (35, 137, 85), (x, y), 14 if index < 7 else 17)
        pygame.draw.circle(self.screen, BG, (388, 342), 3)
        self.text("COME  /  CRECE  /  EVOLUCIONA", self.font_small, MUTED, (78, 575))
        self.text("Tu partida", self.font_small, MUTED, (585, 92))
        self.text("7 niveles disponibles", self.font_heading, WHITE, (585, 120))
        self.text("Cada nivel aumenta velocidad y obstaculos", self.font_small, MUTED, (585, 165))
        self.button(pygame.Rect(585, 250, 300, 52), "JUGAR AHORA", GREEN)
        self.button(pygame.Rect(585, 306, 300, 52), "SNAKE FREE", COLORS["CYAN"])
        self.button(pygame.Rect(585, 362, 300, 52), "SELECCIONAR NIVEL", COLORS["CYAN"])
        self.button(pygame.Rect(585, 418, 300, 52), "DESEMPENO Y PARTIDAS", GOLD)
        self.button(pygame.Rect(585, 474, 300, 52), "COMO JUGAR", GOLD)
        self.button(pygame.Rect(585, 530, 300, 52), "SALIR", RED)
        self.text("ENTER: jugar  |  3: Snake Free  |  ESC: salir", self.font_small, MUTED, (585, 605))

    def draw_levels(self):
        self.text("SELECCION DE NIVEL", self.font_heading, WHITE, (40, 40))
        self.text("Todos los niveles estan disponibles desde el inicio.", self.font_body, MUTED, (40, 82))
        for index, level in enumerate(LEVELS):
            col, row = index % 4, index // 4
            rect = pygame.Rect(90 + col * 200, 180 + row * 150, 170, 105)
            color = COLORS[level["color"]]
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, color, rect, 2, border_radius=10)
            self.text(f"NIVEL {index + 1}", self.font_heading, color, (rect.x + 16, rect.y + 14))
            self.text(f"{level['target']} alimentos", self.font_small, WHITE, (rect.x + 16, rect.y + 55))
            self.text(f"Velocidad {level['speed']:.2f}x  |  {len(level['obstacles'])} bloques", self.font_small, MUTED, (rect.x + 16, rect.y + 78))
        self.button(pygame.Rect(40, 590, 150, 45), "VOLVER", MUTED)

    def draw_howto(self):
        self.text("COMO JUGAR", self.font_heading, GOLD, (40, 40))
        lines = ["Flechas o W/A/S/D: mover la serpiente", "La serpiente avanza automaticamente por la cuadricula", "Come alimentos para crecer y sumar puntos", "Cada 3 alimentos, cambia el color de la serpiente", "Chocar contra borde, cuerpo u obstaculo termina la partida", "Completa el objetivo antes de que termine el tiempo", "Snake Free solo se gana al llenar toda la pantalla", "ESC: volver al menu durante una partida"]
        for index, line in enumerate(lines):
            pygame.draw.circle(self.screen, GREEN, (65, 150 + index * 52), 5)
            self.text(line, self.font_body, WHITE, (85, 140 + index * 52))
        self.button(pygame.Rect(40, 590, 150, 45), "VOLVER", MUTED)

    def draw_game(self):
        board_rect = pygame.Rect(40, 84, BOARD, BOARD)
        pygame.draw.rect(self.screen, (16, 31, 41), board_rect)
        for x in range(GRID + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (40 + x * CELL, 84), (40 + x * CELL, 84 + BOARD))
        for y in range(GRID + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (40, 84 + y * CELL), (40 + BOARD, 84 + y * CELL))
        for x, y in self.obstacles:
            rect = pygame.Rect(40 + x * CELL + 4, 84 + y * CELL + 4, CELL - 8, CELL - 8)
            pygame.draw.rect(self.screen, (90, 108, 121), rect, border_radius=5)
            pygame.draw.line(self.screen, (185, 199, 208), rect.topleft, (rect.right - 4, rect.top), 2)
        fx, fy = self.food
        pygame.draw.circle(self.screen, (117, 82, 18), (40 + fx * CELL + 16, 84 + fy * CELL + 17), 12)
        pygame.draw.circle(self.screen, GOLD, (40 + fx * CELL + 16, 84 + fy * CELL + 15), 9)
        for index, (x, y) in enumerate(self.snake):
            rect = pygame.Rect(40 + x * CELL + 3, 84 + y * CELL + 3, CELL - 6, CELL - 6)
            base_color = COLORS[self.snake_color]
            dark_color = tuple(max(0, channel - 72) for channel in base_color)
            light_color = tuple(min(255, channel + 46) for channel in base_color)
            pygame.draw.ellipse(self.screen, (5, 12, 9), rect.move(3, 4))
            pygame.draw.ellipse(self.screen, dark_color, rect)
            pygame.draw.ellipse(self.screen, base_color, rect.inflate(-3, -3))
            pygame.draw.arc(self.screen, light_color, rect.inflate(-6, -6), 3.4, 5.9, 2)
            pygame.draw.arc(self.screen, (235, 255, 235), rect.inflate(-9, -9), 3.7, 5.1, 1)
            if index == 0:
                pygame.draw.circle(self.screen, WHITE, (rect.centerx + (7 if self.direction == "right" else -7), rect.centery - 5), 3)
                pygame.draw.circle(self.screen, WHITE, (rect.centerx + (7 if self.direction == "right" else -7), rect.centery + 5), 3)
        if self.mode == "free":
            self.text("SNAKE FREE", self.font_heading, COLORS["CYAN"], (590, 85))
            self.text(f"Pantalla  {len(self.snake)}/{GRID * GRID}", self.font_body, WHITE, (590, 150))
            self.text("Sin limite de tiempo", self.font_body, GOLD, (590, 185))
            self.text(f"Puntaje  {self.food_count * 10}", self.font_body, WHITE, (590, 220))
        else:
            self.text(f"NIVEL {self.level_id}", self.font_heading, COLORS[self.level["color"]], (590, 85))
            self.text(f"Alimentos  {self.food_count}/{self.level['target']}", self.font_body, WHITE, (590, 150))
            self.text(f"Tiempo  {max(0, int(self.time_left))}s", self.font_body, GOLD, (590, 185))
            self.text(f"Puntaje  {self.food_count * 10 * self.level_id}", self.font_body, WHITE, (590, 220))
        instruction = "PRESIONA UNA FLECHA" if not self.started else "Flechas / WASD"
        instruction_color = GOLD if not self.started else MUTED
        self.text(instruction, self.font_small, instruction_color, (590, 550))
        self.text("ESC  volver al menu", self.font_small, MUTED, (590, 575))

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
        self.button(pygame.Rect(40, 590, 150, 45), "VOLVER", MUTED)

    def draw_result(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 9, 14, 185))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(535, 110, 370, 470)
        pygame.draw.rect(self.screen, PANEL, box, border_radius=12)
        color = GREEN if self.result_won else RED
        result_title = "SNAKE FREE COMPLETADO" if self.result_won and self.mode == "free" else "NIVEL SUPERADO" if self.result_won else "GAME OVER"
        self.text(result_title, self.font_heading, color, (585, 145))
        self.text(self.result_reason, self.font_body, WHITE, (585, 205))
        self.text(f"Alimentos: {self.food_count}", self.font_body, MUTED, (585, 250))
        self.text(f"Puntaje: {self.score}", self.font_body, WHITE, (585, 280))
        self.button(pygame.Rect(585, 420, 300, 48), "REPETIR PARTIDA", color)
        self.button(pygame.Rect(585, 480, 300, 48), "MENU PRINCIPAL", PANEL_LIGHT)
        if self.next_level:
            self.button(pygame.Rect(585, 540, 300, 48), "SIGUIENTE NIVEL", GOLD)


def main():
    Game().run()


if __name__ == "__main__":
    main()