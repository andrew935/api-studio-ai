import json
from uuid import uuid4

from openai import AsyncOpenAI

from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.approval_store import save_approval
from backend.app.services.llm_client import MODEL
from backend.app.services.tool_calling import (
    AGENT_TOOLS,
    TOOL_HANDLERS,
    requires_approval,
)


async def run_agent(
    message: str,
    client: AsyncOpenAI,
    user_id: int,
    max_steps: int = 5,
) -> str | ToolApproval:
    """Run a bounded model/tool loop until the model returns final text."""
    input_items = [
        {
            "role": "user",
            "content": message,
        }
    ]

    for step in range(max_steps):
        response = await client.responses.create(
            model=MODEL,
            input=input_items,
            tools=AGENT_TOOLS,
        )

        input_items.extend(response.output)
        tool_calls = []

        for item in response.output:
            if item.type == "function_call":
                tool_calls.append(item)

        if not tool_calls:
            return response.output_text

        if step == max_steps - 1:
            raise RuntimeError("Agent reached the maximum number of steps")

        for tool in tool_calls:
            tool_function = TOOL_HANDLERS.get(tool.name)

            if tool_function is None:
                raise RuntimeError("Unknown tool")

            arguments = json.loads(tool.arguments)

            if requires_approval(tool.name):
                approval = ToolApproval(
                    approval_id=str(uuid4()),
                    user_id=user_id,
                    tool_name=tool.name,
                    arguments=arguments,
                    call_id=tool.call_id,
                    status="pending",
                )
                save_approval(approval)
                return approval

            result = await tool_function(**arguments)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool.call_id,
                    "output": json.dumps(result),
                }
            )

    raise RuntimeError("Agent reached the maximum number of steps")
