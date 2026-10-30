import random #lets go gambling on my Hakari shi

example_board = [ #basically, its all lists in lists - all the tricky parts (and party tricks) are basicly contrived nested lists that represent the Sudoku grid
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]

def solve_sudoku(board): #solves the Sudoku board using backtracking, but can solve boards that need guessing
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty
    for i in range(1, 10):
        if is_valid(board, (row, col), i):
            board[row][col] = i
            if solve_sudoku(board):
                return True
            board[row][col] = 0
    return False

def fill_random_sudoku(board): #fills the Sudoku board with random valid numbers
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty
    numbers = list(range(1, 10))
    random.shuffle(numbers)
    for number in numbers:
        if is_valid(board, (row, col), number):
            board[row][col] = number
            if fill_random_sudoku(board):
                return True
            board[row][col] = 0
    return False

def find_empty(board): #returns the position of the first empty cell in the board, or None if no empty cells exist
    for i in range(len(board)):
        for j in range(len(board[i])):
            if board[i][j] == 0:
                return (i, j)
    return None

def is_valid(board, pos, num): #checks if placing a number at a specific position is valid according to Sudoku rules
    row, col = pos
    # Check row
    for i in range(len(board[row])):
        if board[row][i] == num and col != i:
            return False
    # Check column
    for i in range(len(board)):
        if board[i][col] == num and row != i:
            return False
    # Check box
    box_x = col // 3
    box_y = row // 3
    for i in range(box_y * 3, box_y * 3 + 3):
        for j in range(box_x * 3, box_x * 3 + 3):
            if board[i][j] == num and (i, j) != pos:
                return False
    return True

def get_candidates(board): #returns a dictionary of all empty cells and their possible candidate numbers
    candidates = {}
    for row in range(9):
        for col in range(9):
            if board[row][col] == 0:
                candidates[(row, col)] = {
                    number for number in range(1, 10)
                    if is_valid(board, (row, col), number)
                }
    return candidates

def find_naked_single(board, candidates): #finds a cell with only one possible candidate
    # A cell with one candidate must contain that number.
    for (row, col), options in candidates.items():
        if len(options) == 1:
            return row, col, next(iter(options)), "naked single"
    return None

def find_hidden_single(board, candidates): #finds a cell that is the only possible location for a number in a row, column, or box
    # Check each row for a number that has only one possible cell.
    for row in range(9):
        for number in range(1, 10):
            possible_cells = [
                (row, col) for col in range(9)
                if (row, col) in candidates and number in candidates[(row, col)]
            ]
            if len(possible_cells) == 1:
                row, col = possible_cells[0]
                return row, col, number, "hidden single"

    # Check each column for a number that has only one possible cell.
    for col in range(9):
        for number in range(1, 10):
            possible_cells = [
                (row, col) for row in range(9)
                if (row, col) in candidates and number in candidates[(row, col)]
            ]
            if len(possible_cells) == 1:
                row, col = possible_cells[0]
                return row, col, number, "hidden single"

    # Check each 3x3 box for a number that has only one possible cell.
    for box_row in range(0, 9, 3):
        for box_col in range(0, 9, 3):
            for number in range(1, 10):
                possible_cells = [
                    (row, col)
                    for row in range(box_row, box_row + 3)
                    for col in range(box_col, box_col + 3)
                    if (row, col) in candidates and number in candidates[(row, col)]
                ]
                if len(possible_cells) == 1:
                    row, col = possible_cells[0]
                    return row, col, number, "hidden single"
    return None

LOGIC_STRATEGIES = [find_naked_single, find_hidden_single] #list of logical strategies used to solve the Sudoku board

def solve_logically(board, strategies=None): #uses strategies I saw in a YouTube video
    # First make sure the board is a 9x9 grid containing numbers from 0 to 9.
    if len(board) != 9:
        return {"status": "invalid", "board": board, "moves": []}
    for row in board:
        if len(row) != 9:
            return {"status": "invalid", "board": board, "moves": []}
        for number in row:
            if type(number) is not int or number < 0 or number > 9:
                return {"status": "invalid", "board": board, "moves": []}

    # deep copy the board to avoid modifying the original
    working_board = [row[:] for row in board]
    for row in range(9):
        for col in range(9):
            number = working_board[row][col]
            if number and not is_valid(working_board, (row, col), number):
                return {"status": "invalid", "board": working_board, "moves": []}

    moves = []
    if strategies is None:
        strategies = LOGIC_STRATEGIES

    # Keep making one logical move at a time until solved or stuck.
    while True:
        empty_cell = find_empty(working_board)
        if empty_cell is None:
            return {"status": "solved", "board": working_board, "moves": moves}

        candidates = get_candidates(working_board)
        has_empty_cell_without_candidates = False
        for options in candidates.values():
            if len(options) == 0:
                has_empty_cell_without_candidates = True
                break
        if has_empty_cell_without_candidates:
            return {"status": "invalid", "board": working_board, "moves": moves}

        move = None
        for strategy in strategies:
            move = strategy(working_board, candidates)
            if move is not None:
                break
        if move is None:
            return {"status": "stuck", "board": working_board, "moves": moves}

        row, col, number, reason = move
        if (row, col) not in candidates:
            raise ValueError(f"{strategy.__name__} returned a move for a filled cell.")
        if number not in candidates[(row, col)]:
            raise ValueError(f"{strategy.__name__} returned an invalid Sudoku move.")

        working_board[row][col] = number
        moves.append((row, col, number, reason)) #makes a record of each move made as a list of tuples (thx ai)

def print_board(board): #sexy console prints for boards
    for i in range(len(board)):
        if i % 3 == 0 and i != 0:
            print("-" * 21)
        for j in range(len(board[i])):
            if j % 3 == 0 and j != 0:
                print("|", end=" ")
            print(board[i][j], end=" ")
        print()

def generate_random_board(difficulty="hard"): #generates a random Sudoku board (easy means only naked singles are used, which is very satisfying)
    if difficulty == "easy":
        strategies = [find_naked_single]
    elif difficulty == "hard":
        strategies = LOGIC_STRATEGIES
    else:
        raise ValueError("difficulty must be 'easy' or 'hard'.")

    solution = [[0 for _ in range(9)] for _ in range(9)]
    if not fill_random_sudoku(solution):
        raise RuntimeError("Could not generate a complete Sudoku solution.")

    board = [row[:] for row in solution]
    cells = [(row, col) for row in range(9) for col in range(9)]
    random.shuffle(cells)
    for row, col in cells:
        board[row][col] = 0
        if solve_logically(board, strategies)["status"] != "solved":
            board[row][col] = solution[row][col]

    return [board,solution]

# demo_board, demo_solution = generate_random_board("easy")

# print_board(demo_board)
# print()
# print_board(demo_solution)
