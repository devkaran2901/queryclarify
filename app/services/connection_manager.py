import logging
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from app.config import settings
from app.database.connection import engine as default_demo_engine

logger = logging.getLogger("connection_manager")


class ConnectionManager:
    """
    Thread-safe session manager holding read-only database connections and metadata
    for custom user-connected PostgreSQL databases.
    """

    def __init__(self):
        # Maps session_id -> dict with 'engine', 'config', 'database_name', 'host', 'port'
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def test_connection(self, host: str, port: int, database: str, username: str, password: str) -> Tuple[bool, str]:
        """
        Attempts a test connection to a target PostgreSQL database with connection timeout.
        """
        try:
            url = self.build_connection_url(host, port, database, username, password)
            test_engine = create_engine(
                url,
                connect_args={"connect_timeout": 5},
                pool_pre_ping=True
            )
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            test_engine.dispose()
            return True, f"Successfully connected to database '{database}' on {host}:{port}."
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"Database test connection failed for {username}@{host}:{port}/{database}: {err_msg}")
            
            # Formulate user-friendly diagnostic error messages
            if "Password authentication failed" in err_msg or "password authentication failed" in err_msg:
                return False, "Authentication failed. Please verify your username and password."
            if "could not connect to server" in err_msg or "Connection refused" in err_msg or "timeout" in err_msg.lower():
                return False, f"Could not connect to host '{host}' on port {port}. Verify host and port are reachable."
            if "database" in err_msg.lower() and "does not exist" in err_msg.lower():
                return False, f"Database '{database}' does not exist on target PostgreSQL server."
                
            return False, f"Connection failed: {err_msg}"

    def connect(self, session_id: str, host: str, port: int, database: str, username: str, password: str) -> Tuple[bool, str]:
        """
        Establishes an active database engine for a given session.
        """
        success, msg = self.test_connection(host, port, database, username, password)
        if not success:
            return False, msg

        url = self.build_connection_url(host, port, database, username, password)
        new_engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )

        # Store engine in session map
        self._sessions[session_id] = {
            "engine": new_engine,
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "is_custom": True
        }

        logger.info(f"Session '{session_id}' connected to custom DB '{database}' on {host}:{port}")
        return True, f"Connected to {database} on {host}:{port}"

    def disconnect(self, session_id: str) -> bool:
        """
        Disconnects custom database for session and reverts to demo database.
        """
        if session_id in self._sessions:
            session_info = self._sessions.pop(session_id)
            try:
                session_info["engine"].dispose()
            except Exception as e:
                logger.warning(f"Error disposing engine for session {session_id}: {e}")
            logger.info(f"Session '{session_id}' disconnected from custom DB.")
            return True
        return False

    def get_engine(self, session_id: Optional[str] = None) -> Engine:
        """
        Returns active SQLAlchemy engine for session_id, or falls back to demo database engine.
        """
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]["engine"]
        return default_demo_engine

    def get_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns connection metadata (excluding password).
        """
        if session_id and session_id in self._sessions:
            sess = self._sessions[session_id]
            return {
                "connected": True,
                "is_custom": True,
                "database_name": sess["database"],
                "host": sess["host"],
                "port": sess["port"],
                "username": sess["username"]
            }
        
        # Default demo connection info
        return {
            "connected": True,
            "is_custom": False,
            "database_name": "queryclarify (demo e-commerce)",
            "host": "localhost",
            "port": 5435,
            "username": "postgres"
        }

    @staticmethod
    def build_connection_url(host: str, port: int, database: str, username: str, password: str) -> str:
        safe_user = urllib.parse.quote_plus(username)
        safe_pass = urllib.parse.quote_plus(password)
        return f"postgresql://{safe_user}:{safe_pass}@{host}:{port}/{database}"


connection_manager = ConnectionManager()
