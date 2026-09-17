import time
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.database.connection import engine as default_engine

logger = logging.getLogger("query_executor")


def serialize_cell(val: Any) -> Any:
    """Converts non-JSON serializable database types (Decimal, datetime, etc.) to strings/floats."""
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


class QueryExecutor:
    """
    Safely executes validated SELECT queries against any target PostgreSQL Engine in a read-only transaction.
    """

    def execute(
        self,
        sql_query: str,
        engine: Optional[Engine] = None
    ) -> Tuple[bool, List[str], List[Dict[str, Any]], float, str, str]:
        """
        Executes validated SQL and returns:
        (success: bool, columns: List[str], rows: List[Dict[str, Any]], duration_ms: float, summary: str, error: str)
        """
        target_engine = engine or default_engine
        start_time = time.perf_counter()
        
        try:
            with target_engine.connect() as conn:
                # Set read-only transaction mode for safety
                try:
                    conn.execute(text("SET TRANSACTION READ ONLY"))
                except Exception:
                    pass

                result = conn.execute(text(sql_query))
                columns = list(result.keys())
                
                raw_rows = result.fetchall()
                rows = []
                for row in raw_rows:
                    row_dict = {}
                    for col, val in zip(columns, row):
                        row_dict[col] = serialize_cell(val)
                    rows.append(row_dict)

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            summary = self._generate_summary(sql_query, len(rows), columns)
            logger.info(f"Query executed successfully in {duration_ms} ms. Returned {len(rows)} rows.")
            
            return True, columns, rows, duration_ms, summary, ""

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            err_str = str(e)
            
            # Formulate clear user-facing error message
            if "relation" in err_str and "does not exist" in err_str:
                error_msg = "The requested table or view does not exist in the connected database."
            elif "column" in err_str and "does not exist" in err_str:
                error_msg = "The generated SQL referenced a column that does not exist in the database."
            elif "permission denied" in err_str.lower():
                error_msg = "Permission denied. The database user does not have SELECT permissions on the requested table."
            else:
                error_msg = f"Database execution error: {err_str}"

            logger.error(f"Query execution error: {err_str}")
            return False, [], [], duration_ms, "", error_msg

    def _generate_summary(self, sql: str, row_count: int, columns: List[str]) -> str:
        if row_count == 0:
            return "The query executed successfully but returned 0 records."
        if row_count == 1:
            return f"Query returned 1 matching row across columns: {', '.join(columns)}."
        return f"Query returned {row_count} rows across columns: {', '.join(columns)}."


query_executor = QueryExecutor()
