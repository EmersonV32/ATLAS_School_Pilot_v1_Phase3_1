from atlas.rag.retriever import RetrievalQuery

print("=== RetrievalQuery field details ===")
for name, f in RetrievalQuery.model_fields.items():
    req = "required" if f.is_required() else "optional(default=%r)" % f.default
    print("  ", name, ":", f.annotation, "|", req)

print()
print("=== enum members ===")
import enum
seen = set()
for name, f in RetrievalQuery.model_fields.items():
    ann = f.annotation
    candidates = [ann] + list(getattr(ann, "__args__", []))
    for c in candidates:
        if isinstance(c, type) and issubclass(c, enum.Enum) and c not in seen:
            seen.add(c)
            print(c.__name__, "->", [m.value for m in c])
