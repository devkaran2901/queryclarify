import logging
import sqlglot
from sqlglot import exp
from typing import Tuple, List, Set, Optional

logger = logging.getLogger("sql_validator")

DEFAULT_ALLOWED_TABLES = {"customers", "products", "orders", "order_items"}
MAX_LIMIT = 100


class SQLValidator:
    """
    AST Safety Guardrail enforcing read-only operations, table verification,
    multi-statement protection, and automatic row limit enforcement using SQLGlot.
    """

    def __init__(self, allowed_tables: Optional[Set[str]] = None, max_limit: int = MAX_LIMIT):
        self.allowed_tables = allowed_tables
        self.max_limit = max_limit

    def validate_and_sanitize(
        self,
        sql_query: str,
        dynamic_allowed_tables: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str, List[str]]:
        """
        Parses and checks SQL for syntax and safety rules against dynamic or default allowed tables.
        Returns:
            (is_valid: bool, sanitized_sql: str, message: str, tables_used: List[str])
        """
        if not sql_query or not sql_query.strip():
            return False, "", "Empty SQL query provided", []

        clean_sql = sql_query.strip().rstrip(";")

        # Disallow multi-statement query injection
        if ";" in clean_sql:
            return False, clean_sql, "Multi-statement execution is strictly forbidden.", []

        # Parse AST using SQLGlot for PostgreSQL dialect
        try:
            parsed_expressions = sqlglot.parse(clean_sql, read="postgres")
            if not parsed_expressions or len(parsed_expressions) != 1:
                return False, clean_sql, "SQL query contains invalid or multiple statements.", []
            
            expression = parsed_expressions[0]
            if expression is None:
                return False, clean_sql, "Failed to parse SQL AST.", []

        except Exception as e:
            logger.warning(f"SQLGlot parse error: {e}")
            return False, clean_sql, f"SQL syntax error: {str(e)}", []

        # Enforce statement type (MUST be SELECT or CTE WITH ... SELECT)
        if not isinstance(expression, (exp.Select, exp.Union)):
            return False, clean_sql, f"Statement type '{type(expression).__name__}' is not permitted. Only SELECT queries are allowed.", []

        # Scan AST for forbidden operations (Insert, Delete, Drop, Update, Alter, Command, Create, etc.)
        forbidden_types = (
            exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Command,
            exp.Create
        )
        for node in expression.find_all(*forbidden_types):
            return False, clean_sql, f"Forbidden statement operation detected: {type(node).__name__}", []

        # Extract referenced tables
        tables_used = set()
        for table_node in expression.find_all(exp.Table):
            t_name = table_node.name.lower()
            if t_name:
                tables_used.add(t_name)

        # Validate referenced tables exist in connected schema
        target_allowed_tables = dynamic_allowed_tables if dynamic_allowed_tables is not None else (self.allowed_tables or DEFAULT_ALLOWED_TABLES)
        
        # Convert all allowed table names to lowercase for case-insensitive matching
        allowed_set_lower = {t.lower() for t in target_allowed_tables}
        invalid_tables = tables_used - allowed_set_lower

        if invalid_tables:
            return False, clean_sql, f"Referenced tables {invalid_tables} do not exist in the connected database schema.", []

        # Limit enforcement: ensure LIMIT clause exists and is capped at MAX_LIMIT
        limit_node = expression.args.get("limit")
        if limit_node is None:
            # Append LIMIT MAX_LIMIT to AST
            expression = expression.limit(self.max_limit)
        else:
            try:
                curr_limit = int(limit_node.expression.this)
                if curr_limit > self.max_limit:
                    expression.args["limit"].expression.this = str(self.max_limit)
            except (ValueError, AttributeError):
                expression = expression.limit(self.max_limit)

        final_sql = expression.sql(dialect="postgres")
        return True, final_sql, "SQL query is valid and read-only.", sorted(list(tables_used))


sql_validator = SQLValidator()
