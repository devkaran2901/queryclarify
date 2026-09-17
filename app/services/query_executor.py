import time
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List, Tuple
from sqlalchemy import text
from app.database.connection import SessionLocal

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
    Safely executes validated SELECT queries against PostgreSQL in a read-only transaction.
    """

    def execute(self, sql_query: str) -> Tuple[bool, List[str], List[Dict[str, Any]], float, str, str]:
        """
        Executes validated SQL and returns:
        (success: bool, columns: List[str], rows: List[Dict[str, Any]], duration_ms: float, summary: str, error: str)
        """
        db = SessionLocal()
        start_time = time.perf_counter()
        
        try:
            # Set read-only transaction mode for added safety
            db.execute(text("SET TRANSACTION READ ONLY"))
            
            result = db.execute(text(sql_query))
            columns = list(result.keys())
            
            raw_rows = result.fetchall()
            rows = []
            for row in raw_rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    row_dict[col] = serialize_cell(val)
                rows.append(row_dict)

            db.commit()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            summary = self._generate_summary(sql_query, len(rows), columns)
            logger.info(f"Query executed successfully in {duration_ms} ms. Returned {len(rows)} rows.")
            
            return True, columns, rows, duration_ms, summary, ""

        except Exception as e:
            db.rollback()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_msg = f"Database execution error: {str(e)}"
            logger.error(error_msg)
            return False, [], [], duration_ms, "", error_msg

        finally:
            db.close()

    def _generate_summary(self, sql: str, row_count: int, columns: List[str]) -> str:
        if row_count == 0:
            return "The query executed successfully but returned no matching records."
        if row_count == 1:
            return f"Query returned 1 result with fields: {', '.join(columns)}."
        return f"Query returned {row_count} matching rows across columns: {', '.join(columns)}."


query_executor = QueryExecutor()
