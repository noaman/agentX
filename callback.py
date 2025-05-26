from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Any, Dict, Optional
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.base_tool import BaseTool
import re
from datetime import datetime

class Callback:
#                     "description": tool.description,
    def __init__(self):
        self.agent_logs = []

    def _add_log(self, log_type: str, message: str, agent_name: str = "", extra_data: Dict = None):
        """Add a formatted log entry with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "type": log_type,
            "agent": agent_name,
            "message": message,
            "data": extra_data or {}
        }
        self.agent_logs.append(log_entry)

    def getLogs(self):
        """Return formatted logs for display"""
        formatted_logs = []
        for log in self.agent_logs:
            timestamp = log.get("timestamp", "")
            log_type = log.get("type", "").upper()
            agent = log.get("agent", "")
            message = log.get("message", "")
            
            # Create a formatted log string
            if agent:
                formatted_log = f"[{timestamp}] {log_type} | {agent} | {message}"
            else:
                formatted_log = f"[{timestamp}] {log_type} | {message}"
            
            formatted_logs.append(formatted_log)
        
        print("SENDING FORMATTED LOGS ::::::::::::::::", formatted_logs)
        return formatted_logs
    
    def getLogStats(self):
        """Return statistics about the logs"""
        stats = {
            "total_logs": len(self.agent_logs),
            "by_type": {},
            "by_agent": {},
            "recent_activity": []
        }
        
        for log in self.agent_logs:
            log_type = log.get("type", "unknown")
            agent = log.get("agent", "unknown")
            
            # Count by type
            stats["by_type"][log_type] = stats["by_type"].get(log_type, 0) + 1
            
            # Count by agent
            stats["by_agent"][agent] = stats["by_agent"].get(agent, 0) + 1
        
        # Get recent activity (last 5 logs)
        stats["recent_activity"] = self.agent_logs[-5:] if len(self.agent_logs) > 5 else self.agent_logs
        
        return stats
    
    def clearLogs(self):
        """Clear all logs"""
        self.agent_logs.clear()
        
    def getLogsAsJson(self):
        """Return logs as JSON for export"""
        return self.agent_logs
    
    def guardrail_callback(self,callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
            """
            A simple callback function that modifies the LLM request before sending it.
            """
            # Modify the request here if needed

            agent_name = callback_context.agent_name
            self._add_log("guardrail", f"Checking request for inappropriate content", agent_name)
            print(f"Calling guardrail_callback for agent '{agent_name}' {callback_context}")
            # Inspect the last user message in the request contents
            last_user_message = ""
            if llm_request.contents and llm_request.contents[-1].role == 'user':
                if llm_request.contents[-1].parts:
                    last_user_message = llm_request.contents[-1].parts[0].text
            try:
                if "FUCKING" in last_user_message.upper():
                # Return an LlmResponse to skip the actual LLM call
                    self._add_log("guardrail", "Request blocked due to inappropriate language", agent_name)
                    return LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="Your request is blocked because of inappropriate language.")],
                        )
                    )
                else:
                    self._add_log("guardrail", "Request passed content filter", agent_name)
            except Exception as e:
                self._add_log("error", f"Error in guardrail_callback: {e}", agent_name)
                print(f"[Callback] Error in guardrail_callback: {e}")
                # Return None to allow the (modified) request to go to the LLM
                return None
            
            return None


    def before_tool_callback(self,tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext) -> Optional[Dict]:
        """Inspects/modifies tool args or skips the tool call."""
        agent_name = tool_context.agent_name
        tool_name = tool.name
        args_str = str(args)[:100] + "..." if len(str(args)) > 100 else str(args)
        self._add_log("tool_start", f"Starting tool '{tool_name}' with args: {args_str}", agent_name, {"tool": tool_name, "args": args})
        print(f"Before tool call for tool '{tool_name}' in agent '{agent_name}' with args: {args}")
        return None
    
    def after_tool_callback(self,tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict) -> Optional[Dict]:
        """Inspects/modifies tool args or skips the tool call."""
        agent_name = tool_context.agent_name
        tool_name = tool.name
        response_str = str(tool_response)[:100] + "..." if len(str(tool_response)) > 100 else str(tool_response)
        self._add_log("tool_complete", f"Tool '{tool_name}' completed with response: {response_str}", agent_name, {"tool": tool_name, "response": tool_response})

        print(f"Tool call completed for '{tool_name}' in agent '{agent_name}' with response: {tool_response}")
        return None
    

    def after_model_callback(self,callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
        """Inspects/modifies tool args or skips the tool call."""
        agent_name = callback_context.agent_name
        
        # Safely get token usage
        token_usage = 0
        try:
            print("LLM RESPONSE ::::::::::::::::",llm_response)
            if hasattr(llm_response, 'token_usage') and llm_response.token_usage:
                if hasattr(llm_response.token_usage, 'total_tokens'):
                    token_usage = llm_response.token_usage.total_tokens
                elif hasattr(llm_response.token_usage, 'total'):
                    token_usage = llm_response.token_usage.total
                else:
                    token_usage = str(llm_response.token_usage)
        except Exception as e:
            print(f"Could not get token usage: {e}")
            token_usage = "unknown"
        
        # Get response content preview
        response_preview = ""
        try:
            if llm_response.content and llm_response.content.parts:
                response_text = llm_response.content.parts[0].text or ""
                response_preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
        except Exception as e:
            response_preview = "Could not extract response content"
        
        self._add_log("model_response", f"Model response received (tokens: {token_usage}): {response_preview}", agent_name, {"tokens": token_usage})
        print(f"After model call for agent '{agent_name}' with response: {llm_response}\n Token usage: {token_usage}")
        return None
    

    def after_agent_callback(self,callback_context: CallbackContext) -> Optional[LlmResponse]:
        """Inspects/modifies tool args or skips the tool call."""
        agent_name = callback_context.agent_name
        invocation_id = callback_context.invocation_id
        current_state = callback_context.state.to_dict()

        self._add_log("agent_response", f"\n[Callback] Exiting agent: {agent_name} (Inv: {invocation_id})")
        return None