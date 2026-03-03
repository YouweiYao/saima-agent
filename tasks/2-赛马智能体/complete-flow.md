# 赛马智能体 - 需求拆分完整流程

## 概述
赛马智能体用于对招标文件进行需求分析、拆解匹配和风险识别。

## 文件路径
- 输入：`/home/openclaw/niuniu/saima/input/`
- 输出：`/home/openclaw/niuniu/saima/output/`
- 代码：`/home/openclaw/niuniu/code/saima-agent/`
- 状态文件：`/tmp/saima_status.json`

## 完整流程（6步）

### Step 1: 读取招标文件
- 读取 `.docx` 文件
- 提取文字和表格
- 解析招标文件结构

### Step 2: 原文分段（本地分片）
- 模式1（主）：按字符数分片（500字符/块）
- 模式2（备）：按句子分片（解决截断问题）
- 使用 `--sentence` 参数切换

### Step 3: 需求拆分（LLM）
- 模型：qwen-plus（dashscope）
- 并发数：10
- 输出：JSON格式的需求列表

### Step 4: 需求匹配
- 从Excel读取需求库（千帆AB、千帆MB）
- jieba分词 + BM25召回TOP_K候选功能
- LLM评估匹配度（聚合能力判定）
- 并发处理

### Step 5: 风险评估
- 仅当匹配度 < 0.8 时触发
- 评估维度：需求清晰度、复杂度、人天估算

### Step 6: 输出Excel
- 13列字段
- 合并单元格逻辑（从左到右依次判断）

---

## 匹配Prompt（聚合能力判定版）

### 核心规则
1. **聚合匹配**：一个requirement可被多个功能共同覆盖
2. **匹配度** >= 0.8 → 是，否则否
3. **匹配度最高只展示1个**

### 输出字段
- product_name：产品名称
- product_function_level：层级路径
- product_detail_source_text：功能原文
- founction_match_level：0.00-1.00
- is_product_function_matched：是/否

---

## 风险评估Prompt（人天估算增强版）

### 触发条件
- is_product_function_matched = 否（匹配度 < 0.8）

### 评估维度
| 字段 | 说明 |
|------|------|
| delivery_type | 产品交付/定制开发 |
| is_open_requirement | 开放需求是/否 |
| requirement_clarity_score | 0-1之间的小数 |
| clarity_risk_type | 风险类型枚举 |
| customized_work_details | 结构化工作内容 |
| risk_management_strategy | 售前风险应对策略 |

### 复杂度分级
- 低：开发≥3人天，测试≥1人天
- 中：开发≥8人天，测试≥3人天
- 高：开发≥15人天，测试≥5人天

---

## 过滤规则（后处理）
不展示：
- 商务需求（采购/价格/合同/供应商提供）
- 运维/维保需求（7*24支持/问题解答）
- 验收需求（流程/审核/整改）

只展示：
- 功能性需求
- 非功能性需求
- 信创需求

---

## 重要原则（用户制定）
1. **Prompt不可修改**：匹配和风险评估的Prompt未经用户允许不允许修改
2. **LLM必须并发**：需求匹配和风险评估需并发调用

---

## 2026-03-02 工作记录

### 问题排查（上午）
- **DNS失效**：Ubuntu虚拟机DNS配置失效导致无法访问 minimax/qwen/baidu
- **解决**：重启Ubuntu虚拟机
- **症状**：Tokens (ctx %) 显示 unknown/200k，直接对话 timeout 和 llm timeout

### 问题：上下文超限
- **现象**：session 缓存达到 939%，导致超时
- **原因**：
  1. print 输出被捕获写入 session 上下文
  2. match.py 中 LLM 调用是顺序执行，不是并发

### 解决方案

#### 方案一：输出屏蔽
- 创建静默版 `saima.sh`
- 所有 python 执行重定向到 `/dev/null`
- 只保留最终 '完成' 提示

#### 方案二：并发改造
- match.py 改用 ThreadPoolExecutor
- 并发数：10 → 5（避免 dashscope 并发限制）
- 匹配和风险评估都并发执行

#### 方案三：后台执行（本次新增）
- **目标**：避免 exec 超时问题
- **实现**：
  1. `saima_background.py`：带状态更新的主脚本
  2. `start_saima.sh`：nohup 后台启动脚本
  3. `check_status.sh`：状态检查脚本
  4. `/tmp/saima_status.json`：状态文件（JSON格式）

- **状态文件格式**：
```json
{
  "status": "running/completed/error",
  "progress": "15/224",
  "current": "正在匹配需求",
  "output": "/path/to/output.xlsx"
}
```

- **使用方式**：
  - 启动：`bash start_saima.sh`
  - 查看状态：`bash check_status.sh`
  - 状态文件：`/tmp/saima_status.json`

---

## 待完成任务
1. 配置 heartbeat 轮询检查状态文件
2. 完成后自动发送文件到飞书

---

## 2026-03-02 修复记录

### 问题1：需求原文缺失
**原因**：`source_text` 获取位置错误（从 `item` 获取而非 `req`）
**修复**：从 `req.get('source_text')` 获取

### 问题2：无效需求类型调用LLM
**原因**：需求拆分后没有过滤
**修复**：过滤掉商务需求、运维/维保需求、验收需求

### 问题3：状态监控不完整
**原因**：只显示"匹配"状态
**修复**：显示完整3阶段（需求拆分→功能匹配→交付风险评估）

### 问题4：层级格式不完整
**原因**：get_caps函数没有处理空值继承
**修复**：添加层级继承逻辑，跳过空值和"-"

### 问题5：合并单元格逻辑
**原因**：没有实现
**修复**：从左到右依次判断（前面所有列都相同才合并）

### 问题6：Prompt过于简化
**原因**：saima_background.py的prompt缺少source_text
**修复**：使用match.py的完整prompt

### 执行统计（2026-03-02）
- 原始需求：224条
- 过滤后：145条
- LLM调用：301次
- 耗时：9.9分钟
