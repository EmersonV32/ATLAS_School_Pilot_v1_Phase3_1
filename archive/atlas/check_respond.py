import inspect
from atlas.dialogue.dialogue_engine import DialogueEngine, DialogueResult

print("=== respond() ARGS ===")
print(list(inspect.signature(DialogueEngine.respond).parameters))

print("=== DialogueResult FIELDS ===")
fields = getattr(DialogueResult, "__dataclass_fields__", None)
if fields:
    print(list(fields.keys()))
else:
    print([n for n in dir(DialogueResult) if not n.startswith("_")])
