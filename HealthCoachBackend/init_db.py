# init_db.py
from database import engine, Base
from models.models import RunSession

print("🚀 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created")
