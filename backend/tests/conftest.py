import sys
from pathlib import Path

# Add project root (D:\Resume_project) to python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
