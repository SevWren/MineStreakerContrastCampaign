"""
_calc_board_height.py — called by launch.bat to calculate board height from image.
Usage: python _calc_board_height.py <image_path> <board_width>
Prints the board height as a single integer, or exits with code 1 on failure.
"""
import sys
import os

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
    image_path = sys.argv[1]
    board_w    = int(sys.argv[2])

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from board_sizing import derive_board_from_width
    result = derive_board_from_width(image_path, board_w)
    print(result["board_height"])

if __name__ == "__main__":
    main()
