# main.py
import sys
import os 
from PyQt5.QtWidgets import QApplication          # ← 必须有这一行
from ui.main_window import HdictVocConverterWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = HdictVocConverterWindow()
    window.show()
    sys.exit(app.exec_())
    