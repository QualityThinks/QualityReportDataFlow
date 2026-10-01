import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from EnvManager import EnvManager
from DatabaseConnection import DatabaseConnection
from EncryptionManager import EncryptionManagerFactory

def load_environment()->EnvManager:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))
    return EnvManager(project_root / ".env")

def connect_to_mysql_database(env:EnvManager) ->DatabaseConnection:
    # MYSQL_PASSWORD is stored encrypted; decrypt it before use.
    encryption = EncryptionManagerFactory.from_env(env)
    host_address = env.require("MYSQL_HOST")
    port_address = env.require("MYSQL_PORT")
    database = env.require("MYSQL_DATABASE")
    user = env.require("MYSQL_USER")
    password = encryption.decrypt_text(env.require("MYSQL_PASSWORD"))
    return DatabaseConnection(host_address,port_address,database,user,password)

def main():
    env = load_environment()
    dbconn = connect_to_mysql_database(env)
    print("TEST DB CONNECTION")
    result = dbconn.query("SELECT * FROM users")
    print(json.dumps(result, indent=4,default=str))

if __name__ == "__main__":
    main()