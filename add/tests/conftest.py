import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:                                   # tests do not need the real client
    import ollama  # noqa: F401
except ImportError:
    stub = types.ModuleType("ollama")
    stub.Client = lambda **kw: object()
    stub.ChatResponse = object
    sys.modules["ollama"] = stub
