from typing import List

from app.db.dataset_db_model.ga_pair_db import GAPairORM


def get_enhanced_answer_en_prompt(text: str, question: str, language: str, global_prompt: str, answer_prompt: str, ga_pairs: List[GAPairORM], active_ga_pair: GAPairORM):
    """
    Enhanced answer generation prompt template based on GA pairs (English version)

    Args:
        - text (str): Reference text content
        - question (str): Question content
        - language (str, optional): Language (default 'English')
        - global_prompt (str, optional): Global prompt
        - answer_prompt (str, optional): Answer prompt
        - ga_pairs (list, optional): GA pairs array containing genre and audience info
        - active_ga_pair (dict, optional): Currently active GA pair

    Returns:
        str: Formatted prompt string
    """

    # Process global and answer prompts
    if global_prompt:
        global_prompt = f"In subsequent tasks, you must strictly follow these rules: {global_prompt}"
    if answer_prompt:
        answer_prompt = f"In generating answers, you must strictly follow these rules: {answer_prompt}"

    # Build GA pairs related prompt
    ga_prompt = ''
    if active_ga_pair:
        ga_prompt = f"""
## Special Requirements - Genre & Audience Adaptation (MGA):
Adjust your response style and depth according to the following genre and audience combination:

**Current Genre**: {active_ga_pair.text_style}
**Current Genre Describe**: {active_ga_pair.text_desc}
**Target Audience**: {active_ga_pair.audience}
**Target Audience Describe**: {active_ga_pair.audience_desc}

Please ensure:
1. The organization, style, level of detail, and language of the answer should fully comply with the requirements of "{active_ga_pair.text_style}".
2. The answer should consider the comprehension ability and knowledge background of "{active_ga_pair.audience}", striving for clarity and ease of understanding.
3. Word choice and explanation detail match the target audience's knowledge background
4. Maintain content accuracy and professionalism while enhancing specificity
5. If "{active_ga_pair.text_style}" or "{active_ga_pair.audience}" suggests the need, the answer can appropriately include explanations, examples, or steps.
"""
    elif ga_pairs:
        ga_list = "\n".join(
            f"{i + 1}. **{ga.text_style}: {ga.text_desc}** + **{ga.audience}: {ga.audience_desc}**"
            for i, ga in enumerate(ga_pairs)
        )
        ga_prompt = f"""
## Optional Genre & Audience Adaptation Guidance:
The following genre and audience combinations are generated for this content and can be used as style references:

{ga_list}

It is recommended to choose the most appropriate style based on the nature of the question.
"""

    # Construct and return the full prompt
    return f"""
# Role: Fine-tuning Dataset Generation Expert (MGA Enhanced)
## Profile:
- Description: You are an expert in generating fine-tuning datasets, skilled at generating accurate answers to questions from the given content, and capable of adjusting response style according to Genre-Audience combinations to ensure accuracy, relevance, and specificity of answers.
{global_prompt}

## Skills:
1. The answer must be based on the given content.
2. The answer must be accurate and not fabricated.
3. The answer must be relevant to the question.
4. The answer must be logical.
5. Based on the given reference content, integrate into a complete answer using natural and fluent language, without mentioning literature sources or citation marks.
6. Ability to adjust response style and depth according to specified genre and audience combinations.
7. While maintaining content accuracy, enhance the specificity and applicability of answers.

{ga_prompt}

## Workflow:
1. Take a deep breath and work on this problem step-by-step.
2. First, analyze the given file content and question type.
3. Then, extract key information from the content.
4. If a specific genre and audience combination is specified, analyze how to adjust the response style.
5. Next, generate an accurate answer related to the question, adjusting expression according to genre-audience requirements.
6. Finally, ensure the accuracy, relevance, and style compatibility of the answer.

## Reference Content:
{text}

## Question
{question}

## Constraints:
1. The answer must be based on the given content.
2. The answer must be accurate and relevant to the question, and no fabricated information is allowed.
3. The answer must be comprehensive and detailed, containing all necessary information, and it is suitable for use in the training of fine-tuning large language models.
4. The answer must not contain any referential expressions like 'according to the reference/based on/literature mentions', only present the final results.
5. If a genre and audience combination is specified, the expression style and depth must be adjusted while maintaining content accuracy.
6. The answer must directly address the question, ensuring its accuracy and logicality.
{answer_prompt}
"""