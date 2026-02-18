import numpy as np
import matplotlib.pyplot as plt
import random

# Represents a single square on the original 8x8 grid
class UnitSquare:
    def __init__(self, x, y):
        self.initial_coords = (x, y)
        # color can be 'B' (black), 'W' (white), or None (blank)
        # Triangles can be represented as ('B', 'W') etc.
        self.color = None

# Represents the piece of paper, folded or unfolded
class Paper:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        # grid contains stacks of UnitSquares
        self.grid = [[[] for _ in range(height)] for _ in range(width)]

    def place_square(self, square, x, y):
        self.grid[x][y].append(square)

    def get_stack(self, x, y):
        return self.grid[x][y]

def generate_fold_sequence(num_folds):
    """Generates a random sequence of fold operations."""
    # To get to 4x4 from 8x8 requires 2 vertical and 2 horizontal folds
    # on the midlines. More complex folds can be added later.
    # For now, we will use a fixed sequence that produces a 4x4 grid.
    return ['V', 'H'] # V: fold right over left, H: fold top over bottom

def fold_paper(initial_paper, fold_sequence):
    """
    Folds the paper according to the sequence of operations.
    For now, this is a specific implementation for 8x8 -> 4x4.
    """
    folded_paper = Paper(4, 4)
    # This mapping is derived from a V fold then an H fold
    for r_final in range(4):
        for c_final in range(4):
            # These are the 4 source squares in the 8x8 grid that
            # land on the same spot in the 4x4 grid.
            sources = [
                (c_final, r_final),             # from Q00 (top-left)
                (c_final, 7 - r_final),         # from Q01 (bottom-left)
                (7 - c_final, r_final),         # from Q10 (top-right)
                (7 - c_final, 7 - r_final),     # from Q11 (bottom-right)
            ]
            
            # Layering and orientation (z=1 front, z=-1 back)
            # (initial_coords, z_orientation)
            # from bottom (layer 0) to top (layer 3)
            stack_info = [
                ((c_final, r_final), 1),             # Q00
                ((7 - c_final, r_final), -1),        # Q10
                ((7 - c_final, 7 - r_final), 1),     # Q11
                ((c_final, 7 - r_final), -1),        # Q01
            ]
            
            for (c_orig, r_orig), z in stack_info:
                square = initial_paper.get_stack(c_orig, r_orig)[0]
                square.z_orientation = z # Store orientation for painting
                folded_paper.place_square(square, c_final, r_final)

    return folded_paper

def paint_and_unfold(folded_paper):
    """
    Paints the top and bottom of the folded paper and transfers the
    colors back to the original squares.
    """
    for r in range(4):
        for c in range(4):
            stack = folded_paper.get_stack(c, r)
            
            # Top of the stack is black
            top_square = stack[-1]
            if top_square.z_orientation == 1:
                top_square.color = 'B'
            else: # Back side is showing
                # This would mean painting the back. For now, let's assume
                # the game paints the face that is up.
                top_square.color = 'B'

            # Bottom of the stack is white
            bottom_square = stack[0]
            if bottom_square.z_orientation == 1:
                # The front of the bottom square faces down.
                # So we are painting its back. Let's handle this later.
                # For now, let's just color the square object.
                bottom_square.color = 'W'
            else:
                bottom_square.color = 'W'
    
    # The colors are now set on the UnitSquare objects, which are shared
    # with the original unfolded_paper. So, no explicit unfolding needed.

def draw_puzzle(paper):
    """Draws the 8x8 puzzle grid."""
    grid = np.zeros((8, 8, 3)) # RGB grid
    
    color_map = {
        'B': [0, 0, 0],       # Black
        'W': [1, 1, 1],       # White
        None: [0.8, 0.8, 0.8] # Grey for blank
    }
    
    for r in range(8):
        for c in range(8):
            square = paper.get_stack(c, r)[0]
            grid[r, c] = color_map.get(square.color, [0.8, 0.8, 0.8])
            
    plt.imshow(grid, interpolation='nearest')
    ax = plt.gca()
    ax.set_xticks(np.arange(-.5, 8, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 8, 1), minor=True)
    ax.grid(which='minor', color='black', linestyle='-', linewidth=1)
    ax.tick_params(which='minor', size=0)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.show()

def main():
    # 1. Start with an unfolded 8x8 paper
    unfolded_paper = Paper(8, 8)
    for r in range(8):
        for c in range(8):
            unfolded_paper.place_square(UnitSquare(c, r), c, r)

    # 2. Generate a fold sequence (currently fixed)
    fold_sequence = generate_fold_sequence(random.randint(2, 8))

    # 3. Fold the paper
    folded_4x4 = fold_paper(unfolded_paper, fold_sequence)
    
    # 4. Paint the folded paper (which updates the squares)
    paint_and_unfold(folded_4x4)
    
    print("Puzzle generated. Displaying grid:")
    # 5. Display the unfolded puzzle
    draw_puzzle(unfolded_paper)


if __name__ == "__main__":
    main()
