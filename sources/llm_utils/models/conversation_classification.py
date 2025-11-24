"""
Pydantic models for conversation classification LLM responses
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


class PriceMentioned(BaseModel):
    """Price information mentioned in seller's response"""
    item: str = Field(..., description="Item description")
    price: str = Field(..., description="Price amount")
    currency: str = Field(..., description="Currency (EUR/PLN/USD)")

    class Config:
        json_schema_extra = {"additionalProperties": False}


class ConversationClassification(BaseModel):
    """Classification result for a seller conversation"""

    status: Literal["accepted", "accepted_partially", "declined", "communication_needed"] = Field(
        ...,
        description="Overall status of the seller's response"
    )

    decline_reason: Optional[Literal[
        "no_stock",
        "no_export",
        "minimum_order",
        "no_used_parts",
        "price_disagreement",
        "no_cooperation_interest",
        "other"
    ]] = Field(
        None,
        description="Reason for decline if status is 'declined'"
    )

    decline_details: Optional[str] = Field(
        None,
        description="Additional details about the decline reason"
    )

    confidence: int = Field(
        ...,
        ge=1,
        le=5,
        description="Confidence level 1-5"
    )

    seller_sentiment: Literal["positive", "neutral", "negative"] = Field(
        ...,
        description="Overall sentiment of seller's response"
    )

    has_price_info: bool = Field(
        ...,
        description="Whether the response contains price information"
    )

    prices_mentioned: List[PriceMentioned] = Field(
        default_factory=list,
        description="List of prices mentioned in the response"
    )

    availability_info: Optional[str] = Field(
        None,
        description="Information about stock/availability"
    )

    next_steps: str = Field(
        ...,
        description="Suggested next action based on the response"
    )

    summary: str = Field(
        ...,
        description="Brief summary of seller's response in English"
    )

    @field_validator('decline_reason')
    @classmethod
    def validate_decline_reason(cls, v, info):
        """Ensure decline_reason is set when status is declined"""
        status = info.data.get('status')
        if status == 'declined' and v is None:
            raise ValueError("decline_reason is required when status is 'declined'")
        if status != 'declined' and v is not None:
            # Allow but warn - don't raise error, just set to None
            return None
        return v

    @classmethod
    def model_json_schema(cls, by_alias=True, ref_template='#/$defs/{model}'):
        """Generate OpenAI-compatible JSON schema with proper field ordering"""
        schema = super().model_json_schema(by_alias=by_alias, ref_template=ref_template)

        # Reorder schema for OpenAI compatibility
        ordered_schema = {
            "type": "object",
            "additionalProperties": False
        }

        # Add other fields in specific order
        if "properties" in schema:
            # Clean up properties to fix $ref issues
            cleaned_properties = {}
            for prop_name, prop_schema in schema["properties"].items():
                if "$ref" in prop_schema:
                    # For $ref fields, only keep the $ref
                    cleaned_properties[prop_name] = {"$ref": prop_schema["$ref"]}
                else:
                    cleaned_properties[prop_name] = prop_schema
            ordered_schema["properties"] = cleaned_properties
            # OpenAI strict mode requires ALL properties in required array
            ordered_schema["required"] = list(cleaned_properties.keys())
        if "description" in schema:
            ordered_schema["description"] = schema["description"]
        if "title" in schema:
            ordered_schema["title"] = schema["title"]

        # Add $defs last
        if "$defs" in schema:
            # Ensure all nested objects have proper structure
            for def_name, def_schema in schema["$defs"].items():
                if def_schema.get("type") == "object":
                    if "properties" in def_schema:
                        def_schema["required"] = list(def_schema["properties"].keys())
                    def_schema["additionalProperties"] = False
            ordered_schema["$defs"] = schema["$defs"]

        # Add any remaining fields
        for key, value in schema.items():
            if key not in ordered_schema:
                ordered_schema[key] = value

        return ordered_schema

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {"additionalProperties": False}
