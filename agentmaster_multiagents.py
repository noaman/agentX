from contextlib import AsyncExitStack
from datetime import date
import json
import random
from typing import AsyncGenerator
from google.genai import types
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters, SseServerParams
from google.adk.agents.callback_context import CallbackContext

from callback import Callback
from constants import LM_STUDIO_BASE_URL


async def getMultiAgent(prompt_config,model_str,temperature,max_tokens,api_keys):
    {}

