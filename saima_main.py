#!/usr/bin/env python3
MAX_RETRIES = 3
"""赛马智能体 - 需求管理系统（并发版）"""

import sys
import json
import time
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from docx import Document

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
API_KEY = "sk-3d96ade0c8fa40378a4560fdd43b067e"
MODEL = "qwen-plus"
MAX_WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 15  # 默认15

# 分片模式选择: "chunk"=按字符数分片, "sentence"=按句子分片
SPLIT_MODE = "chunk"

def read_word_doc(file_path: str) -> List[str]:
    """读取Word文档，返回段落和表格内容列表"""
    doc = Document(file_path)
    paragraphs = []
    
    # 读取段落
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraphs.append(text)
    
    # 读取表格（新增）
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join([cell.text.strip() for cell in row.cells])
            if row_text.strip():
                paragraphs.append(row_text)
    
    return paragraphs

def split_texts(paragraphs: List[str], max_chars: int = 500) -> List[str]:
    """按字符数分片（主方案）
    
    将段落组合成指定大小的chunks
    优点：简单快速
    缺点：可能截断句子，导致LLM误解（详见issue #1）
    """
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += p + "\n"
        else:
            if current:
                chunks.append(current)
            current = p + "\n"
    if current:
        chunks.append(current)
    return chunks


def split_by_sentences(paragraphs: List[str]) -> List[str]:
    """按句子级别分片（备用方案）
    
    解决长段落被截断导致LLM误解的问题
    按句号、问号、感叹号、分号分割，确保语义完整
    
    问题记录 (2026-03-02):
    - 原文："大模型知识库应具有但不限于以下功能："
    - 被拆分到不同chunk，导致LLM补全了不存在的需求
    - 解决：按句子边界分割，保持语义完整
    """
    sentence_pattern = re.compile(r'([^。！？；\n]+[。！？；])')
    
    chunks = []
    current = ""
    
    for p in paragraphs:
        sentences = sentence_pattern.findall(p)
        
        for sent in sentences:
            if len(current) + len(sent) < 500:
                current += sent
            else:
                if current:
                    chunks.append(current.strip())
                current = sent
        
        # 处理剩余内容
        remaining = sentence_pattern.sub('', p)
        if remaining and len(current) + len(remaining) < 500:
            current += remaining
        elif remaining:
            if current:
                chunks.append(current.strip())
            current = remaining
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks


def call_llm(text: str) -> Dict:
    """调用LLM（带重试机制）"""
    for attempt in range(MAX_RETRIES):
        try:
    """调用LLM"""
    prompt = """你是一位专业的标书需求分析师。

分类规则：
1. 功能性需求：技术功能、模块、能力、系统本身应该具备的功能
2. 非功能性需求：性能、安全、部署、代码采纳率、问答准确率（产品本身的要求）
3. 商务需求：采购、价格、合同、对供应商的要求（投标、验收阶段）、供应商须提供、保密、泄密、知识产权、代码采纳率案例、问答准确率案例、人员要求（项目经理、核心人员经验）、驻场实施、配合接口调试、接受监理、培训、知识转移、试运行期、维保期、项目验收
4. 运维/维保需求：7*24支持、问题解答、维保服务、培训、操作手册、技术文档、源代码交付、系统运维、日常维护
5. 验收需求：验收流程、审核、整改
6. 信创需求：国产化、自主可控

需求点拆分规则：
- 一个需求点表达一个完整且独立的核心要求
- 将不同类别的混合描述拆为多个独立需求点
- **不要做摘要，要拆分细化每个需求点**

输出格式：{"requirements":[{"requirement":"需求描述","category":"分类"}]}
只输出JSON！"""

    try:
            response = requests.post(
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"LLM调用失败: {e}")
    return None
            f"{BASE_URL}",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": f"{prompt}\n\n{text}"}],
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            return json.loads(content)
    except Exception as e:
        print(f"  调用错误: {e}")
    
    return None

def process_chunk_concurrent(chunk: str, idx: int, total: int) -> Dict:
    """处理单个chunk"""
    print(f"  处理 {idx+1}/{total}...")
    result = call_llm(chunk)
    if result:
        return {
            "source_text": chunk,
            "requirements": result.get("requirements", [])
        }
    return {
        "source_text": chunk,
        "requirements": [],
        "error": "调用失败"
    }

def process_requirements_concurrent(chunks: List[str]) -> List[Dict]:
    """并发处理所有分片"""
    results = []
    total = len(chunks)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_chunk_concurrent, chunk, i, total): i 
                   for i, chunk in enumerate(chunks)}
        
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
    
    # 按顺序排序
    results.sort(key=lambda x: chunks.index(x.get('source_text', '')) if x.get('source_text', '') in chunks else 0)
    return results

def main():
    global SPLIT_MODE
    
    if len(sys.argv) < 2:
        print("用法: python3 saima_main.py <word文件> [--sentence]")
        print("  --sentence: 使用句子分片（备用方案）")
        sys.exit(1)
    
    word_file = sys.argv[1]
    
    # 检查是否使用备用方案
    if len(sys.argv) > 2 and sys.argv[2] == "--sentence":
        SPLIT_MODE = "sentence"
    
    print("=" * 60)
    print("赛马智能体 - 需求管理系统（并发版）")
    print(f"模型: {MODEL}")
    print(f"并发数: {MAX_WORKERS}")
    print(f"分片模式: {'句子分片(备用)' if SPLIT_MODE == 'sentence' else '字符分片(主方案)'}")
    print("=" * 60)
    print()
    
    # 步骤1: 读取Word
    t0 = time.time()
    print("=== 步骤1: 读取Word文档 ===")
    texts = read_word_doc(word_file)
    t1 = time.time()
    print(f"✅ 段落数: {len(texts)}, 耗时: {t1-t0:.2f}秒")
    print()
    
    # 步骤2: 分片
    t0 = time.time()
    print("=== 步骤2: 文本分片 ===")
    if SPLIT_MODE == "sentence":
        chunks = split_by_sentences(texts)
    else:
        chunks = split_texts(texts, 500)
    t1 = time.time()
    print(f"✅ 分片数: {len(chunks)}, 耗时: {t1-t0:.2f}秒")
    print()
    
    # 步骤3: 大模型处理（并发）
    t0 = time.time()
    print("=== 步骤3: 大模型需求转化（并发）===")
    results = process_requirements_concurrent(chunks)
    t1 = time.time()
    print(f"✅ 处理完成, 耗时: {t1-t0:.2f}秒")
    print()
    
    # 步骤4: 统计
    total_reqs = sum(len(r.get('requirements', [])) for r in results)
    print(f"总需求数: {total_reqs}")
    
    # 输出JSON
    output = []
    for r in results:
        for req in r.get('requirements', []):
            output.append({
                "source_text": r.get('source_text', ''),
                "requirement": req.get('requirement', ''),
                "category": req.get('category', '')
            })
    
    with open('/home/openclaw/niuniu/saima/output/需求拆分_result.json', 'w', encoding='utf-8') as f:
        json.dump({"results": output}, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: /home/openclaw/niuniu/saima/output/需求拆分_result.json")

if __name__ == "__main__":
    main()
