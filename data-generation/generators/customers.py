"""Generate synthetic customer data"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


class CustomerGenerator:
    """Generates realistic customer master data with SCD Type 2"""

    def __init__(self, num_customers, countries, segments, seed=42):
        self.num_customers = num_customers
        self.countries = countries
        self.segments = segments
        self.faker = Faker()
        random.seed(seed)
        np.random.seed(seed)
        Faker.seed(seed)

    def generate(self):
        """Generate complete customer database"""
        customers = []
        customer_key = 1
        customer_id = 1

        for _ in range(self.num_customers):
            # Choose country based on distribution
            country_name, country_code, _ = self._choose_country()

            # Set Faker locale based on country
            locale = self._get_locale(country_code)
            faker_local = Faker(locale)

            # Generate personal info
            gender = random.choice(["M", "F", "Other"])
            if gender == "M":
                first_name = faker_local.first_name_male()
            elif gender == "F":
                first_name = faker_local.first_name_female()
            else:
                first_name = faker_local.first_name()

            last_name = faker_local.last_name()

            # Generate email
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@{faker_local.free_email_domain()}"

            # Registration date (past 2 years)
            days_ago = random.randint(30, 730)  # 1 month to 2 years
            registration_date = datetime(2026, 2, 17) - timedelta(days=days_ago)

            # Customer segment (determines order count and LTV)
            segment = self._choose_segment()
            ltv_range = self.segments[segment]["ltv_range"]
            total_lifetime_value = round(random.uniform(ltv_range[0], ltv_range[1]), 2)

            # Estimate order count based on segment
            order_count = self._estimate_order_count(segment)

            customer = {
                "customer_key": customer_key,
                "customer_id": customer_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone": faker_local.phone_number()[:20],
                "date_of birth": faker_local.date_of_birth(
                    minimum_age=18, maximum_age=80
                ).strftime("%Y-%m-%d"),
                "gender": gender,
                "address": faker_local.street_address(),
                "city": faker_local.city(),
                "state_province": faker_local.state() if country_code == "US" else None,
                "postal_code": faker_local.postcode(),
                "country": country_name,
                "country_code": country_code,
                "registration_date": registration_date.strftime("%Y-%m-%d"),
                "customer_segment": segment,
                "total_lifetime_value": total_lifetime_value,
                "order_count": order_count,
                "is_active": random.random() > 0.10,  # 90% active
                "marketing_opt_in": random.random() > 0.40,  # 60% opt-in
                "valid_from": registration_date.strftime("%Y-%m-%dT00:00:00Z"),
                "valid_to": None,
                "is_current": True,
                "created_at": registration_date.strftime("%Y-%m-%dT00:00:00Z"),
            }

            customers.append(customer)
            customer_key += 1
            customer_id += 1

        return pd.DataFrame(customers)

    def _choose_country(self):
        """Choose country based on weighted distribution"""
        countries, codes, weights = zip(*self.countries)
        return random.choices(list(zip(countries, codes, weights)), weights=weights)[0]
    
    def _choose_segment(self):
        """Choose customer segment based on weights"""
        segments = list(self.segments.keys())
        weights = [self.segments[s]["weight"] for s in segments]
        return random.choices(segments, weights=weights)[0]
    
    def _estimate_order_count(self, segment):
        """Estimate order count based on segment"""
        if segment == "Bronze":
            return random.randint(0, 5)
        elif segment == "Silver":
            return random.randint(6, 15)
        elif segment == "Gold":
            return random.randint(16, 30)
        else:  # Platinum
            return random.randint(31, 100)
    
    def _get_locale(self, country_code):
        """Map country code to Faker locale"""
        locale_map = {
            "DE": "de_DE",
            "FR": "fr_FR",
            "GB": "en_GB",
            "ES": "es_ES",
            "IT": "it_IT",
            "NL": "nl_NL",
            "EU": "en_US",
        }
        return locale_map.get(country_code, "en_US")


def generate_customers(num_customers, countries, segments, seed=42):
    """Convenience function to generate customers"""
    generator = CustomerGenerator(num_customers, countries, segments, seed)
    return generator.generate()