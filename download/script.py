import sys
import os
import pygame

pygame.init()
print("By Kevin (kevpopper in github)")
# Piece file names
PIECE_NAMES = [
    "WBKI", "WBKN", "WBP", "WKIKN", "WKIP", "WQB", "WQKI", "WQKN",
    "WQP", "WQR", "WRB", "WRKI", "WRKN", "WRP", "WKNP", "WRR",
    "WPP", "WKNKN", "WBB"
]

pieces = {}
show_fog = False

def load_assets():
    global pieces
    for piece_name in PIECE_NAMES:
        file_path = f"pieces/{piece_name}.png"
        if os.path.exists(file_path):
            pieces[piece_name] = pygame.image.load(file_path).convert_alpha()
        else:
            print(f"Warning: {file_path} not found")

    for piece_name in PIECE_NAMES:
        black_name = piece_name.replace("W", "B")
        if black_name not in pieces and piece_name in pieces:
            white_img = pieces[piece_name]
            black_img = white_img.copy()
            pixel_array = pygame.PixelArray(black_img)
            for x in range(black_img.get_width()):
                for y in range(black_img.get_height()):
                    raw_color = black_img.unmap_rgb(pixel_array[x, y])
                    r, g, b, a = raw_color.r, raw_color.g, raw_color.b, raw_color.a
                    pixel_array[x, y] = (255 - r, 255 - g, 255 - b, a)
            pixel_array.close()
            pieces[black_name] = black_img

    print(f"Loaded {len(pieces)} piece configurations.")


# Variables
BOARD_WIDTH = 720
SIDEBAR_WIDTH = 240
WIDTH = BOARD_WIDTH + SIDEBAR_WIDTH
HEIGHT = 720
FPS = 60
TITLE = "Chess Fusion Variant"

# Colors
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
LIGHT_SQUARE = (240, 217, 181)
DARK_SQUARE = (181, 136, 99)
GRAY_PANEL = (40, 40, 40)
HIGHLIGHT_SELECT = (255, 215, 0)
HIGHLIGHT_MOVE = (80, 180, 80)
HIGHLIGHT_CAPTURE = (200, 60, 60)
HIGHLIGHT_EN_PASSANT = (255, 165, 0)

# Board Size Settings
BOARD_SIZE = 6
SQUARE_SIZE = BOARD_WIDTH // BOARD_SIZE

# Setup Phase
board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
moved = [[False for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
selected_piece = None
remove_mode = False
game_started = False

# Playing Phase State
game_phase_playing = False
current_turn = 'W'
selected_square = None
move_queue = []
legal_squares = set()
en_passant_squares = set()
last_pawn_move = None
winner = None

KEY_MAP = {
    '0': PIECE_NAMES[0], '1': PIECE_NAMES[1], '2': PIECE_NAMES[2],
    '3': PIECE_NAMES[3], '4': PIECE_NAMES[4], '5': PIECE_NAMES[5],
    '6': PIECE_NAMES[6], '7': PIECE_NAMES[7], '8': PIECE_NAMES[8],
    '9': PIECE_NAMES[9], 'q': PIECE_NAMES[10], 'w': PIECE_NAMES[11],
    'e': PIECE_NAMES[12], 'r': PIECE_NAMES[13], 't': PIECE_NAMES[14],
    'y': PIECE_NAMES[15], 'u': PIECE_NAMES[16], 'i': PIECE_NAMES[17],
    'o': PIECE_NAMES[18]
}

COMPONENT_LIMITS = {
    "Q": 1, "KI": 1, "B": 2, "KN": 2, "R": 2, "P": 8
}

font = pygame.font.Font(None, 22)
big_font = pygame.font.Font(None, 48)

ROOK_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
BISHOP_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
QUEEN_DIRS = ROOK_DIRS + BISHOP_DIRS
KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]

OVERLAP_PAIRS = {frozenset({'Q', 'R'}), frozenset({'Q', 'B'}), frozenset({'Q', 'KI'})}


def get_piece_traits(piece_str):
    if not piece_str:
        return {}
    core = piece_str[1:]
    traits = {k: 0 for k in COMPONENT_LIMITS.keys()}

    for double_trait in ["KIKN", "KNKN"]:
        if double_trait in core:
            count = core.count(double_trait)
            if double_trait == "KIKN":
                traits["KI"] += count
                traits["KN"] += count
            elif double_trait == "KNKN":
                traits["KN"] += count * 2
            core = core.replace(double_trait, "")

    for double_trait in ["KI", "KN"]:
        if double_trait in core:
            traits[double_trait] += core.count(double_trait)
            core = core.replace(double_trait, "")

    for single_trait in ["Q", "B", "R", "P"]:
        if single_trait in core:
            traits[single_trait] += core.count(single_trait)

    return traits


def check_component_limits(new_piece):
    is_white = new_piece.startswith("W")
    prefix = "W" if is_white else "B"
    incoming_traits = get_piece_traits(new_piece)

    board_totals = {k: 0 for k in COMPONENT_LIMITS.keys()}
    for row in board:
        for cell in row:
            if cell and cell.startswith(prefix):
                cell_traits = get_piece_traits(cell)
                for trait, val in cell_traits.items():
                    board_totals[trait] += val

    for trait, incoming_val in incoming_traits.items():
        if incoming_val > 0:
            max_allowed = COMPONENT_LIMITS[trait]
            current_total = board_totals[trait]
            if current_total + incoming_val > max_allowed:
                return False, f"Limit reached! Trait '{trait}' would hit {current_total + incoming_val}/{max_allowed}."

    return True, ""


def get_move_groups(piece_name):
    traits = get_piece_traits(piece_name)
    trait_list = []
    for t, count in traits.items():
        for _ in range(count):
            trait_list.append(t)

    if len(trait_list) == 0:
        return []
    if len(trait_list) == 1:
        return [(trait_list[0],)]

    if len(trait_list) == 2:
        t1, t2 = trait_list
        if t1 == t2:
            return [(t1,), (t2,)]
        pair = frozenset({t1, t2})
        if pair in OVERLAP_PAIRS:
            return [(t1,), (t2,)]
        else:
            return [(t1, t2)]

    return [(t,) for t in trait_list]


def get_trait_squares(trait, row, col, color, pawn_can_double, include_en_passant=False):
    squares = []

    if trait in ('R', 'B', 'Q'):
        dirs = ROOK_DIRS if trait == 'R' else BISHOP_DIRS if trait == 'B' else QUEEN_DIRS
        for dr, dc in dirs:
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if board[r][c] is None:
                    squares.append((r, c))
                else:
                    if not board[r][c].startswith(color):
                        squares.append((r, c))
                    break
                r += dr
                c += dc

    elif trait == 'KI':
        for dr, dc in QUEEN_DIRS:
            r, c = row + dr, col + dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if board[r][c] is None or not board[r][c].startswith(color):
                    squares.append((r, c))

    elif trait == 'KN':
        for dr, dc in KNIGHT_OFFSETS:
            r, c = row + dr, col + dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if board[r][c] is None or not board[r][c].startswith(color):
                    squares.append((r, c))

    elif trait == 'P':
        direction = -1 if color == 'W' else 1
        fr = row + direction
        if 0 <= row < BOARD_SIZE and 0 <= fr < BOARD_SIZE and board[fr][col] is None:
            squares.append((fr, col))
            if pawn_can_double:
                fr2 = row + 2 * direction
                if 0 <= fr2 < BOARD_SIZE and board[fr2][col] is None:
                    squares.append((fr2, col))
                fr3 = row + 3 * direction
                if 0 <= fr3 < BOARD_SIZE and board[fr3][col] is None:
                    squares.append((fr3, col))

        for dc in (-1, 1):
            r, c = fr, col + dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if board[r][c] is not None and not board[r][c].startswith(color):
                    squares.append((r, c))

        if include_en_passant:
            for en_passant_sq in en_passant_squares:
                if en_passant_sq[0] == fr and abs(en_passant_sq[1] - col) == 1:
                    squares.append(en_passant_sq)

    return squares


def get_legal_squares_for_action(action_spec, row, col, color):
    result = set()
    pawn_can_double = not moved[row][col]
    for trait in action_spec:
        include_en_passant = (trait == 'P')
        result.update(get_trait_squares(trait, row, col, color, pawn_can_double, include_en_passant))
    return result


def check_ready():
    white_count = 0
    for row in [4, 5]:
        for col in range(BOARD_SIZE):
            if board[row][col] and board[row][col].startswith("W"):
                white_count += 1
    return white_count == 8


def check_black_ready():
    black_count = 0
    for row in [0, 1]:
        for col in range(BOARD_SIZE):
            if board[row][col] and board[row][col].startswith("B"):
                black_count += 1
    return black_count == 8


def draw_board(screen):
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            rect = pygame.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            pygame.draw.rect(screen, color, rect)

            if board[row][col]:
                piece_name = board[row][col]
                if piece_name in pieces:
                    piece_img = pieces[piece_name]
                    piece_img = pygame.transform.scale(piece_img, (SQUARE_SIZE, SQUARE_SIZE))
                    screen.blit(piece_img, (col * SQUARE_SIZE, row * SQUARE_SIZE))

    if game_phase_playing:
        if selected_square:
            r, c = selected_square
            pygame.draw.rect(screen, HIGHLIGHT_SELECT,
                             (c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 4)
        for (r, c) in legal_squares:
            center = (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2)
            if (r, c) in en_passant_squares:
                color = HIGHLIGHT_EN_PASSANT
            elif board[r][c] is not None:
                color = HIGHLIGHT_CAPTURE
            else:
                color = HIGHLIGHT_MOVE
            pygame.draw.circle(screen, color, center, 12)


def draw_sidebar(screen):
    sidebar_rect = pygame.Rect(BOARD_WIDTH, 0, SIDEBAR_WIDTH, HEIGHT)
    pygame.draw.rect(screen, GRAY_PANEL, sidebar_rect)

    if game_phase_playing:
        turn_str = "WHITE'S TURN" if current_turn == 'W' else "BLACK'S TURN"
        turn_color = (150, 220, 255) if current_turn == 'W' else (200, 150, 255)
        screen.blit(font.render(turn_str, True, turn_color), (BOARD_WIDTH + 15, 15))

        if move_queue:
            remaining = " + ".join("/".join(spec) for spec in move_queue)
            screen.blit(font.render(f"Moves left: {remaining}", True, WHITE), (BOARD_WIDTH + 15, 45))

        screen.blit(font.render("SPACE: end turn early", True, (180, 180, 180)), (BOARD_WIDTH + 15, HEIGHT - 30))

        if winner:
            pygame.draw.rect(screen, (0, 0, 0), (0, HEIGHT // 2 - 60, BOARD_WIDTH, 120))
            msg = f"{winner} WINS!"
            text = big_font.render(msg, True, (255, 215, 0))
            screen.blit(text, (BOARD_WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 20))
        return

    status_str = "BLACK SETUP" if game_started else "WHITE SETUP"
    status_color = (200, 150, 255) if game_started else (150, 220, 255)
    screen.blit(font.render(status_str, True, status_color), (BOARD_WIDTH + 15, 15))

    mode_str = "MODE: REMOVE (Press P)" if remove_mode else "MODE: PLACE (P to remove)"
    mode_color = (255, 100, 100) if remove_mode else (100, 255, 100)
    screen.blit(font.render(mode_str, True, mode_color), (BOARD_WIDTH + 15, 40))

    pygame.draw.line(screen, WHITE, (BOARD_WIDTH + 10, 70), (WIDTH - 10, 70), 1)

    y_offset = 85
    for key, piece_name in KEY_MAP.items():
        display_name = piece_name if not game_started else piece_name.replace("W", "B")
        text = f"[{key.upper()}] : {display_name}"
        text_surface = font.render(text, True, WHITE)

        if selected_piece == display_name and not remove_mode:
            highlight_rect = pygame.Rect(BOARD_WIDTH + 8, y_offset - 2, SIDEBAR_WIDTH - 16, 22)
            pygame.draw.rect(screen, (80, 80, 100), highlight_rect, 2)

        screen.blit(text_surface, (BOARD_WIDTH + 15, y_offset))
        y_offset += 24


def start_piece_turn(row, col):
    global selected_square, move_queue, legal_squares
    piece_name = board[row][col]
    selected_square = (row, col)
    move_queue = get_move_groups(piece_name)
    if move_queue:
        legal_squares = get_legal_squares_for_action(move_queue[0], row, col, current_turn)
    else:
        legal_squares = set()


def end_turn():
    global selected_square, move_queue, legal_squares, current_turn, en_passant_squares
    selected_square = None
    move_queue = []
    legal_squares = set()
    current_turn = 'B' if current_turn == 'W' else 'W'
    setup_en_passant()


def execute_move(dest_row, dest_col):
    global selected_square, move_queue, legal_squares, winner, last_pawn_move, en_passant_squares
    sel_row, sel_col = selected_square
    moving_piece = board[sel_row][sel_col]
    captured = board[dest_row][dest_col]
    piece_traits = get_piece_traits(moving_piece)

    if piece_traits.get('P', 0) > 0 and (dest_row, dest_col) in en_passant_squares:
        direction = -1 if current_turn == 'W' else 1
        capture_row = dest_row - direction
        captured = board[capture_row][dest_col]
        board[capture_row][dest_col] = None

    if captured:
        captured_traits = get_piece_traits(captured)
        if captured_traits.get('KI', 0) > 0:
            winner = "WHITE" if current_turn == 'W' else "BLACK"

    board[dest_row][dest_col] = moving_piece
    board[sel_row][sel_col] = None
    moved[dest_row][dest_col] = True

    if piece_traits.get('P', 0) > 0:
        promotion_row = 0 if current_turn == 'W' else BOARD_SIZE - 1
        if dest_row == promotion_row:
            prefix = current_turn
            board[dest_row][dest_col] = f"{prefix}QKN"
            print(f"Pawn promoted to {prefix}QKN!")

    if piece_traits.get('P', 0) > 0 and abs(dest_row - sel_row) >= 2:
        last_pawn_move = (sel_row, sel_col, dest_row, dest_col, abs(dest_row - sel_row))
    else:
        last_pawn_move = None

    move_queue.pop(0)
    selected_square = (dest_row, dest_col)

    if winner:
        legal_squares = set()
        return

    if move_queue:
        legal_squares = get_legal_squares_for_action(move_queue[0], dest_row, dest_col, current_turn)
    else:
        end_turn()


def setup_en_passant():
    global en_passant_squares
    en_passant_squares = set()

    if last_pawn_move is None:
        return

    from_r, from_c, to_r, to_c, distance = last_pawn_move
    if distance < 2:
        return

    pawn_color = board[to_r][to_c][0] if board[to_r][to_c] else None
    if pawn_color and pawn_color != current_turn:
        direction = -1 if pawn_color == 'W' else 1
        capture_row = to_r - direction
        en_passant_squares.add((capture_row, to_c))


def main():
    global selected_piece, remove_mode, game_started, show_fog
    global game_phase_playing, selected_square, move_queue, legal_squares, current_turn, winner

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)

    load_assets()
    clock = pygame.time.Clock()

    while True:
        white_ready = check_ready() and not game_started
        black_ready = check_black_ready() and game_started and not game_phase_playing
        ready_button_rect = pygame.Rect(BOARD_WIDTH + 15, HEIGHT - 60, SIDEBAR_WIDTH - 30, 45)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if game_phase_playing:
                    if event.key == pygame.K_SPACE and selected_square and not winner:
                        end_turn()
                    continue

                key_char = event.unicode.lower()
                if key_char == 'p':
                    remove_mode = not remove_mode
                    selected_piece = None
                elif key_char in KEY_MAP:
                    raw_piece = KEY_MAP[key_char]
                    selected_piece = raw_piece if not game_started else raw_piece.replace("W", "B")
                    remove_mode = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos

                if game_phase_playing:
                    if winner or mouse_x >= BOARD_WIDTH:
                        continue
                    col = mouse_x // SQUARE_SIZE
                    row = mouse_y // SQUARE_SIZE
                    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
                        continue

                    if selected_square is None:
                        if board[row][col] and board[row][col].startswith(current_turn):
                            start_piece_turn(row, col)
                    else:
                        if (row, col) in legal_squares:
                            execute_move(row, col)
                        elif board[row][col] and board[row][col].startswith(current_turn):
                            start_piece_turn(row, col)
                    continue

                if not game_started and white_ready and ready_button_rect.collidepoint(event.pos):
                    game_started = True
                    selected_piece = None
                    remove_mode = False
                    show_fog = True

                elif game_started and black_ready and ready_button_rect.collidepoint(event.pos):
                    show_fog = False
                    game_phase_playing = True
                    current_turn = 'W'
                    setup_en_passant()

                elif mouse_x < BOARD_WIDTH:
                    col = mouse_x // SQUARE_SIZE
                    row = mouse_y // SQUARE_SIZE

                    if 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE:
                        if game_started and row in [4, 5]:
                            print("Unauthorized modification: White deployment is locked!")
                        else:
                            if remove_mode:
                                if board[row][col]:
                                    board[row][col] = None
                            elif selected_piece:
                                is_white = selected_piece.startswith("W")
                                home_rows = [4, 5] if is_white else [0, 1]

                                if not game_started and not is_white:
                                    print("Wait for White setup completion.")
                                elif game_started and is_white:
                                    print("White setup phase has ended.")
                                elif row in home_rows:
                                    allowed, message = check_component_limits(selected_piece)
                                    if not allowed:
                                        print(message)
                                    else:
                                        board[row][col] = selected_piece
                                else:
                                    print("Placement error: Out of deployment zone bounds!")

        screen.fill(BLACK)
        draw_board(screen)

        if game_started and show_fog and not game_phase_playing:
            cover_rect = pygame.Rect(0, 4 * SQUARE_SIZE, BOARD_WIDTH, 2 * SQUARE_SIZE)
            pygame.draw.rect(screen, (30, 30, 35), cover_rect)
            fog_text = font.render("WHITE ARMY DEPLOYED (HIDDEN)", True, (120, 120, 120))
            screen.blit(fog_text, (BOARD_WIDTH // 4, int(4.8 * SQUARE_SIZE)))

        draw_sidebar(screen)

        if not game_phase_playing and ((not game_started and white_ready) or (game_started and black_ready)):
            pygame.draw.rect(screen, (46, 139, 87), ready_button_rect, border_radius=4)
            btn_text = font.render("CONFIRM SETUP", True, WHITE)
            text_x = ready_button_rect.x + (ready_button_rect.width - btn_text.get_width()) // 2
            text_y = ready_button_rect.y + (ready_button_rect.height - btn_text.get_height()) // 2
            screen.blit(btn_text, (text_x, text_y))

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
