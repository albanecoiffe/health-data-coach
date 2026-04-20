import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from rag.catalog.indexer import CatalogIndexer
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()
print("DB =", os.getenv("DATABASE_URL"))
DB_URL = os.getenv("DATABASE_URL")

indexer = CatalogIndexer(connection_string=DB_URL)

# ⚠️ IMPORTANT : overwrite=True au moins la première fois
indexer.index(overwrite=True)

print("✅ Catalogue indexé")
