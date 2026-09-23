from typing import Any
from pydantic import BaseModel, ValidationError

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]

class SchemaValidator:
    """
    Enforces structural correctness at every stage boundary.
    Can validate dicts, lists of dicts, or Pydantic model instances.
    """
    def _validate_single(self, model_type: type[BaseModel], data: Any):
        if hasattr(model_type, "model_validate"):
            return model_type.model_validate(data)
        elif hasattr(model_type, "parse_obj"):
            return model_type.parse_obj(data)
        elif isinstance(data, dict):
            return model_type(**data)
        return data

    def validate(self, artifact: Any, model_type: type[BaseModel]) -> ValidationResult:
        errors = []
        try:
            if isinstance(artifact, list):
                for index, item in enumerate(artifact):
                    try:
                        if isinstance(item, BaseModel):
                            item_dict = item.model_dump() if hasattr(item, "model_dump") else item.dict()
                            self._validate_single(model_type, item_dict)
                        elif isinstance(item, dict):
                            self._validate_single(model_type, item)
                        else:
                            self._validate_single(model_type, item)
                    except ValidationError as e:
                        for err in e.errors():
                            loc = " -> ".join(str(l) for l in err.get("loc", []))
                            errors.append(f"Item {index} [{loc}]: {err.get('msg', str(err))}")
                    except Exception as ex:
                        errors.append(f"Item {index}: {str(ex)}")
            else:
                try:
                    if isinstance(artifact, BaseModel):
                        art_dict = artifact.model_dump() if hasattr(artifact, "model_dump") else artifact.dict()
                        self._validate_single(model_type, art_dict)
                    elif isinstance(artifact, dict):
                        self._validate_single(model_type, artifact)
                    else:
                        self._validate_single(model_type, artifact)
                except ValidationError as e:
                    for err in e.errors():
                        loc = " -> ".join(str(l) for l in err.get("loc", []))
                        errors.append(f"[{loc}]: {err.get('msg', str(err))}")
                except Exception as ex:
                    errors.append(str(ex))
        except Exception as e:
            errors.append(f"Unexpected error during validation: {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
