# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mcp>=1.0.0",
#     "openai>=1.0.0",
#     "anthropic>=0.30.0",
#     "google-genai>=1.0.0",
# ]
# ///
"""Stdio MCP server for cross-model code review using portable skills."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

SKILL_SEARCH_PATHS = [
    REPO_ROOT / "dist" / "flat" / "skills",
    REPO_ROOT / "skills",
    Path.home() / ".craft-agent" / "workspaces" / "my-workspace" / "skills",
]

MAX_FILE_LINES = 8000


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _op_get(title: str) -> str | None:
    try:
        result = subprocess.run(
            ["op", "item", "get", title, "--fields", "credential", "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                return data.get("value") or data.get("credential")
            return str(data).strip() if data else None
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def _resolve_credential(env_var: str, op_title: str) -> str | None:
    value = os.environ.get(env_var)
    if value:
        return value
    return _op_get(op_title)


def _review_openai(client: Any, model: str, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def _review_anthropic(client: Any, model: str, system: str, user: str) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def _review_google(client: Any, model: str, system: str, user: str) -> str:
    from google.genai import types
    response = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
        ),
    )
    return response.text


PROVIDER_DEFS: dict[str, dict[str, Any]] = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "op_title": "OpenAI API Key",
        "models": ["gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "default_model": "gpt-4o",
        "review_fn": _review_openai,
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "op_title": "Anthropic API Key",
        "models": [
            "claude-opus-4-6",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ],
        "default_model": "claude-sonnet-4-6",
        "review_fn": _review_anthropic,
    },
    "google": {
        "env_var": "GOOGLE_API_KEY",
        "op_title": "Google AI API Key",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
        "default_model": "gemini-2.5-flash",
        "review_fn": _review_google,
    },
}


# ---------------------------------------------------------------------------
# Provider discovery and client management
# ---------------------------------------------------------------------------

class ProviderCollection:
    def __init__(self) -> None:
        self._available: dict[str, dict[str, Any]] = {}
        self._clients: dict[str, Any] = {}
        self._discover()

    def _discover(self) -> None:
        for name, defn in PROVIDER_DEFS.items():
            key = _resolve_credential(defn["env_var"], defn["op_title"])
            if key:
                self._available[name] = {**defn, "_key": key}

    def list_providers(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "models": defn["models"],
                "default_model": defn["default_model"],
            }
            for name, defn in self._available.items()
        ]

    def get_client(self, provider: str) -> Any:
        if provider not in self._available:
            raise ValueError(
                f"Provider '{provider}' not available. "
                f"Available: {list(self._available)}. "
                f"Set {PROVIDER_DEFS[provider]['env_var']} or add "
                f"'{PROVIDER_DEFS[provider]['op_title']}' to 1Password."
            )
        if provider not in self._clients:
            key = self._available[provider]["_key"]
            self._clients[provider] = self._make_client(provider, key)
        return self._clients[provider]

    @staticmethod
    def _make_client(provider: str, key: str) -> Any:
        if provider == "openai":
            import openai
            return openai.OpenAI(api_key=key)
        if provider == "anthropic":
            import anthropic
            return anthropic.Anthropic(api_key=key)
        if provider == "google":
            from google import genai
            return genai.Client(api_key=key)
        raise ValueError(f"Unknown provider: {provider}")

    def review(self, provider: str, model: str | None, system: str, user: str) -> tuple[str, str]:
        defn = self._available[provider]
        model = model or defn["default_model"]
        client = self.get_client(provider)
        review_text = defn["review_fn"](client, model, system, user)
        return model, review_text


# ---------------------------------------------------------------------------
# Skill resolution
# ---------------------------------------------------------------------------

def resolve_skill(slug: str) -> str:
    if Path(slug).is_absolute() and Path(slug).exists():
        return Path(slug).read_text()

    for base in SKILL_SEARCH_PATHS:
        candidates = [
            base / slug / "SKILL.md",
            base / f"{slug}.md",
            base / slug,
        ]
        for path in candidates:
            if path.is_file():
                text = path.read_text()
                if text.startswith("---"):
                    end = text.find("---", 3)
                    if end != -1:
                        text = text[end + 3:].strip()
                return text

    searched = [str(p) for p in SKILL_SEARCH_PATHS]
    raise FileNotFoundError(
        f"Skill '{slug}' not found. Searched:\n" +
        "\n".join(f"  - {p}" for p in searched)
    )


def read_file(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    lines = p.read_text().splitlines()
    if len(lines) > MAX_FILE_LINES:
        truncated = lines[:MAX_FILE_LINES]
        return (
            "\n".join(truncated)
            + f"\n\n[TRUNCATED: file has {len(lines)} lines, showing first {MAX_FILE_LINES}]"
        )
    return p.read_text()


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

def create_server(providers: ProviderCollection) -> Server:
    server = Server("cross-review")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_providers",
                description=(
                    "List available LLM providers and their models. "
                    "Providers are auto-discovered from API keys in "
                    "environment variables or 1Password."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="review",
                description=(
                    "Send code to another LLM for review using a skill "
                    "from this repo. The skill's markdown content becomes "
                    "the system prompt; the code becomes the user prompt."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to review.",
                        },
                        "skill_slug": {
                            "type": "string",
                            "description": (
                                "Skill to apply. Can be a slug (e.g., 'hostile-review', "
                                "'self-review', 'over-engineering-audit'), a relative "
                                "skill name, or an absolute path to a SKILL.md file."
                            ),
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider name (e.g., 'openai', 'anthropic', 'google').",
                        },
                        "model": {
                            "type": "string",
                            "description": "Model to use. Optional — defaults to provider's default.",
                        },
                    },
                    "required": ["file_path", "skill_slug", "provider"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "list_providers":
            available = providers.list_providers()
            if not available:
                return [TextContent(
                    type="text",
                    text=(
                        "No providers available.\n\n"
                        "To enable providers, set API keys:\n"
                        + "\n".join(
                            f"  - {n}: export {d['env_var']}=<key>"
                            for n, d in PROVIDER_DEFS.items()
                        )
                    ),
                )]
            return [TextContent(
                type="text",
                text=json.dumps({"providers": available}, indent=2),
            )]

        if name == "review":
            file_path = arguments["file_path"]
            skill_slug = arguments["skill_slug"]
            provider = arguments["provider"]
            model = arguments.get("model")

            skill_text = resolve_skill(skill_slug)
            code_text = read_file(file_path)
            user_prompt = f"Review this code:\n\n```\n{code_text}\n```"

            used_model, review_text = providers.review(
                provider, model, skill_text, user_prompt,
            )

            return [TextContent(
                type="text",
                text=json.dumps({
                    "provider": provider,
                    "model": used_model,
                    "skill": skill_slug,
                    "file": file_path,
                    "review": review_text,
                }, indent=2),
            )]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


async def main() -> None:
    providers = ProviderCollection()
    server = create_server(providers)
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(main())
