import json

from openai import AsyncOpenAI

from backend.app.services.llm_client import MODEL


BALANCE_TOOL = {
    "type": "function",
    "name": "get_customer_balance",
    "description": "Get a customer's balance by customer ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "integer",
            },
        },
        "required": ["customer_id"],
        "additionalProperties": False,
    },
    "strict": True,
}

DELETE_CUSTOMER_TOOL = {
    "type": "function",
    "name": "delete_customer",
    "description": "Delete a customer by ID after human approval.",
    "parameters": {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "integer",
            },
        },
        "required": ["customer_id"],
        "additionalProperties": False,
    },
    "strict": True,
}

AGENT_TOOLS = [BALANCE_TOOL, DELETE_CUSTOMER_TOOL]
SENSITIVE_TOOLS = {"delete_customer"}


async def get_customer_balance(customer_id: int) -> dict[str, int | float]:
    """Return deterministic demo data for the tool-calling lesson."""
    return {
        "customer_id": customer_id,
        "balance": 150.0,
    }


async def delete_customer(customer_id: int) -> dict[str, int | str]:
    """Return a deterministic demo result without deleting real data."""
    return {
        "customer_id": customer_id,
        "status": "deleted",
    }


def requires_approval(tool_name: str) -> bool:
    return tool_name in SENSITIVE_TOOLS


TOOL_HANDLERS = {
    "get_customer_balance": get_customer_balance,
    "delete_customer": delete_customer,
}


async def answer_with_tools(
    message: str,
    client: AsyncOpenAI,
) -> str:
    """Answer a message and execute explicitly allowed function tools."""
    first_response = await client.responses.create(
        model=MODEL,
        input=message,
        tools=[BALANCE_TOOL],
    )

    tool_calls = []

    for item in first_response.output:
        if item.type == "function_call":
            tool_calls.append(item)

    if not tool_calls:
        return first_response.output_text

    tool_outputs = []

    for tool_call in tool_calls:
        if tool_call.name != BALANCE_TOOL["name"]:
            raise ValueError("Unknown tool")

        tool_function = TOOL_HANDLERS.get(tool_call.name)

        if tool_function is None:
            raise ValueError("Unknown tool")

        arguments = json.loads(tool_call.arguments)
        result = await tool_function(**arguments)

        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": json.dumps(result),
            }
        )

    final_response = await client.responses.create(
        model=MODEL,
        previous_response_id=first_response.id,
        input=tool_outputs,
        tools=[BALANCE_TOOL],
    )

    return final_response.output_text
