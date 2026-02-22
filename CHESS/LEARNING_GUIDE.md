# ♟️ CHESS GAME — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Chess game** for two players. Support all standard chess rules including piece movements, turn management, check/checkmate detection, and special moves.

---

## 🤔 THINK: Before Reading Further...
**What makes Chess the hardest LLD problem?**

<details>
<summary>👀 Click to reveal</summary>

1. **8 different piece types** each with unique movement rules
2. **Move validation** depends on current board state (can't move through pieces)
3. **Check detection** — is the king under threat after every move?
4. **Checkmate detection** — no legal move exists to escape check
5. **Special moves** — castling, en passant, pawn promotion
6. **Game state** — check, checkmate, stalemate, draw

The core challenge is: **How do you structure movement rules to be extensible without a massive if-else chain?**

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Two players (White, Black) take alternate turns |
| 2 | **6 piece types**: King, Queen, Rook, Bishop, Knight, Pawn |
| 3 | Each piece has its own **movement rules** |
| 4 | Validate moves — can't move through pieces (except Knight) |
| 5 | **Capture** — move to square occupied by opponent |
| 6 | **Check** — king is under attack |
| 7 | **Checkmate** — king is in check with no escape |
| 8 | **Special moves** — castling, en passant, pawn promotion |

---

## 🔥 THE KEY INSIGHT: Piece as Abstract Class

### 🤔 THINK: How to handle 6 different movement rules without a massive if-else?

<details>
<summary>👀 Click to reveal</summary>

**Polymorphism!** Each piece overrides `get_possible_moves()`:

```python
class Piece(ABC):
    def __init__(self, color, row, col):
        self.color = color
        self.row = row
        self.col = col

    @abstractmethod
    def get_possible_moves(self, board) -> list[tuple[int, int]]:
        """Returns all squares this piece can move to."""
        pass

class Knight(Piece):
    def get_possible_moves(self, board):
        moves = []
        offsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),
                   (1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in offsets:
            r, c = self.row + dr, self.col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = board.get_piece(r, c)
                if target is None or target.color != self.color:
                    moves.append((r, c))
        return moves
```

**Each piece knows its own rules** — Board doesn't need to know how a Knight moves.

</details>

---

## 📦 Movement Rules Quick Reference

### 🤔 THINK: Can you list how each piece moves? (rows, columns, diagonals)?

<details>
<summary>👀 Click to reveal</summary>

| Piece | Movement | Can Jump? | Special |
|-------|----------|-----------|---------|
| **King** | 1 square any direction | ❌ | Castling |
| **Queen** | Any number, any direction | ❌ | — |
| **Rook** | Any number, horizontal/vertical | ❌ | Part of castling |
| **Bishop** | Any number, diagonal | ❌ | — |
| **Knight** | L-shape (2+1) | ✅ Yes! | Only jumper |
| **Pawn** | 1 forward (2 from start), capture diagonal | ❌ | En passant, promotion |

**Sliding pieces** (Queen, Rook, Bishop) share logic — move in a direction until blocked:
```python
def get_sliding_moves(self, board, directions):
    moves = []
    for dr, dc in directions:
        r, c = self.row + dr, self.col + dc
        while 0 <= r < 8 and 0 <= c < 8:
            target = board.get_piece(r, c)
            if target is None:
                moves.append((r, c))
            elif target.color != self.color:
                moves.append((r, c))  # Capture
                break                  # Can't go further
            else:
                break                  # Blocked by own piece
            r += dr
            c += dc
    return moves
```

Queen = Rook directions + Bishop directions!

</details>

---

## 📊 Board Representation

### 🤔 THINK: 2D array or dictionary?

<details>
<summary>👀 Click to reveal</summary>

**2D array is natural for chess:**
```python
class Board:
    def __init__(self):
        self.grid = [[None]*8 for _ in range(8)]
        self._setup_pieces()
    
    def get_piece(self, row, col) -> Piece | None:
        return self.grid[row][col]
    
    def move_piece(self, piece, new_row, new_col):
        self.grid[piece.row][piece.col] = None
        self.grid[new_row][new_col] = piece
        piece.row, piece.col = new_row, new_col
```

**Initial setup:**
```
Row 0: [R, N, B, Q, K, B, N, R]  ← Black
Row 1: [P, P, P, P, P, P, P, P]  ← Black pawns
Row 2-5: [empty]
Row 6: [P, P, P, P, P, P, P, P]  ← White pawns
Row 7: [R, N, B, Q, K, B, N, R]  ← White
```

</details>

---

## 🔗 Entity Relationships

```
Game
    ├── Board
    │     └── grid[8][8]: Piece | None
    ├── Players: [White, Black]
    ├── current_turn: Color
    └── status: GameStatus (ACTIVE, CHECK, CHECKMATE, STALEMATE, DRAW)

Piece (ABC)
    ├── color: Color
    ├── row, col
    └── get_possible_moves(board)

King, Queen, Rook, Bishop, Knight, Pawn ← extend Piece
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to detect check?"

<details>
<summary>👀 Click to reveal</summary>

```python
def is_in_check(self, color):
    king_pos = self.find_king(color)
    # Check if ANY opponent piece can move to king's position
    for piece in self.get_all_pieces(opponent_color):
        if king_pos in piece.get_possible_moves(self):
            return True
    return False
```

</details>

### Q2: "How to detect checkmate?"

<details>
<summary>👀 Click to reveal</summary>

```python
def is_checkmate(self, color):
    if not self.is_in_check(color):
        return False  # Not even in check
    
    # Try EVERY possible move for this color
    for piece in self.get_all_pieces(color):
        for move in piece.get_possible_moves(self):
            # Simulate the move
            if not self.would_still_be_in_check(piece, move):
                return False  # Found an escape!
    
    return True  # No escape exists = checkmate
```
**Key:** Must simulate each move and check if king is STILL in check after it.

</details>

### Q3: "How to implement castling?"

<details>
<summary>👀 Click to reveal</summary>

Conditions: King not moved, Rook not moved, no pieces between, king not in check, king doesn't pass through check.
```python
class King(Piece):
    def __init__(self, ...):
        self.has_moved = False
    
    def can_castle(self, board, rook):
        if self.has_moved or rook.has_moved: return False
        if board.is_in_check(self.color): return False
        # Check path is clear and not under attack
        ...
```

</details>

### Q4: "How to implement undo/redo?"

<details>
<summary>👀 Click to reveal</summary>

**Command pattern!**
```python
class MoveCommand:
    piece, from_pos, to_pos, captured_piece
    
    def execute(self, board): ...
    def undo(self, board): ...

class Game:
    move_history: list[MoveCommand]
    
    def undo(self):
        last_move = self.move_history.pop()
        last_move.undo(self.board)
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd use **Piece as an ABC** with 6 subclasses, each implementing `get_possible_moves(board)`. The Board is an 8×8 grid. Sliding pieces (Queen, Rook, Bishop) share move generation logic — move in a direction until blocked. **Check detection** checks if any opponent piece targets the king. **Checkmate** tries every legal move to see if check can be escaped. For extensibility, I'd use the **Command pattern** for undo/redo."

---

## ✅ Pre-Implementation Checklist

- [ ] Color enum (WHITE, BLACK)
- [ ] Piece ABC with get_possible_moves()
- [ ] Knight (L-shape, can jump)
- [ ] Sliding pieces: Rook (horizontal/vertical), Bishop (diagonal), Queen (both)
- [ ] King (1 square, castling), Pawn (forward, capture diagonal, promotion)
- [ ] Board with 8×8 grid, initial setup
- [ ] Move validation (can't stay in check)
- [ ] Check detection, Checkmate detection
- [ ] Game: turn management, status tracking
- [ ] Demo: play a few moves, demonstrate check

---

*Document created during LLD interview prep session*
