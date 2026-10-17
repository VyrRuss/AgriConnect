"""Run with: python -m database.sample_data
Adds a few sample crop listings and agricultural products to MongoDB."""
from database.connection import get_database
from database.product_catalog import SAMPLE_CROPS, SAMPLE_PRODUCTS


def seed():
    db = get_database()
    if db is None:
        raise SystemExit("MongoDB is unavailable. Start MongoDB and check your .env settings.")

    crops = SAMPLE_CROPS
    products = SAMPLE_PRODUCTS

    # Avoid adding the same sample records each time this script runs.
    for crop in crops:
        db.crop_listings.update_one(
            {"crop_name": crop["crop_name"], "location": crop["location"]},
            {"$setOnInsert": crop},
            upsert=True,
        )
    for product in products:
        db.products.update_one(
            {"name": product["name"]},
            {"$setOnInsert": product},
            upsert=True,
        )

    db.users.create_index("email", unique=True)
    print("Sample crop listings and products are ready.")


if __name__ == "__main__":
    seed()
