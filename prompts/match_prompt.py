# 功能匹配Prompt模板
# 用法: from match_prompt import MATCH_SYSTEM_PROMPT, build_match_user_prompt
# prompt原文来自: 功能匹配prompt原文.py

MATCH_SYSTEM_PROMPT = """你是一名专业的软件产品功能匹配分析助手。

你的职责是：基于给定的【用户需求】与【候选产品功能列表】，判断这些功能是否可以满足该需求，并给出结构化、可审计的判断结果。

你必须遵守以下原则：
- 只能基于输入的候选产品功能进行判断
- 不得编造、假设或引入任何未在候选功能中出现的能力
- 判断应保持克制、保守和工程视角
- 若证据不足，应明确给出无法匹配的结论

你是一个系统组件，不是聊天助手。"""

def build_match_user_prompt(req: dict, features: list, threshold: float = 0.8, requirement_id: str = "REQ-001", product_guide_reference: str = "") -> str:
    """
    构建功能匹配的用户Prompt
    
    Args:
        req: 需求字典，包含 requirement, category, source_text
        features: 候选功能列表，每个元素包含 path 和 desc
        threshold: 匹配阈值，默认0.8
        requirement_id: 需求ID
        product_guide_reference: 产品手册参考材料（可选）
    
    Returns:
        完整的用户Prompt字符串
    """
    # 原文只用desc，不用path
    features_str = "\n\n".join(
        f"【候选功能 {i + 1}】\n{f['desc']}"
        for i, f in enumerate(features)
        if isinstance(f, dict) and f.get('desc', '').strip()
    )
    
    user_prompt = f"""请根据以下输入信息，完成一次【需求与产品功能匹配判断】

【一、输入数据（事实来源）】
- source_text：整体需求背景，仅用于理解语义
- requirement：当前评估的用户需求（评估核心）
- category：需求类型，必须原样回写
- features：候选产品功能全集（唯一能力来源）
- product_guide_reference：产品帮助手册/说明文档参考材料（仅辅助理解）
- product_match_threshold：产品匹配硬阈值

--------------------------------
【source_text】
{req.get('source_text', '')}

【requirement】
{req['requirement']}

【category】
{req['category']}

【requirement_id】
{requirement_id}

【features（候选功能全集）】
{features_str}

【product_guide_reference（产品手册参考材料）】
{product_guide_reference if product_guide_reference else '(无)'}


【匹配阈值（硬约束）】
- product_match_threshold = {threshold}

--------------------------------
【二、能力判断边界（必须遵守）】
- features 是唯一允许用于"能力是否存在"的判断依据
- product_guide_reference 仅用于：
  - 帮助理解产品术语、模块背景、功能语义
  - 辅助理解 features 中功能描述的含义
- 禁止仅基于 product_guide_reference 判定功能存在或匹配成立

--------------------------------
【三、功能匹配与评分规则（强制执行）】

1️⃣ 聚合匹配原则
- 一个 requirement 允许被多个候选功能点共同覆盖
- 你需要从 features 中筛选所有与 requirement 语义直接相关的功能点
- 这些功能点共同构成"产品整体能力覆盖结果"

- requirement_id 禁止修改
- requirement_id / requirement / category 原样回写

2️⃣ founction_match_level 定义
- 表示：候选功能集合对需求语义要点的整体覆盖程度
- 取值范围：[0.00, 1.00]
- 类型：字符串
- 覆盖越全面，评分越高；无法覆盖时为 "0"

3️⃣ is_product_function_matched 判定规则
- founction_match_level ≥ {threshold} → is_product_function_matched = "是"
- 否则 → "否"

--------------------------------
【四、matched_functions 输出规则（⚠️核心约束）】

- matched_functions 必须且只能输出 1 个对象
- 该对象表示"单一产品的聚合能力匹配结果"，而非单条功能命中

【字段填充规则】
- product_name：
  - 从命中的 features 中提取产品名称
  - 去重后使用 \\n 进行拼接

⚠️ product_function_level 字段强制规范：
- product_function_level 必须由候选功能中实际存在的层级名称拼接得到
  - 层级来源仅限 features 中明确给出的 L1 / L2 / L3 / L4
  - 允许多条功能路径
  - 多条路径之间使用 \\n 分隔
  - 允许缺失层级（例如只有 L1、L1>L2 或 L1>L2>L3），缺失直接删掉不要拼接-
  - 不允许跳级（例如 L1>L3）
  - 固定使用符号 ">" 作为唯一层级分隔符

- product_detail_source_text：
  - 汇总所有与 requirement 直接相关的 features 功能描述纯文本
  - 多条内容使用 \\n 分隔

--------------------------------
【五、未匹配兜底规则（必须执行）】
- 若没有任何 feature 能覆盖 requirement 语义要点：
  - product_name = "未匹配到产品"
  - product_function_level = ""
  - product_detail_source_text = ""
  - founction_match_level = "0"
  - is_product_function_matched = "否"

--------------------------------
【六、最终输出格式（严格 JSON，不得新增字段）】
 ⚠️ 字段回写约束（强制执行）：
- requirement_id 的值 = 输入中的 requirement_id
- requirement 的值 = 输入中的 requirement
- category 的值 = 输入中的 category
- 不允许为空、不允许重写、不允许生成新值

{{
  "requirement_id": "输入的requirement_id",
  "requirement": "string",
  "category": "string",
  "matched_functions": [
    {{
      "product_name": "string",
      "product_function_level": "string",
      "product_detail_source_text": "string",
      "founction_match_level": "string",
      "is_product_function_matched": "是或否"
    }}
  ]
}}

⚠️ 强制要求：
- 必须一次性输出完整 JSON
- 不允许 markdown、```、解释性文字或额外说明"""
    
    return user_prompt
