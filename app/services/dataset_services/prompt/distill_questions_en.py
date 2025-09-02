import re


def remove_leading_number(label):
    # Regex explanation:
    # ^\d+       Match one or more digits at the start
    # (?:\.\d+)* Match zero or more occurrences of (dot + digits) (non-capturing group)
    # \s+        Match one or more whitespace characters after the number
    number_prefix_regex = r'^\d+(?:\.\d+)*\s+'
    # Only replace if number prefix is found, otherwise return original label
    return re.sub(number_prefix_regex, '', label)


def distill_questions_prompt(tag_path, current_tag, count=10, existing_questions=None, global_prompt=''):
    """
    Generate a prompt for question generation based on tags

    Args:
        tag_path (str): Tag path, e.g. "Sports->Football->Football Player"
        current_tag (str): Current subtag, e.g. "Football Player"
        count (int): Number of questions to generate, default 10
        existing_questions (list): Existing questions to avoid duplication
        global_prompt (str): Global prompt requirements

    Returns:
        str: The complete prompt for question generation
    """
    if existing_questions is None:
        existing_questions = []

    current_tag = remove_leading_number(current_tag)
    existing_questions_text = (
        f"Existing questions include:\n" + "\n".join([f"- {q}" for q in existing_questions]) +
        "\nPlease do not generate questions that are repetitive or highly similar to these."
        if existing_questions
        else ''
    )

    # Build global prompt section
    global_prompt_text = f"You must adhere to this requirement: {global_prompt}" if global_prompt else ''

    return f"""
You are a professional knowledge question generation assistant, proficient in the field of {current_tag}. I need you to help me generate {count} high-quality, diverse questions for the tag "{current_tag}".

The complete tag path is: {tag_path}

Please follow these rules:
{global_prompt_text}
1. The generated questions must be closely related to the topic of "{current_tag}", ensuring comprehensive coverage of the core knowledge points and key concepts of this topic.
2. Questions should be evenly distributed across the following difficulty levels (each level should account for at least 20%):
   - Basic: Suitable for beginners, focusing on basic concepts, definitions, and simple applications.
   - Intermediate: Requires some domain knowledge, involving principle explanations, case analyses, and application scenarios.
   - Advanced: Requires in-depth thinking, including cutting-edge developments, cross-domain connections, complex problem solutions, etc.

3. Question types should be diverse, including but not limited to (the following are just references and can be adjusted flexibly according to the actual situation; there is no need to limit to the following topics):
   - Conceptual explanation: "What is...", "How to define..."
   - Principle analysis: "Why...", "How to explain..."
   - Comparison and contrast: "What is the difference between... and...", "What are the advantages of... compared to..."
   - Application practice: "How to apply... to solve...", "What is the best practice for..."
   - Development trends: "What is the future development direction of...", "What challenges does... face?"
   - Case analysis: "Please analyze... in the case of..."
   - Thought-provoking: "What would happen if...", "How to evaluate..."

4. Question phrasing should be clear, accurate, and professional. Avoid the following:
   - Avoid vague or overly broad phrasing.
   - Avoid closed-ended questions that can be answered with "yes/no".
   - Avoid questions containing misleading assumptions.
   - Avoid repetitive or highly similar questions.

5. The depth and breadth of questions should be appropriate:
   - Cover the history, current situation, theoretical basis, and practical applications of the topic.
   - Include mainstream views and controversial topics in the field.
   - Consider the cross-associations between this topic and related fields.
   - Focus on emerging technologies, methods, or trends in this field.

{existing_questions_text}

Please directly return the questions in the format of a JSON array, without any additional explanations or notes, in the following format:
["Question 1", "Question 2", "Question 3", ...]

Note: Each question should be complete and self-contained, understandable and answerable without relying on other contexts.
"""