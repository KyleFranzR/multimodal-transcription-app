import sys
from pathlib import Path

# Ensure project root is in Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from caecus.gui.app import CaecusApp


def main():
    print("Starting Caecus application...")
    app = CaecusApp()
    app.mainloop()


if __name__ == "__main__":
    main()