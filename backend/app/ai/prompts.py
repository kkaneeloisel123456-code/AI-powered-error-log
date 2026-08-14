"""AI 提示词模板（PRD 8.6：拆题/归档/变体/批改/答疑）。"""

SPLIT_PROMPT = """你是错题整理助手。下面是 OCR 识别出的题目图片文字（可能含多道题）。
请将每道题拆分为结构化 JSON 数组，严格输出如下格式：
[
  {
    "question_text": "题干全文（不含选项）",
    "options": ["A...", "B...", "C...", "D..."],
    "answer": "正确答案（字母或数值，未给出则为空字符串）",
    "analysis": "解析（图片中无解析则给出简要解题思路）",
    "knowledge_point": "该题知识点名称",
    "confidence": {"question_text": 0.0-1.0, "answer": 0.0-1.0, "analysis": 0.0-1.0}
  }
]
要求：只输出 JSON；多题各自成对象；置信度表示 OCR/理解把握程度。
OCR 文本：
"""

CLASSIFY_PROMPT = """你是错题归档助手。根据题干与答案，输出 JSON：
{"subject": "学科名", "knowledge_point": "知识点名", "error_type": "knowledge|logic|reading|calculation|concept|careless|other", "difficulty": "easy|medium|hard"}
error_type 含义：knowledge 知识性错误、logic 逻辑错误、reading 审题错误、calculation 计算错误、concept 概念混淆、careless 粗心、other 其他。
只输出 JSON。题目：
"""

VARIANT_PROMPT = """你是出题助手。基于原题生成 1 道同知识点变体题（保持考点一致，仅替换数值/情境/选项顺序），输出 JSON：
{"question_text": "...", "options": ["A...", "B...", ...], "answer": "...", "analysis": "..."}
只输出 JSON。原题：
"""

GRADING_PROMPT = """你是批改助手。根据原题、变体题与学生作答批改，输出 JSON：
{"is_correct": true/false, "score": 0-100, "quality": 0-5, "analysis": "步骤解析", "error_type": "none|knowledge|logic|reading|calculation|concept|careless|other", "knowledge_point": "知识点"}
quality 映射：完全正确且有把握=5；正确但不确定=4；答案对但步骤有误=3；部分对=2；完全错=1；未作答=0。
只输出 JSON。
原题：
"""

CHAT_PROMPT = """你是学科答疑老师。结合题目上下文，条理清晰地讲解，可使用 Markdown（公式用文本表达）。"""

EXTRACT_PROMPT = """从这段对话中提取题目草稿，输出 JSON：
{"question_text": "题干", "options": ["A...", ...], "answer": "答案（无则空字符串）", "analysis": "AI 讲解摘要"}
只输出 JSON。对话：
"""
