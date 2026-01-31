"""Unified tool execution loop for both OAuth and API key backends.

Extracted from ``api_client.py`` lines 900-1178 to eliminate the duplicated
OAuth vs API-key tool loops.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Iterator, List, Optional, TYPE_CHECKING

from core.logging import get_logger
from tools.base import ToolResult, ToolStatus

if TYPE_CHECKING:
    from tools import ToolRegistry
    from core.command_validator import CommandValidatorChain
    from core.response_analyzer import ResponseAnalyzer
    from core.auto_executor import AutoExecutor

logger = get_logger(__name__)

MAX_TOOL_ROUNDS = 5


def prepare_tool_input(
    tool_name: str,
    tool_input: Dict[str, Any],
    command_validator: Optional[Any] = None,
) -> tuple[Dict[str, Any], Optional[str], List[str]]:
    """Validate and normalize tool input before execution.

    Args:
        tool_name: Name of the tool being called.
        tool_input: Original tool input from the LLM.
        command_validator: Optional command validator chain.

    Returns:
        ``(fixed_input, validation_error, warnings)``
    """
    if tool_name not in ("bash", "bash_tool"):
        return tool_input, None, []

    fixed_input = tool_input
    warnings: List[str] = []
    validation_error: Optional[str] = None

    cmd = fixed_input.get("command", "")
    if cmd and command_validator:
        result = command_validator.validate(cmd)
        warnings.extend(result.warnings)
        if result.is_valid:
            if result.transformed_command and result.transformed_command != cmd:
                logger.debug("CommandValidator transformed: %s -> %s", cmd, result.transformed_command)
                fixed_input = {**fixed_input, "command": result.transformed_command}
        else:
            logger.warning("Command blocked: %s", result.error_message)
            validation_error = result.error_message

    # Normalize claude.ai virtual paths
    cwd_value = fixed_input.get("cwd")
    if isinstance(cwd_value, str) and cwd_value:
        normalized_cwd = cwd_value
        for prefix in ("/home/claude", "/mnt/user-data"):
            if cwd_value.startswith(prefix):
                suffix = cwd_value[len(prefix):].lstrip("/\\")
                normalized_cwd = os.path.join(os.getcwd(), suffix)
                warnings.append(f"Rewrote cwd from {prefix} to local working directory")
                break
        if normalized_cwd != cwd_value:
            fixed_input = {**fixed_input, "cwd": normalized_cwd}

    return fixed_input, validation_error, warnings


def execute_tool_blocks(
    tool_blocks: List[Dict[str, Any]],
    tool_registry: "ToolRegistry",
    command_validator: Optional[Any] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """Execute a batch of tool blocks and return results.

    Returns:
        ``(tool_results, executed_tool_uses, execution_records, all_failed)``
    """
    tool_results: List[Dict[str, Any]] = []
    executed_tool_uses: List[Dict[str, Any]] = []
    execution_records: List[Dict[str, Any]] = []

    for tool_block in tool_blocks:
        tool_name = tool_block.get("name", "")
        tool_id = tool_block.get("id", "")
        tool_input = tool_block.get("input", {})

        tool_input, validation_error, warnings = prepare_tool_input(
            tool_name, tool_input, command_validator
        )

        executed_tool_uses.append({
            "type": "tool_use",
            "id": tool_id,
            "name": tool_name,
            "input": tool_input,
        })

        if validation_error:
            result = ToolResult(status=ToolStatus.ERROR, output="", error=validation_error)
        else:
            result = tool_registry.execute_tool(tool_name, **tool_input)

        execution_records.append({
            "tool_name": tool_name,
            "tool_id": tool_id,
            "tool_input": tool_input,
            "result": result,
            "warnings": warnings,
        })

        # Format result
        if result.status.value == "success":
            tool_content = result.output
        else:
            error_text = result.error or "Unknown error"
            tool_content = (
                f"Error: {error_text}\n{result.output}"
                if result.output and result.output != "(no output)"
                else f"Error: {error_text}"
            )

        if warnings:
            tool_content = "Note: " + " | ".join(warnings) + "\n" + tool_content

        tool_results.append({
            "type": "tool_result",
            "tool_use_id": tool_id,
            "content": tool_content,
        })

    failed = [r for r in execution_records if r["result"].status == ToolStatus.ERROR]
    all_failed = bool(failed) and len(failed) == len(execution_records)

    return tool_results, executed_tool_uses, execution_records, all_failed


def run_tool_loop(
    *,
    stream_fn,
    stream_fn_no_tools=None,
    messages: List[Dict[str, Any]],
    tool_registry: "ToolRegistry",
    command_validator: Optional[Any] = None,
    response_analyzer: Optional["ResponseAnalyzer"] = None,
    auto_executor: Optional["AutoExecutor"] = None,
    add_message,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> Iterator[Dict[str, Any]]:
    """Unified tool execution loop.

    Args:
        stream_fn: Callable that streams events from the LLM for a given round.
                   Signature: ``stream_fn(round: int) -> Iterator[Dict[str, Any]]``
        stream_fn_no_tools: Callable for a final text-only round when tool limit
                            is reached. If None, falls back to error message.
        messages: Mutable message list (modified in place).
        tool_registry: Registry for executing tools.
        command_validator: Optional command validator.
        response_analyzer: Optional response analyzer for auto-execution.
        auto_executor: Optional auto-executor.
        add_message: Callable ``(role, content) -> None`` to add to history.
        max_rounds: Maximum tool execution rounds.

    Yields:
        Stream events.
    """
    tool_round = 0

    while tool_round < max_rounds:
        tool_blocks: List[Dict[str, Any]] = []
        assistant_text: List[str] = []

        for event in stream_fn(tool_round):
            if event.get("type") == "tool_calls_complete":
                tool_blocks.extend(event.get("tool_blocks", []))
            if event.get("type") == "text":
                assistant_text.append(event.get("content", ""))
            yield event

        # Auto-execution check
        if response_analyzer and auto_executor and assistant_text:
            full_response = "".join(assistant_text)
            paste_request = response_analyzer.analyze(full_response)
            if paste_request.detected and paste_request.command:
                if auto_executor.should_auto_execute(paste_request.command):
                    exec_result = auto_executor.execute(paste_request.command)
                    followup = auto_executor.create_followup_message(
                        paste_request.command, exec_result
                    )
                    add_message("user", followup)
                    tool_round -= 1
                    continue

        if not tool_blocks:
            if not assistant_text and tool_round > 0:
                add_message("user", "Please provide your complete answer in text (not just thinking).")
                tool_round += 1
                continue
            break

        # Execute tools
        tool_round += 1
        yield {"type": "tool_round_start", "content": f"Tool execution round {tool_round}"}

        tool_results, executed_tool_uses, execution_records, all_failed = execute_tool_blocks(
            tool_blocks, tool_registry, command_validator
        )

        # Yield individual tool events
        for record in execution_records:
            yield {
                "type": "tool_execute",
                "tool_name": record["tool_name"],
                "tool_input": record["tool_input"],
                "result": record["result"],
                "content": "",
            }

        if all_failed:
            error_lines = [
                f"- {r['tool_name']}: {r['result'].error or 'Unknown error'}"
                for r in execution_records if r["result"].status == ToolStatus.ERROR
            ]
            error_text = (
                "Tool execution failed:\n"
                + "\n".join(error_lines)
                + "\n\nPlease adjust the request or paths and try again."
            )
            add_message("assistant", error_text)
            yield {"type": "text", "content": error_text}
            yield {"type": "message_done", "content": ""}
            return

        # Add to history — combine text + tool_use blocks in one assistant message
        assistant_content: List[Dict[str, Any]] = []
        if assistant_text:
            assistant_content.append({"type": "text", "text": "".join(assistant_text)})
        assistant_content.extend(executed_tool_uses)
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results_with_prompt = tool_results.copy()
        failed_tools = [r for r in execution_records if r["result"].status == ToolStatus.ERROR]
        if failed_tools:
            error_summary = "\n".join(
                f"- {r['tool_name']}: {r['result'].error or 'Unknown error'}"
                for r in failed_tools
            )
            tool_results_with_prompt.append({
                "type": "text",
                "text": f"Some tools failed:\n{error_summary}\nAcknowledge errors and suggest next steps.",
            })
        messages.append({"role": "user", "content": tool_results_with_prompt})

        yield {"type": "tool_round_complete", "content": f"Completed {len(tool_results)} tool(s)"}

    if tool_round >= max_rounds:
        if stream_fn_no_tools is not None:
            # Graceful fallback: force a text-only response from the model
            yield {"type": "info", "content": f"Tool limit ({max_rounds}) reached, generating answer..."}
            add_message("user", "You have used all available tool rounds. Please provide your complete answer now based on the information you have gathered so far. Do not request any more tools.")
            fallback_text: List[str] = []
            for event in stream_fn_no_tools():
                if event.get("type") == "text":
                    fallback_text.append(event.get("content", ""))
                yield event
            final = "".join(fallback_text)
            if final:
                add_message("assistant", final)
        else:
            yield {"type": "error", "content": f"Maximum tool rounds ({max_rounds}) reached"}
