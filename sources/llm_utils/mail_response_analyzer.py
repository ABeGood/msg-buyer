from typing import List, Dict, Any
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")
if not OPENAI_TOKEN:
    raise ValueError("OPENAI_TOKEN environment variable is required but not set")

LLM_CLIENT = OpenAI(api_key=OPENAI_TOKEN, timeout=120, max_retries=3)

class PriceAgent:
    """Price collection agent using chat completions API for price information extraction and routing"""

    def __init__(self, llm_model: str = "gpt-5-mini"):
        self.llm_client = LLM_CLIENT
        self.llm_model = llm_model

    def process_price(
        self,
        user_query: str,
        last_n_messages: List[Message],
        current_price_info: str = "",
    ) -> PriceAgentResponse:
        """
        Process user price input and extract price information

        Args:
            user_query: The user's current query containing price information
            last_n_messages: Recent conversation messages for context
            current_price_info: Currently collected price information

        Returns:
            PriceAgentResponse: Validated price collection response
        """
        # Format conversation history
        conversation_history = self._format_conversation_history(last_n_messages[-6:-1])

        # Create prompt from template
        prompt = PRICE_AGENT_PROMPT.format(
            conversation_history=conversation_history,
            user_message=user_query,
            current_price_info=current_price_info
        )

        # Get JSON schema from Pydantic model
        schema = {
            "name": "price_agent_response",
            "strict": True,
            "schema": PriceAgentResponse.model_json_schema()
        }

        # Call OpenAI with structured output
        messages: List[ChatCompletionMessageParam] = [
            {"role": "system", "content": prompt}
        ]

        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": schema
            },
            reasoning_effort= "low",
            # temperature=0.1
        )

        # Parse and validate response
        response_content = response.choices[0].message.content
        price_result = PriceAgentResponse.model_validate_json(response_content)

        return price_result

    def _format_conversation_history(self, messages: List[Message]) -> str:
        """Format conversation messages into readable history string"""
        if not messages:
            return "No previous conversation history."

        formatted_messages = []
        for msg in messages:
            author = msg.get_author()
            content = msg.get_content()
            author = 'Assistant' if str(author).startswith('bot') else 'User'
            formatted_messages.append(f"{author}: {content}")

        return "\n".join(formatted_messages)