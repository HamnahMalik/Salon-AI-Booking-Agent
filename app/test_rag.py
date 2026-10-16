from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

CHROMA_DIR = "/chromadb"
COLLECTION_NAME = "salon_knowledge"

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_db = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
)

query = "How much is a facial?"

results = vector_db.similarity_search(query, k=3)

for i, doc in enumerate(results, start=1):
    print(f"\n--- Result {i} ---")
    print(doc.page_content)
    print("Source:", doc.metadata.get("source"))
