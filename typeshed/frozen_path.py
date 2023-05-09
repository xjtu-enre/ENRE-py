# -*- coding: utf-8 -*-
import sys
import os


def app_path(relative_path):
    if hasattr(sys, 'frozen'):
        # Handles PyInstaller
        base_path = sys._MEIPASS  # 使用pyinstaller打包后的exe目录
        base_path = base_path + r"\typeshed"
    else:
        base_path = os.path.dirname(__file__)

    return base_path + relative_path  # 没打包前的py目录

