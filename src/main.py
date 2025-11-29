import os
import logging
import sys
from dotenv import load_dotenv

# Ensure src is in path if running from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
load_dotenv()

# Setup Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename='logs/gastos_app_v2.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)

from src.ui.gui import create_main_window

def main():
    root = create_main_window()
    root.mainloop()

if __name__ == "__main__":
    main()
