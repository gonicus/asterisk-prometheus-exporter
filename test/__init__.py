import sys
from pathlib import Path
import logging

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))

# Prevent unit tests from generating expected error output in the console
logging.basicConfig()
logging.getLogger().disabled = True
