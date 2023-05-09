import sys
import os
from pathlib import Path
from enre.pyi.finder import get_search_context
from typeshed.frozen_path import app_path


path_dic = {}

# setup for typing and builtins
typing_path = Path("typing.py")
typing_pytd_path = Path(r"C:\Users\yoghurts\Desktop\Research\ENRE\Codes\ENRE-py\feat-typeshed\ENRE-py\enre\stubs"
                        r"\builtins\typing.pytd")
# typing_pytd_path = Path(r"C:\Users\yoghurts\Desktop\Research\ENRE\Codes\ENRE-py\feat-typeshed\ENRE-py\enre\stubs"
#                         r"\test\typing.pytd")
path_dic["typing"] = typing_path, typing_pytd_path

builtins_path = Path("builtins.py")
builtins_pytd_path = Path(r"C:\Users\yoghurts\Desktop\Research\ENRE\Codes\ENRE-py\feat-typeshed\ENRE-py\enre\stubs"
                          r"\builtins\builtins.pytd")
# builtins_pytd_path = Path(r"C:\Users\yoghurts\Desktop\Research\ENRE\Codes\ENRE-py\feat-typeshed\ENRE-py\enre\stubs"
#                           r"\test\builtins.pytd")
path_dic["builtins"] = builtins_path, builtins_pytd_path


# typeshed
typeshed_path = Path(app_path("\stdlib"))
typeshed_ctx = get_search_context(typeshed=typeshed_path)
