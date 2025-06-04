# No início do código, para debug
from inspect import signature

from vector_store.store import VectorStore

vector_store = VectorStore()
sig = signature(vector_store.db.add_documents)
print(f"Assinatura correta: {sig}")
help(vector_store.db.add_documents)  # Mostra a documentação e parâmetros