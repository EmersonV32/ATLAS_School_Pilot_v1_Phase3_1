import inspect
from atlas.dialogue.prompt_builder import PromptBuilder
from atlas.dialogue.grounding_validator import GroundingValidator

print("=== PromptBuilder.build ===")
print(inspect.getsource(PromptBuilder.build))
print("=== GroundingValidator.validate ===")
print(inspect.getsource(GroundingValidator.validate))
