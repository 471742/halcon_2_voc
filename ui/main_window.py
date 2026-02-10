# ui/main_window.py
import os
import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QFileDialog,
    QTextEdit, QMessageBox, QProgressDialog, QFrame,QApplication
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
from core.converter import hdict_to_voc_xml, voc_xml_to_hdict


class HdictVocConverterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HDict ↔ VOC2007 XML 转换工具")
        self.resize(680, 520)
        self.setMinimumSize(680, 480)

        self.input_path = ""
        self.output_path = ""
        self.custom_image_dir = ""
        self.log_file = None
        self.current_log_path = None

        self.log_dir = "./logs"
        os.makedirs(self.log_dir, exist_ok=True)

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 标题
        title = QLabel("Halcon hdict 与 VOC XML 互转工具")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(8)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # ────────────── 配置区域 ──────────────
        config_group = QGroupBox("基本设置")
        config_group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(12)

        # 转换方向
        h_dir = QHBoxLayout()
        h_dir.addWidget(QLabel("转换方向："))
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["HDict → VOC XML", "VOC XML → HDict"])
        self.cb_mode.currentIndexChanged.connect(self._on_mode_changed)
        h_dir.addWidget(self.cb_mode)
        h_dir.addStretch()
        config_layout.addLayout(h_dir)

        # 输入
        h_in = QHBoxLayout()
        btn_in = QPushButton("选择输入")
        btn_in.setFixedWidth(120)
        btn_in.clicked.connect(self._select_input)
        h_in.addWidget(btn_in)

        self.lbl_in = QLabel("尚未选择")
        self.lbl_in.setStyleSheet("color: #555;")
        h_in.addWidget(self.lbl_in, 1)
        config_layout.addLayout(h_in)

        # 输出
        h_out = QHBoxLayout()
        btn_out = QPushButton("选择输出")
        btn_out.setFixedWidth(120)
        btn_out.clicked.connect(self._select_output)
        h_out.addWidget(btn_out)

        self.lbl_out = QLabel("尚未选择")
        self.lbl_out.setStyleSheet("color: #555;")
        h_out.addWidget(self.lbl_out, 1)
        config_layout.addLayout(h_out)

        # 自定义图片文件夹（仅 HDict→VOC 有效）
        h_img = QHBoxLayout()
        # self.lbl_img_title = QLabel("图片文件夹（可选）：")
        self.btn_img = QPushButton("选择文件夹")
        self.btn_img.setFixedWidth(120)
        self.btn_img.clicked.connect(self._select_image_dir)
        h_img.addWidget(self.btn_img)

        self.lbl_img_dir = QLabel("使用 hdict 中的 image_dir")
        self.lbl_img_dir.setStyleSheet("color: #555;")
        h_img.addWidget(self.lbl_img_dir, 1)
        config_layout.addLayout(h_img)

        layout.addWidget(config_group)

        # ────────────── 操作按钮 ──────────────
        btn_group = QHBoxLayout()
        btn_group.setSpacing(16)

        self.btn_run = QPushButton("开始转换")
        self.btn_run.setFixedHeight(48)
        self.btn_run.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1E88E5; }
            QPushButton:pressed { background-color: #1976D2; }
        """)
        self.btn_run.clicked.connect(self._run_conversion)
        btn_group.addWidget(self.btn_run)

        self.btn_open_log = QPushButton("打开日志文件夹")
        self.btn_open_log.setFixedHeight(48)
        self.btn_open_log.setEnabled(False)
        self.btn_open_log.clicked.connect(self.open_log_folder)
        btn_group.addWidget(self.btn_open_log)

        layout.addLayout(btn_group)

        # ────────────── 日志区域 ──────────────
        log_group = QGroupBox("运行日志")
        log_group.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 13px;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group, 1)

        self._on_mode_changed()

    def _on_mode_changed(self):
        is_h2v = self.cb_mode.currentIndex() == 0

        # 标题文字调整
        self.lbl_in.setText("HDict 文件：" if is_h2v else "VOC XML 文件夹：")
        self.lbl_out.setText("输出文件夹（XML）：" if is_h2v else "输出文件夹（hdict）：")

        # 关键：只在 HDict → VOC 时显示“图片文件夹”相关控件
        # self.lbl_img_title.setVisible(is_h2v)
        self.btn_img.setVisible(is_h2v)
        self.lbl_img_dir.setVisible(is_h2v)

        # 按钮文字
        self.btn_run.setText("HDict → VOC XML" if is_h2v else "VOC XML → HDict")
    
    # 如果切换到 VOC → HDict 模式，自动清空自定义路径（避免误用）
        if not is_h2v:
            self.custom_image_dir = ""
            self.lbl_img_dir.setText("使用 hdict 中的 image_dir")
            self.lbl_img_dir.setStyleSheet("color: #666;")
            self.btn_run.setText("HDict → VOC XML" if is_h2v else "VOC XML → HDict")

    def _select_input(self):
        is_h2v = self.cb_mode.currentIndex() == 0
        if is_h2v:
            path, _ = QFileDialog.getOpenFileName(self, "选择 .hdict 文件", "", "Halcon Dict (*.hdict)")
        else:
            path = QFileDialog.getExistingDirectory(self, "选择 VOC XML 文件夹")
        if path:
            self.input_path = path
            display = os.path.basename(path) if is_h2v else path
            self.lbl_in.setText(display if len(display) < 60 else "..." + display[-57:])
            self.lbl_in.setStyleSheet("color: #000; font-weight: bold;")

    def _select_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path:
            self.output_path = path
            display = path if len(path) < 60 else "..." + path[-57:]
            self.lbl_out.setText(display)
            self.lbl_out.setStyleSheet("color: #000; font-weight: bold;")

    def _select_image_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择图片文件夹（可选）", "")
        if path:
            self.custom_image_dir = path
            display = path if len(path) < 60 else "..." + path[-57:]
            self.lbl_img_dir.setText(display)
            self.lbl_img_dir.setStyleSheet("color: #000; font-weight: bold;")
            self._log(f"已指定自定义图片文件夹：{path}\n")
        else:
            self.custom_image_dir = ""
            self.lbl_img_dir.setText("使用 hdict 中的 image_dir")
            self.lbl_img_dir.setStyleSheet("color: #666;")

    def _log(self, msg: str):
        self.log_text.append(msg.rstrip())
        self.log_text.ensureCursorVisible()
        QApplication.processEvents()

        if self.log_file and not self.log_file.closed:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_file.write(f"[{timestamp}] {msg.strip()}\n")
            self.log_file.flush()

    def open_log_folder(self):
        if self.current_log_path and os.path.exists(self.log_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.log_dir))
        else:
            QMessageBox.information(self, "提示", "暂无日志文件夹或路径无效")

    def _run_conversion(self):
        if not self.input_path:
            QMessageBox.warning(self, "提示", "请选择输入路径")
            return
        if not self.output_path:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            return

        # 生成日志文件
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        mode_text = "hdict_to_voc" if self.cb_mode.currentIndex() == 0 else "voc_to_hdict"
        log_filename = f"{now}_{mode_text}.log"
        self.current_log_path = os.path.join(self.log_dir, log_filename)

        try:
            self.log_file = open(self.current_log_path, "w", encoding="utf-8")
            self.log_file.write(f"转换开始时间: {datetime.datetime.now()}\n")
            self.log_file.write(f"模式: {mode_text}\n")
            self.log_file.write(f"输入: {self.input_path}\n")
            self.log_file.write(f"输出: {self.output_path}\n")
            if self.custom_image_dir:
                self.log_file.write(f"自定义图片目录: {self.custom_image_dir}\n")
            self.log_file.write("-" * 60 + "\n\n")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建日志文件：{e}")
            return

        self.log_text.clear()
        self._log(f"日志保存至：{self.current_log_path}\n")
        self._log("开始处理...\n")

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
                    custom_image_dir=self.custom_image_dir
                )
            else:
                voc_xml_to_hdict(
                    xml_dir=self.input_path,
                    output_dir=self.output_path,
                    log_func=self._log,
                    progress=progress,
                    log_file=self.log_file,
                    custom_image_dir=self.custom_image_dir
                )

            progress.close()
            self._log("\n转换完成 ✓")
            self.log_file.write("\n转换完成\n")
            QMessageBox.information(self, "完成", f"转换完成\n日志已保存至：\n{self.current_log_path}")

        except Exception as e:
            self._log(f"\n错误：{str(e)}")
            if self.log_file:
                self.log_file.write(f"\n错误：{str(e)}\n")
            QMessageBox.critical(self, "失败", str(e))

        finally:
            if self.log_file and not self.log_file.closed:
                self.log_file.close()
                self.log_file = None