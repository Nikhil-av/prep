# CHESS - Complete Implementation
# Patterns: Factory (pieces), Strategy (validation), Template Method

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple

# ============ ENUMS ============

class Color(Enum):
    WHITE = "WHITE"
    BLACK = "BLACK"

class GameStatus(Enum):
    ACTIVE = "ACTIVE"
    WHITE_WINS = "WHITE_WINS"
    BLACK_WINS = "BLACK_WINS"
    STALEMATE = "STALEMATE"


# ============ POSITION ============

class Position:
    """Represents a position on the chess board."""
    
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    
    def is_valid(self) -> bool:
        return 0 <= self.row < 8 and 0 <= self.col < 8
    
    def __eq__(self, other):
        if isinstance(other, Position):
            return self.row == other.row and self.col == other.col
        return False
    
    def __hash__(self):
        return hash((self.row, self.col))
    
    def __str__(self):
        cols = "abcdefgh"
        return f"{cols[self.col]}{8 - self.row}"


# ============ PIECE (Abstract) ============

class Piece(ABC):
    """Abstract base class for all chess pieces."""
    
    def __init__(self, color: Color, position: Position):
        self.color = color
        self.position = position
        self.has_moved = False
    
    @abstractmethod
    def get_symbol(self) -> str:
        pass
    
    @abstractmethod
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        """Get all valid moves for this piece on the given board."""
        pass
    
    def can_move_to(self, target: Position, board: 'Board') -> bool:
        """Check if this piece can move to the target position."""
        return target in self.get_valid_moves(board)
    
    def _is_path_clear(self, target: Position, board: 'Board') -> bool:
        """Check if path is clear (for Rook, Bishop, Queen)."""
        row_dir = 0 if target.row == self.position.row else (1 if target.row > self.position.row else -1)
        col_dir = 0 if target.col == self.position.col else (1 if target.col > self.position.col else -1)
        
        current = Position(self.position.row + row_dir, self.position.col + col_dir)
        while current != target:
            if board.get_piece(current) is not None:
                return False
            current = Position(current.row + row_dir, current.col + col_dir)
        return True
    
    def __str__(self):
        return f"{self.get_symbol()}"


# ============ PIECE IMPLEMENTATIONS ============

class King(Piece):
    def get_symbol(self) -> str:
        return "♔" if self.color == Color.WHITE else "♚"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        for dr, dc in directions:
            new_pos = Position(self.position.row + dr, self.position.col + dc)
            if new_pos.is_valid():
                piece = board.get_piece(new_pos)
                if piece is None or piece.color != self.color:
                    moves.append(new_pos)
        
        return moves


class Queen(Piece):
    def get_symbol(self) -> str:
        return "♕" if self.color == Color.WHITE else "♛"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        directions = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1), (1,-1), (1,0), (1,1)]
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + dr*i, self.position.col + dc*i)
                if not new_pos.is_valid():
                    break
                piece = board.get_piece(new_pos)
                if piece is None:
                    moves.append(new_pos)
                elif piece.color != self.color:
                    moves.append(new_pos)
                    break
                else:
                    break
        
        return moves


class Rook(Piece):
    def get_symbol(self) -> str:
        return "♖" if self.color == Color.WHITE else "♜"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        directions = [(-1,0), (1,0), (0,-1), (0,1)]  # Vertical and horizontal
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + dr*i, self.position.col + dc*i)
                if not new_pos.is_valid():
                    break
                piece = board.get_piece(new_pos)
                if piece is None:
                    moves.append(new_pos)
                elif piece.color != self.color:
                    moves.append(new_pos)
                    break
                else:
                    break
        
        return moves


class Bishop(Piece):
    def get_symbol(self) -> str:
        return "♗" if self.color == Color.WHITE else "♝"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        directions = [(-1,-1), (-1,1), (1,-1), (1,1)]  # Diagonals
        
        for dr, dc in directions:
            for i in range(1, 8):
                new_pos = Position(self.position.row + dr*i, self.position.col + dc*i)
                if not new_pos.is_valid():
                    break
                piece = board.get_piece(new_pos)
                if piece is None:
                    moves.append(new_pos)
                elif piece.color != self.color:
                    moves.append(new_pos)
                    break
                else:
                    break
        
        return moves


class Knight(Piece):
    def get_symbol(self) -> str:
        return "♘" if self.color == Color.WHITE else "♞"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
        
        for dr, dc in knight_moves:
            new_pos = Position(self.position.row + dr, self.position.col + dc)
            if new_pos.is_valid():
                piece = board.get_piece(new_pos)
                if piece is None or piece.color != self.color:
                    moves.append(new_pos)
        
        return moves


class Pawn(Piece):
    def get_symbol(self) -> str:
        return "♙" if self.color == Color.WHITE else "♟"
    
    def get_valid_moves(self, board: 'Board') -> List[Position]:
        moves = []
        direction = -1 if self.color == Color.WHITE else 1  # White moves up, Black moves down
        
        # Forward move
        new_pos = Position(self.position.row + direction, self.position.col)
        if new_pos.is_valid() and board.get_piece(new_pos) is None:
            moves.append(new_pos)
            
            # Double move from starting position
            start_row = 6 if self.color == Color.WHITE else 1
            if self.position.row == start_row:
                double_pos = Position(self.position.row + 2*direction, self.position.col)
                if board.get_piece(double_pos) is None:
                    moves.append(double_pos)
        
        # Diagonal captures
        for dc in [-1, 1]:
            capture_pos = Position(self.position.row + direction, self.position.col + dc)
            if capture_pos.is_valid():
                piece = board.get_piece(capture_pos)
                if piece is not None and piece.color != self.color:
                    moves.append(capture_pos)
        
        return moves


# ============ PIECE FACTORY ============

class PieceFactory:
    """Factory for creating chess pieces."""
    
    @staticmethod
    def create_piece(piece_type: str, color: Color, position: Position) -> Piece:
        pieces = {
            'K': King,
            'Q': Queen,
            'R': Rook,
            'B': Bishop,
            'N': Knight,
            'P': Pawn,
        }
        if piece_type not in pieces:
            raise ValueError(f"Unknown piece type: {piece_type}")
        return pieces[piece_type](color, position)


# ============ BOARD ============

class Board:
    """8x8 Chess board."""
    
    def __init__(self):
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self._setup_pieces()
    
    def _setup_pieces(self):
        """Set up initial chess position."""
        # Back row pieces order
        back_row = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        
        # Black pieces (rows 0-1)
        for col, piece_type in enumerate(back_row):
            self.grid[0][col] = PieceFactory.create_piece(piece_type, Color.BLACK, Position(0, col))
        for col in range(8):
            self.grid[1][col] = PieceFactory.create_piece('P', Color.BLACK, Position(1, col))
        
        # White pieces (rows 6-7)
        for col in range(8):
            self.grid[6][col] = PieceFactory.create_piece('P', Color.WHITE, Position(6, col))
        for col, piece_type in enumerate(back_row):
            self.grid[7][col] = PieceFactory.create_piece(piece_type, Color.WHITE, Position(7, col))
    
    def get_piece(self, position: Position) -> Optional[Piece]:
        if not position.is_valid():
            return None
        return self.grid[position.row][position.col]
    
    def set_piece(self, position: Position, piece: Optional[Piece]):
        self.grid[position.row][position.col] = piece
        if piece:
            piece.position = position
    
    def move_piece(self, from_pos: Position, to_pos: Position) -> Optional[Piece]:
        """Move a piece. Returns captured piece if any."""
        piece = self.get_piece(from_pos)
        captured = self.get_piece(to_pos)
        
        self.set_piece(to_pos, piece)
        self.set_piece(from_pos, None)
        piece.has_moved = True
        
        return captured
    
    def find_king(self, color: Color) -> Optional[Position]:
        """Find the king of given color."""
        for row in range(8):
            for col in range(8):
                piece = self.grid[row][col]
                if isinstance(piece, King) and piece.color == color:
                    return Position(row, col)
        return None
    
    def display(self):
        """Print the board."""
        print("\n    a   b   c   d   e   f   g   h")
        print("  +---+---+---+---+---+---+---+---+")
        for row in range(8):
            print(f"{8-row} |", end="")
            for col in range(8):
                piece = self.grid[row][col]
                symbol = piece.get_symbol() if piece else " "
                print(f" {symbol} |", end="")
            print(f" {8-row}")
            print("  +---+---+---+---+---+---+---+---+")
        print("    a   b   c   d   e   f   g   h\n")


# ============ GAME ============

class ChessGame:
    """Main chess game controller."""
    
    def __init__(self):
        self.board = Board()
        self.current_turn = Color.WHITE
        self.status = GameStatus.ACTIVE
        self.move_history: List[str] = []
    
    def switch_turn(self):
        self.current_turn = Color.BLACK if self.current_turn == Color.WHITE else Color.WHITE
    
    def make_move(self, from_str: str, to_str: str) -> bool:
        """
        Make a move using algebraic notation (e.g., 'e2' to 'e4').
        Returns True if move was successful.
        """
        try:
            from_pos = self._parse_position(from_str)
            to_pos = self._parse_position(to_str)
        except (ValueError, IndexError):
            print("❌ Invalid position format. Use format like 'e2'")
            return False
        
        piece = self.board.get_piece(from_pos)
        
        if piece is None:
            print(f"❌ No piece at {from_str}")
            return False
        
        if piece.color != self.current_turn:
            print(f"❌ It's {self.current_turn.value}'s turn")
            return False
        
        if not piece.can_move_to(to_pos, self.board):
            print(f"❌ Invalid move for {piece.get_symbol()}")
            return False
        
        # Make the move
        captured = self.board.move_piece(from_pos, to_pos)
        
        # Record move
        capture_str = "x" if captured else ""
        self.move_history.append(f"{piece.get_symbol()}{from_str}{capture_str}{to_str}")
        
        # Check for king capture (simplified win condition)
        if isinstance(captured, King):
            self.status = GameStatus.WHITE_WINS if self.current_turn == Color.WHITE else GameStatus.BLACK_WINS
            print(f"🎉 {self.current_turn.value} wins by capturing the King!")
        
        print(f"✅ {piece.get_symbol()} {from_str} → {to_str}" + (f" captures {captured.get_symbol()}" if captured else ""))
        
        self.switch_turn()
        return True
    
    def _parse_position(self, pos_str: str) -> Position:
        """Convert 'e2' to Position(6, 4)."""
        col = ord(pos_str[0].lower()) - ord('a')
        row = 8 - int(pos_str[1])
        return Position(row, col)
    
    def is_over(self) -> bool:
        return self.status != GameStatus.ACTIVE
    
    def get_result(self) -> str:
        if self.status == GameStatus.WHITE_WINS:
            return "White wins!"
        elif self.status == GameStatus.BLACK_WINS:
            return "Black wins!"
        elif self.status == GameStatus.STALEMATE:
            return "Stalemate - Draw!"
        return "Game in progress..."


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("CHESS - DEMO")
    print("=" * 60)
    
    game = ChessGame()
    game.board.display()
    
    # Demo moves (simple opening)
    moves = [
        ("e2", "e4"),   # White pawn
        ("e7", "e5"),   # Black pawn
        ("g1", "f3"),   # White knight
        ("b8", "c6"),   # Black knight
        ("f1", "c4"),   # White bishop
        ("g8", "f6"),   # Black knight
        ("d2", "d3"),   # White pawn
        ("f8", "e7"),   # Black bishop
    ]
    
    for from_pos, to_pos in moves:
        print(f"\n--- {game.current_turn.value}'s turn ---")
        game.make_move(from_pos, to_pos)
        game.board.display()
    
    print("\n" + "=" * 60)
    print("Move History:", " ".join(game.move_history))
    print("=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)
