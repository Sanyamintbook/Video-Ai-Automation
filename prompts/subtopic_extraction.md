You are an educational curriculum expert.

Analyze the provided educational text chunk and extract all granular, teachable subtopics discussed within it.

Educational Content Chunk:
{content}

**YOUR ANALYTICAL APPROACH (MENTAL MODEL):**
1. **Exhaustive Coverage (No Skipping):** You must extract EVERY distinct concept, fact, or mechanism present in the text. Do not leave any concept behind. If a section covers 5 different features, you must extract 5 subtopics or group them perfectly into comprehensive chunks without losing information.
2. **Break Down Large Sections:** If the text covers many distinct concepts, extract them as separate, sequential subtopics.
3. **Group Fragmented Facts Wisely:** If there are tiny related facts, group them into a single cohesive teachable subtopic.
4. **TUTOR-LEVEL SUBTOPICS:** Your `subtopics` array MUST represent perfectly sized, teachable chunks. Each subtopic should contain enough material to deeply cover the concept.

**CRITICAL RULES:** 
1. Only extract concepts that are actually present in this specific chunk of text. Do not invent topics.
2. Ensure absolutely NO educational concepts are skipped or glossed over.
3. Return valid JSON only.
4. **CRITICAL (JSON DICT ONLY):** You MUST output ONLY a single JSON dictionary object (`{{}}`). Do not wrap it in anything else. Failure to return a valid JSON dictionary will break the system.

Required JSON structure:
{{
  "subtopics": ["string"]
}}
