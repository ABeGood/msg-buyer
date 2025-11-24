from sources.database.repository import ProductRepository
from sources.database.config import get_database_url

repo = ProductRepository(get_database_url())
repo.drop_table('abc')
