from app.domain.models.teaching_unit import TeachingUnit
from app.domain.models.slide import Slide

class SlideBuilder:
    def build(self, unit: TeachingUnit, narration_text: str = "") -> Slide:
        return Slide(
            unit_id=unit.unit_id,
            title=unit.learning_goal,
            bullets=unit.bullet_sentences,
            speaker_notes=narration_text
        )
