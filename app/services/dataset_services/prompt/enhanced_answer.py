from typing import List

from app.db.dataset_db_model.ga_pair_db import GAPairORM


def get_enhanced_answer_prompt(text: str, question: str, language: str, global_prompt: str, answer_prompt: str, ga_pairs: List[GAPairORM], active_ga_pair: GAPairORM):
    """
    Enhanced answer generation prompt based on GA pairs

    Args:
        - text (str): Reference text content
        - question (str): Question content
        - language (str, optional): Language (default is '中文')
        - global_prompt (str, optional): Global prompt
        - answer_prompt (str, optional): Answer prompt
        - ga_pairs (list, optional): List of GA pairs containing genre and audience info
        - active_ga_pair (dict, optional): Currently active GA pair

    Returns:
        str: The formatted prompt string
    """
    # Process global and answer prompts
    if global_prompt:
        global_prompt = f"- 在后续的任务中，你务必遵循这样的规则：{global_prompt}"
    if answer_prompt:
        answer_prompt = f"- 在生成答案时，你务必遵循这样的规则：{answer_prompt}"

    # Build GA pairs related prompt
    ga_prompt = ''
    if active_ga_pair:
        ga_prompt = f"""
## 特殊要求 - 体裁与受众适配(MGA)：
根据以下体裁与受众组合，调整你的回答风格和深度：

**当前体裁**: {active_ga_pair.text_style}
**当前体裁描述**: {active_ga_pair.text_desc}
**目标受众**: {active_ga_pair.audience}
**目标受众描述**: {active_ga_pair.audience_desc}

请确保：
1. 答案的组织、风格、详略程度和语言应完全符合「{active_ga_pair.text_style}」的要求。
2. 答案应考虑到「{active_ga_pair.audience}」的理解能力和知识背景，力求清晰易懂。
3. 用词选择和解释详细程度匹配目标受众的知识背景
4. 保持内容的准确性和专业性，同时增强针对性
5.如果「{active_ga_pair.text_style}」或「{active_ga_pair.audience}」暗示需要，答案可以适当包含解释、示例或步骤。
"""
    elif ga_pairs:
        ga_list = "\n".join(
            f"{i + 1}. **{ga.text_style}: {ga.text_desc}** + **{ga.audience}: {ga.audience_desc}**"
            for i, ga in enumerate(ga_pairs)
        )
        ga_prompt = f"""
## 可选体裁与受众适配指导：
以下是为此内容生成的体裁与受众组合，可作为回答风格的参考：

{ga_list}

建议根据问题性质，选择最适合的风格进行回答。
"""

    # Construct and return the full prompt
    return f"""
# Role: 微调数据集生成专家 (MGA增强版)
## Profile:
- Description: 你是一名微调数据集生成专家，擅长从给定的内容中生成准确的问题答案，并能根据体裁与受众(Genre-Audience)组合调整回答风格，确保答案的准确性、相关性和针对性。
{global_prompt}

## Skills:
1. 答案必须基于给定的内容
2. 答案必须准确，不能胡编乱造
3. 答案必须与问题相关
4. 答案必须符合逻辑
5. 基于给定参考内容，用自然流畅的语言整合成一个完整答案，不需要提及文献来源或引用标记
6. 能够根据指定的体裁与受众组合调整回答风格和深度
7. 在保持内容准确性的同时，增强答案的针对性和适用性

{ga_prompt}

## Workflow:
1. Take a deep breath and work on this problem step-by-step.
2. 首先，分析给定的文件内容和问题类型
3. 然后，从内容中提取关键信息
4. 如果有指定的体裁与受众组合，分析如何调整回答风格
5. 接着，生成与问题相关的准确答案，并根据体裁受众要求调整表达方式
6. 最后，确保答案的准确性、相关性和风格适配性

## 参考内容：
{text}

## 问题
{question}

## Constrains:
1. 答案必须基于给定的内容
2. 答案必须准确，必须与问题相关，不能胡编乱造
3. 答案必须充分、详细、包含所有必要的信息、适合微调大模型训练使用
4. 答案中不得出现 ' 参考 / 依据 / 文献中提到 ' 等任何引用性表述，只需呈现最终结果
5. 如果指定了体裁与受众组合，必须在保持内容准确性的前提下，调整表达风格和深度
6. 答案必须直接回应问题， 确保答案的准确性和逻辑性。
{answer_prompt}
"""