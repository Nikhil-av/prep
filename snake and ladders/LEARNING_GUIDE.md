# 🐍🪜 SNAKE & LADDER GAME — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Snake & Ladder board game** for N players. Players take turns rolling a dice, move across a board with snakes (go down) and ladders (go up), and the first to reach position 100 wins.

---

## 🤔 THINK: Before Reading Further...
**What clarifying questions would you ask?**

<details>
<summary>👀 Click to reveal</summary>

| # | Question | Why? |
|---|----------|------|
| 1 | "How many players?" | Determines if we need a turn queue |
| 2 | "Standard 100-square board?" | Board size could be configurable |
| 3 | "What happens if you roll past 100?" | **Overshoot rule** — stay where you are |
| 4 | "Multiple dice?" | Usually 1 dice, 1-6. But could be configurable |
| 5 | "Can a snake's head be at a ladder's bottom?" | Entity placement validation |
| 6 | "Does landing on a ladder/snake end your turn, or can they chain?" | Usually single effect, no chaining |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | N players take **turns** rolling a dice |
| 2 | **Snakes** move player from head → tail (down) |
| 3 | **Ladders** move player from bottom → top (up) |
| 4 | **Overshoot rule** — must land exactly on 100 to win |
| 5 | First player to reach 100 wins, game ends |
| 6 | Board is configurable (add custom snakes/ladders) |

---

## 🤔 THINK: Entity Identification

**How many classes do you need? What's the relationship between Snake and Ladder?**

<details>
<summary>👀 Click to reveal</summary>

### Key Insight: Snake and Ladder are the SAME thing!

```
Snake:  start=25, end=5   (start > end → goes DOWN)
Ladder: start=10, end=30  (start < end → goes UP)
```

Both have a `start` position and an `end` position. The only difference is direction. So:

```python
class BoardEntity:       # Abstract base
    start: int
    end: int

class Snake(BoardEntity):   # start > end
class Ladder(BoardEntity):  # start < end
```

**Even simpler:** Just use a single `dict[int, int]` on the Board:
```python
entity_map = {25: 5, 10: 30, ...}  # position → jump_to
```
If value < key → snake. If value > key → ladder.

### All Entities:
| Entity | Purpose |
|--------|---------|
| **Dice** | roll() → random 1-6 |
| **Player** | id, name, position |
| **BoardEntity** | Abstract base (start, end) |
| **Snake** | extends BoardEntity (start > end) |
| **Ladder** | extends BoardEntity (start < end) |
| **Board** | size, entity_map, get_final_position() |
| **Game** | players, board, dice, game loop |

</details>

---

## 🔥 THE KEY METHOD: `get_final_position()`

### 🤔 THINK: What are the 3 cases when a player rolls the dice?

<details>
<summary>👀 Click to reveal</summary>

```python
def get_final_position(self, current_pos, dice_value):
    new_pos = current_pos + dice_value
    
    # Case 1: Overshoot — stay where you are
    if new_pos > self.board_size:
        return current_pos
    
    # Case 2: Landing on snake/ladder — jump
    if new_pos in self.entity_map:
        entity = self.entity_map[new_pos]
        if new_pos > entity:
            print(f"🐍 Snake! {new_pos} → {entity}")
        else:
            print(f"🪜 Ladder! {new_pos} → {entity}")
        return entity
    
    # Case 3: Normal move
    return new_pos
```

**Common bug:** Returning `new_pos` instead of `current_pos` on overshoot!

</details>

---

## 📊 Game Loop

```python
def play(self):
    while not self.is_game_over():
        for player in self.players:
            dice_value = self.dice.roll()
            old_pos = player.position
            new_pos = self.board.get_final_position(old_pos, dice_value)
            player.position = new_pos
            
            if new_pos == self.board.board_size:
                print(f"🎉 {player.name} WINS!")
                return player
```

---

## 🔗 Entity Relationships

```
Game
  ├── Board
  │     └── entity_map: dict[int, int]  (snakes + ladders combined)
  ├── Dice
  └── Players: list[Player]
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Abstract Base Class** | BoardEntity → Snake, Ladder | Shared structure, distinguishable type |
| **Composition** | Game has Board, Dice, Players | Game composes all components |
| **Singleton** (optional) | Game system | If managing multiple games |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How would you support multiple dice?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Dice:
    def __init__(self, count=1, sides=6):
        self.count = count
        self.sides = sides
    
    def roll(self):
        return sum(random.randint(1, self.sides) for _ in range(self.count))
```
Config-driven. `Dice(count=2, sides=6)` → rolls two dice, sums result.

</details>

### Q2: "How would you add special rules like 'roll 6, get another turn'?"

<details>
<summary>👀 Click to reveal</summary>

```python
def play_turn(self, player):
    while True:
        dice_value = self.dice.roll()
        self.move_player(player, dice_value)
        if dice_value != 6:  # Extra turn only on 6
            break
        if player.position == self.board.board_size:
            break
        print(f"🎲 {player.name} rolled 6! Extra turn!")
```

Or use **Strategy pattern** for game rules:
```python
class GameRule(ABC):
    def should_replay(self, dice_value) -> bool: pass

class ExtraTurnOnSix(GameRule):
    def should_replay(self, dice_value):
        return dice_value == 6
```

</details>

### Q3: "How to make the board support other game variations (100→200, circular board)?"

<details>
<summary>👀 Click to reveal</summary>

Board size is already configurable. For circular:
```python
def get_final_position(self, current, dice):
    new_pos = (current + dice) % self.board_size  # Wrap around
    return self.entity_map.get(new_pos, new_pos)
```

</details>

### Q4: "How to handle concurrent/multiplayer over network?"

<details>
<summary>👀 Click to reveal</summary>

- Game state lives on **server**
- Each player sends "roll" command via WebSocket
- Server validates turn order, applies move, broadcasts updated state
- Use **Command pattern**: `RollCommand(player_id)` → server processes → returns `GameState`

</details>

---

## ⚠️ Common Bugs

| Bug | Fix |
|-----|-----|
| Overshoot returns `new_pos` instead of `current_pos` | `if new_pos > 100: return current_pos` |
| Iterating dict keys instead of values | `for player in self.players.values()` |
| Creating new Dice() every turn | Store as `self.dice` instance variable |
| Singleton `__init__` not guarded | `if hasattr(self, '_initialized'): return` |

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design Snake & Ladder with a **Board** that stores all snakes and ladders in a **single dictionary** (`{position: jump_to}`) for O(1) lookup. Snake and Ladder extend a common **BoardEntity** ABC. The key method is `get_final_position()` which handles 3 cases: overshoot (stay), landing on entity (jump), or normal move. The Game manages turn order and checks win condition (exactly 100). Dice is configurable for count and sides."

---

## ✅ Pre-Implementation Checklist

- [ ] BoardEntity ABC with start/end
- [ ] Snake (start > end) and Ladder (start < end)
- [ ] Board with entity_map dict for O(1) lookup
- [ ] Overshoot rule in get_final_position()
- [ ] Player with position tracking
- [ ] Configurable Dice
- [ ] Game loop with turn management
- [ ] Win condition: exactly 100
- [ ] Demo with print output

---

*Document created during LLD interview prep session*
