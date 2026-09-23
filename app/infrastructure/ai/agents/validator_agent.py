import json
from typing import Dict, Any

from pydantic import BaseModel, Field

from app.domain.models.narration_segment import NarrationSegment
from app.domain.models.teaching_unit import TeachingUnit
from app.infrastructure.ai.agents.base_agent import BaseAgent

class ValidationResult(BaseModel):
    status: str = Field(description="Must be 'passed' if the narration is strictly grounded in the source references, or 'failed' if it hallucinates or omits critical concepts.")
    issues: list[str] = Field(description="List of specific issues found. Empty if passed.")

class ValidatorAgent(BaseAgent):
    """
    SemanticValidator: Checks narration against source_refs to catch hallucinations.
    """
    
    async def run(self, segment: NarrationSegment, unit: TeachingUnit) -> NarrationSegment:
        # We construct the input payload combining the unit's source refs and the generated script
        payload = {
            "learning_goal": unit.learning_goal,
            "bullet_sentences": unit.bullet_sentences,
            "source_refs": unit.source_refs,
            "generated_narration": segment.narration_text
        }
        
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "issues": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["status", "issues"]
        }
        
        result_obj = await self.generate_structured(
            prompt_name="validator",
            context=payload,
            schema=schema,
        )
        
        # Translate to the standard PENDING/PASS/FAIL expected by NarrationSegment
        if result_obj.get("status", "").lower() == "passed":
            segment.validation_status = "PASS"
        else:
            segment.validation_status = "FAIL"
            
        segment.validation_notes = result_obj.get("issues", [])
        
        return segment
