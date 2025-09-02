def distill_tags_prompt(tag_path: str, parent_tag: str, existing_tags: list[str] = None, count: int = 10,
                        global_prompt: str = '') -> str:
    """
    根据标签构造子标签的提示词

    Args:
        tag_path (str): 标签链路，例如 "知识库->体育"
        parent_tag (str): 主题标签名称，例如"体育"
        existing_tags (list[str]): 该标签下已经创建的子标签（避免重复），例如 ["足球", "乒乓球"]
        count (int): 希望生成子标签的数量，例如：10
        global_prompt (str): 项目全局提示词

    Returns:
        str: 提示词
    """
    if existing_tags is None:
        existing_tags = []

    existing_tags_text = (
        f"已有的子标签包括：{'、'.join(existing_tags)}，请不要生成与这些重复的标签。"
        if existing_tags
        else ""
    )

    # 构建全局提示词部分
    global_prompt_text = f"你必须遵循这个要求：{global_prompt}" if global_prompt else ""

    return f"""
你是一个专业的知识标签生成助手。我需要你帮我为主题"{parent_tag}"生成{count}个子标签。

标签完整链路是：{tag_path if tag_path else parent_tag}

请遵循以下规则：
{global_prompt_text}
1. 生成的标签应该是"{parent_tag}"领域内的专业子类别或子主题
2. 每个标签应该简洁、明确，通常为2-6个字
3. 标签之间应该有明显的区分，覆盖不同的方面
4. 标签应该是名词或名词短语，不要使用动词或形容词
5. 标签应该具有实用性，能够作为问题生成的基础
6. 标签应该有明显的序号，主题为 1 汽车，子标签应该为 1.1 汽车品牌，1.2 汽车型号，1.3 汽车价格等
7. 若主题没有序号，如汽车，说明当前在生成顶级标签，子标签应为 1 汽车品牌 2 汽车型号 3 汽车价格等

{existing_tags_text}

请直接以JSON数组格式返回标签，不要有任何额外的解释或说明，格式如下：
["序号 标签1", "序号 标签2", "序号 标签3", ...]
"""