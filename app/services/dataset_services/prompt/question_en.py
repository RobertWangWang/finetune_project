from app.db.dataset_db_model.ga_pair_db import GAPairORM


def build_ga_prompt(active_ga_pair: GAPairORM = None):
    """
    Builds the GA prompt string.
    :param active_ga_pair: The currently active GA pair (dict or None)
    :return: The constructed GA prompt string
    """
    if active_ga_pair:
        return f"""
## Special Requirements - Genre & Audience Perspective Questioning:
Adjust your questioning approach and question style based on the following genre and audience combination:

**Target Genre**: {active_ga_pair.text_style}
**Target Genre Describe**: {active_ga_pair.text_desc}
**Target Audience**: {active_ga_pair.audience}
**Target Audience Describe**: {active_ga_pair.audience_desc}

Please ensure:
1. The question should fully conform to the style, focus, depth, and other attributes defined by "{active_ga_pair.text_style}".
2. The question should consider the knowledge level, cognitive characteristics, and potential points of interest of "{active_ga_pair.audience}".
3. Propose questions from the perspective and needs of this audience group.
4. Maintain the specificity and practicality of the questions, ensuring consistency in the style of questions and answers.
5. The question should have a certain degree of clarity and specificity, avoiding being too broad or vague.
"""
    return ''


def get_question_prompt_en(text: str = "", number: int = 1, language: str = "zh", global_prompt: str = "", question_prompt: str = "", active_ga_pair: GAPairORM = None):
    """
    Question generation prompt template.
    :param: Dictionary containing:
        - text: The text to be processed
        - number: The number of questions (default: text length // 240)
        - language: The language of questions (default: 'English')
        - global_prompt: Global prompt for the LLM
        - question_prompt: Specific prompt for question generation
        - active_ga_pair: The currently active GA pair
    :return: The complete prompt for question generation
    """
    # text = params.get('text', '')
    # number = params.get('number', max(1, len(text) // 240))
    # language = params.get('language', 'English')
    # global_prompt = params.get('global_prompt', '')
    # question_prompt = params.get('question_prompt', '')
    # active_ga_pair = params.get('active_ga_pair')

    if global_prompt:
        global_prompt = f"In subsequent tasks, you must strictly follow these rules: {global_prompt}"
    if question_prompt:
        question_prompt = f"- In generating questions, you must strictly follow these rules: {question_prompt}"

    # Build GA pairs related prompts
    ga_prompt = build_ga_prompt(active_ga_pair)

    return f"""
    # Role Mission
    You are a professional text analysis expert, skilled at extracting key information from complex texts and generating structured data(only generate questions) that can be used for model fine-tuning.
    {global_prompt}

    ## Core Task
    Based on the text provided by the user(length: {len(text)} characters), generate no less than {number} high-quality questions.

    ## Constraints(Important!!!)
    ✔️ Must be directly generated based on the text content.
    ✔️ Questions should have a clear answer orientation.
    ✔️ Should cover different aspects of the text.
    ❌ It is prohibited to generate hypothetical, repetitive, or similar questions.

    {ga_prompt}

    ## Processing Flow
    1. 【Text Parsing】Process the content in segments, identify key entities and core concepts.
    2. 【Question Generation】Select the best questioning points based on the information density{', and incorporate the specified genre-audience perspective' if ga_prompt else ''}
    3. 【Quality Check】Ensure that:
       - The answers to the questions can be found in the original text.
       - The labels are strongly related to the question content.
       - There are no formatting errors.
       {'- Question style matches the specified genre and audience' if ga_prompt else ''}

    ## Output Format
    - The JSON array format must be correct.
    - Use English double-quotes for field names.
    - The output JSON array must strictly follow the following structure:
    ```json
    ["Question 1", "Question 2", "..."]
    ```

    ## Output Example
    ```json
    [ "What core elements should an AI ethics framework include?", "What new regulations does the Civil Code have for personal data protection?"]
     ```

    ## Text to be Processed
    {text}

    ## Restrictions
    - Must output in the specified JSON format and do not output any other irrelevant content.
    - Generate no less than {number} high-quality questions.
    - Questions should not be related to the material itself. For example, questions related to the author, chapters, table of contents, etc. are prohibited.
    {question_prompt}
    """