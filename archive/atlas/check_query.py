import inspect
from atlas.rag.retriever import RetrievalQuery, RetrievalResult, RetrievedChunk

for cls in (RetrievalQuery, RetrievedChunk):
    print("===", cls.__name__, "FIELDS ===")
    fields = getattr(cls, "__dataclass_fields__", None)
    if fields:
        for n, f in fields.items():
            print("  ", n, ":", getattr(f.type, "__name__", f.type))
    else:
        pf = getattr(cls, "model_fields", None)
        if pf:
            for n in pf:
                print("  ", n)
        else:
            print("  (plain) ", [n for n in dir(cls) if not n.startswith("_")])
    print()

import inspect as _i
try:
    src = _i.getsource(RetrievalQuery.__init__)
    print("=== RetrievalQuery.__init__ ===")
    print(src)
except (TypeError, OSError):
    print("RetrievalQuery has no custom __init__ (dataclass/pydantic auto)")
