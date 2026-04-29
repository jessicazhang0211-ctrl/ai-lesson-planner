from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class LessonStepSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class LessonExerciseSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class LessonPlanSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str = Field(min_length=1)
    objectives: List[str] = Field(default_factory=list)
    steps: List[LessonStepSchema] = Field(default_factory=list)
    activities: List[LessonStepSchema] = Field(default_factory=list)
    exercises: List[LessonExerciseSchema] = Field(default_factory=list)
    _meta: Optional[Dict[str, Any]] = None


def validate_lesson_payload(payload: Dict[str, Any]) -> tuple[bool, Dict[str, Any], List[str]]:
    try:
        obj = LessonPlanSchema.model_validate(payload)
        result = obj.model_dump(by_alias=True)
        # Keep custom runtime meta if present in original payload.
        if isinstance(payload.get("_meta"), dict):
            result["_meta"] = payload.get("_meta")
        return True, result, []
    except ValidationError as e:
        issues = []
        for err in e.errors():
            loc = ".".join([str(x) for x in err.get("loc", [])]) or "$"
            msg = err.get("msg", "invalid")
            issues.append(f"{loc}: {msg}")
        return False, payload if isinstance(payload, dict) else {}, issues
