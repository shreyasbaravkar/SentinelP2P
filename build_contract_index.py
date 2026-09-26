import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer

# Load contracts
contracts = pd.read_csv("contracts.csv")
print(f"Loaded {len(contracts)} contracts")

# Load a small, fast embedding model (runs locally, no API key needed)
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Embed the contract_text column
print("Embedding contract text...")
texts = contracts["contract_text"].tolist()
embeddings = model.encode(texts, show_progress_bar=True)

# Set up Qdrant in local on-disk mode (no server needed)
client = QdrantClient(path="./qdrant_data")

collection_name = "contracts"
vector_size = embeddings.shape[1]  # 384 for this model

client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
)

# Upload contract vectors, keeping vendor_id and contract_text as payload
points = [
    PointStruct(
        id=i,
        vector=embeddings[i].tolist(),
        payload={
            "contract_id": row["contract_id"],
            "vendor_id": row["vendor_id"],
            "contract_text": row["contract_text"],
        },
    )
    for i, row in contracts.iterrows()
]

client.upsert(collection_name=collection_name, points=points)

print(f"Indexed {len(points)} contracts into Qdrant collection '{collection_name}'")