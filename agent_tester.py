import gradio as gr
import json
import os
import asyncio
import re
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import threading

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(project_root)


# Global cache for all MCP tools
all_tools_cache = None
mcp_servers = []
mcp_loaded = False

from agentmaster import getADKAgent
from constants import ALL_MODELS, GEMINI_API_KEY, OPENAI_API_KEY
from mcp_client import MCPCLient

class AgentTester:
    def __init__(self):
        self.chat_history = []
        self.agent_logs = []
        self.callback_logs = []
        self.callback = None
        self.mcp_tools = []
        self.selected_mcp_tools = []
        self.adk_agent = None
        self.agent_json = None
        self.selected_model = None
        self.selected_config = None
        self.streaming = False
        self.welcome_message = ""
        self.messages = []
        self.config_content = {}
        self.model_params = {
            "temperature": 1.0,
            "max_tokens": 2000,
        }
        self.filter_logs = {
            "event_types": ["start", "end", "handoff", "tool"],
            "log_types": ["info", "warning", "error"],
            "search_term": "",
        }
        self.token_metrics = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }
        self.is_processing = False

    def list_config_files(self, config_dir="agent_config"):
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            return []
        config_files = sorted([f for f in os.listdir(config_dir) if f.endswith(".json")])
        return config_files

    def load_config_content(self, config_file, config_dir="agent_config"):
        try:
            print("Reached in load_config_content 1 .......",config_file)
            if config_file == "mcp_config.json":
                config_path = os.path.join("mcp", config_file)
            else:
                config_path = os.path.join(config_dir, config_file)
                
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading config file: ", e)
            self.agent_logs.append(f"Error loading config file: {e}")
            return {}

    async def initialize_agent(self, model_input: str, config_file: str):
        print("Reached in initialize_agent 1 .......")
        self.adk_agent = None
        self.agent_json = None
        self.selected_model = model_input
        self.mcp_tools = []
        self.selected_mcp_tools = []
        self.chat_history = []
        self.agent_logs = []
        self.streaming = False
        self.selected_config = config_file
        self.welcome_message = ""
        self.callback_logs = []
        self.messages = []
        self.is_processing = False

        try:
            self.config_content = self.load_config_content(config_file)
            
            if "mcp_tools" in self.config_content:
                self.selected_mcp_tools = self.config_content["mcp_tools"]

            api_keys = {
                "GEMINI_API_KEY": GEMINI_API_KEY,
                "OPENAI_API_KEY": OPENAI_API_KEY
            }
            
            self.callback ,self.adk_agent = await getADKAgent(
                self.config_content,
                self.selected_model,
                self.model_params.get("temperature", 0.1),
                self.model_params.get("max_tokens", 1024),
                api_keys=api_keys
            )
            
            # Clear any existing logs from the callback
            if self.callback:
                self.callback.agent_logs.clear()
            
            self.welcome_message = (
                self.config_content.get("welcome_message", "Hello! I'm ready to assist you.")
                + "\n\n model : "
                + str(self.selected_model)
            )
            
            # Add welcome message to chat history
            self.messages.append({"role": "assistant", "content": self.welcome_message})
            
            return True
        except Exception as e:
            print("Failed to initialize agent: ", e)
            self.agent_logs.append(f"Failed to initialize agent: {str(e)}")
            return False

    async def process_query(self, query: str):
        if not self.adk_agent:
            yield "Error: Please initialize an agent first"
            return
        
        self.is_processing = True
        self.callback_logs.clear()
        full_response = ""
        
        try:
            async for chunk in self.adk_agent.send_query(query):
                # Get updated logs from callback
                self.callback_logs = await self.adk_agent.getLogs()
                full_response += chunk
                yield full_response
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.agent_logs.append(error_msg)
            yield error_msg
        finally:
            # Get final logs after processing
            self.callback_logs = await self.adk_agent.getLogs()
            self.is_processing = False

def create_agent_tester_interface():
    agent_tester = AgentTester()
    
    # Minimal CSS for message alignment and processing animation only
    minimal_css = """
    <style>
    /* Compact layout adjustments */
    .gradio-container {
        padding: 8px !important;
    }
    
    .gr-tab-pane {
        padding: 8px !important;
    }
    
    .gr-tabs {
        margin-bottom: 8px !important;
    }
    
    .gr-button {
        margin: 2px !important;
    }
    
    .gr-form {
        gap: 8px !important;
    }
    
    .user-message {
        text-align: right !important;
        margin-left: auto !important;
        background: none !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 12px 16px !important;
        max-width: 70% !important;
        margin-bottom: 8px !important;
    }
    
    .bot-message {
        text-align: left !important;
        margin-right: auto !important;
        background: #f8f9fa !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 18px 18px 18px 4px !important;
        padding: 12px 16px !important;
        max-width: 70% !important;
        margin-bottom: 8px !important;
    }
    
    .thinking-dots {
        display: inline-block;
        margin-left: 4px;
    }
    
    .dot1, .dot2, .dot3 {
        animation: thinking 1.5s infinite;
    }
    
    .dot2 {
        animation-delay: 0.3s;
    }
    
    .dot3 {
        animation-delay: 0.6s;
    }
    
    @keyframes thinking {
        0%, 60%, 100% {
            opacity: 0.3;
        }
        30% {
            opacity: 1;
        }
    }
    
    /* MCP Tools Interface Improvements */
    .dataframe tbody tr {
        cursor: pointer !important;
        transition: background-color 0.2s ease !important;
    }
    
    .dataframe tbody tr:hover {
        background-color: #f8f9fa !important;
    }
    
    .dataframe tbody tr:active {
        background-color: #e9ecef !important;
        transform: scale(0.98) !important;
        transition: all 0.1s ease !important;
    }
    
    /* Prevent text selection on tool rows */
    .dataframe tbody tr td {
        user-select: none !important;
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        -ms-user-select: none !important;
    }
    
    /* Add visual feedback for tool actions */
    .dataframe tbody tr td:last-child {
        font-weight: bold !important;
        text-align: center !important;
    }
    
    /* Success/Error feedback styling */
    .tool-feedback {
        padding: 8px 12px !important;
        border-radius: 4px !important;
        margin: 4px 0 !important;
        font-size: 12px !important;
        font-weight: bold !important;
    }
    
    .tool-success {
        background-color: #d4edda !important;
        color: #155724 !important;
        border: 1px solid #c3e6cb !important;
    }
    
    .tool-error {
        background-color: #f8d7da !important;
        color: #721c24 !important;
        border: 1px solid #f5c6cb !important;
    }
    
    /* Debounce visual feedback */
    .tool-processing {
        opacity: 0.6 !important;
        pointer-events: none !important;
    }
    </style>
    """
    
    with gr.Blocks(
        title="🤖 Agentic AI Interface",
        css=minimal_css
    ) as interface:
        # Main Header
        with gr.Row():
            gr.Markdown("# 🤖 Agents Tester")
        
        with gr.Row():
            # Left Sidebar - Control Panel
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ **Control Center**")
                
                # Status Section
                with gr.Group():
                    gr.Markdown("#### 📊 **Status**")
                    agent_status = gr.HTML(
                        '<div>Agent: Disconnected</div>',
                        elem_id="agent_status"
                    )
                
                # Model Configuration
                with gr.Group():
                    gr.Markdown("#### 🧠 **Model Setup**")
                    model_selector = gr.Dropdown(
                        choices=ALL_MODELS,
                        label="🎯 Select Model",
                        value=ALL_MODELS[0] if ALL_MODELS else None,
                        interactive=True
                    )
                    
                    with gr.Row():
                        with gr.Column(scale=4):
                            config_files = agent_tester.list_config_files()
                            config_selector = gr.Dropdown(
                                choices=config_files,
                                label="📋 Configuration Profile",
                                value=config_files[0] if config_files else None,
                                interactive=True
                            )
                        with gr.Column(scale=1):
                            refresh_config_btn = gr.Button(
                                "🔄",
                                size="sm",
                                variant="secondary",
                                elem_id="refresh_config",
                                elem_classes=["refresh-btn"]
                            )
                            gr.HTML(
                                '<div style="font-size: 10px; color: #6c757d; text-align: center; margin-top: 2px;">Refresh configs</div>',
                                elem_id="refresh_tooltip"
                            )
                
                # Advanced Parameters
                with gr.Accordion("🔧 **Advanced Parameters**", open=False):
                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=0.2,
                        step=0.1,
                        label="🌡️ Temperature"
                    )
                    max_tokens = gr.Slider(
                        minimum=100,
                        maximum=8000,
                        value=2000,
                        step=100,
                        label="📝 Max Tokens"
                    )
                
                # Initialize Button
                init_btn = gr.Button(
                    "🚀 Initialize Agent",
                    variant="primary",
                    size="lg"
                )
                
                # Quick Metrics
                with gr.Group():
                    gr.Markdown("#### 📈 **Performance Metrics**")
                    metrics_display = gr.HTML("""
                        <div>
                            <div>Requests: 0</div>
                            <div>Tokens: 0</div>
                        </div>
                    """)
            
            # Main Content Area
            with gr.Column(scale=4):
                with gr.Tabs() as main_tabs:
                    # Chat Tab
                    with gr.TabItem("💬 Chat Interface", id=0):
                        with gr.Column():
                            # Placeholder for uninitialized state
                            chat_placeholder = gr.HTML(
                                value="""
                                <div style="text-align: center; padding: 100px 20px; background: #f8f9fa; border-radius: 10px; margin: 20px 0;">
                                    <div style="font-size: 48px; margin-bottom: 20px;">🤖</div>
                                    <h2 style="color: #6c757d; margin-bottom: 15px;">Agent Not Initialized</h2>
                                    <p style="color: #6c757d; font-size: 16px; margin-bottom: 20px;">
                                        Please select a model and configuration, then click "🚀 Initialize Agent" to start chatting.
                                    </p>
                                    <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0;">
                                        <strong>Steps to get started:</strong><br>
                                        1. Select a model from the dropdown<br>
                                        2. Choose a configuration file<br>
                                        3. Click "🚀 Initialize Agent"<br>
                                        4. Start chatting!
                                    </div>
                                </div>
                                """,
                                visible=True
                            )
                            
                            # Actual chat interface (hidden initially)
                            chat_interface = gr.Column(visible=False)
                            with chat_interface:
                                # Chat Display - Increased height and removed unnecessary header space
                                chatbot = gr.Chatbot(
                                    label="",
                                    height=550,
                                    type="messages",
                                    elem_id="chatbot",
                                    show_label=False,
                                    container=False,
                                    bubble_full_width=False,
                                    avatar_images=None,
                                    show_copy_button=False,
                                    layout="bubble",
                                    placeholder="Start a conversation with your AI agent..."
                                )
                                
                                # Input Area
                                with gr.Row():
                                    with gr.Column(scale=8):
                                        msg = gr.Textbox(
                                            label="",
                                            placeholder="💭 Type your message here...",
                                            lines=1,
                                            show_label=False,
                                            container=False,
                                            autofocus=True
                                        )
                                    with gr.Column(scale=1):
                                        submit_btn = gr.Button(
                                            "Send",
                                            variant="primary",
                                            size="lg"
                                        )
                                
                                # Tool Activity & Logs Section - Made more compact
                                with gr.Accordion("🔧 **Tool Activity & Logs**", open=False):
                                    with gr.Row():
                                        with gr.Column():
                                            gr.Markdown("##### Tool Activity")
                                            tool_activity = gr.HTML(
                                                value="<div>Tool activities will appear here...</div>",
                                                elem_id="tool_activity"
                                            )
                                        with gr.Column():
                                            gr.Markdown("##### System Logs")
                                            logs_display = gr.HTML(
                                                value="<div>System logs will appear here...</div>",
                                                elem_id="logs_display"
                                            )
                    
                    # Configuration Tab
                    with gr.TabItem("⚙️ Configuration", id=1):
                        with gr.Column():
                            gr.Markdown("### 🛠️ **Agent Configuration**")
                            
                            # Basic Configuration
                            with gr.Group():
                                gr.Markdown("#### ℹ️ **Basic Information**")
                                with gr.Row():
                                    with gr.Column():
                                        name_input = gr.Textbox(
                                            label="🏷️ Agent Name",
                                            value="",
                                            interactive=True
                                        )
                                        with gr.Row():
                                            is_stream = gr.Checkbox(
                                                label="🌊 Streaming",
                                                value=False,
                                                interactive=True
                                            )
                                            is_chat = gr.Checkbox(
                                                label="💬 Chat Mode",
                                                value=False,
                                                interactive=True
                                            )
                                    with gr.Column():
                                        model_info = gr.Textbox(
                                            label="🧠 Current Model",
                                            value="",
                                            interactive=False
                                        )
                                        config_info = gr.Textbox(
                                            label="📋 Active Config",
                                            value="",
                                            interactive=False
                                        )
                            
                            # Agent Personality
                            with gr.Group():
                                gr.Markdown("#### 🎭 **Agent Personality**")
                                welcome_msg = gr.Textbox(
                                    label="👋 Welcome Message",
                                    value="",
                                    lines=3,
                                    interactive=True
                                )
                                
                                background = gr.Textbox(
                                    label="📚 Background & Context",
                                    value="",
                                    lines=4,
                                    interactive=True
                                )
                            
                            # Task Configuration
                            with gr.Group():
                                gr.Markdown("#### 🎯 **Task Configuration**")
                                task_details = gr.Textbox(
                                    label="📋 Task Details",
                                    value="",
                                    lines=4,
                                    interactive=True
                                )
                                
                                input_values = gr.Textbox(
                                    label="📥 Input Parameters",
                                    value="",
                                    lines=3,
                                    interactive=True
                                )
                                
                                output_format = gr.Textbox(
                                    label="📤 Output Format",
                                    value="",
                                    lines=4,
                                    interactive=True
                                )
                            
                            # MCP Tools Section
                            with gr.Accordion("🛠️ **MCP Tools Management**", open=True):
                                gr.HTML("""
                                    <div class="tools-header">
                                        <span>🔧</span>
                                        <span>Tool Configuration</span>
                                    </div>
                                """)
                                
                                # Tool status display
                                tools_status = gr.HTML(
                                    value="<div style='text-align: center; color: #6c757d; font-size: 12px; padding: 4px;'>Click on tools to add/remove them</div>",
                                    elem_id="tools_status"
                                )
                                
                                with gr.Row():
                                    # Available Tools
                                    with gr.Column(scale=1):
                                        gr.Markdown("##### 📦 **Available Tools**")
                                        server_selector = gr.Dropdown(
                                            label="🖥️ MCP Server",
                                            choices=[],
                                            interactive=True
                                        )
                                        
                                        available_tools_df = gr.Dataframe(
                                            headers=["🔧 Tool", "⚡ Action"],
                                            datatype=["str", "str"],
                                            interactive=False,
                                            label=""
                                        )
                                    
                                    # Selected Tools
                                    with gr.Column(scale=1):
                                        gr.Markdown("##### ✅ **Active Tools**")
                                        selected_tools_df = gr.Dataframe(
                                            headers=["🔧 Tool", "⚡ Action"],
                                            datatype=["str", "str"],
                                            interactive=False,
                                            label=""
                                        )
                                        
                                        selected_tools_state = gr.State([])
                            
                            # Save Configuration
                            with gr.Row():
                                # Save status notification
                                save_status = gr.HTML(
                                    value="",
                                    elem_id="save_status",
                                    visible=False
                                )
                            
                            save_config_btn = gr.Button(
                                "💾 Save Configuration",
                                variant="primary",
                                size="lg"
                            )
                    
                    # Logs & Debugging Tab
                    with gr.TabItem("📊 Logs & Debug", id=2):
                        with gr.Column():
                            gr.Markdown("### 📈 **System Logs & Debugging**")
                            
                            # Log Controls
                            with gr.Row():
                                refresh_logs_btn = gr.Button(
                                    "🔄 Refresh"
                                )
                                clear_logs_btn = gr.Button(
                                    "🗑️ Clear"
                                )
                                export_logs_btn = gr.Button(
                                    "📥 Export"
                                )
                            
                            # Logs Display
                            logs = gr.Textbox(
                                label="📋 System Logs",
                                lines=15,
                                interactive=False,
                                elem_id="logs",
                                placeholder="System logs will appear here..."
                            )

            # Helper functions for MCP tools (keeping the existing logic)
            def load_mcp_servers():
                global mcp_servers, all_tools_cache, mcp_loaded
                if mcp_loaded:
                    return mcp_servers
                
                try:
                    mcp_client = MCPCLient()
                    mcp_client.load_servers("mcp/mcp_config.json")
                    mcp_servers = [server.name for server in mcp_client.servers]
                    all_tools_cache = asyncio.run(mcp_client.load_all_tools())
                    mcp_loaded = True
                    print(f"Loaded {len(mcp_servers)} MCP servers: {mcp_servers}")
                    return mcp_servers
                except Exception as e:
                    print(f"Error loading MCP servers: {e}")
                    all_tools_cache = {}
                    mcp_loaded = True
                    return []
            
            def generate_chat_header(agent_name="", tools_list=None):
                """Generate dynamic chat header with agent name and tools"""
                if not agent_name and not tools_list:
                    return "<div>💬 Conversation</div>"
                
                # Format agent name
                agent_display = f"🤖 {agent_name}" if agent_name else "🤖 Agent"
                
                # Format tools
                tools_display = ""
                if tools_list and len(tools_list) > 0:
                    tool_names = []
                    for tool in tools_list:
                        if isinstance(tool, dict):
                            tool_name = tool.get('tool', tool.get('server', 'Unknown'))
                            tool_names.append(tool_name)
                        else:
                            tool_names.append(str(tool))
                    
                    if len(tool_names) <= 3:
                        tools_display = f" • 🛠️ Tools: {', '.join(tool_names)}"
                    else:
                        tools_display = f" • 🛠️ Tools: {', '.join(tool_names[:3])} +{len(tool_names)-3} more"
                
                return f"<div>💬 {agent_display}{tools_display}</div>"
            
            def get_available_tools(server_name, selected_tools):
                """Get list of available tools for a server, excluding already selected ones"""
                try:
                    if not server_name or not all_tools_cache or server_name not in all_tools_cache:
                        return []
                    
                    # Ensure selected_tools is a list and properly formatted
                    if not isinstance(selected_tools, list):
                        selected_tools = []
                    
                    # Create set of selected tools for efficient lookup
                    selected_set = set()
                    for tool in selected_tools:
                        if isinstance(tool, dict) and 'server' in tool and 'tool' in tool:
                            selected_set.add((tool['server'], tool['tool']))
                    
                    tool_rows = []
                    for tool in all_tools_cache[server_name]:
                        if isinstance(tool, dict) and "name" in tool:
                            tool_name = tool["name"]
                            if (server_name, tool_name) not in selected_set:
                                tool_rows.append([f"{server_name}: {tool_name}", "➕ Add"])
                    
                    return tool_rows
                except Exception as e:
                    print(f"Error in get_available_tools: {e}")
                    return []
            
            def get_selected_tools_display(selected_tools):
                """Format selected tools for display in dataframe"""
                try:
                    if not selected_tools or not isinstance(selected_tools, list):
                        return []
                    
                    tool_rows = []
                    for tool in selected_tools:
                        if isinstance(tool, dict):
                            server = tool.get('server', 'Unknown')
                            tool_name = tool.get('tool', 'Unknown')
                            label = f"{server}: {tool_name}"
                            tool_rows.append([label, "❌ Remove"])
                        else:
                            # Handle malformed tool entries
                            tool_rows.append([f"Invalid tool: {str(tool)}", "❌ Remove"])
                    
                    return tool_rows
                except Exception as e:
                    print(f"Error in get_selected_tools_display: {e}")
                    return []
            
            def initialize_mcp_tools(config_file):
                """Initialize MCP tools display when config is loaded"""
                try:
                    servers = load_mcp_servers()
                    selected_tools = []
                    
                    if config_file:
                        config_content = agent_tester.load_config_content(config_file)
                        mcp_tools = config_content.get("mcp_tools", [])
                        
                        # Validate and clean the mcp_tools data
                        for tool in mcp_tools:
                            if isinstance(tool, dict) and 'server' in tool and 'tool' in tool:
                                selected_tools.append({
                                    'server': str(tool['server']),
                                    'tool': str(tool['tool'])
                                })
                    
                    first_server = servers[0] if servers else None
                    available_tools = get_available_tools(first_server, selected_tools)
                    selected_tools_display = get_selected_tools_display(selected_tools)
                    default_status = reset_tools_status()
                    
                    return (
                        gr.update(choices=servers, value=first_server),
                        available_tools,
                        selected_tools_display,
                        selected_tools,
                        default_status
                    )
                except Exception as e:
                    print(f"Error in initialize_mcp_tools: {e}")
                    return (
                        gr.update(choices=[], value=None),
                        [],
                        [],
                        [],
                        "<div style='text-align: center; color: #dc3545; font-size: 12px; padding: 4px;'>❌ Error loading MCP tools</div>"
                    )
            
            def update_available_tools_with_status(server_name, selected_tools):
                """Update available tools when server selection changes with status reset"""
                try:
                    available_tools = get_available_tools(server_name, selected_tools)
                    status_msg = reset_tools_status()
                    return available_tools, status_msg
                except Exception as e:
                    print(f"Error in update_available_tools_with_status: {e}")
                    return [], "<div style='text-align: center; color: #dc3545; font-size: 12px; padding: 4px;'>❌ Error loading tools</div>"
            
            def add_tool(evt: gr.SelectData, selected_tools, server_name):
                """Add a tool to the selected tools list"""
                try:
                    # Validate inputs
                    if evt is None or evt.index is None or not all_tools_cache or not server_name:
                        return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
                    
                    # Ensure selected_tools is a proper list
                    if not isinstance(selected_tools, list):
                        selected_tools = []
                    
                    # Get current available tools
                    available_tools = get_available_tools(server_name, selected_tools)
                    
                    # Validate row index
                    row_index = evt.index[0] if isinstance(evt.index, list) else evt.index
                    if row_index < 0 or row_index >= len(available_tools):
                        return get_selected_tools_display(selected_tools), available_tools, selected_tools
                    
                    # Extract tool information
                    tool_label = available_tools[row_index][0]
                    try:
                        server, tool = tool_label.split(": ", 1)
                    except ValueError:
                        print(f"Invalid tool label format: {tool_label}")
                        return get_selected_tools_display(selected_tools), available_tools, selected_tools
                    
                    # Check if tool is already selected (double-click protection)
                    for existing_tool in selected_tools:
                        if (isinstance(existing_tool, dict) and 
                            existing_tool.get("server") == server and 
                            existing_tool.get("tool") == tool):
                            return get_selected_tools_display(selected_tools), available_tools, selected_tools
                    
                    # Add the new tool
                    new_tool = {"server": server, "tool": tool}
                    new_selected = selected_tools.copy()
                    new_selected.append(new_tool)
                    
                    return (
                        get_selected_tools_display(new_selected),
                        get_available_tools(server_name, new_selected),
                        new_selected
                    )
                    
                except Exception as e:
                    print(f"Error in add_tool: {e}")
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
            
            def remove_tool(evt: gr.SelectData, selected_tools, server_name):
                """Remove a tool from the selected tools list"""
                try:
                    # Validate inputs
                    if evt is None or evt.index is None:
                        return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
                    
                    # Ensure selected_tools is a proper list
                    if not isinstance(selected_tools, list):
                        selected_tools = []
                    
                    # Get current selected tools display
                    selected_display = get_selected_tools_display(selected_tools)
                    
                    # Validate row index
                    row_index = evt.index[0] if isinstance(evt.index, list) else evt.index
                    if row_index < 0 or row_index >= len(selected_display):
                        return selected_display, get_available_tools(server_name, selected_tools), selected_tools
                    
                    # Extract tool information
                    tool_label = selected_display[row_index][0]
                    try:
                        server, tool = tool_label.split(": ", 1)
                    except ValueError:
                        print(f"Invalid tool label format: {tool_label}")
                        return selected_display, get_available_tools(server_name, selected_tools), selected_tools
                    
                    # Remove the tool
                    new_selected = []
                    for existing_tool in selected_tools:
                        if (isinstance(existing_tool, dict) and 
                            existing_tool.get("server") == server and 
                            existing_tool.get("tool") == tool):
                            continue  # Skip this tool (remove it)
                        new_selected.append(existing_tool)
                    
                    return (
                        get_selected_tools_display(new_selected),
                        get_available_tools(server_name, new_selected),
                        new_selected
                    )
                    
                except Exception as e:
                    print(f"Error in remove_tool: {e}")
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
            
            def reset_tools_status():
                """Reset tools status to default message"""
                return "<div style='text-align: center; color: #6c757d; font-size: 12px; padding: 4px;'>Click on tools to add/remove them</div>"
            
            def add_tool_with_feedback(evt: gr.SelectData, selected_tools, server_name):
                """Add a tool with user feedback"""
                try:
                    result = add_tool(evt, selected_tools, server_name)
                    # Check if a tool was actually added
                    if len(result[2]) > len(selected_tools):
                        status_msg = "<div style='text-align: center; color: #28a745; font-size: 12px; padding: 4px;'>✅ Tool added successfully!</div>"
                        print("✅ Tool added successfully")
                    else:
                        status_msg = "<div style='text-align: center; color: #ffc107; font-size: 12px; padding: 4px;'>⚠️ Tool already selected or invalid</div>"
                    return result + (status_msg,)
                except Exception as e:
                    print(f"❌ Error adding tool: {e}")
                    status_msg = "<div style='text-align: center; color: #dc3545; font-size: 12px; padding: 4px;'>❌ Error adding tool</div>"
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools, status_msg
            
            def remove_tool_with_feedback(evt: gr.SelectData, selected_tools, server_name):
                """Remove a tool with user feedback"""
                try:
                    result = remove_tool(evt, selected_tools, server_name)
                    # Check if a tool was actually removed
                    if len(result[2]) < len(selected_tools):
                        status_msg = "<div style='text-align: center; color: #28a745; font-size: 12px; padding: 4px;'>✅ Tool removed successfully!</div>"
                        print("✅ Tool removed successfully")
                    else:
                        status_msg = "<div style='text-align: center; color: #ffc107; font-size: 12px; padding: 4px;'>⚠️ Tool not found or invalid</div>"
                    return result + (status_msg,)
                except Exception as e:
                    print(f"❌ Error removing tool: {e}")
                    status_msg = "<div style='text-align: center; color: #dc3545; font-size: 12px; padding: 4px;'>❌ Error removing tool</div>"
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools, status_msg
            
            # Connect MCP events with improved debouncing
            init_btn.click(
                fn=lambda config: initialize_mcp_tools(config),
                inputs=[config_selector],
                outputs=[server_selector, available_tools_df, selected_tools_df, selected_tools_state, tools_status],
                show_progress=False
            )
            
            # Event Handlers
            async def process_message(message, history):
                if not message:
                    yield history, "", "", ""
                    return
                
                # Add user message
                history.append({"role": "user", "content": message})
                
                # Add processing animation as temporary assistant message
                processing_content = """🤖 Agent is thinking<span class="thinking-dots">
    <span class="dot1">●</span><span class="dot2">●</span><span class="dot3">●</span>
</span>

<style>
.thinking-dots {
    display: inline-block;
    margin-left: 8px;
    font-size: 18px;
    letter-spacing: 2px;
}

.dot1, .dot2, .dot3 {
    animation: thinking 1.2s infinite;
    color: #007bff;
    font-weight: bold;
}

.dot2 {
    animation-delay: 0.2s;
    color: #28a745;
}

.dot3 {
    animation-delay: 0.4s;
    color: #ffc107;
}

@keyframes thinking {
    0%, 60%, 100% {
        opacity: 0.2;
        transform: scale(0.8);
    }
    30% {
        opacity: 1;
        transform: scale(1.2);
    }
}
</style>"""
                
                history.append({"role": "assistant", "content": processing_content})
                yield history, "", "", ""
                
                full_response = ""
                tool_activities = []
                logs_content = []
                
                try:
                    async for response in agent_tester.process_query(message):
                        full_response = response
                        
                        # Replace the processing message with the actual response
                        history[-1] = {"role": "assistant", "content": full_response}
                        
                        # Extract tool activities from callback logs
                        current_logs = agent_tester.callback_logs
                        tool_activities = []
                        for log in current_logs:
                            if "TOOL_START" in log.upper() or "TOOL_COMPLETE" in log.upper():
                                tool_activities.append(log)
                        
                        # Format tool activity display
                        tool_html = ""
                        if tool_activities:
                            tool_html = "<div style='font-family: monospace; font-size: 12px;'>"
                            for activity in tool_activities[-10:]:  # Show last 10 tool activities
                                if "TOOL_START" in activity.upper():
                                    color = "#0d6efd"  # Blue
                                elif "TOOL_COMPLETE" in activity.upper():
                                    color = "#198754"  # Green
                                else:
                                    color = "#6c757d"  # Gray
                                tool_html += f"<div style='color: {color}; margin-bottom: 4px; padding: 2px;'>🔧 {activity}</div>"
                            tool_html += "</div>"
                        else:
                            tool_html = "<div>Tool activities will appear here...</div>"
                        
                        # Format logs display
                        logs_html = ""
                        if current_logs:
                            logs_html = "<div style='font-family: monospace; font-size: 12px;'>"
                            for log in current_logs[-20:]:  # Show last 20 logs
                                # Add color coding based on log type
                                if "ERROR" in log.upper():
                                    color = "#dc3545"  # Red
                                elif "GUARDRAIL" in log.upper():
                                    color = "#fd7e14"  # Orange
                                elif "TOOL_START" in log.upper():
                                    color = "#0d6efd"  # Blue
                                elif "TOOL_COMPLETE" in log.upper():
                                    color = "#198754"  # Green
                                elif "MODEL_RESPONSE" in log.upper():
                                    color = "#6f42c1"  # Purple
                                else:
                                    color = "#6c757d"  # Gray
                                
                                logs_html += f"<div style='color: {color}; margin-bottom: 4px; padding: 2px;'>{log}</div>"
                            logs_html += "</div>"
                        else:
                            logs_html = "<div>System logs will appear here...</div>"
                        
                        yield history, "", tool_html, logs_html
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    history[-1] = {"role": "assistant", "content": error_msg}
                    logs_html = f"<div>Error: {str(e)}</div>"
                    yield history, "", "", logs_html

            def initialize_agent(model, config):
                if not model or not config:
                    return [
                        gr.update(value="⚠️ Please select both a model and configuration"),
                        gr.update(value=[]),
                        gr.update(value={}),
                        gr.update(value=""),
                        gr.update(value=False),
                        gr.update(value=False),
                        gr.update(value=model),
                        gr.update(value=config),
                        gr.update(value=""),
                        gr.update(value=""),
                        gr.update(value=""),
                        gr.update(value=""),
                        gr.update(value=""),
                        gr.update(value={}),
                        'Agent: Failed to Initialize',
                        "<div>Tool activities will appear here...</div>",
                        "<div>System logs will appear here...</div>",
                        gr.update(visible=True),  # chat_placeholder
                        gr.update(visible=False)  # chat_interface
                    ]
                
                agent_tester.model_params = {
                    "temperature": temperature.value,
                    "max_tokens": max_tokens.value
                }
                success = asyncio.run(agent_tester.initialize_agent(model, config))
                
                if success:
                    config_content = agent_tester.config_content
                    initial_messages = [{"role": "assistant", "content": agent_tester.welcome_message}]
                    agent_name = config_content.get("name", "AI Assistant")
                    selected_tools = config_content.get("mcp_tools", [])
                    
                    return [
                        gr.update(value=f"✅ Agent initialized successfully with {model}"),
                        gr.update(value=initial_messages),
                        gr.update(value=selected_tools),
                        gr.update(value=agent_name),
                        gr.update(value=config_content.get("is_stream", False)),
                        gr.update(value=config_content.get("is_chat", False)),
                        gr.update(value=model),
                        gr.update(value=config),
                        gr.update(value=config_content.get("welcome_message", "")),
                        gr.update(value=config_content.get("background", "")),
                        gr.update(value=config_content.get("task_details", "")),
                        gr.update(value=config_content.get("input_values", "")),
                        gr.update(value=config_content.get("output_format", "")),
                        gr.update(value=selected_tools),
                        'Agent: Connected & Ready',
                        "<div>Tool activities will appear here...</div>",
                        "<div>System logs will appear here...</div>",
                        gr.update(visible=False),  # chat_placeholder
                        gr.update(visible=True)   # chat_interface
                    ]
                return [
                    gr.update(value="❌ Failed to initialize agent"),
                    gr.update(value=[]),
                    gr.update(value={}),
                    gr.update(value=""),
                    gr.update(value=False),
                    gr.update(value=False),
                    gr.update(value=model),
                    gr.update(value=config),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value=""),
                    gr.update(value={}),
                    'Agent: Failed to Initialize',
                    "<div>Tool activities will appear here...</div>",
                    "<div>System logs will appear here...</div>",
                    gr.update(visible=True),  # chat_placeholder
                    gr.update(visible=False)  # chat_interface
                ]
            
            def update_logs():
                logs_html = ""
                if agent_tester.callback_logs:
                    logs_html = "<div style='font-family: monospace; font-size: 12px;'>"
                    for log in agent_tester.callback_logs[-20:]:  # Show last 20 logs
                        # Add color coding based on log type
                        if "ERROR" in log.upper():
                            color = "#dc3545"  # Red
                        elif "GUARDRAIL" in log.upper():
                            color = "#fd7e14"  # Orange
                        elif "TOOL_START" in log.upper():
                            color = "#0d6efd"  # Blue
                        elif "TOOL_COMPLETE" in log.upper():
                            color = "#198754"  # Green
                        elif "MODEL_RESPONSE" in log.upper():
                            color = "#6f42c1"  # Purple
                        else:
                            color = "#6c757d"  # Gray
                        
                        logs_html += f"<div style='color: {color}; margin-bottom: 4px; padding: 2px;'>{log}</div>"
                    logs_html += "</div>"
                else:
                    logs_html = "<div>System logs will appear here...</div>"
                
                return "\n".join(agent_tester.callback_logs), logs_html
            
            def clear_logs():
                if agent_tester.callback:
                    agent_tester.callback.clearLogs()
                agent_tester.callback_logs.clear()
                agent_tester.agent_logs.clear()
                logs_html = "<div>System logs will appear here...</div>"
                tool_html = "<div>Tool activities will appear here...</div>"
                return "", logs_html, tool_html
            
            def export_logs():
                """Export logs as JSON file"""
                if agent_tester.callback:
                    import json
                    from datetime import datetime
                    
                    logs_data = {
                        "export_timestamp": datetime.now().isoformat(),
                        "agent_name": agent_tester.config_content.get("name", "Unknown"),
                        "model": agent_tester.selected_model,
                        "logs": agent_tester.callback.getLogsAsJson(),
                        "stats": agent_tester.callback.getLogStats()
                    }
                    
                    filename = f"agent_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(filename, 'w') as f:
                        json.dump(logs_data, f, indent=2)
                    
                    return f"✅ Logs exported to {filename}"
                else:
                    return "❌ No agent initialized"
            
            def refresh_config_files():
                """Refresh the list of available configuration files"""
                config_files = agent_tester.list_config_files()
                if config_files:
                    status_msg = f"🔄 Refreshed: Found {len(config_files)} configuration file(s) - Ready to initialize!"
                else:
                    status_msg = "🔄 Refreshed: No configuration files found - Create one using Agent Builder"
                return (
                    gr.update(choices=config_files, value=config_files[0] if config_files else None),
                    status_msg
                )
            
            # Connect all events
            
            # MCP Tools event connections
            server_selector.change(
                fn=update_available_tools_with_status,
                inputs=[server_selector, selected_tools_state],
                outputs=[available_tools_df, tools_status],
                show_progress=False
            )
            
            # Add tool with debouncing and feedback
            available_tools_df.select(
                fn=add_tool_with_feedback,
                inputs=[selected_tools_state, server_selector],
                outputs=[selected_tools_df, available_tools_df, selected_tools_state, tools_status],
                show_progress=False
            )
            
            # Remove tool with debouncing and feedback
            selected_tools_df.select(
                fn=remove_tool_with_feedback,
                inputs=[selected_tools_state, server_selector],
                outputs=[selected_tools_df, available_tools_df, selected_tools_state, tools_status],
                show_progress=False
            )
            
            # Configuration save function
            def save_configuration_with_loading(
                name, is_stream, is_chat, welcome_msg, background,
                task_details, input_values, output_format, config_file,
                selected_tools, model, temperature_val, max_tokens_val
            ):
                # Return loading state first
                yield (
                    'Saving configuration and reinitializing agent...',
                    [],
                    'Agent: Updating...',
                    gr.update(variant="secondary", value="💾 Saving...", interactive=False),
                    generate_chat_header(),
                    "<div>System logs will appear here...</div>"
                )
                
                # Perform the actual save and reinitialize
                try:
                    updated_config = {
                        "name": name,
                        "welcome_message": welcome_msg,
                        "background": background,
                        "task_details": task_details,
                        "input_values": input_values,
                        "output_format": output_format,
                        "is_stream": is_stream,
                        "is_chat": is_chat,
                        "mcp_tools": selected_tools
                    }
                    
                    config_path = os.path.join("agent_config", config_file)
                    with open(config_path, "w") as f:
                        json.dump(updated_config, f, indent=2)
                    
                    # Update agent_tester config
                    agent_tester.config_content = updated_config
                    
                    # Update model parameters
                    agent_tester.model_params = {
                        "temperature": temperature_val,
                        "max_tokens": max_tokens_val
                    }
                    
                    # Reinitialize agent with updated configuration
                    success = asyncio.run(agent_tester.initialize_agent(model, config_file))
                    
                    if success:
                        initial_messages = [{"role": "assistant", "content": agent_tester.welcome_message}]
                        agent_name = updated_config.get("name", "AI Assistant")
                        selected_tools = updated_config.get("mcp_tools", [])
                        yield (
                            '✅ Configuration saved and agent reinitialized successfully!',
                            initial_messages,
                            'Agent: Updated & Ready',
                            gr.update(variant="primary", value="💾 Save Configuration", interactive=True),
                            generate_chat_header(agent_name, selected_tools),
                            "<div>System logs will appear here...</div>"
                        )
                    else:
                        yield (
                            '⚠️ Configuration saved but failed to reinitialize agent. Please initialize manually.',
                            [],
                            'Agent: Failed to Reinitialize',
                            gr.update(variant="primary", value="💾 Save Configuration", interactive=True),
                            generate_chat_header(),
                            "<div>System logs will appear here...</div>"
                        )
                         
                except Exception as e:
                    yield (
                        f'❌ Failed to save configuration: {str(e)}',
                        [],
                        'Agent: Configuration Error',
                        gr.update(variant="primary", value="💾 Save Configuration", interactive=True),
                        generate_chat_header(),
                        "<div>System logs will appear here...</div>"
                    )
            
            def update_config_display(config_content, model, config_file):
                """Update configuration display with proper tool handling"""
                try:
                    if not config_content:
                        return {
                            name_input: "",
                            is_stream: False,
                            is_chat: False,
                            model_info: model or "",
                            config_info: config_file or "",
                            welcome_msg: "",
                            background: "",
                            task_details: "",
                            input_values: "",
                            output_format: "",
                            selected_tools_df: [],
                            selected_tools_state: []
                        }
                    
                    # Validate and clean the mcp_tools data
                    mcp_tools = config_content.get("mcp_tools", [])
                    selected_tools_val = []
                    
                    if isinstance(mcp_tools, list):
                        for tool in mcp_tools:
                            if isinstance(tool, dict) and 'server' in tool and 'tool' in tool:
                                selected_tools_val.append({
                                    'server': str(tool['server']),
                                    'tool': str(tool['tool'])
                                })
                    
                    return {
                        name_input: config_content.get("name", ""),
                        is_stream: config_content.get("is_stream", False),
                        is_chat: config_content.get("is_chat", False),
                        model_info: model or "",
                        config_info: config_file or "",
                        welcome_msg: config_content.get("welcome_message", ""),
                        background: config_content.get("background", ""),
                        task_details: config_content.get("task_details", ""),
                        input_values: config_content.get("input_values", ""),
                        output_format: config_content.get("output_format", ""),
                        selected_tools_df: get_selected_tools_display(selected_tools_val),
                        selected_tools_state: selected_tools_val
                    }
                except Exception as e:
                    print(f"Error in update_config_display: {e}")
                    return {
                        name_input: "",
                        is_stream: False,
                        is_chat: False,
                        model_info: model or "",
                        config_info: config_file or "",
                        welcome_msg: "",
                        background: "",
                        task_details: "",
                        input_values: "",
                        output_format: "",
                        selected_tools_df: [],
                        selected_tools_state: []
                    }
            
            # Main event connections
            init_btn.click(
                fn=initialize_agent,
                inputs=[model_selector, config_selector],
                outputs=[
                    logs, chatbot, selected_tools_df,
                    name_input, is_stream, is_chat,
                    model_info, config_info,
                    welcome_msg, background, task_details,
                    input_values, output_format, selected_tools_state,
                    agent_status,
                    tool_activity, logs_display,
                    chat_placeholder, chat_interface
                ]
            )
            
            init_btn.click(
                fn=lambda m, c: update_config_display(agent_tester.config_content, m, c),
                inputs=[model_selector, config_selector],
                outputs=[
                    name_input, is_stream, is_chat, model_info,
                    config_info, welcome_msg, background, task_details,
                    input_values, output_format, selected_tools_df, selected_tools_state
                ]
            )
            
            submit_btn.click(
                fn=process_message,
                inputs=[msg, chatbot],
                outputs=[chatbot, msg, tool_activity, logs_display]
            )
            
            msg.submit(
                fn=process_message,
                inputs=[msg, chatbot],
                outputs=[chatbot, msg, tool_activity, logs_display]
            )
            
            save_config_btn.click(
                fn=save_configuration_with_loading,
                inputs=[
                    name_input, is_stream, is_chat, welcome_msg,
                    background, task_details, input_values,
                    output_format, config_selector, selected_tools_state,
                    model_selector, temperature, max_tokens
                ],
                outputs=[logs, chatbot, agent_status, save_config_btn, tool_activity, logs_display]
            )
            
            clear_logs_btn.click(
                fn=clear_logs,
                outputs=[logs, logs_display, tool_activity]
            )
            
            refresh_logs_btn.click(
                fn=update_logs,
                outputs=[logs, logs_display]
            )
            
            export_logs_btn.click(
                fn=export_logs,
                outputs=[logs]
            )
            
            refresh_config_btn.click(
                fn=refresh_config_files,
                outputs=[config_selector, agent_status]
            )

    return interface

if __name__ == "__main__":
    create_agent_tester_interface().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    ) 