# Name: <Your Name>          Student ID: <Your Student ID>
# 5FTC2067 AI Principles - Mini Project
# Dice Tic-Tac-Toe: Human (X) vs Bot (O). The bot uses Expectimax.
#
# RULES
#  1. Both players roll 2 dice every turn (human presses Roll, then the bot rolls).
#  2. A double beats any non-double. Otherwise the higher total goes.
#     Two doubles: higher total goes.
#  3. Tie (same total, or equal doubles): nothing happens, both reroll.
#  4. The player who goes places a mark on an empty cell.
#     With a double they may instead OVERWRITE one opponent mark (optional).
#  5. 3 in a row wins immediately. Draw only when the board is full.

import random
import tkinter
from itertools import product

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
HUMAN = "X"
BOT = "O"
EMPTY = ""

# All 8 winning lines, as board indexes 0-8 (row by row)
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
         (0, 3, 6), (1, 4, 7), (2, 5, 8),
         (0, 4, 8), (2, 4, 6)]

# How many dice rolls the bot looks ahead
SEARCH_DEPTH = 4

COLOR_BLUE = "#4584b6"
COLOR_RED = "#ff6b6b"
COLOR_GREEN = "#69db7c"
COLOR_GRAY = "#343434"
COLOR_LIGHT_GRAY = "#646464"
COLOR_INDIGO = "#748ffc"


# ======================================================================
# GAME LOGIC (no UI here, shared by the game and the AI)
# ======================================================================

def roll_dice():
    """Roll 2 dice. Returns a tuple like (3, 5)."""
    return (random.randint(1, 6), random.randint(1, 6))


def is_double(dice):
    """True if both dice show the same number.
    dice: tuple of two numbers, e.g. (4, 4)"""
    return dice[0] == dice[1]


def decide_roller(human_dice, bot_dice):
    """Decide who goes. Returns HUMAN, BOT, or None (tie -> reroll).
    human_dice, bot_dice: tuples of two numbers"""
    human_double = is_double(human_dice)
    bot_double = is_double(bot_dice)

    # 1. A double beats a non-double
    if human_double and not bot_double:
        return HUMAN
    if bot_double and not human_double:
        return BOT

    # 2. Both doubles or both non-doubles: higher total goes
    if sum(human_dice) > sum(bot_dice):
        return HUMAN
    if sum(bot_dice) > sum(human_dice):
        return BOT
    return None


def winning_line(board):
    """Return the winning line (3 indexes) or None.
    board: tuple/list of 9 cells ('X', 'O' or '')"""
    for a, b, c in LINES:
        if board[a] != EMPTY and board[a] == board[b] == board[c]:
            return (a, b, c)
    return None


def get_moves(board, player, has_double):
    """List the cell indexes the player may play.
    board: tuple of 9 cells
    player: HUMAN or BOT
    has_double: True if the player rolled a double (allows overwriting)"""
    opponent = BOT if player == HUMAN else HUMAN
    moves = [i for i, cell in enumerate(board) if cell == EMPTY]
    if has_double:
        moves += [i for i, cell in enumerate(board) if cell == opponent]
    return moves


def apply_move(board, index, player):
    """Return a NEW board with the player's mark on cell 'index'.
    board: tuple of 9 cells, index: cell 0-8, player: HUMAN or BOT"""
    new_board = list(board)
    new_board[index] = player
    return tuple(new_board)


# ======================================================================
# AI: EXPECTIMAX
# ======================================================================

def compute_roll_probabilities():
    """Enumerate all 36 x 36 dice pairs and count who goes and whether
    they have a double. Ties are removed (they are rerolled), so the
    probabilities are renormalised.
    Returns {(mover, has_double): probability}"""
    all_rolls = list(product(range(1, 7), repeat=2))
    counts = {}
    total = 0
    for human_dice in all_rolls:
        for bot_dice in all_rolls:
            mover = decide_roller(human_dice, bot_dice)
            if mover is None:
                continue
            mover_dice = human_dice if mover == HUMAN else bot_dice
            key = (mover, is_double(mover_dice))
            counts[key] = counts.get(key, 0) + 1
            total += 1
    return {key: count / total for key, count in counts.items()}


ROLL_PROBS = compute_roll_probabilities()
_cache = {}   # remembers values already calculated: (board, depth) -> value


def heuristic(board):
    """Estimate how good the board is for the bot (-0.9 to +0.9).
    Counts lines that only one player can still complete.
    board: tuple of 9 cells"""
    score = 0
    for line in LINES:
        marks = [board[i] for i in line]
        bots = marks.count(BOT)
        humans = marks.count(HUMAN)
        if humans == 0:
            score += bots ** 2
        elif bots == 0:
            score -= humans ** 2
    return max(-0.9, min(0.9, score / 20))


def expectimax(board, depth):
    """Value of the board for the bot BEFORE the next dice roll.
    CHANCE node: average over the roll outcomes (who goes, double or not).
    Inside it: MAX node when the bot goes, MIN node when the human goes.
    board: tuple of 9 cells
    depth: how many more dice rolls to look ahead"""
    line = winning_line(board)
    if line:
        # Faster wins are worth slightly more
        bonus = 1 + 0.01 * depth
        return bonus if board[line[0]] == BOT else -bonus
    if EMPTY not in board:
        return 0
    if depth == 0:
        return heuristic(board)

    key = (board, depth)
    if key in _cache:
        return _cache[key]

    value = 0
    for (mover, double), prob in ROLL_PROBS.items():
        moves = get_moves(board, mover, double)
        results = [expectimax(apply_move(board, m, mover), depth - 1)
                   for m in moves]
        value += prob * (max(results) if mover == BOT else min(results))

    _cache[key] = value
    return value


def choose_bot_move(board, has_double):
    """Pick the bot's move: the one with the best expectimax value.
    board: tuple of 9 cells
    has_double: True if the bot rolled a double"""
    moves = get_moves(board, BOT, has_double)
    depth = SEARCH_DEPTH
    best_value = -float("inf")
    best_moves = []
    for move in moves:
        value = expectimax(apply_move(board, move, BOT), depth - 1)
        if value > best_value + 1e-9:
            best_value = value
            best_moves = [move]
        elif abs(value - best_value) <= 1e-9:
            best_moves.append(move)
    return random.choice(best_moves)


# ---- END OF LOGIC ----


# ======================================================================
# GAME UI (tkinter)
# ======================================================================

def schedule(delay, function):
    """Run 'function' after 'delay' ms. Remembered so Restart can cancel it.
    delay: milliseconds, function: the function to call"""
    pending_jobs.append(window.after(delay, function))


def show_dice():
    """Update the dice boxes for the human (H) and the bot (R).
    Uses the globals human_dice and bot_dice ('-' when not rolled)."""
    for i in range(2):
        human_labels[i]["text"] = str(human_dice[i]) if human_dice else "-"
        bot_labels[i]["text"] = str(bot_dice[i]) if bot_dice else "-"


def place(index, player):
    """Put a mark on the board (also overwrites).
    index: cell 0-8, player: HUMAN or BOT"""
    cells[index] = player
    color = COLOR_BLUE if player == HUMAN else COLOR_RED
    buttons[index].config(text=player, foreground=color)


def human_roll():
    """Roll button: human rolls first, then the bot rolls automatically."""
    global phase, human_dice, bot_dice
    if phase != "wait_roll":
        return
    phase = "rolling"
    roll_button.config(state="disabled")
    human_dice = roll_dice()
    bot_dice = None            # bot dice reset until the bot rolls
    show_dice()
    label["text"] = "Bot is rolling..."
    schedule(700, bot_roll)


def bot_roll():
    """The bot rolls its dice after the human has rolled."""
    global bot_dice
    bot_dice = roll_dice()
    show_dice()
    schedule(900, resolve_roll)


def resolve_roll():
    """Compare both rolls and decide who plays, or reroll on a tie."""
    global phase
    mover = decide_roller(human_dice, bot_dice)

    if mover is None:
        label["text"] = "Tie! Nobody goes. Roll again."
        phase = "wait_roll"
        roll_button.config(state="normal")
    elif mover == HUMAN:
        phase = "human_move"
        if is_double(human_dice) and BOT in cells:
            label["text"] = "DOUBLE! Pick an empty cell, or click an O to overwrite it."
        else:
            label["text"] = "You go! Pick an empty cell."
    else:
        phase = "bot_move"
        label["text"] = "Bot goes..."
        schedule(700, bot_play)


def on_cell_click(index):
    """Human clicks a cell: place on an empty one, or overwrite an O if
    the human rolled a double.
    index: cell 0-8"""
    if phase != "human_move":
        return
    can_overwrite = is_double(human_dice) and cells[index] == BOT
    if cells[index] != EMPTY and not can_overwrite:
        return
    place(index, HUMAN)
    finish_turn("")


def bot_play():
    """The bot chooses and plays its move with expectimax."""
    move = choose_bot_move(tuple(cells), is_double(bot_dice))
    overwrote = cells[move] == HUMAN
    place(move, BOT)
    finish_turn("Bot overwrote your X! " if overwrote else "")


def finish_turn(note):
    """After a move: check win / draw, otherwise ask for the next roll.
    note: extra text to show before 'press Roll'"""
    global phase
    line = winning_line(cells)
    if line:
        winner = cells[line[0]]
        label.config(text="YOU WIN!" if winner == HUMAN else "BOT WIN!",
                     foreground=COLOR_GREEN)
        for i in line:
            buttons[i].config(foreground=COLOR_GREEN, background=COLOR_LIGHT_GRAY)
        phase = "game_over"
    elif EMPTY not in cells:
        label.config(text="Draw!", foreground=COLOR_GREEN)
        phase = "game_over"
    else:
        label["text"] = note + "Your turn: press ROLL."
        phase = "wait_roll"
        roll_button.config(state="normal")


def new_game():
    """Restart button: cancel pending steps and reset everything."""
    global cells, phase, human_dice, bot_dice
    for job in pending_jobs:
        window.after_cancel(job)
    pending_jobs.clear()

    cells = [EMPTY] * 9
    human_dice = None
    bot_dice = None
    phase = "wait_roll"
    show_dice()
    label.config(text="Press ROLL to start.", foreground="white")
    roll_button.config(state="normal")
    for button in buttons:
        button.config(text="", foreground=COLOR_BLUE, background=COLOR_GRAY)


# ---- Game state ----
cells = [EMPTY] * 9      # logical board
phase = "wait_roll"      # wait_roll / rolling / human_move / bot_move / game_over
human_dice = None
bot_dice = None
pending_jobs = []

class RoundedButton(tkinter.Canvas):
    """A button with rounded corners, drawn on a Canvas.
    parent: widget that holds it, text: label shown on the button
    command: function called on click, radius: corner roundness in px
    fill / text_color: button colors, off_fill: color when disabled"""

    def __init__(self, parent, text, command, radius=18, height=60,
                 fill="white", text_color=COLOR_INDIGO, off_fill="#cfcfcf"):
        super().__init__(parent, height=height, highlightthickness=0,
                         background=parent.cget("background"), cursor="hand2")
        self._text = text
        self._command = command
        self._radius = radius
        self._fill = fill
        self._text_color = text_color
        self._off_fill = off_fill
        self._enabled = True
        self.bind("<Configure>", lambda event: self._draw())
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        """Redraw the rounded rectangle and the text."""
        self.delete("all")
        x1, y1 = 2, 2
        x2, y2 = self.winfo_width() - 2, self.winfo_height() - 2
        r = self._radius
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                  x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                  x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(points, smooth=True, outline="",
                            fill=self._fill if self._enabled else self._off_fill)
        self.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=self._text,
                         fill=self._text_color, font=("Consolas", 20))

    def _on_click(self, event):
        """Run the command only when the button is enabled."""
        if self._enabled:
            self._command()

    def config(self, **options):
        """Supports state='disabled' / 'normal', like a normal Button."""
        if "state" in options:
            self._enabled = options.pop("state") != "disabled"
            self._draw()
        if options:
            super().config(**options)

# ---- Window ----
window = tkinter.Tk()
window.title("Dice Tic Tac Toe (Player vs Bot)")
window.resizable(False, False)
frame = tkinter.Frame(window)

# Row 0: status text
label = tkinter.Label(frame, text="Press ROLL to start.", font=("Consolas", 14),
                      background=COLOR_GRAY, foreground="white",
                      wraplength=430, height=2)
label.grid(row=0, column=0, columnspan=3, sticky="we")

# Row 1: Roll button (rounded)
# Row 1: Roll button (rounded, silver)
roll_button = RoundedButton(frame, text="ROLL", command=human_roll,
                            fill="#c0c0c0", text_color="#3949ab",
                            off_fill="#e6e6e6")
roll_button.grid(row=1, column=0, columnspan=3, sticky="we", padx=4, pady=4)

# Rows 2-4: board
buttons = []
for i in range(9):
    button = tkinter.Button(frame, text="", font=("Consolas", 50, "bold"),
                            background=COLOR_GRAY, foreground=COLOR_BLUE,
                            width=4, height=1,
                            command=lambda i=i: on_cell_click(i))
    button.grid(row=2 + i // 3, column=i % 3)
    buttons.append(button)

# Row 5: dice display (H = human, R = robot)
dice_frame = tkinter.Frame(frame, background=COLOR_GRAY)
dice_frame.grid(row=5, column=0, columnspan=3, sticky="we")


def make_dice_row(title):
    """Build 'title: [d1] [d2]' inside dice_frame and return the 2 dice labels.
    title: text shown before the dice ('H:' or 'R:')"""
    tkinter.Label(dice_frame, text=title, font=("Consolas", 20),
                  background=COLOR_GRAY, foreground="white").pack(side="left", padx=(20, 4))
    dice_labels = []
    for _ in range(2):
        d = tkinter.Label(dice_frame, text="-", font=("Consolas", 20, "bold"), width=2,
                          background="white", foreground="black", relief="sunken")
        d.pack(side="left", padx=4, pady=6)
        dice_labels.append(d)
    return dice_labels


human_labels = make_dice_row("H:")
bot_labels = make_dice_row("R:")

# Row 6: Restart "button" (a Label, so the black background shows on Mac)
restart_button = tkinter.Label(frame, text="Restart", font=("Consolas", 20),
                               background="black", foreground="#ffde57",
                               pady=6, cursor="hand2")
restart_button.bind("<ButtonPress-1>",
                    lambda event: restart_button.config(background=COLOR_LIGHT_GRAY))
restart_button.bind("<ButtonRelease-1>",
                    lambda event: (restart_button.config(background="black"), new_game()))
restart_button.grid(row=6, column=0, columnspan=3, sticky="we")

frame.pack()

# Center the window
window.update()
w, h = window.winfo_width(), window.winfo_height()
x = int(window.winfo_screenwidth() / 2 - w / 2)
y = int(window.winfo_screenheight() / 2 - h / 2)
window.geometry(f"{w}x{h}+{x}+{y}")

window.mainloop()