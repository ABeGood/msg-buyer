"""Script to get 5 random products from database"""
from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sqlalchemy import text
import json

repo = ProductRepository(get_database_url())
engine = repo.engine

with engine.connect() as conn:
    result = conn.execute(text('SELECT * FROM products ORDER BY RANDOM() LIMIT 5'))
    rows = result.fetchall()
    columns = result.keys()
    products = [dict(zip(columns, row)) for row in rows]
    print(json.dumps(products, indent=2, ensure_ascii=False, default=str))
