# core/converter.py
import os
from PIL import Image
from pathlib import Path
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QApplication
)
try:
    import halcon as ha
except ImportError:
    ha = None


def hdict_to_voc_xml(hdict_path: str, output_dir: str, log_func=print, progress=None, log_file=None,custom_image_dir=""):
    if ha is None:
        raise RuntimeError("未找到 Halcon Python 绑定，无法读取 hdict")

    log_func(f"读取 hdict: {hdict_path}")
    
    d = ha.read_dict(hdict_path, [], [])
    
    samples = ha.get_dict_tuple(d, "samples")
    if not samples:
        raise ValueError("未找到 'samples' 字段 或 samples 为空")
    
    image_dir = custom_image_dir.strip()
    if image_dir and os.path.isdir(image_dir):
        log_func(f"使用用户指定的图片文件夹：{image_dir}")
    else:
        try:
            image_dir_list = ha.get_dict_tuple(d, 'image_dir')
            image_dir = image_dir_list[0] if image_dir_list else ""
            log_func(f"使用 hdict 中的 image_dir：{image_dir}")
        except:
            image_dir = ""
            log_func("未读取到 image_dir，将尝试使用相对路径或跳过图像尺寸读取")

    if image_dir and not os.path.isabs(image_dir):
        log_func("警告：image_dir 是相对路径，可能导致拼接失败")

    # 获取类别名称
    class_names = []
    try:
        class_names = ha.get_dict_tuple(d, 'class_names')
        log_func(f"读取到 {len(class_names)} 个类别名称")
    except:
        log_func("未读取到 'class_names'，使用默认类别名")
        class_names = []
    
    total = len(samples)
    log_func(f"共 {total} 个样本")

    # 初始化进度条
    if progress:
        progress.setRange(0, total)
        progress.setValue(0)
        progress.setLabelText("正在处理样本...")

    for i, sample in enumerate(samples):
        # 检查用户是否点击了取消
        if progress and progress.wasCanceled():
            log_func("用户取消了转换")
            raise Exception("用户取消操作")
        try:
            filename_list = ha.get_dict_tuple(sample, 'image_file_name')
            filename = filename_list[0] if filename_list and len(filename_list) > 0 else f"img_{i:06d}.jpg"
            
            # 拼接完整路径
            full_image_path = ""
            if image_dir:
                full_image_path = os.path.join(image_dir, filename)
            else:
                full_image_path = filename  # 如果都没有，就直接用 filename（可能已经是绝对路径）

            # 边界框坐标（四个键分开存储）
            row1_list = col1_list = row2_list = col2_list = label_id_list = []
            has_bbox = False

            try:
                row1_list = ha.get_dict_tuple(sample, 'bbox_row1')
                col1_list = ha.get_dict_tuple(sample, 'bbox_col1')
                row2_list = ha.get_dict_tuple(sample, 'bbox_row2')
                col2_list = ha.get_dict_tuple(sample, 'bbox_col2')
                label_id_list = ha.get_dict_tuple(sample, 'bbox_label_id')
                has_bbox = True
            except:
                log_func(f"样本 {i} 缺少 bbox 信息（{filename}），将生成空标注 XML")

            # bbox 长度处理
            num_boxes = 0
            if has_bbox and len(row1_list) > 0:
                num_boxes = len(row1_list)
                if not (len(col1_list) == num_boxes and len(row2_list) == num_boxes and len(col2_list) == num_boxes):
                    log_func(f"样本 {i} bbox 坐标长度不一致，只处理有效部分")
                    num_boxes = min(len(row1_list), len(col1_list), len(row2_list), len(col2_list))

            # 获取图像宽高
            width = 0
            height = 0
            if os.path.exists(full_image_path) and os.path.isfile(full_image_path):
                try:
                    with Image.open(full_image_path) as img:
                        width, height = img.size
                    log_func(f"从图像文件读取尺寸: {filename} → {width}x{height}")
                except Exception as e:
                    log_func(f"读取图像失败 {filename}: {str(e)}，使用默认尺寸 0x0")
            else:
                log_func(f"图像文件不存在: {full_image_path}，使用默认尺寸 0x0")

            # 开始构建 XML
            root = ET.Element("annotation")
            ET.SubElement(root, "folder").text = "VOC2007"
            ET.SubElement(root, "filename").text = filename

            size_el = ET.SubElement(root, "size")
            ET.SubElement(size_el, "width").text = str(width)
            ET.SubElement(size_el, "height").text = str(height)
            ET.SubElement(size_el, "depth").text = "3"

            # 添加 object（如果有 bbox）
            if has_bbox and num_boxes > 0:
                for j in range(num_boxes):
                    row1 = row1_list[j]
                    col1 = col1_list[j]
                    row2 = row2_list[j]
                    col2 = col2_list[j]

                    label_id = label_id_list[j] if j < len(label_id_list) else 0
                    
                    # ──────────────── 关键修改：使用真实的类别名 ────────────────
                    if label_id < len(class_names):
                        class_name = class_names[label_id]
                    else:
                        class_name = f"unknown_class_{label_id}"

                    obj = ET.SubElement(root, "object")
                    ET.SubElement(obj, "name").text = class_name
                    ET.SubElement(obj, "pose").text = "Unspecified"
                    ET.SubElement(obj, "truncated").text = "0"
                    ET.SubElement(obj, "difficult").text = "0"

                    bb = ET.SubElement(obj, "bndbox")
                    ET.SubElement(bb, "xmin").text = str(int(col1))
                    ET.SubElement(bb, "ymin").text = str(int(row1))
                    ET.SubElement(bb, "xmax").text = str(int(col2))
                    ET.SubElement(bb, "ymax").text = str(int(row2))

            # 保存（无论是否有 object 都保存）
            xml_path = os.path.join(output_dir, Path(filename).stem + ".xml")
            ET.ElementTree(root).write(xml_path, encoding="utf-8", xml_declaration=True)
            log_func(f"生成: {os.path.basename(xml_path)} （{'有' if num_boxes > 0 else '无'}标注，{num_boxes} 个框）")

        except Exception as e:
            log_func(f"样本 {i} 处理失败: {str(e)}")
        
        # 更新进度
        if progress:
            progress.setValue(i + 1)
            progress.setLabelText(f"正在处理样本 {i+1}/{total} ({filename})")
            QApplication.processEvents()   # 重要：让 UI 响应

    if progress:
        progress.setValue(total)
        progress.setLabelText("转换完成")

    log_func("hdict 转 VOC XML 完成")

    # ha.clear_dict(d)
    # ha.clear_all_dicts()


def voc_xml_to_hdict(
    xml_dir: str,
    output_dir: str,
    log_func=print,
    progress=None,
    log_file=None,
    custom_image_dir=""
):
    if ha is None:
        raise RuntimeError("未找到 Halcon Python 绑定，无法生成 hdict")

    xml_files = sorted([f for f in os.listdir(xml_dir) if f.lower().endswith('.xml')])
    if not xml_files:
        raise ValueError("选择的文件夹中没有 .xml 文件")

    total = len(xml_files)
    log_func(f"找到 {total} 个 XML 文件")

    if progress:
        progress.setRange(0, total)
        progress.setValue(0)
        progress.setLabelText("正在处理 XML...")

    # 确定 image_dir
    image_dir = custom_image_dir.strip()
    if image_dir and os.path.isdir(image_dir):
        log_func(f"使用用户指定的图片文件夹: {image_dir}")
    else:
        image_dir = xml_dir  # 默认使用 XML 目录作为 image_dir
        log_func(f"使用默认图片文件夹: {image_dir}")

    # 创建根字典
    dataset = ha.create_dict()

   # 使用列表保持首次出现顺序 + 映射表保证一致性
    class_names_ordered = []           # 按首次出现顺序保存名称
    class_name_to_id = {}              # name → id 的映射

    samples = []

    for idx, xml_file in enumerate(xml_files):
        if progress and progress.wasCanceled():
            log_func("用户取消了转换")
            raise Exception("用户取消操作")

        try:
            tree = ET.parse(os.path.join(xml_dir, xml_file))
            root = tree.getroot()

            # 修改点：直接从 XML 文件名获取图像文件名，默认 .jpg
            xml_stem = os.path.splitext(xml_file)[0]  # 去掉 .xml 后缀
            filename = f"{xml_stem}.jpg"

            # 可选：记录原始 XML 里的 filename（用于调试对比）
            original_filename_in_xml = root.findtext("filename", "").strip()
            if original_filename_in_xml and original_filename_in_xml != filename:
                log_func(f"警告：{xml_file} 内 filename 为 {original_filename_in_xml}，但使用 XML 文件名 {filename}")

            size = root.find("size")
            width = int(size.findtext("width", "0")) if size else 0
            height = int(size.findtext("height", "0")) if size else 0

            row1_list = []
            col1_list = []
            row2_list = []
            col2_list = []
            label_id_list = []

            for obj in root.findall("object"):
                name = obj.findtext("name", "").strip()
                if not name:
                    continue

                # 如果是新类别，添加到有序列表，并分配 ID
                if name not in class_name_to_id:
                    new_id = len(class_names_ordered)
                    class_names_ordered.append(name)
                    class_name_to_id[name] = new_id

                # 获取 bbox
                bb = obj.find("bndbox")
                if bb is None:
                    continue

                try:
                    xmin = float(bb.findtext("xmin", 0))
                    ymin = float(bb.findtext("ymin", 0))
                    xmax = float(bb.findtext("xmax", 0))
                    ymax = float(bb.findtext("ymax", 0))
                except:
                    continue

                row1_list.append(ymin)
                col1_list.append(xmin)
                row2_list.append(ymax)
                col2_list.append(xmax)
                label_id_list.append(class_name_to_id[name])

            # 创建 sample 字典
            sample = ha.create_dict()
            ha.set_dict_tuple(sample, 'image_file_name', [filename])
            ha.set_dict_tuple(sample, 'image_width', [width])
            ha.set_dict_tuple(sample, 'image_height', [height])

            if row1_list:
                ha.set_dict_tuple(sample, 'bbox_row1', row1_list)
                ha.set_dict_tuple(sample, 'bbox_col1', col1_list)
                ha.set_dict_tuple(sample, 'bbox_row2', row2_list)
                ha.set_dict_tuple(sample, 'bbox_col2', col2_list)
                ha.set_dict_tuple(sample, 'bbox_label_id', label_id_list)

            samples.append(sample)

            log_func(f"解析 {xml_file}: {filename} ({len(row1_list)} 个框)")

        except Exception as e:
            log_func(f"解析失败 {xml_file}: {str(e)}")
            continue

        if progress:
            progress.setValue(idx + 1)
            progress.setLabelText(f"正在处理 XML {idx+1}/{total}")
            QApplication.processEvents()

    # 设置根字典
    ha.set_dict_tuple(dataset, 'samples', samples)
    ha.set_dict_tuple(dataset, 'image_dir', [image_dir])

    # 关键：使用首次出现顺序的 class_names
    ha.set_dict_tuple(dataset, 'class_names', class_names_ordered)
    
    # class_ids 可以是 0 到 n-1
    ha.set_dict_tuple(dataset, 'class_ids', list(range(len(class_names_ordered))))

    # 保存
    out_file = os.path.join(output_dir, "dataset.hdict")
    ha.write_dict(dataset, out_file, [], [])
    log_func(f"生成 hdict: {out_file}")
    
    # 调试输出：验证对应关系
    log_func("生成的 class_names（按首次出现顺序）：")
    for i, name in enumerate(class_names_ordered):
        log_func(f"  ID {i}: {name}")

    if progress:
        progress.setValue(total)
        progress.setLabelText("转换完成")