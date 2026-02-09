# main.py
import sys
import os 
from PyQt5.QtWidgets import QApplication          # ← 必须有这一行
from ui.main_window import HdictVocConverterWindow
# 根据实际测试成功的路径修改下面这一行
HALCON_BIN = r"D:\MVTEC Software\HALCON-25.11-Progress\bin\x64-win64"

if HALCON_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = HALCON_BIN + os.pathsep + os.environ.get("PATH", "")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HdictVocConverterWindow()
    window.show()
    sys.exit(app.exec_())