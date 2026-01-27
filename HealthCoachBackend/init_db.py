# init_db.py
from services.database import engine, Base
from models import RunSession

print("🚀 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created")
