import inspect
from atlas.rag.retriever import HybridRetriever

print("=== retrieve() ARGS ===")
print(list(inspect.signature(HybridRetriever.retrieve).parameters))
print()
print("=== retrieve() SOURCE ===")
print(inspect.getsource(HybridRetriever.retrieve))
