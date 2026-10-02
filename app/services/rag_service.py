import os
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document as DocxDocument

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_store")

_client = None
_collection = None
_embedder = None


def _get_embedder():
    """Lazy-loaded so the app can start even before the model is cached."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        # Small, CPU-friendly model — runs fine on a Mac M1.
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _client.get_or_create_collection("study_materials")
    return _collection


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
def extract_text_from_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Simple sliding-window chunker. Good enough for notes/textbook PDFs;
    swap in a sentence-aware splitter later if needed."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def index_document(user_id: int, filename: str, text: str) -> int:
    """Chunk, embed, and store a document's text for one user.
    Returns the number of chunks indexed."""
    collection = _get_collection()
    embedder = _get_embedder()

    chunks = chunk_text(text)
    if not chunks:
        return 0

    embeddings = embedder.encode(chunks).tolist()
    ids = [f"user{user_id}_{filename}_{i}" for i in range(len(chunks))]
    metadatas = [{"user_id": str(user_id), "filename": filename, "chunk_index": i}
                 for i in range(len(chunks))]

    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    return len(chunks)


def retrieve_context(user_id: int, question: str, top_k: int = 4) -> list[dict]:
    """Return the most relevant chunks for this user's question, each with
    its source filename so answers can be cited."""
    collection = _get_collection()
    embedder = _get_embedder()

    query_embedding = embedder.encode([question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"user_id": str(user_id)},
    )

    hits = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        hits.append({"text": doc, "source": meta.get("filename", "unknown")})
    return hits
