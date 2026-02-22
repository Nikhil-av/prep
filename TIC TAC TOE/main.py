# TIC TAC TOE - Complete Implementation
# Patterns: Simple game loop, State management

from enum import Enum
from typing import List, Optional

# ============ ENUMS ============

class Player(Enum):
    X = "X"
    O = "O"
    EMPTY = " "

class GameState(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    X_WINS = "X_WINS"
    O_WINS = "O_WINS"
    DRAW = "DRAW"


# ============ BOARD ============

class Board:
    """3x3 Tic Tac Toe board."""
    
    def __init__(self):
        self.grid: List[List[Player]] = [
            [Player.EMPTY for _ in range(3)] for _ in range(3)
        ]
        self.moves_count = 0
    
    def make_move(self, row: int, col: int, player: Player) -> bool:
        """Place a mark on the board. Returns True if successful."""
        if not self._is_valid_position(row, col):
            print(f"❌ Invalid position: ({row}, {col})")
            return False
        
        if self.grid[row][col] != Player.EMPTY:
            print(f"❌ Position ({row}, {col}) is already occupied")
            return False
        
        self.grid[row][col] = player
        self.moves_count += 1
        return True
    
    def _is_valid_position(self, row: int, col: int) -> bool:
        return 0 <= row < 3 and 0 <= col < 3
    
    def is_full(self) -> bool:
        return self.moves_count >= 9
    
    def check_winner(self) -> Optional[Player]:
        """Check if there's a winner. Returns winning player or None."""
        
        # Check rows
        for row in range(3):
            if self._check_line(self.grid[row][0], self.grid[row][1], self.grid[row][2]):
                return self.grid[row][0]
        
        # Check columns
        for col in range(3):
            if self._check_line(self.grid[0][col], self.grid[1][col], self.grid[2][col]):
                return self.grid[0][col]
        
        # Check diagonals
        if self._check_line(self.grid[0][0], self.grid[1][1], self.grid[2][2]):
            return self.grid[0][0]
        
        if self._check_line(self.grid[0][2], self.grid[1][1], self.grid[2][0]):
            return self.grid[0][2]
        
        return None
    
    def _check_line(self, a: Player, b: Player, c: Player) -> bool:
        """Check if three positions have the same non-empty player."""
        return a == b == c and a != Player.EMPTY
    
    def display(self):
        """Print the board."""
        print("\n  0   1   2")
        for i, row in enumerate(self.grid):
            print(f"{i} {row[0].value} | {row[1].value} | {row[2].value}")
            if i < 2:
                print("  -----------")
        print()


# ============ PLAYER CLASS ============

class GamePlayer:
    """Represents a human player."""
    
    def __init__(self, name: str, symbol: Player):
        self.name = name
        self.symbol = symbol
    
    def get_move(self) -> tuple:
        """Get move from player input."""
        while True:
            try:
                move = input(f"{self.name} ({self.symbol.value}), enter row,col: ")
                row, col = map(int, move.strip().split(","))
                return row, col
            except ValueError:
                print("Invalid input. Enter as: row,col (e.g., 1,2)")


# ============ GAME ============

class TicTacToe:
    """Main game controller."""
    
    def __init__(self, player1_name: str = "Player 1", player2_name: str = "Player 2"):
        self.board = Board()
        self.players = [
            GamePlayer(player1_name, Player.X),
            GamePlayer(player2_name, Player.O)
        ]
        self.current_player_index = 0
        self.state = GameState.IN_PROGRESS
    
    @property
    def current_player(self) -> GamePlayer:
        return self.players[self.current_player_index]
    
    def switch_player(self):
        self.current_player_index = 1 - self.current_player_index
    
    def play_turn(self, row: int, col: int) -> bool:
        """Play a single turn. Returns True if move was valid."""
        if self.state != GameState.IN_PROGRESS:
            print("Game is already over!")
            return False
        
        if not self.board.make_move(row, col, self.current_player.symbol):
            return False
        
        # Check for winner
        winner = self.board.check_winner()
        if winner:
            self.state = GameState.X_WINS if winner == Player.X else GameState.O_WINS
        elif self.board.is_full():
            self.state = GameState.DRAW
        else:
            self.switch_player()
        
        return True
    
    def is_over(self) -> bool:
        return self.state != GameState.IN_PROGRESS
    
    def get_result(self) -> str:
        if self.state == GameState.X_WINS:
            return f"🎉 {self.players[0].name} (X) wins!"
        elif self.state == GameState.O_WINS:
            return f"🎉 {self.players[1].name} (O) wins!"
        elif self.state == GameState.DRAW:
            return "🤝 It's a draw!"
        return "Game in progress..."
    
    def play_game(self):
        """Run the full game loop."""
        print("\n" + "=" * 40)
        print("TIC TAC TOE")
        print("=" * 40)
        print("Enter moves as: row,col (e.g., 0,1)")
        
        while not self.is_over():
            self.board.display()
            row, col = self.current_player.get_move()
            self.play_turn(row, col)
        
        self.board.display()
        print(self.get_result())


# ============ DEMO (Automated Game) ============

class DemoGame:
    """Automated demo game without user input."""
    
    @staticmethod
    def run():
        print("=" * 60)
        print("TIC TAC TOE - AUTOMATED DEMO")
        print("=" * 60)
        
        game = TicTacToe("Alice", "Bob")
        
        # Predefined moves for demo
        moves = [
            (0, 0),  # X
            (1, 1),  # O
            (0, 1),  # X
            (2, 2),  # O
            (0, 2),  # X wins!
        ]
        
        for row, col in moves:
            print(f"\n{game.current_player.name} plays ({row}, {col})")
            game.play_turn(row, col)
            game.board.display()
            
            if game.is_over():
                break
        
        print(game.get_result())
        
        # Demo 2: Draw game
        print("\n" + "=" * 60)
        print("DEMO 2: Draw Game")
        print("=" * 60)
        
        game2 = TicTacToe("Player1", "Player2")
        
        draw_moves = [
            (0, 0), (0, 1), (0, 2),
            (1, 1), (1, 0), (1, 2),
            (2, 1), (2, 0), (2, 2),
        ]
        
        for row, col in draw_moves:
            game2.play_turn(row, col)
        
        game2.board.display()
        print(game2.get_result())
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED!")
        print("=" * 60)


if __name__ == "__main__":
    DemoGame.run()
    
    # Uncomment to play interactive game:
    # game = TicTacToe("Alice", "Bob")
    # game.play_game()
