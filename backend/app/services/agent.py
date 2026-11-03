import json
from uuid import uuid4

from openai import AsyncOpenAI

from backend.app.schemas.tool_approval import ToolApproval
from backend.app.services.approval_store import (
    execute_approved_tool,
    get_agent_run,
    get_approval,
    save_agent_run,
    save_approval,
    take_agent_run,
)
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
    """Start a bounded model/tool loop."""
    input_items: list[object] = [
        {
            "role": "user",
            "content": message,
        }
    ]

    return await _run_agent_loop(
        input_items,
        client,
        user_id,
        max_steps,
    )


async def resume_agent(
    approval_id: str,
    current_user_id: int,
    client: AsyncOpenAI,
    max_steps: int = 5,
) -> str | ToolApproval:
    """Execute an approved tool and continue its saved agent run."""
    approval = get_approval(approval_id)

    if approval is None:
        raise KeyError("Approval not found")

    if approval.user_id != current_user_id:
        raise PermissionError(
            "Cannot resume another user's agent"
        )

    if approval.status != "approved":
        raise RuntimeError("Approval is not approved")

    if get_agent_run(approval_id) is None:
        raise RuntimeError("Agent state not found")

    result = await execute_approved_tool(
        approval_id,
        current_user_id,
    )
    input_items = take_agent_run(approval_id)

    if input_items is None:
        raise RuntimeError("Agent state not found")

    input_items.append(
        {
            "type": "function_call_output",
            "call_id": approval.call_id,
            "output": json.dumps(result),
        }
    )

    return await _run_agent_loop(
        input_items,
        client,
        current_user_id,
        max_steps,
    )


async def _run_agent_loop(
    input_items: list[object],
    client: AsyncOpenAI,
    user_id: int,
    max_steps: int,
) -> str | ToolApproval:
    """Continue a bounded model/tool loop from existing input state."""

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
                save_agent_run(approval.approval_id, input_items)
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
