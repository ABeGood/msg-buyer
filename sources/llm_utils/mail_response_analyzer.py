from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from sources.llm_utils.models.conversation_classification import ConversationClassification
from sources.llm_utils.prompts.prompts import SELLER_RESPONSE_CLASSIFIER_PROMPT

import re
from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
if not OPENAI_TOKEN:
    raise ValueError("OPENAI_TOKEN environment variable is required but not set")

LLM_CLIENT = OpenAI(api_key=OPENAI_TOKEN, timeout=120, max_retries=3)
LLM_MODEL = "gpt-4o-mini"


def analyze_seller_response(
    messages: List[Dict[str, Any]],
) -> ConversationClassification:
    """
    Analyze seller response and classify the conversation outcome.

    Args:
        messages: List of message dicts with keys: direction, subject, body, sent_at/received_at
        positions_info: Optional string describing positions we inquired about

    Returns:
        ConversationClassification: Validated classification result
    """
    try:
        # Format conversation history
        conversation_history = _format_conversation_history(messages)

        # Create prompt from template
        prompt = SELLER_RESPONSE_CLASSIFIER_PROMPT.format(
            conversation_history=conversation_history,
        )

        # Get JSON schema from Pydantic model
        schema = {
            "name": "conversation_classification",
            "strict": True,
            "schema": ConversationClassification.model_json_schema()
        }

        # Call OpenAI with structured output
        llm_messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt}
        ]

        response = LLM_CLIENT.chat.completions.create(
            model=LLM_MODEL,
            messages=llm_messages,
            response_format={
                "type": "json_schema",
                "json_schema": schema
            },
            temperature=0.1
        )

        # Parse and validate response
        response_content = response.choices[0].message.content
        classification_result = ConversationClassification.model_validate_json(response_content)

        return classification_result
    except Exception as e:
        print(e)


def _format_conversation_history(messages: List[Dict[str, Any]]) -> str:
    """
    Format email messages into readable conversation history.
    Removes email citations/quotes from responses.

    Args:
        messages: List of message dicts with direction, subject, body, timestamps

    Returns:
        Formatted conversation string
    """
    if not messages:
        return "No conversation history."

    formatted = []

    for msg in messages:
        direction = msg.get('direction', 'unknown')
        subject = msg.get('subject', '')
        body = msg.get('body', '')
        timestamp = msg.get('sent_at') or msg.get('received_at') or msg.get('created_at', '')

        # Label based on direction
        if direction == 'outbound':
            label = "[US → SELLER]"
        elif direction == 'inbound':
            label = "[SELLER → US]"
            # Remove email citations from inbound messages
            body = _remove_email_citations(body)
        else:
            label = f"[{direction.upper()}]"

        # Format timestamp if available
        time_str = ""
        if timestamp:
            if isinstance(timestamp, str):
                time_str = f" ({timestamp[:19]})"  # Truncate ISO format
            else:
                time_str = f" ({timestamp})"

        # Build formatted message
        formatted.append(f"{label}{time_str}")
        if subject:
            formatted.append(f"Subject: {subject}")
        formatted.append(f"{body.strip()}")
        formatted.append("")  # Empty line between messages

    return "\n".join(formatted)


def _remove_email_citations(body: str) -> str:
    """
    Remove email citation/quote blocks from response body.

    Handles common patterns:
    - Lines starting with ">" (quoted text)
    - "On ... wrote:" blocks
    - "-------- Original Message --------" blocks
    - Polish/German equivalents
    """
    if not body:
        return body

    lines = body.split('\n')
    cleaned_lines = []
    in_quote_block = False

    for line in lines:
        stripped = line.strip()

        # Detect start of quote block
        if any(pattern in stripped.lower() for pattern in [
            'original message',
            'wiadomość oryginalna',
            'ursprüngliche nachricht',
            '-------- ',
            '________',
            'from:',
            'od:',
            'von:',
        ]):
            # Check if this looks like a quote header
            if any(marker in stripped.lower() for marker in ['wrote:', 'napisał:', 'schrieb:', 'sent:', 'wysłano:']):
                in_quote_block = True
                continue

        # Skip lines starting with ">" (quoted text)
        if stripped.startswith('>'):
            continue

        # Skip "On date, person wrote:" patterns
        if re.match(r'^(On|W dniu|Am)\s+.+\s+(wrote|napisał|schrieb):', stripped, re.IGNORECASE):
            in_quote_block = True
            continue

        # If in quote block, skip until we hit a non-quoted line
        if in_quote_block:
            if stripped and not stripped.startswith('>') and not stripped.startswith('|'):
                # Check if this looks like new content (not continuation of quote)
                if len(stripped) > 10 and not any(c in stripped[:20] for c in ['>', '|', ':']):
                    in_quote_block = False
                    cleaned_lines.append(line)
            continue

        cleaned_lines.append(line)

    # Remove excessive blank lines
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()