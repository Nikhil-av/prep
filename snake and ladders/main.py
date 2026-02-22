from enum import Enum
from abc import ABC
import uuid
import random

# ═══════════════════════════════════════════════════════════════
#                        ENUMS
# ═══════════════════════════════════════════════════════════════

class PlayerStatus(Enum):
    PLAYING = 1
    WON = 2

class GameStatus(Enum):
    IN_PROGRESS = 1
    FINISHED = 2

# ═══════════════════════════════════════════════════════════════
#                        ENTITIES
# ═══════════════════════════════════════════════════════════════

class Player:
    def __init__(self, name):
        self.name = name
        self._id = uuid.uuid4()
        self.status = PlayerStatus.PLAYING
        self.position = 0  # 0 = off the board
    def set_status(self, status):
        self.status = status
    def set_position(self, position):
        self.position = position
    def get_position(self):
        return self.position
    def get_status(self):
        return self.status
    def __str__(self):
        return f"Player: {self.name}, Position: {self.position}, Status: {self.status.name}"

class Dice:
    def __init__(self, start=1, end=6):
        self.start = start
        self.end = end
    def roll(self):
        return random.randint(self.start, self.end)

class BoardEntity(ABC):
    """Abstract base — both Snake and Ladder are just (start → end) mappings."""
    def __init__(self, start_pos, end_pos):
        self.start_pos = start_pos
        self.end_pos = end_pos

class Snake(BoardEntity):
    def __init__(self, head, tail):
        assert head > tail, "Snake head must be higher than tail!"
        super().__init__(head, tail)
    def __str__(self):
        return f"🐍 Snake({self.start_pos} → {self.end_pos})"

class Ladder(BoardEntity):
    def __init__(self, bottom, top):
        assert top > bottom, "Ladder top must be higher than bottom!"
        super().__init__(bottom, top)
    def __str__(self):
        return f"🪜 Ladder({self.start_pos} → {self.end_pos})"

class Board:
    def __init__(self, board_size=100):
        self.board_size = board_size
        # Single entity map for O(1) lookup — cleaner than separate dicts
        self.entity_map = {}  # {start_pos: BoardEntity}

    def add_snake(self, snake: Snake):
        self.entity_map[snake.start_pos] = snake

    def add_ladder(self, ladder: Ladder):
        self.entity_map[ladder.start_pos] = ladder

    def get_final_position(self, position):
        """Check if position has a snake or ladder, return final position."""
        if position in self.entity_map:
            entity = self.entity_map[position]
            print(f"       {entity}")
            return entity.end_pos
        return position

class Game:
    def __init__(self, players: list[Player], board: Board):
        self.players = {p._id: p for p in players}  # Dict for O(1) lookup
        self.player_order = list(self.players.keys())  # Maintain turn order
        self.status = GameStatus.IN_PROGRESS
        self.board = board
        self.dice = Dice()  # Create ONCE, not every turn
        self.winner = None

    def add_player(self, player: Player):
        self.players[player._id] = player
        self.player_order.append(player._id)

    def is_game_on(self):
        return self.status == GameStatus.IN_PROGRESS

    def simulate_game(self):
        print("\n🎲 Game Started!")
        print(f"   Players: {', '.join(p.name for p in self.players.values())}")
        print("─" * 50)

        turn_count = 0
        while self.is_game_on():
            for player_id in self.player_order:
                player = self.players[player_id]

                if player.get_status() != PlayerStatus.PLAYING:
                    continue

                roll = self.dice.roll()
                curr_pos = player.get_position()
                new_pos = curr_pos + roll

                # Overshoot rule: must land EXACTLY on 100
                if new_pos > self.board.board_size:
                    print(f"   {player.name} at {curr_pos}, rolled {roll} → {new_pos} > {self.board.board_size}, stays at {curr_pos}")
                    continue

                # Check for snake or ladder
                final_pos = self.board.get_final_position(new_pos)
                player.set_position(final_pos)

                if final_pos != new_pos:
                    print(f"   {player.name} at {curr_pos}, rolled {roll} → {new_pos} → moved to {final_pos}")
                else:
                    print(f"   {player.name} at {curr_pos}, rolled {roll} → moved to {final_pos}")

                # Win condition
                if final_pos == self.board.board_size:
                    player.set_status(PlayerStatus.WON)
                    self.status = GameStatus.FINISHED
                    self.winner = player
                    print(f"\n🎉 {player.name} WINS at position {self.board.board_size}!")
                    return player

            turn_count += 1

        return None


class SnakeAndLadders:
    """Singleton — manages board and games."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SnakeAndLadders, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, board_size=100):
        if self._initialized:
            return
        self._initialized = True
        self.board_size = board_size
        self.board = Board(board_size)
        self.games = []

    def add_snake(self, snake: Snake):
        self.board.add_snake(snake)

    def add_ladder(self, ladder: Ladder):
        self.board.add_ladder(ladder)

    def create_game(self, players: list[Player]) -> Game:
        game = Game(players, self.board)
        self.games.append(game)
        return game


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("     SNAKE & LADDER - LLD DEMO")
    print("=" * 50)

    # --- Setup System ---
    system = SnakeAndLadders(board_size=100)

    # --- Add Snakes ---
    print("\n🐍 Adding Snakes:")
    snakes = [Snake(99, 10), Snake(65, 25), Snake(52, 11), Snake(34, 1)]
    for s in snakes:
        system.add_snake(s)
        print(f"   {s}")

    # --- Add Ladders ---
    print("\n🪜 Adding Ladders:")
    ladders = [Ladder(3, 38), Ladder(8, 30), Ladder(28, 74), Ladder(58, 77), Ladder(75, 86)]
    for l in ladders:
        system.add_ladder(l)
        print(f"   {l}")

    # --- Create Players ---
    player1 = Player("Nikhil")
    player2 = Player("Priya")
    player3 = Player("Rahul")

    # --- Create & Play Game ---
    game = system.create_game([player1, player2, player3])
    winner = game.simulate_game()

    # --- Final Positions ---
    print("\n📊 Final Positions:")
    for player in game.players.values():
        print(f"   {player}")

    # --- Singleton Check ---
    print(f"\n🔒 Singleton Check:")
    system2 = SnakeAndLadders()
    print(f"   system is system2: {system is system2} ✓")

    print("\n" + "=" * 50)
    print("     GAME COMPLETE! 🎉")
    print("=" * 50)