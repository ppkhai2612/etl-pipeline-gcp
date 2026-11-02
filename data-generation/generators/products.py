"""Generate synthetic product catalog"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


class ProductGenerator:
    """Generates realistic product catalog with SCD Type 2"""

    def __init__(self, num_products, categories, brands, price_ranges, seed=42):
        self.num_products = num_products
        self.categories = categories
        self.brands = brands
        self.price_ranges = price_ranges
        self.faker = Faker()
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

    def generate(self):
        """Generate complete product catalog"""
        products = []
        product_key = 1
        product_id = 1

        for _ in range(self.num_products):
            # Choose category, subcategory, and brand
            category = random.choice(list(self.categories.keys()))
            subcategory = random.choice(self.categories[category])
            brand = random.choice(self.brands[category])

            # Generate product name
            product_name = self._generate_product_name(category, subcategory)

            # Price based on category
            min_price, max_price = self.price_ranges[category]
            unit_price = round(random.uniform(min_price, max_price), 2)
            cost_price = round(unit_price * random.uniform(0.40, 0.70), 2)

            # Stock quantity (realistic distribution)
            stock_quantity = int(np.random.lognormal(mean=4, sigma=1.5))
            stock_quantity = max(0, min(stock_quantity, 1000))

            days_ago = random.randint(0, 1095)  # 3 years
            release_date = datetime(2026, 2, 17) - timedelta(days=days_ago)

            product = {
                "product_key": product_key,
                "product_id": product_id,
                "product_name": product_name,
                "product_description": self.faker.text(max_nb_chars=200),
                "category": category,
                "subcategory": subcategory,
                "brand": brand,
                "model_number": self._generate_model_number(),
                "sku": f"{category[:4].upper()}-{subcategory[:4].upper()}-{product_id:06d}",
                "barcode": self.faker.ean13(),
                "unit_price": unit_price,
                "cost_price": cost_price,
                "currency": "EUR",
                "stock_quantity": stock_quantity,
                "reorder_level": max(10, int(stock_quantity * 0.2)),
                "supplier_id": random.randint(5000, 5100),
                "supplier_name": self.faker.company(),
                "weight_kg": round(random.uniform(0.05, 50), 2),
                "dimensions_cm": f"{random.randint(5, 200)}x{random.randint(5, 150)}x{random.randint(5, 100)}",
                "color": random.choice(
                    ["Black", "White", "Red", "Blue", "Green", "Silver", "Multi", None]
                ),
                "size": random.choice(["S", "M", "L", "XL", "Standard", None]),
                "is_active": random.random() > 0.05,  # 95% active
                "is_featured": random.random() < 0.10,  # 10% featured
                "average_rating": round(random.uniform(2.5, 5.0), 1),
                "review_count": int(np.random.lognormal(mean=2, sigma=1.5)),
                "release_date": release_date.strftime("%Y-%m-%d"),
                "valid_from": release_date.strftime("%Y-%m-%dT00:00:00Z"),
                "valid_to": None,
                "is_current": True,
            }

            products.append(product)
            product_key += 1
            product_id += 1

        return pd.DataFrame(products)

    def _generate_product_name(self, category, subcategory):
        """Generate realistic product name"""
        adjectives = [
            "Premium",
            "Professional",
            "Deluxe",
            "Ultra",
            "Classic",
            "Modern",
            "Elegant",
        ]
        materials = ["Cotton", "Leather", "Steel", "Aluminum", "Plastic", "Wood"]

        if category == "Electronics":
            types = [
                "Mouse",
                "Keyboard",
                "Headphones",
                "Speaker",
                "Monitor",
                "Webcam",
                "Cable",
            ]
            return f"{random.choice(adjectives)} {random.choice(types)}"
        elif category == "Clothing":
            types = ["T-Shirt", "Jeans", "Dress", "Jacket", "Sneakers", "Boots"]
            return f"{random.choice(adjectives)} {random.choice(materials)} {random.choice(types)}"
        elif category == "Books":
            return self.faker.catch_phrase()
        else:
            return f"{random.choice(adjectives)} {subcategory} Item"

    def _generate_model_number(self):
        """Generate realistic model number"""
        prefix = random.choice(["MX", "PRO", "HD", "ULT", "XR", "ZX"])
        number = random.randint(100, 9999)
        suffix = random.choice(["", "-A", "-B", "-X", "-S"])
        return f"{prefix}-{number}{suffix}"


def generate_products(num_products, categories, brands, price_ranges, seed):
    """Convenience function to generate products"""
    generator = ProductGenerator(num_products, categories, brands, price_ranges, seed)
    return generator.generate()