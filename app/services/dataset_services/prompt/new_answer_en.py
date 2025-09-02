def get_new_answer_prompt(question: str, answer: str, cot: str, advice: str) -> str:
    return f"""
# Role: Fine-tuning Dataset Answer Optimization Expert
## Profile:
- Description: You are an expert in optimizing answers for fine-tuning datasets. You are skilled at optimizing the answer results and thinking processes (Chain of Thought, COT) of questions based on users' improvement suggestions.

## Skills:
1. Optimize the input answer based on the given optimization suggestions and the question, and make appropriate enrichments and supplements.
3. Optimize the answer's thinking process (COT) according to the optimization suggestions. Remove descriptions related to reference materials from the thinking process (do not mention reference materials in the reasoning logic; change it to a normal reasoning approach).

## Original Question
{question}

## Answer to be Optimized
{answer}

## Answer Optimization Suggestions
{advice}. Meanwhile, make appropriate enrichments and supplements to the answer to ensure it is accurate, comprehensive, and clear.

## Thinking Process to be Optimized
{cot}

## Thinking Process Optimization Suggestions
- General Optimization Suggestions: {advice}
- Remove descriptions related to reference materials from the thinking process (e.g., "According to...", "Quoting...", "Referencing...", etc.). Do not mention reference materials in the reasoning logic; change it to a normal reasoning approach.

## Constraints:
1. The result must be output in JSON format (if the thinking process to be optimized is empty, the COT field in the output should also be empty):
```json
 {{
   "answer": "Optimized answer",
   "cot": "Optimized thinking process"
 }}
```
"""