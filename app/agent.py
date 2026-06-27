# ruff: noqa
import datetime
from zoneinfo import ZoneInfo
import re
import sys
from typing import Any
import os
import google.auth

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.workflow import Workflow, START, node
from google.adk.agents.context import Context
from google.genai import types

from app.mcp_decryption_server import decrypt_file

use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "False") == "True"

if use_vertex:
    try:
        _, project_id = google.auth.default()
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    except Exception:
        os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
else:
    # Clear Google Cloud environment variables so Google GenAI uses GEMINI_API_KEY
    os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
    os.environ.pop("GOOGLE_CLOUD_LOCATION", None)
    os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)


# --- Tools ---

def request_decryption(ctx: Context, file_path: str) -> str:
    """Requests decryption of a local file.

    Args:
        file_path: The absolute path of the file to decrypt.
    """
    ctx.state["requires_decryption"] = True
    ctx.state["file_path"] = file_path
    return f"Decryption request registered for file: {file_path}."


async def decrypt_file_tool(ctx: Context, file_path: str) -> str:
    """Decrypts a local file using the secure raw key stored in workflow state.

    Args:
        file_path: The absolute path of the file to decrypt.
    """
    key = ctx.state.get("secure_raw_key", "")
    if not key:
        return "Error: No decryption key found in security context."

    try:
        # Call the server's decryption logic directly in-memory to prevent subprocess overhead
        return decrypt_file(file_path, key)
    except Exception as e:
        return f"Error executing local file decryption: {str(e)}"


# --- Agents ---

triage_agent = Agent(
    name="triage_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Triage Agent for SafeHaven. Your job is to analyze the user's request.\n"
        "If the user is asking to decrypt a file, you must call the `request_decryption` tool "
        "with the absolute path of the file.\n"
        "If no file decryption is requested, answer the user's question directly."
    ),
    tools=[request_decryption],
)

execution_agent = Agent(
    name="execution_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Execution Agent for SafeHaven. You have access to local file decryption tools.\n"
        "Your task is to decrypt the file at the path provided in your input.\n"
        "Call the `decrypt_file_tool` with the file path to perform the decryption.\n"
        "Do not ask the user for the key; it is already stored and handled securely in the environment.\n"
        "Once decrypted, present the decrypted content clearly to the user."
    ),
    tools=[decrypt_file_tool],
)


# --- Workflow Nodes ---

@node(name="security_node")
def security_node(ctx: Context, node_input: str) -> str:
    # 1. Backtracking check
    if ".." in node_input or "..\\" in node_input or "../" in node_input:
        ctx.route = "block"
        return "[BLOCKED] Security violation: Input contains backtracking directories ('..')."

    # 2. Block override/bypass phrases
    blocked_phrases = ["override admin", "bypass"]
    prompt_lower = node_input.lower()
    if any(phrase in prompt_lower for phrase in blocked_phrases):
        ctx.route = "block"
        return "[BLOCKED] Security violation: Request matches blocked phrases ('override admin' or 'bypass')."

    # 3. Intercept key and scrub PII
    # Capture password/key
    key_pattern = r"(?i)\b(?:key|password|pass|pwd|secret)[:=\s]+([A-Za-z0-9_]+)\b"
    key_match = re.search(key_pattern, node_input)
    
    raw_key = ""
    scrubbed_prompt = node_input
    
    if key_match:
        raw_key = key_match.group(1)
        # Scrub key
        scrubbed_prompt = re.sub(
            r"(?i)(\b(?:key|password|pass|pwd|secret)[:=\s]+)[A-Za-z0-9_]+\b",
            r"\1[SCRUBBED_KEY]",
            scrubbed_prompt
        )

    # Scrub Email PII
    scrubbed_prompt = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[SCRUBBED_EMAIL]",
        scrubbed_prompt
    )

    # Scrub Name PII
    scrubbed_prompt = re.sub(
        r"(?i)\b(?:my name is|i am|name:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
        "name: [SCRUBBED_NAME]",
        scrubbed_prompt
    )

    # Save raw key securely in-memory inside session state
    if raw_key:
        ctx.state["secure_raw_key"] = raw_key

    ctx.route = "triage"
    return scrubbed_prompt


@node(name="block_node")
def block_node(node_input: str) -> str:
    return node_input


@node(name="triage_router")
def triage_router(ctx: Context, node_input: Any) -> Any:
    if ctx.state.get("requires_decryption"):
        ctx.route = "execution"
        return ctx.state.get("file_path")
    else:
        ctx.route = "respond"
        return node_input


@node(name="respond_directly_node")
def respond_directly_node(node_input: Any) -> Any:
    return node_input


# --- Graph Definition ---

safehaven_supervisor = Workflow(
    name="safehaven_supervisor",
    description="Zero-trust multi-agent supervisor with pre-execution security layer.",
    edges=[
        (START, security_node),
        (security_node, {
            "block": block_node,
            "triage": triage_agent,
        }),
        (triage_agent, triage_router),
        (triage_router, {
            "execution": execution_agent,
            "respond": respond_directly_node,
        }),
    ],
)

app = App(
    root_agent=safehaven_supervisor,
    name="app",
)

root_agent = safehaven_supervisor

