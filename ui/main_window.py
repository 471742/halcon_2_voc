# ui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFileDialog,
    QTextEdit, QMessageBox,QApplication,QProgressDialog
)
from PyQt5.QtCore import Qt
import os
import datetime
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
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

        # self.log_dir = os.path.join(os.path.expanduser("~"), "Desktop", "转换日志")  # 可自定义路径
        self.log_dir = "./logs"  # 日志文件存放目录
        os.makedirs(self.log_dir, exist_ok=True)

        self.current_log_path = None

        # 新增按钮
        self.btn_open_log = QPushButton("打开日志文件夹")
        self.btn_open_log.setEnabled(False)
        self.btn_open_log.clicked.connect(self.open_log_folder)
        layout.addWidget(self.btn_open_log)  # 建议放在日志文本框下方
        
        self.custom_image_dir = ""  # 新增：用户手动指定的图像根目录

        # 新增：图片文件夹选择区域（建议放在“选择输出目录”下面）
        row_img = QHBoxLayout()
        row_img.addWidget(QLabel("图片文件夹（可选）："))
        
        self.btn_select_img_dir = QPushButton("选择文件夹")
        self.btn_select_img_dir.clicked.connect(self._select_image_dir)
        row_img.addWidget(self.btn_select_img_dir)

        self.lbl_img_dir = QLabel("使用 hdict 中的 image_dir")
        self.lbl_img_dir.setStyleSheet("color: #666;")
        row_img.addWidget(self.lbl_img_dir)
        row_img.addStretch()
        layout.addLayout(row_img)

        self._on_mode_changed()
    
    def _select_image_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择图片文件夹", "")
        if path:
            self.custom_image_dir = path
            self.lbl_img_dir.setText(path if len(path) < 60 else "..." + path[-57:])
            self.lbl_img_dir.setStyleSheet("color: #000;")
            self._log(f"已指定自定义图片文件夹：{path}\n")
        else:
            self.custom_image_dir = ""
            self.lbl_img_dir.setText("使用 hdict 中的 image_dir")
            self.lbl_img_dir.setStyleSheet("color: #666;")

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

        if hasattr(self, 'log_file') and not self.log_file.closed:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_file.write(f"[{timestamp}] {msg.strip()}\n")
            self.log_file.flush()  # 实时写入

    def open_log_folder(self):
        if self.current_log_path and os.path.exists(self.log_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.log_dir))
        else:
            QMessageBox.information(self, "提示", "暂无日志文件夹或路径无效")
    def _run_conversion(self):
        if not self.input_path:
            QMessageBox.warning(self, "提示", "请选择输入")
            return
        if not self.output_path:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            return

        self.log_text.clear()
        self._log("开始处理...\n")

       # 生成日志文件名（按时间）
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        mode_text = "hdict_to_voc" if self.cb_mode.currentIndex() == 0 else "voc_to_hdict"
        log_filename = f"{now}_{mode_text}.log"
        self.current_log_path = os.path.join(self.log_dir, log_filename)

        # 清空界面日志
        self.log_text.clear()
        self._log(f"日志将保存至：{self.current_log_path}\n")
        self._log("开始处理...\n")

        # 创建文件日志处理器（简单方式：用 open 写入）
        self.log_file = open(self.current_log_path, "w", encoding="utf-8")
        self.log_file.write(f"转换开始时间: {datetime.datetime.now()}\n")
        self.log_file.write(f"模式: {mode_text}\n")
        self.log_file.write(f"输入: {self.input_path}\n")
        self.log_file.write(f"输出: {self.output_path}\n")
        self.log_file.write("-" * 60 + "\n")

        # 启用打开日志按钮
        self.btn_open_log.setEnabled(True)

        try:
            progress = QProgressDialog("正在转换...", "取消", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)

            if self.cb_mode.currentIndex() == 0:
                hdict_to_voc_xml(
                    hdict_path=self.input_path,
                    output_dir=self.output_path,
                    log_func=self._log,
                    progress=progress,
                    log_file=self.log_file,
                    custom_image_dir=self.custom_image_dir   # 新增参数
                )
            else:
                voc_xml_to_hdict(
                    xml_dir=self.input_path,
                    output_dir=self.output_path,
                    log_func=self._log,
                    progress=progress,               # 新增进度条
                    log_file=self.log_file,          # 新增日志文件
                    custom_image_dir=self.custom_image_dir  # 新增自定义图片目录
                )
            progress.close()
            self._log("\n转换完成 ✓")
            self.log_file.write("\n转换完成\n")
            QMessageBox.information(self, "完成", f"转换完成\n日志已保存至：\n{self.current_log_path}")

        except Exception as e:
            self._log(f"\n错误：{str(e)}")
            self.log_file.write(f"\n错误：{str(e)}\n")
            QMessageBox.critical(self, "失败", str(e))
        finally:
            if hasattr(self, 'log_file') and not self.log_file.closed:
                self.log_file.close()