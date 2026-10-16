import os
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

BASE_DIR = Path("/app")
KB_DIR = Path("/knowledge_base")
CHROMA_DIR = Path("/chromadb")

COLLECTION_NAME = "salon_knowledge"


def load_documents():
    documents = []

    for file_path in KB_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")

        documents.append(
            Document(
                page_content=text,
                metadata={"source": file_path.name}
            )
        )

    return documents


def build_vector_db():
    documents = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80
    )

    chunks = splitter.split_documents(documents)

    print(f"Loaded documents: {len(documents)}")
    print(f"Created chunks: {len(chunks)}")

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR)
    )

    print("ChromaDB created successfully")
    print(f"Saved to: {CHROMA_DIR}")


if __name__ == "__main__":
    build_vector_db()
