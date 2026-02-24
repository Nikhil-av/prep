# ❌⭕ TIC-TAC-TOE — Complete LLD Guide
## From Zero to Interview-Ready

---

## 📖 Table of Contents
1. [Problem Statement](#-problem-statement)
2. [The Key Insight: O(1) Win Detection](#-the-key-insight)
3. [Complete Class Design with Code](#-complete-class-design)
4. [AI Strategy Pattern](#-ai-strategy)
5. [Full Working Implementation](#-full-implementation)
6. [Follow-Up Questions (15+)](#-follow-up-questions)
7. [Quick Recall Script](#-quick-recall)

---

## 🎯 Problem Statement

> Design a **Tic-Tac-Toe** game for N×N board. Handle move validation, win detection, draw detection, and extensibility for AI opponents.

**Why this is asked:**
- Tests the O(1) **win detection algorithm** — the star of this problem
- Tests **N×N extensibility** — most candidates hard-code 3×3
- Tests **Strategy pattern** for AI

---

## 🔥 The Key Insight: O(1) Win Detection with ±1 Counters

### 🤔 THINK: After every move, checking ALL rows, columns, and diagonals is O(n²). Can you do O(1)?

<details>
<summary>👀 Click to reveal — This is what makes you stand out</summary>

**The trick:** Assign **+1 for Player X** and **-1 for Player O**. Keep running sums for each row, column, and both diagonals. If any counter reaches `+n` or `-n`, that player has won!

```
Board state:
  X | O | X
  O | X | .
  . | . | X

Counters after all moves:
  row_counts    = [+1, 0, +1]     # Row 0: X+O+X = +1
  col_counts    = [0, 0, +3]      # Col 2: X+.+X = wait, need to trace...
  diag_count    = +3               # Main diagonal: X+X+X = 3 → X WINS!
  anti_diag_count = +1
```

**When `diag_count == n (=3)` → Player X wins!** No need to scan the board.

```python
class WinDetector:
    """O(1) win detection after each move."""
    
    def __init__(self, size: int):
        self.size = size
        self.row_counts = [0] * size
        self.col_counts = [0] * size
        self.diag_count = 0       # Main diagonal (top-left to bottom-right)
        self.anti_diag_count = 0  # Anti-diagonal (top-right to bottom-left)
    
    def record_move(self, row: int, col: int, value: int) -> bool:
        """
        value: +1 for Player X, -1 for Player O
        Returns True if this move wins the game.
        """
        self.row_counts[row] += value
        self.col_counts[col] += value
        
        if row == col:             # On main diagonal?
            self.diag_count += value
        if row + col == self.size - 1:  # On anti-diagonal?
            self.anti_diag_count += value
        
        # Check if any counter reached ±n
        n = self.size
        return (abs(self.row_counts[row]) == n or
                abs(self.col_counts[col]) == n or
                abs(self.diag_count) == n or
                abs(self.anti_diag_count) == n)
```

### Step-by-step trace for 3×3:

```
Move 1: X plays (0,0) — value = +1
  row_counts[0] = 1, col_counts[0] = 1
  On main diag (0==0) → diag = 1
  Max |count| = 1 < 3 → no win

Move 2: O plays (0,1) — value = -1
  row_counts[0] = 0, col_counts[1] = -1
  Not on diags
  Max |count| = 1 < 3 → no win

Move 3: X plays (1,1) — value = +1
  row_counts[1] = 1, col_counts[1] = 0
  On main diag (1==1) → diag = 2
  On anti-diag (1+1==2) → anti_diag = 1
  Max |count| = 2 < 3 → no win

Move 4: O plays (2,0) — value = -1
  row_counts[2] = -1, col_counts[0] = 0
  On anti-diag (2+0==2) → anti_diag = 0
  Max |count| = 1 < 3 → no win

Move 5: X plays (2,2) — value = +1
  row_counts[2] = 0, col_counts[2] = 1
  On main diag (2==2) → diag = 3  ← |3| == 3 → X WINS! 🎉

Winner detected in O(1) — just 4 additions and 4 comparisons!
```

### 🤔 Why ±1 instead of separate counters per player?

With separate counters, you'd need `x_row_counts[3]`, `o_row_counts[3]`, `x_col_counts[3]`, `o_col_counts[3]`... that's **8 arrays** instead of **4 counters**.

The ±1 trick combines both players into a single counter. Beautiful!

</details>

---

## 🏗️ Complete Class Design

### Player

```python
from enum import Enum
import random

class Player:
    def __init__(self, name: str, symbol: str, value: int):
        """
        value: +1 for X, -1 for O (used in win detection)
        """
        self.name = name
        self.symbol = symbol
        self.value = value
    
    def __str__(self):
        return f"{self.symbol} {self.name}"
```

### Board

```python
class Board:
    def __init__(self, size: int = 3):
        self.size = size
        self.grid = [['·'] * size for _ in range(size)]
        self.empty_cells = size * size
    
    def is_valid_move(self, row: int, col: int) -> bool:
        return (0 <= row < self.size and 
                0 <= col < self.size and 
                self.grid[row][col] == '·')
    
    def place(self, row: int, col: int, symbol: str):
        self.grid[row][col] = symbol
        self.empty_cells -= 1
    
    def is_full(self) -> bool:
        return self.empty_cells == 0
    
    def display(self):
        print()
        for i, row in enumerate(self.grid):
            print("   " + " │ ".join(row))
            if i < self.size - 1:
                print("   " + "──┼──" * (self.size - 1) + "──")
        print()
```

### TicTacToe Game

```python
class TicTacToeGame:
    def __init__(self, size: int = 3):
        self.size = size
        self.board = Board(size)
        self.detector = WinDetector(size)
        self.players: list[Player] = []
        self.current_player_idx = 0
        self.is_over = False
        self.winner: Player | None = None
        self.move_count = 0
    
    def add_player(self, name: str, symbol: str, value: int):
        self.players.append(Player(name, symbol, value))
    
    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]
    
    def make_move(self, row: int, col: int) -> bool:
        if self.is_over:
            print("   ❌ Game is over!"); return False
        
        if not self.board.is_valid_move(row, col):
            print(f"   ❌ Invalid move ({row}, {col})!"); return False
        
        player = self.current_player
        self.board.place(row, col, player.symbol)
        self.move_count += 1
        
        # O(1) win check!
        if self.detector.record_move(row, col, player.value):
            self.is_over = True
            self.winner = player
            print(f"   🏆 {player} wins!")
            return True
        
        # Draw check
        if self.board.is_full():
            self.is_over = True
            print("   🤝 Draw!")
            return True
        
        # Next player's turn
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        return True
```

---

## 🤖 AI Strategy Pattern

### 🤔 THINK: How to support different AI difficulties?

<details>
<summary>👀 Click to reveal</summary>

```python
from abc import ABC, abstractmethod

class AIStrategy(ABC):
    @abstractmethod
    def choose_move(self, board: Board, player: Player) -> tuple[int, int]:
        pass

class RandomAI(AIStrategy):
    """Easy: picks a random empty cell."""
    def choose_move(self, board, player):
        empty = [(r, c) for r in range(board.size) 
                 for c in range(board.size) if board.grid[r][c] == '·']
        return random.choice(empty)

class MinimaxAI(AIStrategy):
    """
    Unbeatable: uses Minimax algorithm.
    
    For 3×3: explores all possible future states (max 9! = 362,880).
    Returns move that maximizes AI's chance and minimizes opponent's.
    """
    def choose_move(self, board, player):
        best_score = float('-inf')
        best_move = None
        
        for r in range(board.size):
            for c in range(board.size):
                if board.grid[r][c] == '·':
                    board.grid[r][c] = player.symbol
                    score = self._minimax(board, player, False, 0)
                    board.grid[r][c] = '·'
                    if score > best_score:
                        best_score = score
                        best_move = (r, c)
        
        return best_move
    
    def _minimax(self, board, ai_player, is_maximizing, depth):
        # Check terminal states
        winner = self._check_winner(board)
        if winner == ai_player.symbol: return 10 - depth
        if winner and winner != ai_player.symbol: return depth - 10
        if all(board.grid[r][c] != '·' for r in range(board.size) 
               for c in range(board.size)): return 0
        
        if is_maximizing:
            best = float('-inf')
            for r in range(board.size):
                for c in range(board.size):
                    if board.grid[r][c] == '·':
                        board.grid[r][c] = ai_player.symbol
                        best = max(best, self._minimax(board, ai_player, False, depth+1))
                        board.grid[r][c] = '·'
            return best
        else:
            best = float('inf')
            opp = 'O' if ai_player.symbol == 'X' else 'X'
            for r in range(board.size):
                for c in range(board.size):
                    if board.grid[r][c] == '·':
                        board.grid[r][c] = opp
                        best = min(best, self._minimax(board, ai_player, True, depth+1))
                        board.grid[r][c] = '·'
            return best
    
    def _check_winner(self, board):
        n = board.size
        for i in range(n):
            if board.grid[i][0] != '·' and all(board.grid[i][c] == board.grid[i][0] for c in range(n)):
                return board.grid[i][0]
            if board.grid[0][i] != '·' and all(board.grid[r][i] == board.grid[0][i] for r in range(n)):
                return board.grid[0][i]
        if board.grid[0][0] != '·' and all(board.grid[i][i] == board.grid[0][0] for i in range(n)):
            return board.grid[0][0]
        if board.grid[0][n-1] != '·' and all(board.grid[i][n-1-i] == board.grid[0][n-1] for i in range(n)):
            return board.grid[0][n-1]
        return None
```

**Why Strategy pattern?**
```python
# Easy mode
game = TicTacToeVsAI(ai_strategy=RandomAI())

# Hard mode  
game = TicTacToeVsAI(ai_strategy=MinimaxAI())

# Same game code, different intelligence!
```

</details>

---

## 🔧 Full Demo

```python
if __name__ == "__main__":
    print("=" * 40)
    print("   TIC-TAC-TOE DEMO (3×3)")
    print("=" * 40)
    
    game = TicTacToeGame(3)
    game.add_player("Alice", "X", +1)
    game.add_player("Bob", "O", -1)
    
    moves = [(0,0), (0,1), (1,1), (0,2), (2,2)]  # X wins diagonal
    
    for r, c in moves:
        print(f"\n   {game.current_player} plays ({r}, {c})")
        game.make_move(r, c)
        game.board.display()
        if game.is_over: break
    
    print("\n" + "=" * 40)
    print("   4×4 DEMO")
    print("=" * 40)
    
    game4 = TicTacToeGame(4)
    game4.add_player("Carol", "X", +1)
    game4.add_player("Dave", "O", -1)
    
    # X wins row 0
    moves4 = [(0,0), (1,0), (0,1), (1,1), (0,2), (1,2), (0,3)]
    for r, c in moves4:
        game4.make_move(r, c)
        if game4.is_over:
            game4.board.display()
            break
```

---

## 🎤 Follow-Up Questions (15+)

| Q | Question | Key Answer |
|---|----------|-----------|
| 1 | "O(1) vs O(n²) win check?" | ±1 counters: 4 additions + 4 comparisons vs scanning entire board |
| 2 | "N×N extensibility?" | WinDetector works for any N. Just change `size` param |
| 3 | "Minimax complexity?" | O(b^d): branching factor b, depth d. For 3×3, max ~9! states |
| 4 | "Alpha-beta pruning?" | Cut Minimax tree by eliminating branches that won't affect result |
| 5 | "More than 2 players?" | Add more values (+1, -1, +2); win = any counter = ±n |
| 6 | "Connect 4?" | Same counter approach but check for 4-in-a-row, gravity |
| 7 | "Undo move?" | Command pattern: store move as command, undo reverses counter |
| 8 | "Online multiplayer?" | Server holds game state, WebSocket for moves |
| 9 | "Different board shapes?" | Hex grid → different adjacency, same counter idea |
| 10 | "Tournament mode?" | Bracket manager, match results, leaderboard |
| 11 | "Why +1/-1 instead of X/O?" | Math: `sum == n` means n X's in a line. Can't do math with chars |
| 12 | "Draw detection?" | `empty_cells == 0` and no winner |
| 13 | "Symmetry optimization?" | First move = only 3 unique positions (corner, edge, center) |
| 14 | "Compare with Chess?" | Both: turn-based, ABC for extensibility. Chess: much more complex |
| 15 | "Why is Pawn hard but TicTacToe is simple?" | Fewer rules, fixed board, no piece hierarchy |

---

## 🧠 Quick Recall Script

> "**O(1) win detection** is the star. Assign **+1 to X, -1 to O**. Maintain `row_counts[n]`, `col_counts[n]`, `diag_count`, `anti_diag_count`. After each move, increment counters. If any `|counter| == n` → that player wins. Works for N×N. AI uses **Strategy pattern**: RandomAI (easy), MinimaxAI (unbeatable)."

---

## ✅ Pre-Implementation Checklist

- [ ] Player (name, symbol, value: +1/-1)
- [ ] Board (grid, size, is_valid_move, place, is_full, display)
- [ ] WinDetector (row_counts, col_counts, diag, anti_diag, record_move → bool)
- [ ] record_move: increment 4 counters, check |counter| == n
- [ ] TicTacToeGame (board, detector, players, current_player, make_move)
- [ ] make_move: validate → place → check win → check draw → switch player
- [ ] AIStrategy ABC → RandomAI, MinimaxAI
- [ ] Demo: 3×3 with win, 4×4 extensibility demo

---

*Version 3.0 — Truly Comprehensive Edition*
