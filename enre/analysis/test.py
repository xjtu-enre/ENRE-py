import os
import sys
from pathlib import Path

print(sys.executable)
print()
paths = [Path(path) for path in sys.path]
print(paths)

here = os.path.abspath(os.path.dirname(__file__)).removesuffix(r"enre\analysis")
internal_typeshed = os.path.join(here, 'typeshed\stdlib')
print(internal_typeshed)