from sources.database.repository import ProductRepository
from sources.database.config import get_database_url
from sqlalchemy import create_engine, text

# repo = ProductRepository(get_database_url())
# repo.drop_table('abc')

engine = create_engine(get_database_url())

# Add is_read column to messages table
# with engine.connect() as conn:
#     conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE;"))
#     conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_is_read ON messages(is_read);"))
#     conn.commit()
#     print("Migration completed: added is_read column to messages table")

# Create conversation_classifications table
# with engine.connect() as conn:
#     conn.execute(text("""
#         CREATE TABLE IF NOT EXISTS conversation_classifications (
#             conversation_id INTEGER PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
#             status VARCHAR(50) NOT NULL,
#             decline_reason VARCHAR(50),
#             decline_details TEXT,
#             confidence INTEGER NOT NULL,
#             seller_sentiment VARCHAR(20) NOT NULL,
#             has_price_info BOOLEAN NOT NULL DEFAULT FALSE,
#             prices_mentioned JSONB,
#             availability_info TEXT,
#             next_steps TEXT,
#             summary TEXT,
#             created_at TIMESTAMP NOT NULL DEFAULT NOW(),
#             updated_at TIMESTAMP NOT NULL DEFAULT NOW()
#         );
#     """))
#     conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_class_status ON conversation_classifications(status);"))
#     conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_class_decline_reason ON conversation_classifications(decline_reason);"))
#     conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_class_updated_at ON conversation_classifications(updated_at);"))
#     conn.commit()
#     print("Migration completed: created conversation_classifications table")

# Add seller_phone column to products table
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS seller_phone VARCHAR(50);"))
    conn.commit()
    print("Migration completed: added seller_phone column to products table")
