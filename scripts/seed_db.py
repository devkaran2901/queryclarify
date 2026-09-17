import sys
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.connection import SessionLocal
from app.database.models import Customer, Product, Order, OrderItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")


def seed_database():
    random.seed(42)
    db = SessionLocal()

    try:
        logger.info("Clearing existing data...")
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(Product).delete()
        db.query(Customer).delete()
        db.commit()

        logger.info("Seeding customers...")
        countries = [
            "India", "USA", "UK", "Germany", "Japan",
            "Canada", "Australia", "France", "Brazil", "Singapore"
        ]
        
        first_names = [
            "Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Isha", "Aditya", "Neha", "Rahul", "Kavya",
            "John", "Emily", "Michael", "Sarah", "David", "Jessica", "James", "Emma", "Robert", "Olivia",
            "Hans", "Freja", "Kenji", "Yuki", "Lucas", "Sophie", "Liam", "Chloe", "Mateo", "Camila",
            "Chen", "Mei", "Raj", "Siddharth", "Tanvi", "Sanya", "Arjun", "Deepak", "Pooja", "Amit",
            "Daniel", "Laura", "Alex", "Elena", "Carlos", "Isabella", "Gabriel", "Mia", "Noah", "Ava"
        ]
        
        last_names = [
            "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Joshi", "Nair", "Reddy", "Rao",
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Müller", "Weber", "Tanaka", "Sato", "Silva", "Santos", "Dupont", "Martin", "Wong", "Lee"
        ]

        customers = []
        base_date = datetime(2024, 1, 1)
        for i in range(1, 51):
            fn = first_names[i - 1]
            ln = random.choice(last_names)
            name = f"{fn} {ln}"
            email = f"{fn.lower()}.{ln.lower()}{i}@example.com".replace(" ", "")
            country = countries[(i - 1) % len(countries)]
            created_at = base_date + timedelta(days=random.randint(0, 180))
            
            customer = Customer(
                id=i,
                name=name,
                email=email,
                country=country,
                created_at=created_at
            )
            customers.append(customer)

        db.add_all(customers)
        db.commit()
        logger.info(f"Seeded {len(customers)} customers.")

        logger.info("Seeding products...")
        product_catalog = [
            ("Wireless Noise-Canceling Headphones", "Electronics", 199.99),
            ("Smartphone Pro 15", "Electronics", 999.00),
            ("4K Ultra HD Smart TV 55-inch", "Electronics", 499.50),
            ("Mechanical Gaming Keyboard", "Electronics", 89.99),
            ("Ergonomic Wireless Mouse", "Electronics", 45.00),
            ("Bluetooth Portable Speaker", "Electronics", 59.99),
            ("USB-C Multi-Port Hub", "Electronics", 29.99),
            ("Smart Watch Series X", "Electronics", 249.99),

            ("Organic Cotton T-Shirt", "Apparel", 24.99),
            ("Slim Fit Denim Jeans", "Apparel", 59.99),
            ("Waterproof Winter Jacket", "Apparel", 129.99),
            ("Running Sneakers Pro", "Apparel", 89.99),
            ("Classic Leather Belt", "Apparel", 34.50),
            ("Wool Blend Sweater", "Apparel", 69.99),

            ("Stainless Steel Cookware Set", "Home & Kitchen", 149.99),
            ("Automatic Espresso Coffee Machine", "Home & Kitchen", 299.99),
            ("Robot Vacuum Cleaner", "Home & Kitchen", 220.00),
            ("Air Fryer Max 5L", "Home & Kitchen", 99.99),
            ("Blender SmoothMaster 1000W", "Home & Kitchen", 79.99),
            ("Memory Foam Queen Pillow", "Home & Kitchen", 39.99),

            ("Designing Data-Intensive Applications", "Books", 44.99),
            ("Python Crash Course 3rd Ed", "Books", 35.00),
            ("Clean Code by Robert Martin", "Books", 42.50),
            ("System Design Interview Guide", "Books", 39.99),
            ("The Pragmatic Programmer", "Books", 49.99),

            ("Yoga Mat Non-Slip 6mm", "Sports", 29.99),
            ("Adjustable Dumbbell Set 24kg", "Sports", 199.99),
            ("Insulated Stainless Water Bottle 1L", "Sports", 22.50),
            ("Mountain Bike Helmet Pro", "Sports", 64.99),
            ("Resistance Bands Fitness Set", "Sports", 19.99)
        ]

        products = []
        for i, (p_name, category, price) in enumerate(product_catalog, start=1):
            product = Product(
                id=i,
                name=p_name,
                category=category,
                price=Decimal(str(price))
            )
            products.append(product)

        db.add_all(products)
        db.commit()
        logger.info(f"Seeded {len(products)} products.")

        logger.info("Seeding orders and order items...")
        statuses = ["completed"] * 80 + ["pending"] * 10 + ["cancelled"] * 10
        
        orders = []
        all_order_items = []
        order_item_id_counter = 1

        order_start_date = datetime(2025, 1, 1)
        order_end_date = datetime(2026, 3, 15)
        date_range_days = (order_end_date - order_start_date).days

        for order_id in range(1, 301):
            customer = random.choice(customers)
            # Ensure order_date is after customer creation date
            order_date = max(
                customer.created_at + timedelta(days=1),
                order_start_date + timedelta(days=random.randint(0, date_range_days))
            )
            status = random.choice(statuses)

            # Choose 1 to 5 items for this order
            num_items = random.randint(1, 5)
            selected_products = random.sample(products, num_items)

            total_amount = Decimal("0.00")
            order_items_for_order = []

            for prod in selected_products:
                qty = random.randint(1, 4)
                unit_price = prod.price
                line_total = Decimal(qty) * unit_price
                total_amount += line_total

                item = OrderItem(
                    id=order_item_id_counter,
                    order_id=order_id,
                    product_id=prod.id,
                    quantity=qty,
                    unit_price=unit_price
                )
                order_item_id_counter += 1
                order_items_for_order.append(item)

            order = Order(
                id=order_id,
                customer_id=customer.id,
                order_date=order_date,
                status=status,
                total_amount=total_amount
            )
            orders.append(order)
            all_order_items.extend(order_items_for_order)

        db.add_all(orders)
        db.commit()
        db.add_all(all_order_items)
        db.commit()

        logger.info(f"Seeded {len(orders)} orders with {len(all_order_items)} order items.")
        logger.info("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
