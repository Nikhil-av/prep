# ❌⭕ TIC TAC TOE — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Tic-Tac-Toe game** — two players take turns placing marks (X/O) on a 3×3 grid. First to get 3 in a row (horizontal, vertical, or diagonal) wins.

---

## 🤔 THINK: Before Reading Further...
**This seems simple. What makes it interview-worthy?**

<details>
<summary>👀 Click to reveal</summary>

The game is simple, but interviewers test:
1. **Clean OOP design** — separate Board, Player, Game concerns
2. **Extensible to N×N grid** — not hardcoded for 3
3. **Win condition algorithm** — O(1) check vs O(N²) brute force
4. **Input validation** — occupied cell, out of bounds
5. **Ability to add AI opponent** — Strategy pattern for player types

The real question is: **Can you make a simple problem extensible?**

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Two players take alternate turns |
| 2 | Place mark (X/O) on empty cell |
| 3 | Win detection: 3-in-a-row (row, column, or diagonal) |
| 4 | Draw detection: all cells filled, no winner |
| 5 | Input validation: occupied cell, out of bounds |
| 6 | **Extensible to N×N grid** |

---

## 🔥 THE KEY INSIGHT: O(1) Win Detection

### 🤔 THINK: After each move, how do you check if someone won? Do you scan the entire board?

<details>
<summary>👀 Click to reveal</summary>

**❌ WRONG: Scan entire board after each move — O(N²)**
```python
def check_win(self):
    for row in self.grid:
        if all(cell == 'X' for cell in row): return True
    # ... check columns, diagonals
```

**✅ CORRECT: Track counts per row/col/diagonal — O(1) per move!**

```python
class Board:
    def __init__(self, n):
        self.n = n
        self.row_count = [{} for _ in range(n)]    # row_count[r][player] = count
        self.col_count = [{} for _ in range(n)]    # col_count[c][player] = count
        self.diag_count = {}                        # main diagonal
        self.anti_diag_count = {}                   # anti-diagonal
    
    def place_mark(self, row, col, player):
        self.grid[row][col] = player.symbol
        
        # Update counts
        self.row_count[row][player] = self.row_count[row].get(player, 0) + 1
        self.col_count[col][player] = self.col_count[col].get(player, 0) + 1
        if row == col:
            self.diag_count[player] = self.diag_count.get(player, 0) + 1
        if row + col == self.n - 1:
            self.anti_diag_count[player] = self.anti_diag_count.get(player, 0) + 1
        
        # Check win — O(1)!
        if (self.row_count[row].get(player, 0) == self.n or
            self.col_count[col].get(player, 0) == self.n or
            self.diag_count.get(player, 0) == self.n or
            self.anti_diag_count.get(player, 0) == self.n):
            return True  # WIN!
        
        return False
```

**This scales to any N×N board!** O(1) check vs O(N²) brute force.

> **Interview tip:** Start with O(N²) brute force, then optimize to O(1) — shows optimization thinking.

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal all entities</summary>

| Entity | Key Attributes |
|--------|---------------|
| **Player** | id, name, symbol (X/O) |
| **Board** | grid[N][N], row/col/diag counts |
| **Game** | players, board, current_turn, status |
| **GameStatus** | IN_PROGRESS, WIN, DRAW |
| **PlayerType** (optional) | HUMAN, AI (for extensibility) |

</details>

---

## 🔗 Entity Relationships

```
Game
    ├── Board
    │     ├── grid[N][N]: str | None
    │     └── row/col/diag counts (for O(1) win check)
    ├── Players: [Player_X, Player_O]
    └── current_turn: Player
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to extend to N×N grid where K-in-a-row wins?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Board:
    def __init__(self, n, k):
        self.n = n    # Grid size
        self.k = k    # Win length

    # O(1) check: just compare count >= k instead of count == n
    if self.row_count[row].get(player, 0) >= self.k:
        return True
```

Examples: 5×5 with 4-in-a-row, 15×15 with 5-in-a-row (Gomoku).

</details>

### Q2: "How to add an AI opponent?"

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern:**
```python
class MoveStrategy(ABC):
    @abstractmethod
    def get_move(self, board) -> tuple[int, int]: pass

class HumanInput(MoveStrategy):
    def get_move(self, board):
        row = int(input("Row: "))
        col = int(input("Col: "))
        return (row, col)

class RandomAI(MoveStrategy):
    def get_move(self, board):
        empty = [(r,c) for r in range(board.n) 
                 for c in range(board.n) if board.grid[r][c] is None]
        return random.choice(empty)

class MinimaxAI(MoveStrategy):
    def get_move(self, board):
        # Minimax algorithm with alpha-beta pruning
        ...
```

</details>

### Q3: "How to support undo?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Game:
    move_history: list[tuple[int, int, Player]]
    
    def undo(self):
        row, col, player = self.move_history.pop()
        self.board.grid[row][col] = None
        # Decrement counts
        self.board.row_count[row][player] -= 1
        self.board.col_count[col][player] -= 1
        # ... update diag counts
        self.current_turn = player  # Give turn back
```

</details>

### Q4: "How to support multiplayer (>2 players)?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Game:
    def __init__(self, players: list[Player], board_size: int):
        self.players = players  # 3+ players
        self.current_index = 0
    
    def next_turn(self):
        self.current_index = (self.current_index + 1) % len(self.players)
```

Each player has a unique symbol. Board tracks counts per player.

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design TicTacToe with **Board, Player, Game** classes. The key optimization is **O(1) win detection** — I track counts per row, column, and both diagonals. After each move, I check if any count equals N. For extensibility, the board supports N×N with K-in-a-row wins. I'd use **Strategy pattern** for player types (Human, RandomAI, MinimaxAI) to make it extensible."

---

## ✅ Pre-Implementation Checklist

- [ ] Player (name, symbol)
- [ ] Board (N×N grid, O(1) win detection via counts)
- [ ] Input validation (bounds, occupied cell)
- [ ] Win detection (row, col, both diagonals)
- [ ] Draw detection (all cells filled + no winner)
- [ ] Game loop (alternate turns)
- [ ] Extensible to N×N
- [ ] Demo: play a game, show win/draw

---

*Document created during LLD interview prep session*
