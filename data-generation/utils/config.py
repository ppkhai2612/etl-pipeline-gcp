"""Configuration constants for data generation"""

# Data Volumes
NUM_PRODUCTS = 5000
NUM_CUSTOMERS = 20000
NUM_ORDERS = 500000

# Date Ranges
HISTORICAL_START_DATE = "2025-02-17"
HISTORICAL_END_DATE = "2026-02-17"

# Random Seed (for reproducibility)
RANDOM_SEED = 42

# Product Configuration
CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Tablets", "Audio", "Accessories"],
    "Clothing": ["Men", "Women", "Kids", "Shoes", "Accessories"],
    "Home & Garden": ["Furniture", "Kitchen", "Bedding", "Decor", "Tools"],
    "Sports": ["Fitness", "Outdoor", "Team Sports", "Water Sports", "Winter Sports"],
    "Books": ["Fiction", "Non-Fiction", "Science", "Biography", "Children"],
}

BRANDS = {
    "Electronics": [
        "TechCorp",
        "DigitalPro",
        "SmartDevice",
        "ElectroMax",
        "GadgetKing",
    ],
    "Clothing": [
        "FashionHub",
        "StyleWear",
        "TrendyClothes",
        "UrbanStyle",
        "ClassicWear",
    ],
    "Home & Garden": [
        "HomeComfort",
        "GardenPro",
        "CozyLiving",
        "ModernHome",
        "EcoGarden",
    ],
    "Sports": ["SportsPro", "ActiveGear", "FitLife", "OutdoorMax", "AthleteChoice"],
    "Books": ["BookWorld", "ReadMore", "ClassicBooks", "ModernPublish", "PageTurner"],
}

PRICE_RANGES = {
    "Electronics": (29.99, 1999.99),
    "Clothing": (9.99, 299.99),
    "Home & Garden": (19.99, 999.99),
    "Sports": (14.99, 599.99),
    "Books": (5.99, 49.99),
}

# Customer Configuration
COUNTRIES = [
    ("Germany", "DE", 0.35),
    ("France", "FR", 0.20),
    ("United Kingdom", "GB", 0.15),
    ("Spain", "ES", 0.10),
    ("Italy", "IT", 0.10),
    ("Netherlands", "NL", 0.05),
    ("European Union", "EU", 0.05),
]

CUSTOMER_SEGMENTS = {
    "Bronze": {"ltv_range": (0, 200), "weight": 0.60},
    "Silver": {"ltv_range": (200, 1000), "weight": 0.25},
    "Gold": {"ltv_range": (1000, 5000), "weight": 0.12},
    "Platinum": {"ltv_range": (5000, 20000), "weight": 0.03},
}

# Order Configuration
ORDER_STATUSES = [
    ("pending", 0.05),
    ("paid", 0.10),
    ("processing", 0.15),
    ("shipped", 0.35),
    ("delivered", 0.30),
    ("cancelled", 0.03),
    ("returned", 0.01),
    ("refunded", 0.01),
]

PAYMENT_METHODS = [
    ("credit_card", 0.45),
    ("debit_card", 0.25),
    ("paypal", 0.15),
    ("bank_transfer", 0.10),
    ("apple_pay", 0.03),
    ("google_pay", 0.02),
]

DEVICE_TYPES = [
    ("desktop", 0.40),
    ("mobile", 0.45),
    ("tablet", 0.15),
]

CURRENCIES = {
    "DE": "EUR",
    "FR": "EUR",
    "GB": "GBP",
    "ES": "EUR",
    "IT": "EUR",
    "NL": "EUR",
    "EU": "EUR",
}