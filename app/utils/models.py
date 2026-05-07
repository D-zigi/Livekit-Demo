"""
Module for generating descriptions of Pydantic model instances.
This module provides functions to create string representations of Pydantic models,
Utility functions for validating Pydantic models against payloads.
"""
from typing import TypeVar, List, Type, Optional, Any
from pydantic import BaseModel, ValidationError, create_model

T = TypeVar('T', bound=BaseModel)

def modify_payload(value: dict, payload: dict, name: Optional[str] = None) -> dict:
    """
    Modify each item in the payload by updating it with the given value dictionary.

    Args:
        payload (dict): The payload containing items to modify.
        name (str): The key in the payload to extract items from.
        value (dict): The dictionary to update each item with.
    """
    items = payload.get(name, None)
    if items is None:
        raise ValidationError(f"No {name} found in payload.")

    # If items is not a list, convert it to a list
    if not isinstance(items, list):
        items = [items]

    # Modify each item
    for item in items:
        if isinstance(item, dict):
            item.update(value)

    # Update the payload with modified items
    payload[name] = items
    return payload

def validate_payload(model: Type[T], payload: dict | list[Any] | Any, name: Optional[str] = None) -> List[T]:
    """
    Validate the payload against the provided Pydantic model.

    Args:
        model (Type[T]): The Pydantic model to validate against.
        payload (dict): The payload to validate.
        name (str, optional): The key in the payload to extract items from. Defaults to None.

    Returns:
        List[T]: A list of validated Pydantic model instances.
    """
    # Get the items from the payload
    if name is None or isinstance(payload, list):
        # If no name is provided, use the payload directly
        items = payload
    else:
        # Extract the items from the payload using the provided name
        items = payload.get(name, None)
        if items is None:
            raise ValidationError(f"No {name} found in payload.")

    # If items is not a list, convert it to a list
    if not isinstance(items, list):
        items = [items]

    # Validate each item against the model
    validated_items = []
    for item in items:
        validated_items.append(
            model.model_validate(item)
        )

    return validated_items


def create_response_model(model: Type[T], name: str, as_list: Optional[bool] = None) -> Type[BaseModel]:
    """
    Generates a response model for
    payload validation with table row/s data.
    """
    if as_list is None:
        as_list = name.endswith("s")

    title = name.capitalize() + "ResponseModel"
    field_type: Any = List[model] if as_list else model

    response_model = create_model(
        title,
        **{name: (field_type, ...)}  # type: ignore[call-overload]
    )
    return response_model


def describe_pydantic_object(obj: BaseModel, name: Optional[str] = None) -> str:
    """Generates a string description of a Pydantic model instance."""
    lines = []
    # Iterate over the fields of the Pydantic model
    for field_name, field in obj.__pydantic_fields__.items():
        value = getattr(obj, field_name)
        desc = field.description or ""
        line = f"{field_name}: {value}" + (f" - {desc}" if desc else "")
        lines.append(line)
    # Use the class name as the title
    name = name or (obj.__class__.__name__)
    return f"{name}:\n" + "\n".join(lines)

def describe_pydantic_objects(objs: List[T], name: str) -> str:
    """Generates a string description for a list of Pydantic model instances."""
    descriptions = [describe_pydantic_object(obj, name) for obj in objs]
    for i, description in enumerate(descriptions):
        descriptions[i] = f"{i + 1}:\n{description}"
    return f"{name}s:\n{"\n".join(descriptions)}"
