import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EnvManager import EnvManager

env = EnvManager(PROJECT_ROOT / ".env")

print(env.env_file_path)
print(env.variable_names)
