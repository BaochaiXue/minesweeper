import sys
import random

from PyQt6 import QtCore, QtGui, QtWidgets


class StartWindow(QtWidgets.QWidget):
    """
    A small window where the user can input N (grid size) and M (number of mines).
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Minesweeper Settings")

        # Main layout
        layout = QtWidgets.QVBoxLayout()

        # Grid for labels/lineedits
        form_layout = QtWidgets.QGridLayout()
        layout.addLayout(form_layout)

        # N label and lineedit
        label_n = QtWidgets.QLabel("Grid Size N:")
        self.lineedit_n = QtWidgets.QLineEdit("10")
        form_layout.addWidget(label_n, 0, 0)
        form_layout.addWidget(self.lineedit_n, 0, 1)

        # M label and lineedit
        label_m = QtWidgets.QLabel("Number of Mines M:")
        self.lineedit_m = QtWidgets.QLineEdit("15")
        form_layout.addWidget(label_m, 1, 0)
        form_layout.addWidget(self.lineedit_m, 1, 1)

        # Error label
        self.error_label = QtWidgets.QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        # Start button
        start_button = QtWidgets.QPushButton("Start Game")
        start_button.clicked.connect(self.on_start_game)
        layout.addWidget(start_button)

        self.setLayout(layout)

    def on_start_game(self) -> None:
        """
        Reads N and M, does validation, and if valid, launches MinesweeperWindow.
        """
        try:
            N = int(self.lineedit_n.text())
            M = int(self.lineedit_m.text())
        except ValueError:
            self.error_label.setText("Please enter valid integers!")
            return

        if N <= 0:
            self.error_label.setText("N must be > 0!")
            return
        if M < 0 or M >= N * N:
            self.error_label.setText("Invalid range for M! (0 <= M < N*N)")
            return

        # If valid, open the game window and close the start window
        self.minesweeper_window = MinesweeperWindow(N, M)
        self.minesweeper_window.show()
        self.close()


class CellButton(QtWidgets.QPushButton):
    """
    Custom button that emits leftClicked and rightClicked signals.
    We store row, col to identify the position in the grid.
    """

    leftClicked = QtCore.pyqtSignal(int, int)
    rightClicked = QtCore.pyqtSignal(int, int)

    def __init__(self, row: int, col: int, parent=None) -> None:
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setFixedSize(40, 40)  # Adjust as needed

    def mousePressEvent(self, event: "QtGui.QMouseEvent") -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.leftClicked.emit(self.row, self.col)
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            self.rightClicked.emit(self.row, self.col)
        super().mousePressEvent(event)


class MinesweeperWindow(QtWidgets.QWidget):
    """
    The main Minesweeper game window, containing an N x N grid of CellButtons
    and the logic for placing mines, revealing cells, and checking win/lose.
    """

    def __init__(self, N: int, M: int) -> None:
        super().__init__()
        self.N = N
        self.M = M
        self.game_over = False

        # Board data
        self.board = [
            [
                {
                    "is_mine": False,
                    "adjacent_mines": 0,
                    "is_revealed": False,
                    "is_flagged": False,
                }
                for _ in range(N)
            ]
            for _ in range(N)
        ]

        # Place mines
        self._place_mines()
        # Calculate adjacency
        self._calculate_adjacency()

        # We will store references to CellButton objects
        self.buttons = [[None for _ in range(N)] for _ in range(N)]

        self.init_ui()

    def init_ui(self) -> None:
        """
        Creates the grid of buttons and info label.
        """
        self.setWindowTitle(f"Minesweeper - {self.N} x {self.N}, Mines: {self.M}")

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        # Grid layout for N x N buttons
        grid_layout = QtWidgets.QGridLayout()

        for r in range(self.N):
            for c in range(self.N):
                btn = CellButton(r, c)
                btn.setText("")  # Initially blank
                btn.leftClicked.connect(self.left_click)
                btn.rightClicked.connect(self.right_click)

                grid_layout.addWidget(btn, r, c)
                self.buttons[r][c] = btn

        main_layout.addLayout(grid_layout)

        # Info label at the bottom
        self.info_label = QtWidgets.QLabel("Be careful!")
        main_layout.addWidget(self.info_label)

    def _place_mines(self) -> None:
        """
        Randomly place M mines in the board.
        """
        all_positions = [(r, c) for r in range(self.N) for c in range(self.N)]
        mine_positions = random.sample(all_positions, self.M)
        for r, c in mine_positions:
            self.board[r][c]["is_mine"] = True

    def _calculate_adjacency(self) -> None:
        """
        For each non-mine cell, calculate the number of adjacent mines.
        """
        for r in range(self.N):
            for c in range(self.N):
                if self.board[r][c]["is_mine"]:
                    self.board[r][c]["adjacent_mines"] = -1
                else:
                    count = 0
                    for nr in range(max(0, r - 1), min(self.N, r + 2)):
                        for nc in range(max(0, c - 1), min(self.N, c + 2)):
                            if self.board[nr][nc]["is_mine"]:
                                count += 1
                    self.board[r][c]["adjacent_mines"] = count

    def left_click(self, row: int, col: int) -> None:
        """
        Handles left-click on a cell.
        """
        if self.game_over:
            return

        cell = self.board[row][col]

        # Do nothing if flagged or already revealed
        if cell["is_flagged"] or cell["is_revealed"]:
            return

        cell["is_revealed"] = True
        self._update_button(row, col)

        # If it's a mine, game over
        if cell["is_mine"]:
            self.info_label.setText("You hit a mine! Game Over!")
            self.game_over = True
            self._show_all_mines()
            self._show_endgame_dialog("You hit a mine! Game Over!")
            return

        # Flood-fill if 0 adjacent mines
        if cell["adjacent_mines"] == 0:
            self._flood_fill(row, col)

        # Check win
        if self._check_win():
            self.info_label.setText("Congratulations, you won!")
            self.game_over = True
            self._show_endgame_dialog("Congratulations, you won!")

    def right_click(self, row: int, col: int) -> None:
        """
        Handles right-click on a cell (flag/unflag).
        """
        if self.game_over:
            return

        cell = self.board[row][col]

        # Cannot flag an already revealed cell
        if cell["is_revealed"]:
            return

        cell["is_flagged"] = not cell["is_flagged"]
        self._update_button(row, col)

    def _update_button(self, row: int, col: int) -> None:
        """
        Update the appearance of a button based on the cell state.
        """
        cell = self.board[row][col]
        btn = self.buttons[row][col]

        if cell["is_flagged"]:
            btn.setText("⚑")
            btn.setStyleSheet("color: red; background-color: white;")
        elif cell["is_revealed"]:
            if cell["is_mine"]:
                btn.setText("*")
                btn.setStyleSheet("color: white; background-color: red;")
            else:
                adjacent = cell["adjacent_mines"]
                text = str(adjacent) if adjacent > 0 else ""
                btn.setText(text)
                color = self._get_color(adjacent)
                btn.setStyleSheet(f"color: {color}; background-color: lightgray;")
        else:
            # Not revealed, not flagged
            btn.setText("")
            btn.setStyleSheet("")

    def _get_color(self, adjacent: int) -> str:
        """
        Return a color string based on the number of adjacent mines.
        """
        colors = {
            1: "blue",
            2: "green",
            3: "red",
            4: "purple",
            5: "maroon",
            6: "turquoise",
            7: "black",
            8: "gray",
        }
        return colors.get(adjacent, "black")

    def _flood_fill(self, row: int, col: int) -> None:
        """
        Reveal all neighbors of a cell with 0 adjacent mines (recursive flood fill).
        """
        stack = [(row, col)]
        while stack:
            r, c = stack.pop()
            for nr in range(max(0, r - 1), min(self.N, r + 2)):
                for nc in range(max(0, c - 1), min(self.N, c + 2)):
                    neighbor = self.board[nr][nc]
                    if (
                        (not neighbor["is_revealed"])
                        and (not neighbor["is_flagged"])
                        and (not neighbor["is_mine"])
                    ):
                        neighbor["is_revealed"] = True
                        self._update_button(nr, nc)
                        if neighbor["adjacent_mines"] == 0:
                            stack.append((nr, nc))

    def _check_win(self) -> bool:
        """
        Checks if all non-mine cells are revealed -> win.
        """
        for r in range(self.N):
            for c in range(self.N):
                cell = self.board[r][c]
                if (not cell["is_mine"]) and (not cell["is_revealed"]):
                    return False
        return True

    def _show_all_mines(self) -> None:
        """
        Reveal all mines (called on game over).
        """
        for r in range(self.N):
            for c in range(self.N):
                cell = self.board[r][c]
                if cell["is_mine"]:
                    cell["is_revealed"] = True
                    self._update_button(r, c)

    def _show_endgame_dialog(self, msg: str) -> None:
        """
        After the game ends, show a dialog offering two options:
        1. Replay with the same N, M.
        2. Return to the start window to set new N, M.
        """
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Game Over")
        layout = QtWidgets.QVBoxLayout(dlg)

        label = QtWidgets.QLabel(f"{msg}\nWould you like to play again?")
        layout.addWidget(label)

        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)

        replay_btn = QtWidgets.QPushButton("Replay (Same N, M)")
        change_btn = QtWidgets.QPushButton("Return to Settings")
        btn_layout.addWidget(replay_btn)
        btn_layout.addWidget(change_btn)

        replay_btn.clicked.connect(lambda: self._replay_game(dlg))
        change_btn.clicked.connect(lambda: self._go_to_start_screen(dlg))

        dlg.exec()

    def _replay_game(self, popup: "QtWidgets.QDialog") -> None:
        """
        Create a new MinesweeperWindow with the same N, M.
        We hide/close the current window, but store a reference to the new window
        so it remains alive and doesn't trigger the application to exit.
        """
        popup.close()
        self.hide()  # or self.close() if you want to fully destroy the old window

        # Keep a reference so it's not garbage-collected.
        self._child_window = MinesweeperWindow(self.N, self.M)
        self._child_window.show()

    def _go_to_start_screen(self, popup: "QtWidgets.QDialog") -> None:
        """
        Close current window and show the StartWindow again.
        """
        popup.close()
        self.hide()  # or self.close()

        self._child_window = StartWindow()
        self._child_window.show()


def main() -> None:
    """
    Entry point: create QApplication and show the StartWindow.
    """
    app = QtWidgets.QApplication(sys.argv)
    window = StartWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
