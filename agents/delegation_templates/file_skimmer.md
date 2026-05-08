# File Skimmer — Delegation Template

> For reading large files without bloating director context.
> Use cheap models — this is summarization, not reasoning.

## Prompt Template

```
Read the following file and provide a structured summary.

## File
{file_content}

## Answer These Questions
1. What is the primary purpose of this file?
2. What are the key functions/classes/sections and what does each do? (1 sentence each)
3. What external dependencies does it import or reference?
4. What tables, schemas, or data sources does it interact with? (exact names)
5. Are there any TODOs, FIXMEs, or commented-out code that suggests unfinished work?
6. {custom_question_from_director}

## Output Format
Keep total response under 500 tokens. Be specific about names —
the director needs exact identifiers, not descriptions.
```

## Model: Cheapest available (Llama 3.x 8B, Mixtral via Databricks FMAPI)
## Memory Slice: None
## Use When: Any file >200 lines that the director needs context on but doesn't need to read fully
