import pytest
from sqlalchemy import inspect
from app.database.connection import SessionLocal, engine
from app.database.models import Customer, Product, Order, OrderItem


def test_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = {"customers", "products", "orders", "order_items"}
    for table in expected_tables:
        assert table in tables, f"Table {table} does not exist in database"


def test_customer_count():
    db = SessionLocal()
    try:
        count = db.query(Customer).count()
        assert count >= 50, f"Expected at least 50 customers, found {count}"
        
        # Verify country diversity
        countries = db.query(Customer.country).distinct().all()
        assert len(countries) >= 5, "Expected at least 5 distinct countries"
    finally:
        db.close()


def test_product_count():
    db = SessionLocal()
    try:
        count = db.query(Product).count()
        assert count >= 30, f"Expected at least 30 products, found {count}"

        # Verify category diversity
        categories = db.query(Product.category).distinct().all()
        assert len(categories) >= 4, "Expected at least 4 distinct product categories"
    finally:
        db.close()


def test_order_and_item_counts():
    db = SessionLocal()
    try:
        order_count = db.query(Order).count()
        assert order_count >= 300, f"Expected at least 300 orders, found {order_count}"

        item_count = db.query(OrderItem).count()
        assert item_count >= 700, f"Expected at least 700 order items, found {item_count}"
    finally:
        db.close()


def test_order_totals_integrity():
    db = SessionLocal()
    try:
        # Sample 20 random orders and verify total_amount matches line items sum
        orders = db.query(Order).limit(20).all()
        for order in orders:
            expected_total = sum(item.quantity * item.unit_price for item in order.items)
            assert abs(order.total_amount - expected_total) < 0.01, (
                f"Order {order.id} total mismatch: {order.total_amount} vs calculated {expected_total}"
            )
    finally:
        db.close()
