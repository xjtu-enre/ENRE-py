from pathlib import Path

path_dic = {}

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
