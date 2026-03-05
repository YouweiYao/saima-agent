# 风险评估Prompt模板
# 用法: from risk_prompt import RISK_SYSTEM_PROMPT, build_risk_user_prompt
# prompt原文来自: 定开工作拆解和风险评估prompt原文.py

def extract_is_product_function_matched(matched_functions) -> str:
    """
    is_product_function_matched 提取（最终规范版）

    输出值：只可能是 "是" 或 "否"

    判定铁律：
    - 只有明确等于 "是" 才返回 "是"
    - 其余所有情况（缺失 / 异常 / 不确定）一律返回 "否"
    """
    result = "否"
    if not isinstance(matched_functions, list) or not matched_functions:
        return result
    first = matched_functions[0]
    if not isinstance(first, dict):
        return result
    value = first.get("is_product_function_matched")
    if not isinstance(value, str):
        return result
    if value.strip() == "是":
        return "是"
    return result

RISK_SYSTEM_PROMPT = """你是一名具有丰富软件交付与实施经验的技术方案专家，长期负责金融、政务、工业、能源等行业的软件项目需求澄清、实施评估、交付方案设计与成本测算，同时具备丰富的售前与投标支持经验。

⚠️ 重要前提（必须遵守）：
- 客户所属行业为：金融 / 政务 / 工业 / 能源
- 在缺乏明确限制条件的情况下，必须默认按照上述行业中的「最复杂、最严格、最保守」应用场景进行评估
- 不得基于理想实施环境或最低合规要求进行乐观估算
- 若存在多种实现路径，必须选择交付成本与风险最高的合理路径作为评估依据

⚠️ 标品交付事实规则（最高优先级）：
- 是否为标品交付，只允许基于：is_product_function_matched
- 本阶段不得重新计算、修正或质疑任何产品匹配结论

⚠️ 标品交付直通约束：
- 仅当明确存在 is_product_function_matched = "是" 时，才允许判定为标品交付
- 否则一律进入【非标品交付】评估流程

你是系统评估组件，不是聊天助手。"""

def build_risk_user_prompt(req: dict, matched_result: dict) -> str:
    """
    构建风险评估的用户Prompt
    
    Args:
        req: 需求字典，包含 requirement, category, source_text, requirement_id
        matched_result: 匹配结果，包含 matched_functions, product_detail_source_text
    
    Returns:
        完整的用户Prompt字符串
    """
    source_text = req.get('source_text', '')
    requirement = req.get('requirement', '')
    category = req.get('category', '')
    requirement_id = req.get('requirement_id', 'REQ-001')
    
    matched_functions = matched_result.get('matched_functions', [])
    is_matched = extract_is_product_function_matched(matched_functions)
    product_detail_source_text = matched_result.get('product_detail_source_text', '')
    
    user_prompt = f"""【输入参数说明】
- source_text：需求原始文档，仅作背景参考
- requirement：当前评估的单条需求（评估核心，事实来源）
- product_detail_source_text：已有产品能力描述，可能为空
- is_product_function_matched：当前需求是否匹配产品功能，匹配为是，不匹配为否
- requirement_id：用户需求编号

--------------------------------
【source_text】
{source_text}

--------------------------------
【requirement（用户需求）】
{requirement}

--------------------------------
【category】
{category}

--------------------------------
【is_product_function_matched（是否匹配产品功能）】
{is_matched}

--------------------------------
【product_detail_source_text（匹配的产品功能描述原文）】
{product_detail_source_text}

--------------------------------
【requirement_id（用户需求编号，不可修改）】
{requirement_id}

--------------------------------
【处理规则（⚠️必须严格遵守）】

1️⃣ 标品交付直通规则（最高优先级）
- 若当前 requirement 的 matched_functions 中：存在 is_product_function_matched = "是"
- 则该 requirement 视为【标品交付】，必须固定返回：
  - delivery_type = "产品交付"
  - is_open_requirement = "否"
  - requirement_clarity_score = 0
  - customized_work_details = ""
  - risk_management_strategy = ""
  - reqirement_quality_level = ""
  - clarity_risk_type = ""
- 不得输出任何分析性或解释性内容

2️⃣ 仅当is_product_function_matched为"否"时，才允许执行以下评估
- 需求清晰度与风险判断
- 定制化工作与成本评估（强制保守）
- 售前阶段风险应对策略

--------------------------------
【分析与生成任务（必须全部完成后再输出 JSON）】

一、需求清晰度与风险判断
- 输出 requirement_clarity_score（0~1）
- clarity_risk_type 必须从以下枚举中选择其一：
  信息缺失 / 歧义过多 / 范围不清 / 行业隐含依赖 / 产品强依赖 / 无明显风险
- 判断规则（强制）：
  - 若需求涉及权限、审计、安全、合规、模型可控性等行业常见隐含要求但未明确说明，应优先判定为存在风险
  - 在金融 / 政务 / 能源场景下，默认存在额外合规与治理约束

二、定制化工作与成本评估（仅限非标品，强制保守）

Step 1：复杂度分级（必须给出）
- 低复杂度 / 中复杂度 / 高复杂度
强制规则：
- 涉及模型管理、模型仓库、多模型类型、模型导入或生命周期管理 → 不得低于「中复杂度」
- 涉及权限分级、审计、跨系统、合规或监管 → 优先判定为「高复杂度」

Step 2：工作内容拆分（至少包含）
- 需求澄清与方案确认（含行业合规假设）
- 设计与技术方案制定
- 开发实现
- 集成或适配
- 测试与验证（必须包含安全 / 合规场景）

Step 3：人天估算（反低估机制，必须给区间）
- 低复杂度：开发 ≥3 人天，测试 ≥1 人天
- 中复杂度：开发 ≥8 人天，测试 ≥3 人天
- 高复杂度：开发 ≥15 人天，测试 ≥5 人天
规则：
- 人天必须给 X–Y 区间，不得只给总人天
- 测试成本不得省略
- 若存在需求风险，必须单独给出风险人天
- 若估算低于下限，必须自动上调至下限

customized_work_details 输出结构（必须换行，管理层可读）：
1️⃣ Summary
- 是否定制化
- 复杂度级别
- 在金融 / 政务 / 工业 / 能源场景下的主要交付挑战

2️⃣ Work Breakdown
- 按工作类型逐条列出关键工作内容

3️⃣ Man-day Estimation
- 基础人天
  - 开发：X–Y 人天（原因）
  - 测试：X–Y 人天（原因）
- 风险人天
  - 开发：X–Y 人天（风险来源）
  - 测试：X–Y 人天（风险来源）

三、售前风险应对策略（risk_management_strategy）
- 必须采用「风险说明 → 对应应对措施」结构
- 仅限售前阶段可执行动作（客户发标至投标前）
- 条目化 + 换行
- 每条需明确：风险 → 影响 → 应对措施

--------------------------------
【输出格式（严格 JSON，仅补充 matched_functions）】
 ⚠️ 字段回写约束（强制执行）：
  - requirement_id 的值 = 输入中的 requirement_id
{{
  "requirement_id": "输入的requirement_id",
  "matched_functions": [
    {{
      "delivery_type": "string",
      "reqirement_quality_level": "string",
      "customized_work_details": "string",
      "is_open_requirement": "是或否",
      "risk_management_strategy": "string",
      "requirement_clarity_score": 0.0,
      "clarity_risk_type": "string"
    }}
  ]
}}

⚠️ 强制要求：
- 必须一次性输出完整 JSON
- 不允许 markdown / ``` / 任何解释性文字"""
    
    return user_prompt
