# init_db.py
from database import engine, Base
from core.models.RunSession import RunSession

print("🚀 Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created")
