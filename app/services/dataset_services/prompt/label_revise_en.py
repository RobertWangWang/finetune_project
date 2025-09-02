import json


def get_label_revise_prompt_en(text, existing_tags, deleted_content="", new_content="", global_prompt="", domain_tree_prompt=""):
    tag_prompt = json.dumps([tag.dict() for tag in existing_tags], ensure_ascii=False)

    prompt = f"""
{global_prompt}

I need your help to revise an existing domain tree structure to adapt to content changes.
{domain_tree_prompt}

【Existing Domain Tree Structure】
Here is the current domain tree structure (JSON format):
```json
{tag_prompt}
```

【Deleted Content】
Here are the table of contents from the deleted literature:
```
{deleted_content}
```

【New Content】
Here are the table of contents from the newly added literature:
```
{new_content}
```

【All Existing Literature TOC】
Below is an overview of the table of contents from all current literature in the system:
```
{text}
```

Please analyze the above information and revise the existing domain tree structure according to the following principles:
1. Maintain the overall structure of the domain tree, avoiding large-scale reconstruction
2. For domain tags related to deleted content:
   - If a tag is only related to the deleted content and no supporting content can be found in the existing literature, remove the tag
   - If a tag is also related to other retained content, keep the tag
3. For newly added content:
   - If new content can be classified into existing tags, prioritize using existing tags
   - If new content introduces new domains or concepts not present in the existing tag system, create new tags
4. Each tag must correspond to actual content in the table of contents, do not create empty tags without corresponding content support
5. Ensure that the revised domain tree still has a good hierarchical structure with reasonable parent-child relationships between tags

## Constraints
1. The number of primary domain labels should be between 5 and 10.
2. The number of secondary domain labels ≤ 5 per primary label.
3. There should be at most two classification levels.
4. The classification must be relevant to the original catalog content.
5. The output must conform to the specified JSON format.
6. The names of the labels should not exceed 6 characters.
7. Do not output any content other than the JSON.
8. Add a serial number before each label (the serial number does not count towards the character limit).

Output the complete revised domain tree structure using the JSON format below:

```json
[
  {{
    "label": "1 Primary Domain Label",
    "child": [
      {{"label": "1.1 Secondary Domain Label 1"}},
      {{"label": "1.2 Secondary Domain Label 2"}}
    ]
  }},
  {{
    "label": "2 Primary Domain Label (No Sub - labels)"
  }}
]
```

Ensure that your answer only contains the domain tree in JSON format without any explanatory text.
    """
    return prompt