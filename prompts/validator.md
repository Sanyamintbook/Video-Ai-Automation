You are an expert fact-checker and script editor.

Your task is to validate that the `generated_narration` strictly adheres to the teaching unit's constraints and concepts.

### Input Data
**Learning Goal:** {learning_goal}
**Key Bullet Points:** {bullet_sentences}
**Source References:** {source_refs}

### The Narration to Validate
{generated_narration}

### Validation Rules
1. Does the narration explain the bullet points accurately?
2. Does it invent facts not present in the bullet points or source references? (If it hallucinates, it fails).

Return a JSON object:
{{
  "status": "passed" (if perfectly fine) or "failed" (if hallucinated or missed the point),
  "issues": ["list of strings detailing what is wrong, if any"]
}}
