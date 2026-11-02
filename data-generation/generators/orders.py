"""Generate synthetic order transactions"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


class OrderGenerator:
    """Generates realistic order transactions"""

    def __init__(
        self,
        num_orders,
        customers_df,
        products_df,
        start_date,
        end_date,
        statuses,
        payment_methods,
        device_types,
        currencies,
        seed=42,
    ):
        self.num_orders = num_orders
        self.customers_df = customers_df
        self.products_df = products_df
        self.start_date = start_date
        self.end_date = end_date
        self.statuses = statuses
        self.payment_methods = payment_methods
        self.device_types = device_types
        self.currencies = currencies
        self.faker = Faker()
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

        # Pre-calculate customer weights (Pareto principle)
        self.customer_weights = self._calculate_customer_weights()

        # Pre-calculate product weights (popular products ordered more)
        self.product_weights = self._calculate_product_weights()

    def generate(self):
        """Generate all orders"""
        orders = []
        order_id = 1

        # Generate date range
        date_range = pd.date_range(start=self.start_date, end=self.end_date, freq="D")

        # Distribute orders across days
        orders_per_day = self._distribute_orders(len(date_range))

        for date, daily_orders in zip(date_range, orders_per_day):
            for _ in range(daily_orders):
                order = self._generate_order(order_id, date)
                orders.append(order)
                order_id += 1

        return pd.DataFrame(orders)

    def _generate_order(self, order_id, order_date):
        """Generate a single order"""
        # Choose customer and product
        customer = self._choose_customer()
        product = self._choose_product()

        # Generate timestamp on order_date
        hour = np.random.choice(range(24), p=self._hour_weights())
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        order_timestamp = datetime(
            order_date.year, order_date.month, order_date.day, hour, minute, second
        )

        # Quantity (most orders are 1 item, some are multiple)
        quantity = int(
            np.random.choice([1, 2, 3, 4, 5], p=[0.70, 0.15, 0.08, 0.05, 0.02])
        )

        # Pricing calculations
        unit_price = product["unit_price"]
        total_amount = round(quantity * unit_price, 2)

        # Discount (30% of orders have discount)
        discount_amount = 0
        if random.random() < 0.30:
            discount_amount = round(total_amount * random.uniform(0.05, 0.25), 2)

        subtotal = total_amount - discount_amount
        tax_amount = round(subtotal * 0.19, 2)  # 19% VAT (EU standard)

        # Shipping (20% free shipping)
        shipping_cost = (
            0 if random.random() < 0.20 else round(random.uniform(2.99, 15.99), 2)
        )

        # Order status
        status = random.choices(
            [s[0] for s in self.statuses], weights=[s[1] for s in self.statuses]
        )[0]

        # Payment method
        payment_method = random.choices(
            [p[0] for p in self.payment_methods],
            weights=[p[1] for p in self.payment_methods],
        )[0]

        # Device type
        device_type = random.choices(
            [d[0] for d in self.device_types], weights=[d[1] for d in self.device_types]
        )[0]

        # Currency based on customer country
        currency = self.currencies.get(customer["country_code"], "EUR")

        # Addresses
        shipping_address = f"{customer['address']}, {customer['city']}, {customer['country']} {customer['postal_code']}"
        billing_address = shipping_address  # 95% same address
        if random.random() < 0.05:
            billing_address = f"{self.faker.street_address()}, {customer['city']}, {customer['country']}"

        # Timestamps
        created_at = order_timestamp
        updated_at = created_at + timedelta(minutes=random.randint(0, 240))

        order = {
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "product_id": product["product_id"],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "order_timestamp": order_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "quantity": quantity,
            "unit_price": unit_price,
            "total_amount": total_amount,
            "discount_amount": discount_amount,
            "tax_amount": tax_amount,
            "shipping_cost": shipping_cost,
            "order_status": status,
            "payment_method": payment_method,
            "shipping_address": shipping_address,
            "billing_address": billing_address,
            "currency": currency,
            "device_type": device_type,
            "ip_address": self.faker.ipv4(),
            "session_id": f"sess_{self.faker.uuid4()[:12]}",
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": updated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        return order

    def _distribute_orders(self, num_days):
        """Distribute orders across days with realistic variation"""
        # Base: equal distribution
        base_orders_per_day = self.num_orders // num_days

        # Add variation (±20%)
        orders_per_day = []
        remaining = self.num_orders

        for i in range(num_days):
            if i == num_days - 1:
                # Last day gets all remaining
                orders_per_day.append(remaining)
            else:
                # Random variation
                daily = int(base_orders_per_day * random.uniform(0.80, 1.20))
                daily = min(daily, remaining)
                orders_per_day.append(daily)
                remaining -= daily

        return orders_per_day

    def _calculate_customer_weights(self):
        """Pareto principle: 20% of customers generate 80% of orders"""
        # Use customer segment to weight
        segment_weights = {"Bronze": 1, "Silver": 3, "Gold": 6, "Platinum": 10}
        weights = (
            self.customers_df["customer_segment"].map(segment_weights).fillna(1).values
        )
        return weights / weights.sum()

    def _calculate_product_weights(self):
        """Popular products (high ratings, reviews) ordered more frequently"""
        weights = self.products_df["average_rating"] * np.log1p(
            self.products_df["review_count"]
        )

        # Inactive products have very low weight
        weights = weights * self.products_df["is_active"]
        weights = weights.replace(0, 0.01)  # Avoid zero weights

        return weights / weights.sum()

    def _choose_customer(self):
        """Choose customer based on Pareto distribution"""
        idx = np.random.choice(len(self.customers_df), p=self.customer_weights)
        return self.customers_df.iloc[idx]

    def _choose_product(self):
        """Choose product based on popularity"""
        idx = np.random.choice(len(self.products_df), p=self.product_weights)
        return self.products_df.iloc[idx]

    def _hour_weights(self):
        """Weighted hour distribution (more orders during business hours)"""
        weights = np.array(
            [
                0.01,
                0.01,
                0.01,
                0.01,
                0.01,
                0.02,  # 00:00-05:00 (night)
                0.03,
                0.05,
                0.08,
                0.10,
                0.12,
                0.12,  # 06:00-11:00 (morning)
                0.10,
                0.08,
                0.06,
                0.05,
                0.04,
                0.03,  # 12:00-17:00 (afternoon)
                0.02,
                0.02,
                0.02,
                0.01,
                0.01,
                0.01,  # 18:00-23:00 (evening)
            ]
        )
        # Normalize to ensure sum = 1.0
        return weights / weights.sum()


def generate_orders(
    num_orders,
    customers_df,
    products_df,
    start_date,
    end_date,
    statuses,
    payment_methods,
    device_types,
    currencies,
    seed=42,
):
    """Convenience function to generate orders"""
    generator = OrderGenerator(
        num_orders,
        customers_df,
        products_df,
        start_date,
        end_date,
        statuses,
        payment_methods,
        device_types,
        currencies,
        seed,
    )
    return generator.generate()