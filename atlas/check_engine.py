import inspect
from atlas.dialogue.dialogue_engine import DialogueEngine

print("=== CONSTRUCTOR ARGS ===")
print(list(inspect.signature(DialogueEngine.__init__).parameters))

print("=== PUBLIC METHODS ===")
for name in dir(DialogueEngine):
    if not name.startswith("_"):
        print(name)
