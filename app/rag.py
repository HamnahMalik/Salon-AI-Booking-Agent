from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

CHROMA_DIR = "/chromadb"
COLLECTION_NAME = "salon_knowledge"

client = OpenAI()

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)

vector_db = Chroma(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
)


def ask_salon(question: str) -> str:
    results = vector_db.similarity_search(
        question,
        k=4
    )

    context = "\n\n---\n\n".join(
        doc.page_content
        for doc in results
    )

    prompt = f"""
You are the customer assistant for Glow & Grace Salon.

Answer using ONLY the salon information below.

Important:
- If the customer asks what services are offered, list all services
  found in the provided context.
- If the customer asks about prices, staff, hours, policies,
  walk-ins, home service, or booking, use the relevant information
  from the context.
- Do not say information is unavailable if it is present anywhere
  in the supplied context.
- Keep the answer natural and concise.
- If the information truly does not exist in the context, say that
  it is not currently available.

Salon information:

{context}

Customer question:
{question}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text.strip()
