# config.py
import os

# Model configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.55"))

# Paths
DATA_DIR = "data"
INDEX_DIR = os.path.join(DATA_DIR, "indexes")
PROTOTYPES_PATH = "prototypes.json"