from sqlalchemy import inspect
from sqlalchemy.orm import Session
from app.database.connection import engine, SessionLocal
from app.database.models import Customer, Product, Order, OrderItem


class SchemaInspector:
    """
    Introspects the PostgreSQL database to construct a compact,
    LLM-friendly context representation of tables, columns, constraints,
    relationships, and categorical value hints.
    """

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def get_schema_summary(self) -> str:
        """
        Generates a concise text representation of the database schema
        suitable for system prompts in Text-to-SQL and Ambiguity Detection.
        """
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        schema_lines = []
        schema_lines.append("DATABASE SCHEMA:")
        schema_lines.append("================")

        for table_name in sorted(tables):
            schema_lines.append(f"\nTABLE {table_name}")
            
            # Columns
            columns = inspector.get_columns(table_name)
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", []))
            
            # Foreign keys
            fk_constraints = inspector.get_foreign_keys(table_name)
            fk_map = {}
            for fk in fk_constraints:
                for constrained_col, referred_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                    fk_map[constrained_col] = f"{fk['referred_table']}.{referred_col}"

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

        # Add domain value hints
        hints = self.get_domain_value_hints()
        if hints:
            schema_lines.append("\nDOMAIN VALUE HINTS:")
            schema_lines.append("===================")
            for hint_key, values in hints.items():
                schema_lines.append(f"- {hint_key}: {', '.join(map(str, values))}")

        return "\n".join(schema_lines)

    def get_domain_value_hints(self) -> dict:
        """
        Retrieves distinct categorical sample values for columns to help the LLM
        generate accurate WHERE clauses (e.g. valid order statuses or product categories).
        """
        db: Session = SessionLocal()
        try:
            countries = [c[0] for c in db.query(Customer.country).distinct().limit(10).all() if c[0]]
            categories = [c[0] for c in db.query(Product.category).distinct().limit(10).all() if c[0]]
            statuses = [s[0] for s in db.query(Order.status).distinct().all() if s[0]]

            return {
                "customers.country sample values": countries,
                "products.category sample values": categories,
                "orders.status valid values": statuses
            }
        except Exception:
            return {}
        finally:
            db.close()


schema_inspector = SchemaInspector()
