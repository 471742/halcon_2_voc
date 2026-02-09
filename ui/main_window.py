# ui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFileDialog,
    QTextEdit, QMessageBox,QApplication
)
from PyQt5.QtCore import Qt

from core.converter import hdict_to_voc_xml, voc_xml_to_hdict


class HdictVocConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HDict ↔ VOC2007 XML 转换工具")
        self.resize(620, 420)

        self.input_path = ""
        self.output_path = ""

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 方向
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("转换方向："))
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["HDict → VOC XML", "VOC XML → HDict"])
        self.cb_mode.currentIndexChanged.connect(self._on_mode_changed)
        h1.addWidget(self.cb_mode)
        h1.addStretch()
        layout.addLayout(h1)

        # 输入
        h2 = QHBoxLayout()
        btn_in = QPushButton("选择输入")
        btn_in.clicked.connect(self._select_input)
        h2.addWidget(btn_in)
        self.lbl_in = QLabel("尚未选择")
        self.lbl_in.setStyleSheet("color: #666;")
        h2.addWidget(self.lbl_in)
        h2.addStretch()
        layout.addLayout(h2)

        # 输出
        h3 = QHBoxLayout()
        btn_out = QPushButton("选择输出目录")
        btn_out.clicked.connect(self._select_output)
        h3.addWidget(btn_out)
        self.lbl_out = QLabel("尚未选择")
        self.lbl_out.setStyleSheet("color: #666;")
        h3.addWidget(self.lbl_out)
        h3.addStretch()
        layout.addLayout(h3)

        # 执行
        self.btn_run = QPushButton("开始转换")
        self.btn_run.setStyleSheet("font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self._run_conversion)
        layout.addWidget(self.btn_run)

        # 日志
        layout.addWidget(QLabel("日志："))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background: #f8f9fa; font-family: Consolas;")
        layout.addWidget(self.log_text)

        self._on_mode_changed()

    def _on_mode_changed(self):
        is_h2v = self.cb_mode.currentIndex() == 0
        self.btn_run.setText("HDict → VOC" if is_h2v else "VOC → HDict")

    def _select_input(self):
        is_h2v = self.cb_mode.currentIndex() == 0
        if is_h2v:
            path, _ = QFileDialog.getOpenFileName(self, "选择 .hdict 文件", "", "Halcon Dict (*.hdict)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择 VOC XML 文件夹")
        if path:
            self.input_path = path
            self.lbl_in.setText(path if len(path) < 60 else "..." + path[-57:])
            self.lbl_in.setStyleSheet("color: #000;")

    def _select_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.output_path = path
            self.lbl_out.setText(path if len(path) < 60 else "..." + path[-57:])
            self.lbl_out.setStyleSheet("color: #000;")

    def _log(self, msg: str):
        self.log_text.append(msg)
        self.log_text.ensureCursorVisible()
        QApplication.processEvents()

    def _run_conversion(self):
        if not self.input_path:
            QMessageBox.warning(self, "提示", "请选择输入")
            return
        if not self.output_path:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            return

        self.log_text.clear()
        self._log("开始处理...\n")

        try:
            if self.cb_mode.currentIndex() == 0:
                hdict_to_voc_xml(
                    hdict_path=self.input_path,
                    output_dir=self.output_path,
                    log_func=self._log
                )
            else:
                voc_xml_to_hdict(
                    xml_dir=self.input_path,
                    output_dir=self.output_path,
                    log_func=self._log
                )
            self._log("\n转换完成 ✓")
            QMessageBox.information(self, "完成", "转换已完成！")
        except Exception as e:
            self._log(f"\n错误：{str(e)}")
            QMessageBox.critical(self, "失败", str(e))