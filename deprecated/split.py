# 定义一个 main 函数，传入 params 参数。params 中包含了节点配置的输入变量。
# 需要定义一个字典作为输出变量
# 引用节点定义的变量：params['变量名']
# 运行环境 Python3；预置 Package：NumPy
import json
import math
import re
from typing import List, Dict, Any, Tuple

def main(params):
    """
    处理传入的参数，按照mergeMaxNumber和段落类型结合的方式分片
    
    Args:
        params: 包含输入参数的字典，通常包含：
            - file_texts: JSON格式的文件文本内容
            - mergeMaxNumber: 合并的最大字符数
    
    Returns:
        dict: 包含处理结果的字典，格式为 {"line_texts":[{"source_text":"合并后的字符串"}]}
    """
    try:
        # 检查必要的参数是否存在
        if 'file_texts' not in params:
            return {
                "line_texts": [{"source_text": "错误：缺少 file_texts 参数"}],
                "error": "missing_parameter"
            }
        
        # 获取 mergeMaxNumber 参数
        if 'mergeMaxNumber' not in params:
            return {
                "line_texts": [{"source_text": "错误：缺少 mergeMaxNumber 参数"}],
                "error": "missing_parameter"
            }
        
        merge_max_number = int(params['mergeMaxNumber'])
        if merge_max_number < 1:
            merge_max_number = 1000  # 设置默认值
            print(f"mergeMaxNumber 参数无效，使用默认值: {merge_max_number}")
        
        # 解析JSON数据
        data = json.loads(params['file_texts'])
        
        # 提取内容
        files = data.get("files", [])
        if not files:
            print("没有找到文件内容")
            return {"line_texts": [{"source_text": ""}]}
        
        # 提取文档内容
        document_content = files[0].get("content", {})
        paragraphs = document_content.get("paragraphs", [])
        
        print(f"段落总数: {len(paragraphs)}")
        print(f"mergeMaxNumber: {merge_max_number}")
        
        # 存储合并后的文本片段
        merged_texts = []
        current_fragment = ""
        current_fragment_length = 0
        
        # 遍历所有段落
        for i, para in enumerate(paragraphs):
            para_type = para.get("type", "text")
            # 过滤掉页眉和页脚
            if para_type in ["head_tail", "pageFooter", "pageNumbers"]:
                continue
            
            # 处理表格类型段落
            if para_type == "table":
                # 先处理当前积累的文本片段（如果有的话）
                if current_fragment:
                    # 清理和转换当前片段
                    cleaned_fragment = clean_and_convert_text(current_fragment)
                    if cleaned_fragment:
                        merged_texts.append({"source_text": cleaned_fragment})
                    current_fragment = ""
                    current_fragment_length = 0
                
                # 处理表格
                table_text = extract_table_text(para)
                table_text_length = len(table_text)
                
                # 规则3: 表格独自成一段，不与其他段落合并
                # 规则4: 如果表格内容长度大于mergeMaxNumber，进行切分
                if table_text_length <= merge_max_number:
                    # 表格内容不超过限制，直接作为一个片段
                    cleaned_table_text = clean_and_convert_text(table_text)
                    if cleaned_table_text:
                        merged_texts.append({"source_text": cleaned_table_text})
                else:
                    # 表格内容超过限制，需要切分
                    table_fragments = split_long_text(table_text, merge_max_number)
                    for fragment in table_fragments:
                        cleaned_fragment = clean_and_convert_text(fragment)
                        if cleaned_fragment:
                            merged_texts.append({"source_text": cleaned_fragment})
            
            # 处理文本类型段落
            else:
                text = extract_text_from_paragraph(para)
                if not text:
                    continue
                    
                text_length = len(text)
                
                # 如果当前片段为空，开始新的片段
                if current_fragment_length == 0:
                    current_fragment = text
                    current_fragment_length = text_length
                    continue
                
                # 检查是否应该与当前片段合并
                should_merge = True
                
                # 规则2: 如果当前字符串长度不够mergeMaxNumber，但是后面的字符串长度自身大于mergeMaxNumber，则不继续拼接
                if text_length > merge_max_number:
                    should_merge = False
                
                # 检查合并后的长度是否超过限制
                if current_fragment_length + text_length + 1 > merge_max_number:  # +1 为换行符
                    should_merge = False
                
                # 如果应该合并
                if should_merge:
                    current_fragment += "\n" + text
                    current_fragment_length += text_length + 1
                else:
                    # 保存当前片段
                    if current_fragment:
                        cleaned_fragment = clean_and_convert_text(current_fragment)
                        if cleaned_fragment:
                            merged_texts.append({"source_text": cleaned_fragment})
                    
                    # 处理当前文本
                    if text_length <= merge_max_number:
                        # 文本长度不超过限制，开始新的片段
                        current_fragment = text
                        current_fragment_length = text_length
                    else:
                        # 文本长度超过限制，需要切分
                        current_fragment = ""
                        current_fragment_length = 0
                        text_fragments = split_long_text(text, merge_max_number)
                        for fragment in text_fragments:
                            cleaned_fragment = clean_and_convert_text(fragment)
                            if cleaned_fragment:
                                merged_texts.append({"source_text": cleaned_fragment})
        
        # 处理最后一个片段
        if current_fragment:
            cleaned_fragment = clean_and_convert_text(current_fragment)
            if cleaned_fragment:
                merged_texts.append({"source_text": cleaned_fragment})
        
        # 如果没有提取到任何文本，返回一个空字符串的对象
        if not merged_texts:
            merged_texts = [{"source_text": ""}]
        
        print(f"生成的文本片段数量: {len(merged_texts)}")
        dict_line_texts = {"line_texts": merged_texts}
        # 创建输出字典
        output_object = {
            "line_texts": merged_texts,
        }
        
    except json.JSONDecodeError as e:
        error_msg = f"JSON解析错误: {str(e)}"
        print(error_msg)
        return {
            "line_texts": [{"source_text": error_msg}],
            "error": "json_decode_error"
        }
    except KeyError as e:
        error_msg = f"缺少必要的键: {str(e)}"
        print(error_msg)
        return {
            "line_texts": [{"source_text": error_msg}],
            "error": "missing_key"
        }
    except Exception as e:
        error_msg = f"处理过程中发生错误: {str(e)}"
        print(error_msg)
        return {
            "line_texts": [{"source_text": error_msg}],
            "error": "processing_error"
        }
    
    # 返回输出字典类型变量 output_object，包含代码节点所需的输出数据
    return output_object


def clean_and_convert_text(text: str) -> str:
    """
    清理文本中的特殊字符，并将换行符替换为分号
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理和转换后的文本
    """
    if not text:
        return ""
    
    # 首先处理转义字符
    text = text.replace("\\\\n", " ").replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
    
    # 移除控制字符（ASCII码小于32的字符，除了换行、回车、制表符）
    # 先保留换行符以便后续处理
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', text)
    
    # 将各种换行符统一转换为标准换行符
    text = re.sub(r'\r\n|\r|\n', '\n', text)
    
    # 移除过多的空白字符
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 将多个连续的换行符合并为一个
    text = re.sub(r'\n+', '\n', text)
    
    # 将换行符替换为分号（注意保留有意义的分隔）
    lines = text.strip().split('\n')
    
    # 清理每一行
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # 移除行首行尾的特殊字符
            line = re.sub(r'^[^\w\u4e00-\u9fa5]+|[^\w\u4e00-\u9fa5]+$', '', line)
            if line:
                cleaned_lines.append(line)
    
    # 用分号连接清理后的行
    result = '; '.join(cleaned_lines)
    
    # 清理多余的分号和空格
    result = re.sub(r';+', ';', result)
    result = re.sub(r' ;', ';', result)
    result = re.sub(r'; ', ';', result)
    
    # 移除首尾的分号和空格
    result = result.strip('; ')
    
    return result


def extract_table_text(paragraph: Dict) -> str:
    """
    从表格段落中提取文本
    
    Args:
        paragraph: 表格段落
        
    Returns:
        str: 表格的文本表示
    """
    table_content = paragraph.get("table", {})
    cells = table_content.get("cells", [])
    matrix = table_content.get("matrix", [])
    
    table_lines = []
    
    # 按行组织表格数据
    for row in matrix:
        row_cells = []
        for cell_idx in row:
            if isinstance(cell_idx, int) and cell_idx < len(cells):
                cell = cells[cell_idx]
                cell_text = cell.get("text", "")
                # 清理文本
                if cell_text:
                    # 替换转义字符
                    cell_text = cell_text.replace("\\\\n", " ").replace("\\n", " ").strip()
                    if cell_text:
                        row_cells.append(cell_text)
        if row_cells:
            # 使用短横线连接单元格内容
            row_text = " | ".join(row_cells)
            table_lines.append(row_text)
    
    # 如果有表头，可以添加分隔线
    if table_lines:
        # 在表格前后添加空行，使其更清晰
        return "\n" + "\n".join(table_lines) + ""
    
    return ""


def extract_text_from_paragraph(paragraph: Dict) -> str:
    """
    从文本段落中提取文本
    
    Args:
        paragraph: 文本段落
        
    Returns:
        str: 提取的文本
    """
    text = paragraph.get("text", "")
    if text:
        # 清理文本中的基本转义字符
        text = text.replace("\\n", "\n").strip()
        # 去除多余的空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return "\n".join(lines)
    return ""


def split_long_text(text: str, max_length: int) -> List[str]:
    """
    将长文本分割成多个不超过最大长度的片段
    
    Args:
        text: 要分割的文本
        max_length: 每个片段的最大长度
        
    Returns:
        List[str]: 分割后的文本片段列表
    """
    if len(text) <= max_length:
        return [text]
    
    fragments = []
    start_index = 0
    
    while start_index < len(text):
        # 计算结束位置
        end_index = start_index + max_length
        
        # 如果还有更多文本，尝试在句子边界分割
        if end_index < len(text):
            # 查找最近的分隔符
            last_semicolon = text.rfind(';', start_index, end_index)
            last_period = text.rfind('.', start_index, end_index)
            last_newline = text.rfind('\n', start_index, end_index)
            last_comma = text.rfind(',', start_index, end_index)
            
            # 优先在分号处分割，其次在句号、换行、逗号处分割
            if last_semicolon > start_index + 100:  # 确保至少有100个字符
                end_index = last_semicolon + 1
            elif last_period > start_index + 100:
                end_index = last_period + 1
            elif last_newline > start_index + 50:
                end_index = last_newline + 1
            elif last_comma > start_index + 50:
                end_index = last_comma + 1
        
        # 提取片段
        fragment = text[start_index:end_index].strip()
        if fragment:
            fragments.append(fragment)
        
        # 移动到下一个片段
        start_index = end_index
    
    return fragments
