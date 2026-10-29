from openai import AsyncOpenAI

from backend.app.schemas.llm import SupportClassification


MODEL = "gpt-6-luna"
INSTRUCTIONS = (
    "Classify the support message as billing, technical, or other. "
    "Set needs_human_review to true when the request is ambiguous or risky."
)


def create_openai_client(
    timeout=30.0,
    max_retries=2,
) -> AsyncOpenAI:
    """Create a client that reads OPENAI_API_KEY from the environment."""

    return AsyncOpenAI(
        timeout=timeout,
        max_retries=max_retries,
    )


async def classify_support_message(
    message: str,
    client: AsyncOpenAI,
) -> SupportClassification:
    """Classify one support message using a structured model response."""
    if not message.strip():
        raise ValueError("Support message must not be empty")

    response = await client.responses.parse(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=message,
        text_format=SupportClassification,
        max_output_tokens=200,
    )

    if response.output_parsed is None:
        raise ValueError("The model did not return a support classification")

    return response.output_parsed

