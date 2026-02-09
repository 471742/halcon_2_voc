# core/converter.py
import os
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    import halcon as ha
except ImportError:
    ha = None


def hdict_to_voc_xml(hdict_path: str, output_dir: str, log_func=print):
    if ha is None:
        raise RuntimeError("未找到 Halcon Python 绑定，无法读取 hdict")

    log_func(f"读取 hdict: {hdict_path}")
    
    d = ha.read_dict(hdict_path, [], [])
    
    samples = ha.get_dict_tuple(d, "samples")
    if not samples:
        raise ValueError("未找到 'samples' 字段 或 samples 为空")

    # ──────────────── 新增：读取类别名称 ────────────────
    class_names = []
    try:
        class_names = ha.get_dict_tuple(d, 'class_names')
        log_func(f"读取到 {len(class_names)} 个类别名称")
    except Exception as e:
        log_func(f"未读取到 'class_names'，将使用默认类别名: {str(e)}")
        class_names = []  # 后面会 fallback 到 class_{id}

    log_func(f"共 {len(samples)} 个样本")

    for i, sample in enumerate(samples):
        try:
            filename_list = ha.get_dict_tuple(sample, 'image_file_name')
            filename = filename_list[0] if filename_list and len(filename_list) > 0 else f"img_{i:06d}.jpg"

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

            # 图像尺寸
            width = height = 0
            try:
                w_list = ha.get_dict_tuple(sample, 'image_width')
                width = int(w_list[0]) if w_list and len(w_list) > 0 else 0
            except:
                pass
            try:
                h_list = ha.get_dict_tuple(sample, 'image_height')
                height = int(h_list[0]) if h_list and len(h_list) > 0 else 0
            except:
                pass

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
            log_func(f"样本 {i} 处理失败（{filename if 'filename' in locals() else '未知'}）：{str(e)}")
            # 异常时仍尝试生成最简 XML
            try:
                root = ET.Element("annotation")
                ET.SubElement(root, "folder").text = "VOC2007"
                ET.SubElement(root, "filename").text = filename if 'filename' in locals() else f"unknown_{i}.jpg"
                size_el = ET.SubElement(root, "size")
                ET.SubElement(size_el, "width").text = "0"
                ET.SubElement(size_el, "height").text = "0"
                ET.SubElement(size_el, "depth").text = "3"
                xml_path = os.path.join(output_dir, Path(filename).stem + ".xml" if 'filename' in locals() else f"unknown_{i}.xml")
                ET.ElementTree(root).write(xml_path, encoding="utf-8", xml_declaration=True)
                log_func(f"  → 异常后仍生成最小 XML: {os.path.basename(xml_path)}")
            except:
                pass
            continue

    log_func("hdict 转 VOC XML 完成")

    # ha.clear_dict(d)
    # ha.clear_all_dicts()


def voc_xml_to_hdict(xml_dir: str, output_dir: str, log_func=print):
    """ VOC XML 文件夹 → Halcon .hdict """
    if ha is None:
        raise RuntimeError("未找到 Halcon Python 绑定，无法生成 hdict")

    xml_files = [f for f in os.listdir(xml_dir) if f.lower().endswith(".xml")]
    if not xml_files:
        raise ValueError("文件夹中没有 .xml 文件")

    log_func(f"找到 {len(xml_files)} 个 XML 文件")

    dataset = ha.create_dict()
    samples = []
    class_set = set()

    for xml_file in sorted(xml_files):
        try:
            tree = ET.parse(os.path.join(xml_dir, xml_file))
            root = tree.getroot()

            filename = root.findtext("filename", "").strip()
            if not filename:
                continue

            size = root.find("size")
            w = int(size.findtext("width", "0"))
            h = int(size.findtext("height", "0"))

            bboxes = []
            cls_names = []

            for obj in root.findall("object"):
                name = obj.findtext("name", "").strip()
                if not name:
                    continue
                class_set.add(name)

                bb = obj.find("bndbox")
                if not bb:
                    continue

                try:
                    xmin = float(bb.findtext("xmin"))
                    ymin = float(bb.findtext("ymin"))
                    xmax = float(bb.findtext("xmax"))
                    ymax = float(bb.findtext("ymax"))
                    bboxes.append([ymin, xmin, ymax, xmax])  # row1,col1,row2,col2
                    cls_names.append(name)
                except:
                    pass

            if not bboxes:
                continue

            sample = ha.create_dict()
            ha.set_dict_tuple(sample, "image_file_name", filename)
            ha.set_dict_tuple(sample, "image_width", [w])
            ha.set_dict_tuple(sample, "image_height", [h])
            ha.set_dict_tuple(sample, "bbox", bboxes)
            ha.set_dict_tuple(sample, "class_id", cls_names)  # 暂用字符串

            samples.append(sample)
            log_func(f"解析: {xml_file}")

        except Exception as e:
            log_func(f"{xml_file} 解析失败: {e}")

    ha.set_dict_tuple(dataset, "samples", samples)
    ha.set_dict_tuple(dataset, "class_names", list(sorted(class_set)))

    out_path = os.path.join(output_dir, "dataset.hdict")
    ha.write_dict(dataset, out_path, "dict", [])
    # ha.clear_all_dicts()          # 清理所有字典（全局，慎用）
    log_func(f"生成 hdict: {out_path}")