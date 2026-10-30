import os
import random
from pathlib import Path
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import soduku


# ---------------------------------------------------------------------------
# Window, board, and theme settings
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 860
WINDOW_HEIGHT = 720
CELL_SIZE = 58
GRID_SIZE = CELL_SIZE * 9
GRID_LEFT = 42
GRID_TOP = 126
UI_FONT_FAMILY = "Consolas"
TITLE_LOGO_SIZE = (192, 72)

# Colors
BACKGROUND = (0, 0, 0)
CELL_COLOR = (0, 0, 0)
GRID_COLOR = (255, 0, 170)
MAJOR_GRID_COLOR = (0, 255, 40)
TEXT_COLOR = (255, 255, 255)
CLUE_COLOR = (255, 255, 255)
PLAYER_COLOR = (0, 255, 40)
INCORRECT_COLOR = (255, 0, 55)
UNKNOWN_GUESS_COLOR = (255, 115, 0)
SELECTED_COLOR = (0, 95, 25)
RELATED_COLOR = (0, 35, 10)
HINT_CELL_COLOR = (55, 45, 0)
BUTTON_COLOR = (0, 0, 0)
BUTTON_HOVER_COLOR = (0, 105, 25)
BUTTON_TEXT_COLOR = (255, 255, 255)
MUTED_COLOR = (190, 205, 215)
SUCCESS_COLOR = (0, 255, 40)
ERROR_COLOR = (255, 0, 55)
WARNING_COLOR = (255, 115, 0)
HINT_COLOR = (255, 245, 0)

# Streak and hint settings
STREAK_GAIN = 20
STREAK_INCORRECT_PENALTY = int(STREAK_GAIN * 1.25)
STREAK_DECAY_PER_SECOND = 2
STREAK_MIN_DECAY_PER_SECOND = STREAK_DECAY_PER_SECOND / 5
HINT_MAX_DELAY = 4.0
HINT_MIN_DELAY = 0.5
HINT_ANSWER_FADE_SECONDS = 10.0
HINT_ANSWER_STREAK_LIMIT = 25
ENTRY_FEEDBACK_DURATION = 0.45
TICKER_SPEED = 42
TICKER_WIDTH = 585
TICKER_HEIGHT = 60
TICKER_RIGHT = WINDOW_WIDTH - 24
TICKER_BOTTOM = 72

# Difficulty modes
DIFFICULTY_MODES = [
    {"name": "Zoomer", "logic": "easy", "highlights": True, "hints": True},
    {"name": "Kid Gloves", "logic": "easy", "highlights": True, "hints": False},
    {"name": "Insightful", "logic": "easy", "highlights": False, "hints": False},
    {"name": "Sharp", "logic": "hard", "highlights": True, "hints": True},
    {"name": "Unc", "logic": "hard", "highlights": True, "hints": False},
    {
        "name": "Dopamine Deprived",
        "logic": "hard",
        "highlights": False,
        "hints": False,
    },
]


# ---------------------------------------------------------------------------
# Puzzle setup and gameplay calculations
# ---------------------------------------------------------------------------

def new_game(mode):
    puzzle, solution = soduku.generate_random_board(mode["logic"])
    if mode["logic"] == "easy":
        strategies = [soduku.find_naked_single]
    else:
        strategies = soduku.LOGIC_STRATEGIES

    solve_result = soduku.solve_logically(puzzle, strategies)
    if solve_result["status"] != "solved":
        raise RuntimeError("Generated puzzle could not be solved logically.")

    return (
        [row[:] for row in puzzle],
        [row[:] for row in puzzle],
        [row[:] for row in solution],
        solve_result["moves"],
    )


def get_next_mode(mode):
    current_index = next(
        index for index, option in enumerate(DIFFICULTY_MODES)
        if option["name"] == mode["name"]
    )
    return DIFFICULTY_MODES[(current_index + 1) % len(DIFFICULTY_MODES)]


def get_next_hint_cell(logical_steps, board):
    for row, col, number, _ in logical_steps:
        if board[row][col] != number:
            return row, col
    return None


def get_hint_answer(logical_steps, board, hint_cell):
    if hint_cell is None:
        return None
    for row, col, number, _ in logical_steps:
        if (row, col) == hint_cell and board[row][col] != number:
            return number
    return None


def get_hint_answer_alpha(streak, elapsed_seconds):
    if streak >= HINT_ANSWER_STREAK_LIMIT:
        return 0
    progress = max(0, min(1, elapsed_seconds / HINT_ANSWER_FADE_SECONDS))
    return int(255 * progress)


def get_hint_delay(streak):
    progress = max(0, min(100, streak)) / 100
    return HINT_MAX_DELAY - progress * (HINT_MAX_DELAY - HINT_MIN_DELAY)


def get_streak_decay_rate(streak):
    progress = max(0, min(100, streak)) / 100
    decay_range = STREAK_DECAY_PER_SECOND - STREAK_MIN_DECAY_PER_SECOND
    return STREAK_MIN_DECAY_PER_SECOND + progress * decay_range


def update_game_time(elapsed_seconds, hint_elapsed, streak, delta_time):
    elapsed_seconds += delta_time
    hint_elapsed += delta_time
    decay_rate = get_streak_decay_rate(streak)
    streak = max(0, streak - decay_rate * delta_time)
    return elapsed_seconds, hint_elapsed, streak


def update_hint(
        logical_steps, board, mode, game_started, game_solved, hint_elapsed,
        streak,
        active_hint_cell, hint_answer_elapsed, delta_time):
    hint_cell = None
    if game_started and not game_solved and mode["highlights"]:
        next_cell = get_next_hint_cell(logical_steps, board)
        if next_cell and hint_elapsed_is_ready(hint_elapsed, streak):
            hint_cell = next_cell

    hint_just_appeared = hint_cell != active_hint_cell
    if hint_just_appeared:
        active_hint_cell = hint_cell
        hint_answer_elapsed = 0.0
    elif hint_cell is not None and streak < HINT_ANSWER_STREAK_LIMIT:
        hint_answer_elapsed += delta_time

    hint_answer = None
    hint_answer_alpha = 0
    if mode["hints"]:
        hint_answer = get_hint_answer(logical_steps, board, hint_cell)
        hint_answer_alpha = get_hint_answer_alpha(streak, hint_answer_elapsed)

    return (
        hint_cell,
        active_hint_cell,
        hint_answer_elapsed,
        hint_answer,
        hint_answer_alpha,
    )


def hint_elapsed_is_ready(hint_elapsed, streak):
    return hint_elapsed >= get_hint_delay(streak)


def format_elapsed_time(elapsed_seconds):
    total_seconds = int(elapsed_seconds)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"


# ---------------------------------------------------------------------------
# Window and mouse-coordinate helpers
# ---------------------------------------------------------------------------

def cell_at_position(position):
    x, y = position
    if not (GRID_LEFT <= x < GRID_LEFT + GRID_SIZE
            and GRID_TOP <= y < GRID_TOP + GRID_SIZE):
        return None

    col = (x - GRID_LEFT) // CELL_SIZE
    row = (y - GRID_TOP) // CELL_SIZE
    return row, col


def move_selection(selected_cell, key, ctrl_held=False):
    if selected_cell is None:
        row, col = 4, 4
    else:
        row, col = selected_cell

    step = 3 if ctrl_held else 1
    if key == pygame.K_UP:
        row -= step
    elif key == pygame.K_DOWN:
        row += step
    elif key == pygame.K_LEFT:
        col -= step
    elif key == pygame.K_RIGHT:
        col += step

    row = max(0, min(8, row))
    col = max(0, min(8, col))
    return row, col


def get_display_viewport(display_size):
    display_width, display_height = display_size
    scale = min(display_width / WINDOW_WIDTH, display_height / WINDOW_HEIGHT)
    viewport_width = round(WINDOW_WIDTH * scale)
    viewport_height = round(WINDOW_HEIGHT * scale)
    left = (display_width - viewport_width) // 2
    top = (display_height - viewport_height) // 2
    return pygame.Rect(left, top, viewport_width, viewport_height)


def map_to_ui_position(position, viewport):
    if not viewport.collidepoint(position):
        return None

    x = round((position[0] - viewport.left) * WINDOW_WIDTH / viewport.width)
    y = round((position[1] - viewport.top) * WINDOW_HEIGHT / viewport.height)
    return x, y


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_button(screen, font, rectangle, label, mouse_position):
    is_hovered = (
        mouse_position is not None and rectangle.collidepoint(mouse_position)
    )
    color = BUTTON_HOVER_COLOR if is_hovered else BUTTON_COLOR
    pygame.draw.rect(screen, color, rectangle, border_radius=8)
    pygame.draw.rect(screen, MAJOR_GRID_COLOR, rectangle, width=2, border_radius=8)
    text = font.render(label, True, BUTTON_TEXT_COLOR)
    screen.blit(text, text.get_rect(center=rectangle.center))


def draw_board_cell(
        screen, board, starting_board, selected_cell, font,
        unknown_guess_cells, row, col, hint_cell, hint_answer,
        hint_answer_alpha, feedback_values):
    rectangle = pygame.Rect(
        GRID_LEFT + col * CELL_SIZE,
        GRID_TOP + row * CELL_SIZE,
        CELL_SIZE,
        CELL_SIZE,
    )
    cell = (row, col)

    pygame.draw.rect(screen, CELL_COLOR, rectangle)
    if selected_cell == cell:
        pygame.draw.rect(screen, SELECTED_COLOR, rectangle)
    elif selected_cell and (
            selected_cell[0] == row or selected_cell[1] == col):
        pygame.draw.rect(screen, RELATED_COLOR, rectangle)

    if hint_cell == cell and selected_cell != cell:
        pygame.draw.rect(screen, HINT_CELL_COLOR, rectangle)

    number = board[row][col]
    if number:
        if starting_board[row][col]:
            color = CLUE_COLOR
        elif not soduku.is_valid(board, cell, number):
            color = INCORRECT_COLOR
        elif cell in unknown_guess_cells:
            color = UNKNOWN_GUESS_COLOR
        else:
            color = PLAYER_COLOR

        display_number = feedback_values.get(cell, number)
        text = font.render(str(display_number), True, color)
        screen.blit(text, text.get_rect(center=rectangle.center))

    if hint_cell == cell and hint_answer is not None:
        answer_text = font.render(str(hint_answer), True, HINT_COLOR)
        answer_text.set_alpha(hint_answer_alpha)
        screen.blit(answer_text, answer_text.get_rect(center=rectangle.center))

    if hint_cell == cell:
        pygame.draw.rect(screen, HINT_COLOR, rectangle, width=4)


def draw_grid_lines(screen):
    for line in range(10):
        line_width = 4 if line % 3 == 0 else 2
        line_color = MAJOR_GRID_COLOR if line % 3 == 0 else GRID_COLOR
        x = GRID_LEFT + line * CELL_SIZE
        y = GRID_TOP + line * CELL_SIZE
        pygame.draw.line(
            screen,
            line_color,
            (x, GRID_TOP),
            (x, GRID_TOP + GRID_SIZE),
            line_width,
        )
        pygame.draw.line(
            screen,
            line_color,
            (GRID_LEFT, y),
            (GRID_LEFT + GRID_SIZE, y),
            line_width,
        )


def draw_board(
        screen, board, starting_board, selected_cell, font, unknown_guess_cells,
        hint_cell=None, hint_answer=None, hint_answer_alpha=0,
        feedback_values=None):
    feedback_values = feedback_values or {}
    for row in range(9):
        for col in range(9):
            draw_board_cell(
                screen,
                board,
                starting_board,
                selected_cell,
                font,
                unknown_guess_cells,
                row,
                col,
                hint_cell,
                hint_answer,
                hint_answer_alpha,
                feedback_values,
            )
    draw_grid_lines(screen)


def draw_timer_and_streak(screen, elapsed_seconds, streak):
    hud_font = pygame.font.SysFont(UI_FONT_FAMILY, 19, bold=True)
    timer_text = hud_font.render(
        f"TIME  {format_elapsed_time(elapsed_seconds)}", True, TEXT_COLOR
    )
    screen.blit(timer_text, (GRID_LEFT, GRID_TOP - 34))
    streak_label = hud_font.render("STREAK", True, TEXT_COLOR)
    screen.blit(streak_label, (GRID_LEFT + 190, GRID_TOP - 34))

    gauge = pygame.Rect(GRID_LEFT + 278, GRID_TOP - 30, 240, 20)
    pygame.draw.rect(screen, CELL_COLOR, gauge, border_radius=5)
    pygame.draw.rect(screen, GRID_COLOR, gauge, width=2, border_radius=5)
    fill_progress = max(0, min(100, streak)) / 100
    fill_width = int((gauge.width - 4) * fill_progress)
    if fill_width:
        fill_left = gauge.left + 2
        fill_top = gauge.top + 2
        fill_height = gauge.height - 4
        for offset in range(fill_width):
            gradient_progress = offset / max(1, fill_width - 1)
            fill_color = interpolate_color(
                SUCCESS_COLOR, GRID_COLOR, gradient_progress
            )
            pygame.draw.line(
                screen,
                fill_color,
                (fill_left + offset, fill_top),
                (fill_left + offset, fill_top + fill_height - 1),
            )


def interpolate_color(start_color, end_color, progress):
    progress = max(0, min(1, progress))
    return tuple(
        round(start + (end - start) * progress)
        for start, end in zip(start_color, end_color)
    )


def draw_reveal_prompt(screen):
    board_area = pygame.Rect(GRID_LEFT, GRID_TOP, GRID_SIZE, GRID_SIZE)
    pygame.draw.rect(screen, BACKGROUND, board_area)
    pygame.draw.rect(screen, MAJOR_GRID_COLOR, board_area, width=4)

    prompt_font = pygame.font.SysFont(UI_FONT_FAMILY, 30, bold=True)
    prompt = prompt_font.render("PRESS SPACE", True, SUCCESS_COLOR)
    screen.blit(prompt, prompt.get_rect(center=board_area.center))

    sub_prompt = pygame.font.SysFont(UI_FONT_FAMILY, 18).render(
        "The timer starts when the board is revealed.", True, TEXT_COLOR
    )
    screen.blit(
        sub_prompt,
        sub_prompt.get_rect(center=(board_area.centerx, board_area.centery + 38)),
    )


def get_assistance_label(mode):
    if mode["highlights"] and mode["hints"]:
        return "Highlights + hints"
    if mode["highlights"]:
        return "Highlights only"
    return "No highlights or hints"


def get_status_color(status):
    if "conflict" in status.lower():
        return ERROR_COLOR
    if "unknown guess" in status.lower():
        return WARNING_COLOR
    if status in ("Puzzle solved!", "Good move.", "Timer started."):
        return SUCCESS_COLOR
    return MUTED_COLOR


def get_control_buttons():
    panel_left = GRID_LEFT + GRID_SIZE + 38
    return (
        pygame.Rect(panel_left, GRID_TOP + 58, 234, 42),
        pygame.Rect(panel_left, GRID_TOP + 114, 234, 44),
        pygame.Rect(panel_left, GRID_TOP + 174, 234, 44),
    )


def load_title_logo():
    logo_path = Path(__file__).with_name("Sprite-0001.svg")
    logo = pygame.image.load(str(logo_path))
    return pygame.transform.scale(logo, TITLE_LOGO_SIZE)


def load_ticker_messages(message_file=None):
    if message_file is None:
        if getattr(sys, "frozen", False):
            message_file = Path(sys.executable).resolve().with_name(
                "ticker_messages.txt"
            )
        else:
            message_file = Path(__file__).with_name("ticker_messages.txt")
    else:
        message_file = Path(message_file)

    try:
        messages = [
            line.strip()
            for line in message_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except OSError as error:
        raise RuntimeError(
            f"Could not load ticker messages from {message_file}."
        ) from error

    if not messages:
        raise ValueError(f"No ticker messages found in {message_file}.")
    return messages


def create_ticker_surface(messages):
    ticker_font = pygame.font.SysFont(UI_FONT_FAMILY, 24, bold=True)
    ticker_text = "   //   ".join(messages) + "   //   "
    return ticker_font.render(ticker_text, True, PLAYER_COLOR)


def draw_ticker(screen, ticker_surface, offset):
    ticker = pygame.Rect(
        TICKER_RIGHT - TICKER_WIDTH,
        TICKER_BOTTOM - TICKER_HEIGHT,
        TICKER_WIDTH,
        TICKER_HEIGHT,
    )
    pygame.draw.rect(screen, CELL_COLOR, ticker)
    pygame.draw.rect(screen, GRID_COLOR, ticker, width=2)

    old_clip = screen.get_clip()
    text_area = ticker.inflate(-8, -4)
    screen.set_clip(text_area)

    x = text_area.left - offset
    text_y = ticker.centery - ticker_surface.get_height() // 2
    while x < text_area.right:
        screen.blit(ticker_surface, (x, text_y))
        x += ticker_surface.get_width()

    screen.set_clip(old_clip)


def draw_mode_panel(screen, mode, fullscreen, mouse_position):
    normal_font = pygame.font.SysFont(UI_FONT_FAMILY, 22)
    small_font = pygame.font.SysFont(UI_FONT_FAMILY, 17)
    panel_left = GRID_LEFT + GRID_SIZE + 38
    subtitle = normal_font.render("Choose a mode", True, TEXT_COLOR)
    screen.blit(subtitle, (panel_left, GRID_TOP + 10))

    difficulty_button, new_button, fullscreen_button = get_control_buttons()
    draw_button(
        screen, normal_font, difficulty_button, mode["name"], mouse_position
    )
    draw_button(screen, normal_font, new_button, "New puzzle", mouse_position)
    fullscreen_label = "Exit fullscreen" if fullscreen else "Enter fullscreen"
    draw_button(
        screen, normal_font, fullscreen_button, fullscreen_label, mouse_position
    )

    instruction_lines = [
        f"Logic: {mode['logic'].title()}",
        get_assistance_label(mode),
        "Click a square; press 1-9",
        "to enter a number.",
        "Red: conflicts with Sudoku rules.",
        "Orange: differs from generated answer.",
        "Backspace/Delete clears it.",
        "Arrow keys move selection.",
        "Ctrl+arrows move 3 cells.",
        "Correct answers build streak; it decays.",
        "Below 25%, hints fade in after 10s.",
        "F11 toggles fullscreen.",
    ]
    for index, line in enumerate(instruction_lines):
        text = small_font.render(line, True, MUTED_COLOR)
        screen.blit(text, (panel_left, GRID_TOP + 232 + index * 26))


def draw_status(screen, status):
    small_font = pygame.font.SysFont(UI_FONT_FAMILY, 17)
    status_text = small_font.render(status, True, get_status_color(status))
    screen.blit(status_text, (GRID_LEFT, GRID_TOP + GRID_SIZE + 20))


def draw_screen(
        screen, board, starting_board, selected_cell, mode, status,
        fullscreen, mouse_position, unknown_guess_cells=None, revealed=False,
        elapsed_seconds=0, streak=0, hint_cell=None, hint_answer=None,
        hint_answer_alpha=0, feedback_values=None, ticker_surface=None,
        ticker_offset=0, title_logo=None):
    screen.fill(BACKGROUND)

    board_font = pygame.font.SysFont(UI_FONT_FAMILY, 30, bold=True)
    if title_logo is None:
        title_font = pygame.font.SysFont(UI_FONT_FAMILY, 34, bold=True)
        title = title_font.render("Sudoku", True, TEXT_COLOR)
        screen.blit(title, (GRID_LEFT, 42))
    else:
        screen.blit(title_logo, (GRID_LEFT, 5))

    draw_board(
        screen,
        board,
        starting_board,
        selected_cell,
        board_font,
        unknown_guess_cells or set(),
        hint_cell if revealed else None,
        hint_answer if revealed else None,
        hint_answer_alpha if revealed else 0,
        feedback_values,
    )
    draw_timer_and_streak(screen, elapsed_seconds, streak)

    if not revealed:
        draw_reveal_prompt(screen)

    if ticker_surface is not None:
        draw_ticker(screen, ticker_surface, ticker_offset)

    draw_mode_panel(screen, mode, fullscreen, mouse_position)
    draw_status(screen, status)


# ---------------------------------------------------------------------------
# Player input and display-mode helpers
# ---------------------------------------------------------------------------

def number_from_key(key):
    if pygame.K_1 <= key <= pygame.K_9:
        return key - pygame.K_0
    if pygame.K_KP1 <= key <= pygame.K_KP9:
        return key - pygame.K_KP1 + 1
    return None


def create_entry_feedback(board, entered_cell, is_correct):
    feedback_values = {}
    for row in range(9):
        for col in range(9):
            cell = (row, col)
            if cell == entered_cell or board[row][col] == 0:
                continue
            feedback_values[cell] = 0 if is_correct else random.randint(0, 9)
    return feedback_values


def handle_cell_key(
        key, selected_cell, board, starting_board, solution,
        unknown_guess_cells, game_started, streak, hint_elapsed, game_solved,
        current_status):
    if not game_started:
        return (
            "Press SPACE to reveal the board and start.",
            streak,
            hint_elapsed,
            game_solved,
            None,
        )

    row, col = selected_cell
    cell = (row, col)
    if starting_board[row][col] != 0:
        return (
            "Given numbers cannot be changed.",
            streak,
            hint_elapsed,
            game_solved,
            None,
        )

    feedback_correct = None
    if key in (pygame.K_BACKSPACE, pygame.K_DELETE):
        board[row][col] = 0
        unknown_guess_cells.discard(cell)
        status = "Number erased."
    else:
        number = number_from_key(key)
        if number is None:
            status = current_status
        else:
            was_already_correct = board[row][col] == solution[row][col]
            board[row][col] = number
            is_valid = soduku.is_valid(board, cell, number)
            feedback_correct = is_valid and number == solution[row][col]
            if not is_valid:
                unknown_guess_cells.discard(cell)
                streak = max(0, streak - STREAK_INCORRECT_PENALTY)
                status = (
                    "Conflict: number violates Sudoku rules. "
                    f"Streak -{STREAK_INCORRECT_PENALTY}."
                )
            elif feedback_correct:
                unknown_guess_cells.discard(cell)
                status = "Good move."
                if not was_already_correct:
                    streak = min(100, streak + STREAK_GAIN)
                    hint_elapsed = 0.0
            else:
                unknown_guess_cells.add(cell)
                status = "Unknown guess: differs from generated answer."

    if board == solution:
        status = "Puzzle solved!"
        game_solved = True

    return status, streak, hint_elapsed, game_solved, feedback_correct


def toggle_fullscreen(screen, fullscreen):
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    return screen, fullscreen


def scale_ui_surface(surface, target_size):
    if surface.get_size() == target_size:
        return surface
    return pygame.transform.scale(surface, target_size)


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Sudoku")
    clock = pygame.time.Clock()
    logical_screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    title_logo = load_title_logo()
    ticker_surface = create_ticker_surface(load_ticker_messages())
    ticker_offset = 0.0

    mode = DIFFICULTY_MODES[0]
    board, starting_board, solution, logical_steps = new_game(mode)
    selected_cell = None
    unknown_guess_cells = set()
    status = "Press SPACE to reveal the board and start."
    running = True
    fullscreen = False
    game_started = False
    game_solved = False
    elapsed_seconds = 0.0
    hint_elapsed = 0.0
    active_hint_cell = None
    hint_answer_elapsed = 0.0
    streak = 0
    feedback_values = {}
    feedback_remaining = 0.0

    difficulty_button, new_button, fullscreen_button = get_control_buttons()

    while running:
        delta_time = clock.tick(30) / 1000
        ticker_offset = (
            ticker_offset + TICKER_SPEED * delta_time
        ) % ticker_surface.get_width()
        if feedback_remaining > 0:
            feedback_remaining = max(0, feedback_remaining - delta_time)
            if feedback_remaining == 0:
                feedback_values.clear()

        if game_started and not game_solved:
            elapsed_seconds, hint_elapsed, streak = update_game_time(
                elapsed_seconds, hint_elapsed, streak, delta_time
            )

        (
            hint_cell,
            active_hint_cell,
            hint_answer_elapsed,
            hint_answer,
            hint_answer_alpha,
        ) = update_hint(
            logical_steps,
            board,
            mode,
            game_started,
            game_solved,
            hint_elapsed,
            streak,
            active_hint_cell,
            hint_answer_elapsed,
            delta_time,
        )

        viewport = get_display_viewport(screen.get_size())
        mouse_position = map_to_ui_position(pygame.mouse.get_pos(), viewport)
        draw_screen(
            logical_screen, board, starting_board, selected_cell, mode,
            status, fullscreen, mouse_position, unknown_guess_cells,
            game_started, elapsed_seconds, streak, hint_cell, hint_answer,
            hint_answer_alpha, feedback_values, ticker_surface, ticker_offset,
            title_logo,
        )
        screen.fill(BACKGROUND)
        scaled_screen = scale_ui_surface(logical_screen, viewport.size)
        screen.blit(scaled_screen, viewport.topleft)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if not game_started:
                    game_started = True
                    elapsed_seconds = 0.0
                    hint_elapsed = 0.0
                    status = "Timer started."

            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                screen, fullscreen = toggle_fullscreen(screen, fullscreen)
                viewport = get_display_viewport(screen.get_size())

            elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                ctrl_held = bool(event.mod & pygame.KMOD_CTRL)
                selected_cell = move_selection(
                    selected_cell, event.key, ctrl_held
                )

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                viewport = get_display_viewport(screen.get_size())
                click_position = map_to_ui_position(event.pos, viewport)
                if click_position is None:
                    continue
                if difficulty_button.collidepoint(click_position):
                    mode = get_next_mode(mode)
                    board, starting_board, solution, logical_steps = new_game(mode)
                    selected_cell = None
                    unknown_guess_cells.clear()
                    game_started = False
                    game_solved = False
                    elapsed_seconds = 0.0
                    hint_elapsed = 0.0
                    active_hint_cell = None
                    hint_answer_elapsed = 0.0
                    streak = 0
                    feedback_values.clear()
                    feedback_remaining = 0.0
                    status = f"New {mode['name']} puzzle."
                elif new_button.collidepoint(click_position):
                    board, starting_board, solution, logical_steps = new_game(mode)
                    selected_cell = None
                    unknown_guess_cells.clear()
                    game_started = False
                    game_solved = False
                    elapsed_seconds = 0.0
                    hint_elapsed = 0.0
                    active_hint_cell = None
                    hint_answer_elapsed = 0.0
                    streak = 0
                    feedback_values.clear()
                    feedback_remaining = 0.0
                    status = "New puzzle."
                elif fullscreen_button.collidepoint(click_position):
                    screen, fullscreen = toggle_fullscreen(screen, fullscreen)
                    viewport = get_display_viewport(screen.get_size())
                else:
                    selected_cell = cell_at_position(click_position)

            elif event.type == pygame.KEYDOWN and selected_cell is not None:
                (
                    status,
                    streak,
                    hint_elapsed,
                    game_solved,
                    feedback_correct,
                ) = handle_cell_key(
                    event.key,
                    selected_cell,
                    board,
                    starting_board,
                    solution,
                    unknown_guess_cells,
                    game_started,
                    streak,
                    hint_elapsed,
                    game_solved,
                    status,
                )
                if feedback_correct is not None:
                    feedback_values = create_entry_feedback(
                        board, selected_cell, feedback_correct
                    )
                    feedback_remaining = ENTRY_FEEDBACK_DURATION

    pygame.quit()


if __name__ == "__main__":
    main()
