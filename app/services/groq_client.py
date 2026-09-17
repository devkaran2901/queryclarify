import json
import logging
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from groq import Groq
from app.config import settings

logger = logging.getLogger("groq_client")

T = TypeVar("T", bound=BaseModel)


class GroqClient:
    """
    Wrapper around Groq SDK with structured output parsing (Pydantic validation)
    and automatic fallback to deterministic mock response engine when Groq API key is missing
    or API calls fail.
    """

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.client: Optional[Groq] = None
        
        if self.api_key and self.api_key != "your_groq_api_key_here":
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info(f"Initialized Groq client with model: {self.model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}. Fallback engine will be used.")

    def is_available(self) -> bool:
        return self.client is not None

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T]
    ) -> T:
        """
        Executes a prompt against Groq LLM and parses response into Pydantic response_model.
        """
        if self.is_available():
            try:
                logger.info("Calling Groq API...")
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=1024
                )
                raw_json = response.choices[0].message.content
                parsed = json.loads(raw_json)
                return response_model.model_validate(parsed)
            except Exception as e:
                logger.error(f"Groq API error: {e}. Falling back to mock engine.")

        # Fallback implementation
        return self._mock_fallback(user_prompt, response_model)

    def _mock_fallback(self, user_prompt: str, response_model: Type[T]) -> T:
        """
        Deterministic mock engine fallback for offline testing or when API key is missing.
        Recognizes standard sample prompts for testing ambiguity and SQL generation.
        """
        prompt_lower = user_prompt.lower()
        model_name = response_model.__name__

        if model_name == "AmbiguityResponse":
            # Ambiguous queries
            if any(term in prompt_lower for term in ["best customer", "top customer", "valuable customer"]):
                return response_model.model_validate({
                    "ambiguous": True,
                    "ambiguity_type": "metric",
                    "reason": "The term 'best customer' is ambiguous because it can refer to revenue, order volume, or item quantities.",
                    "ambiguities": ["best customer"],
                    "clarification_question": "What metric should define the 'best customer'?",
                    "options": [
                        {
                            "id": "highest_revenue",
                            "label": "Highest Total Revenue",
                            "description": "Rank customers by total spending on completed orders."
                        },
                        {
                            "id": "most_orders",
                            "label": "Most Orders",
                            "description": "Rank customers by total number of completed orders."
                        },
                        {
                            "id": "highest_quantity",
                            "label": "Highest Quantity Purchased",
                            "description": "Rank customers by total number of item units bought."
                        }
                    ]
                })

            if any(term in prompt_lower for term in ["top product", "best product", "best selling"]):
                return response_model.model_validate({
                    "ambiguous": True,
                    "ambiguity_type": "ranking",
                    "reason": "The term 'top product' could mean highest sales revenue or highest units sold.",
                    "ambiguities": ["top product"],
                    "clarification_question": "How should we rank top products?",
                    "options": [
                        {
                            "id": "highest_revenue",
                            "label": "Highest Sales Revenue",
                            "description": "Rank products by total gross sales revenue."
                        },
                        {
                            "id": "units_sold",
                            "label": "Highest Quantity Sold",
                            "description": "Rank products by total number of units sold."
                        }
                    ]
                })

            if any(term in prompt_lower for term in ["recent sales", "recent orders", "latest sales"]):
                return response_model.model_validate({
                    "ambiguous": True,
                    "ambiguity_type": "time",
                    "reason": "'Recent' is relative and unspecified.",
                    "ambiguities": ["recent"],
                    "clarification_question": "What time period should be considered for 'recent'?",
                    "options": [
                        {
                            "id": "last_30_days",
                            "label": "Last 30 Days",
                            "description": "Orders placed within the last 30 days."
                        },
                        {
                            "id": "last_90_days",
                            "label": "Last 90 Days",
                            "description": "Orders placed within the last 90 days."
                        },
                        {
                            "id": "year_to_date",
                            "label": "Year to Date",
                            "description": "Orders placed since the start of the current year."
                        }
                    ]
                })

            # Clear queries
            return response_model.model_validate({
                "ambiguous": False,
                "ambiguity_type": None,
                "reason": "The user query provides explicit, unambiguous criteria.",
                "ambiguities": [],
                "clarification_question": None,
                "options": []
            })

        elif model_name == "SQLResponse":
            # Generate deterministic fallback SQL
            if "india" in prompt_lower:
                return response_model.model_validate({
                    "sql": "SELECT id, name, email, country, created_at FROM customers WHERE LOWER(country) = 'india' ORDER BY id ASC LIMIT 100",
                    "explanation": "Selects all customers located in India.",
                    "tables_used": ["customers"]
                })

            if "highest revenue" in prompt_lower or "best customer" in prompt_lower:
                return response_model.model_validate({
                    "sql": "SELECT c.id, c.name, c.email, c.country, SUM(o.total_amount) AS total_revenue FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.id, c.name, c.email, c.country ORDER BY total_revenue DESC LIMIT 1",
                    "explanation": "Calculates total revenue per customer for completed orders and returns the top customer.",
                    "tables_used": ["customers", "orders"]
                })

            if "most orders" in prompt_lower:
                return response_model.model_validate({
                    "sql": "SELECT c.id, c.name, c.email, COUNT(o.id) AS order_count FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'completed' GROUP BY c.id, c.name, c.email ORDER BY order_count DESC LIMIT 1",
                    "explanation": "Counts total completed orders per customer and returns the top customer.",
                    "tables_used": ["customers", "orders"]
                })

            if "highest sales revenue" in prompt_lower or "top product" in prompt_lower:
                return response_model.model_validate({
                    "sql": "SELECT p.id, p.name, p.category, SUM(oi.quantity * oi.unit_price) AS total_revenue FROM products p JOIN order_items oi ON p.id = oi.product_id JOIN orders o ON oi.order_id = o.id WHERE o.status = 'completed' GROUP BY p.id, p.name, p.category ORDER BY total_revenue DESC LIMIT 10",
                    "explanation": "Calculates total sales revenue per product for completed orders.",
                    "tables_used": ["products", "order_items", "orders"]
                })

            if "electronics" in prompt_lower:
                return response_model.model_validate({
                    "sql": "SELECT id, name, category, price FROM products WHERE LOWER(category) = 'electronics' ORDER BY price DESC LIMIT 100",
                    "explanation": "Lists all products belonging to the Electronics category.",
                    "tables_used": ["products"]
                })

            # Default generic query
            return response_model.model_validate({
                "sql": "SELECT id, name, email, country FROM customers LIMIT 10",
                "explanation": "Returns sample customer records.",
                "tables_used": ["customers"]
                })

        raise ValueError(f"Unsupported response model for mock fallback: {model_name}")


groq_client = GroqClient()
