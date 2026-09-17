import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from app.database.connection import engine as default_engine

logger = logging.getLogger("schema_inspector")


class SchemaInspector:
    """
    Introspects any connected PostgreSQL database to construct a compact,
    LLM-friendly context representation of schemas, tables, columns, constraints,
    relationships, and categorical value hints.
    """

    def __init__(self, db_engine: Optional[Engine] = None):
        self.default_engine = db_engine or default_engine

    def get_schema_summary(self, engine: Optional[Engine] = None) -> str:
        """
        Generates a concise text representation of the target database schema
        suitable for system prompts in Text-to-SQL and Ambiguity Detection.
        """
        target_engine = engine or self.default_engine
        
        try:
            inspector = inspect(target_engine)
            tables = inspector.get_table_names()
        except Exception as e:
            logger.error(f"Failed to inspect database schema: {e}")
            return f"Error retrieving schema: {str(e)}"

        schema_lines = []
        schema_lines.append("DATABASE SCHEMA:")
        schema_lines.append("================")

        for table_name in sorted(tables):
            schema_lines.append(f"\nTABLE {table_name}")
            
            try:
                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                pk_cols = set(pk_constraint.get("constrained_columns", []))
                
                fk_constraints = inspector.get_foreign_keys(table_name)
                fk_map = {}
                for fk in fk_constraints:
                    for constrained_col, referred_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                        fk_map[constrained_col] = f"{fk.get('referred_table')}.{referred_col}"

                for col in columns:
                    col_name = col["name"]
                    col_type = str(col["type"])
                    col_desc = f"- {col_name} {col_type}"
                    
                    flags = []
                    if col_name in pk_cols:
                        flags.append("PRIMARY KEY")
                    if col_name in fk_map:
                        flags.append(f"FOREIGN KEY -> {fk_map[col_name]}")
                    
                    if flags:
                        col_desc += f" ({', '.join(flags)})"
                    
                    schema_lines.append(col_desc)
            except Exception as e:
                logger.warning(f"Error inspecting table {table_name}: {e}")
                schema_lines.append(f"- (Table details unavailable: {e})")

        # Add domain value hints dynamically
        hints = self.get_domain_value_hints(target_engine, tables)
        if hints:
            schema_lines.append("\nDOMAIN VALUE HINTS:")
            schema_lines.append("===================")
            for hint_key, values in hints.items():
                schema_lines.append(f"- {hint_key}: {', '.join(map(str, values))}")

        return "\n".join(schema_lines)

    def get_tables(self, engine: Optional[Engine] = None) -> List[str]:
        """Returns sorted list of table names in target database."""
        target_engine = engine or self.default_engine
        try:
            inspector = inspect(target_engine)
            return sorted(inspector.get_table_names())
        except Exception:
            return []

    def get_domain_value_hints(self, engine: Engine, tables: List[str]) -> Dict[str, List[Any]]:
        """
        Dynamically inspects sample values for varchar/categorical columns (e.g. status, category, country, role).
        """
        hints = {}
        inspector = inspect(engine)

        for table in tables:
            try:
                columns = inspector.get_columns(table)
                for col in columns:
                    col_name = col["name"].lower()
                    col_type = str(col["type"]).lower()

                    # Look for likely categorical string columns
                    if any(kw in col_name for kw in ["status", "category", "type", "country", "role", "state", "genre"]) and ("char" in col_type or "text" in col_type):
                        query_str = f"SELECT DISTINCT \"{col['name']}\" FROM \"{table}\" WHERE \"{col['name']}\" IS NOT NULL LIMIT 10"
                        with engine.connect() as conn:
                            res = conn.execute(text(query_str)).fetchall()
                            values = [r[0] for r in res if r[0] is not None]
                            if values:
                                hints[f"{table}.{col['name']} sample values"] = values
            except Exception as e:
                logger.debug(f"Skipping value hints for table {table}: {e}")

        return hints


schema_inspector = SchemaInspector()
