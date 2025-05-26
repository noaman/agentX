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



class ADKAGENT:
    def __init__(self,adkagent,callback=None,is_stream=False) -> None:
        self.adkagent = adkagent
        self.callback = callback
        session_service = InMemorySessionService()
        self.USER_ID = f"user_{random.randint(1000, 9999)}"
        self.SESSION_ID = f"session_{random.randint(10000, 99999)}"
        session_service.create_session(app_name=self.adkagent.name, user_id=self.USER_ID, session_id=self.SESSION_ID)

        self.runner = Runner(agent=self.adkagent, app_name=self.adkagent.name, session_service=session_service)
        self.run_config = RunConfig(streaming_mode="sse" if is_stream else None)

        

    async def getLogs(self):
        if self.callback:
            return self.callback.getLogs()
        return []
    
    async def send_query(self, query: str) -> AsyncGenerator[str, None]:
        final_response_text = "Agent did not produce a final response."
        content = types.Content(role='user', parts=[types.Part(text=query)])

        async for event in self.runner.run_async(user_id=self.USER_ID, session_id=self.SESSION_ID, new_message=content, run_config=self.run_config):
            if hasattr(event, 'content_part_delta') and event.content_part_delta:
                delta = event.content_part_delta
                if delta.text:
                    yield delta.text
            # try:
            #     if event.content.parts[0].function_call:
            #         yield str(event.content.parts[0].function_call)
            # except Exception as e:
            #     # logger.error(f"Error during send_query: {e}")
            #     continue

            if event.is_final_response():
                final_response_text = event.content.parts[0].text if event.content and event.content.parts else final_response_text
                break
        yield final_response_text
    



MCP_CONFIG_PATH = "mcp/mcp_config.json"


def getModelClient(model_input,api_keys):
        model_client = None
        provider, model_name = model_input.split(":")
        model_str = f"{provider}/{model_name}"
        if provider == "openai":
            model_client = LiteLlm(api_key=api_keys["OPENAI_API_KEY"], model=model_str)
        elif provider == "gemini":
            model_client = LiteLlm(api_key=api_keys["GEMINI_API_KEY"], model=model_str)
        elif provider == "lm_studio":
            model_client = LiteLlm(api_key="lm_studio", model=model_str,base_url=LM_STUDIO_BASE_URL)
        
        return model_client

async def load_mcp_servers_config(MCP_CONFIG_PATH):
    {}


async def loadmcp_tools(mcp_tool_configs,mcp_servers_config):
    all_tools = []
    tools_by_server = {}
    for tool in mcp_tool_configs:
        tools_by_server.setdefault(tool["server"], []).append(tool["tool"])

    try:
        async with AsyncExitStack() as stack:

            for server_name, tool_list in tools_by_server.items():
                server_config = mcp_servers_config.get("mcpServers", {}).get(server_name)
                if not server_config:
                    continue

                command = server_config.get("command")
                if command in ["uvx","uv", "npx"]:
                    conn_params = StdioServerParameters(command=command, args=server_config.get("args", []), env=server_config.get("env"))
                elif command == "remote":
                    conn_params = SseServerParams(url=server_config.get("end_point"))
                else:
                    continue

                tools, _exit_stack = await MCPToolset.from_server(connection_params=conn_params, async_exit_stack=stack)
                print("Reached in get_agent 8.5 .......",tool_list)
                for t in tools:
                    if t.name in tool_list:
                        print(t.auth_scheme)
                        print(t.mcp_tool)
                        print("Reached in get_agent 8.6 .......",t.name)
                        all_tools.append(t)

    except Exception as e:
        await stack.aclose()
    finally:
        await _exit_stack.aclose()

    return all_tools

async def getADKAgent(prompt_config,model_str,temperature,max_tokens,api_keys):
    callback = Callback()
    mcp_servers_config = None
    with open(MCP_CONFIG_PATH, 'r') as f:
        mcp_servers_config =  json.load(f)
    agent_name = prompt_config.get("name","Chat Buddy")
    background = prompt_config.get("background","you are a friendly agent")
    input_values = prompt_config.get("input_values","you will be asked some questions")
    task_details = prompt_config.get("task_details","respond to the question")
    output_format = prompt_config.get("output_format","responnd in a friendly manner")
    mcp_tools_configured = prompt_config.get("mcp_tools",None)
    today = date.today()

    instructions =f"""
    <your_background>:{background}\n\n
    <input_type_expected>"{input_values}\n\n
    <steps_to_perform>"{task_details}\n\n
    <output_format_for_response>"{output_format}\n\n
    <current_context>:Todays date is {today}\n\n
    """
    model_client = getModelClient(model_str,api_keys)

    mcp_tools_to_add = []
    if mcp_tools_configured:
        mcp_tools_to_add = await loadmcp_tools(mcp_tools_configured,mcp_servers_config)

    generate_content_config = types.GenerateContentConfig(temperature=temperature, max_output_tokens=max_tokens)
    adk_agent=LlmAgent(
            name=prompt_config.get("name","Chat Buddy").replace(" ", "_"),
            description=prompt_config.get("background",""),
            instruction=instructions,
            model=model_client,
            generate_content_config=generate_content_config,
            tools=mcp_tools_to_add,
            before_model_callback= callback.guardrail_callback,
            before_tool_callback=callback.before_tool_callback,
            after_tool_callback=callback.after_tool_callback,
            after_model_callback=callback.after_model_callback,
            after_agent_callback=callback.after_agent_callback,
        )
    
  
    adk_agent_object = ADKAGENT(adkagent=adk_agent, callback=callback)
    return callback,adk_agent_object




# async def send_query(self, query: str) -> AsyncGenerator[str, None]:
    