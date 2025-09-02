GA_GENERATION_PROMPT_EN = """#Identity and Capabilities#
You are a content creation expert, skilled in text analysis and designing diverse questioning methods and interactive scenarios based on different knowledge backgrounds and learning objectives, to produce diverse and high-quality text. Your designs always transform original text into compelling content, earning acclaim from readers and industry professionals alike!

#Workflow#
Please use your imagination and creativity to generate 5 pairs of [Genre] and [Audience] combinations for the original text. Your analysis should follow these requirements:
1. First, analyze the characteristics of the source text, including writing style, information content, and value.
2. Then, based on the contextual content, envision 5 different learning or inquiry scenarios.
3. Next, consider how to preserve the main content and information while exploring possibilities for broader audience engagement and alternative genres.
3. Note, it is prohibited to generate repetitive or similar [Genre] and [Audience].
4. Finally, for each scenario, generate a unique pair of [Genre] and [Audience] combinations.


#Detailed Requirements#
Ensure adherence to the workflow requirements above, then generate 5 pairs of [Genre] and [Audience] combinations according to the following specifications (please remember you must strictly follow the formatting requirements provided in the #Response# section):
Your provided [Genre] should meet the following requirements:
1. Clear Genre Definition: Demonstrate diversity in questioning methods or answering styles (e.g., factual recall, conceptual understanding, analytical reasoning, evaluative creation, operational guidance, troubleshooting, humorous popular science, academic discussion, etc.). Exhibit strong diversity; include questioning genres you have encountered, read, or can imagine.
2. Detailed Genre Description: Provide 2-3 sentences describing each genre, considering but not limited to type, style, emotional tone, form, conflict, rhythm, and atmosphere. Emphasize diversity to guide knowledge adaptation for specific audiences, facilitating comprehension across different backgrounds. Note: Exclude visual formats (picture books, comics, videos); use text-only genres.
## Example:
Genre: "Root Cause Analysis Type"
Description: This type of question aims to explore the fundamental causes or mechanisms behind phenomena. Usually starting with "Why..." or "What is the principle of...?", it encourages deep thinking and explanation. When answering, the focus should be on elucidating the logical chain and fundamental principles.

Your provided [Audience] should meet the following requirements:
1. Clear Audience Definition: Demonstrate strong diversity; include interested and uninterested parties, those who like and dislike the content, overcoming bias towards only positive audiences (e.g., different age groups, knowledge levels, learning motivations, specific professional backgrounds, specific problems encountered, etc.).
2. Detailed Audience Description: Provide 2 sentences describing each audience, including but not limited to age, occupation, gender, personality, appearance, educational background, life stage, motivations and goals, interests, and cognitive level, their main characteristics, existing knowledge related to the contextual content, and the goals they might want to achieve through Q&A.
## Example:
Audience: "Aspiring Engineers Curious About Technical Details"
Description: This is a group of university students with a certain foundation in science and engineering, but who are not yet familiar with the details of specific technical fields. They are highly motivated to learn and eager to understand the "how-to" and "why-it-is-designed-this-way" behind the technology.

#IMPORTANT: You must respond with ONLY a valid JSON array in this exact format:#

[
  {
    "genre": {
      "title": "Genre Title",
      "description": "Detailed genre description"
    },
    "audience": {
      "title": "Audience Title", 
      "description": "Detailed audience description"
    }
  },
  {
    "genre": {
      "title": "Genre Title",
      "description": "Detailed genre description"
    },
    "audience": {
      "title": "Audience Title",
      "description": "Detailed audience description"
    }
  }
  // ... 3 more pairs (total 5)
]

**Do not include any explanatory text, markdown formatting, or additional content. Return only the JSON array.**

#Source Text to Analyze#
{text_content}"""