import gradio as gr
import json
import os
import asyncio
import re
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(project_root)
print("Project root", project_root)

# Global cache for all MCP tools
all_tools_cache = None
mcp_servers = []
mcp_loaded = False

from agentmaster import getADKAgent
from constants import ALL_MODELS, GEMINI_API_KEY, OPENAI_API_KEY
from mcp_client import MCPCLient

class AgentBuilder:
    def __init__(self):
        self.chat_history = []
        self.callback = None
        self.agent_logs = []
        self.mcp_tools = []
        self.selected_mcp_tools = []
        self.adk_agent = None
        self.agent_json = None
        self.selected_model = None
        self.streaming = False
        self.welcome_message = ""
        self.messages = []
        self.config_content = {}
        self.model_params = {
            "temperature": 1.0,
            "max_tokens": 2000,
        }
        self.generated_config = {}
        self.is_processing = False

    def load_config_content(self, config_file="agent_creator.json", config_dir="agent_creator_config"):
        try:
            if config_file == "agent_creator.json":
                config_path = os.path.join(config_dir, config_file)
            else:
                config_path = os.path.join(config_dir, config_file)
                
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading config file: ", e)
            self.agent_logs.append(f"Error loading config file: {e}")
            return {}

    async def initialize_agent(self, model_input: str):
        print("Reached in initialize_agent 1 .......")
        self.adk_agent = None
        self.agent_json = None
        self.selected_model = model_input
        self.mcp_tools = []
        self.selected_mcp_tools = []
        self.chat_history = []
        self.agent_logs = []
        self.streaming = False
        self.welcome_message = ""
        self.messages = []
        self.generated_config = {}
        self.is_processing = False

        try:
            # Always load agent_creator.json for the builder
            self.config_content = self.load_config_content("agent_creator.json")

            api_keys = {
                "GEMINI_API_KEY": GEMINI_API_KEY,
                "OPENAI_API_KEY": OPENAI_API_KEY
            }
            
            self.callback,self.adk_agent = await getADKAgent(
                self.config_content,
                self.selected_model,
                self.model_params.get("temperature", 0.1),
                self.model_params.get("max_tokens", 1024),
                api_keys=api_keys
            )
            
            self.welcome_message = (
                self.config_content.get("welcome_message", "Hello! I'm ready to help you build an AI agent.")
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

    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON structure from LLM output text."""
        try:
            json_text = re.sub(r'```json|```', '', text)
            start, end = json_text.find('{'), json_text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(json_text[start:end+1])
        except (ValueError, json.JSONDecodeError) as e:
            pass
        return None

    async def process_query(self, query: str):
        if not self.adk_agent:
            yield "Error: Please initialize an agent first"
            return
        
        self.is_processing = True
        full_response = ""
        
        try:
            async for chunk in self.adk_agent.send_query(query):
                full_response += chunk
                yield full_response
                
            # Try to extract JSON from the response
            self.agent_json = self.extract_json_from_text(full_response)
            if self.agent_json:
                self.generated_config = self.agent_json.copy()
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.agent_logs.append(error_msg)
            yield error_msg
        finally:
            self.is_processing = False

def create_agent_builder_interface():
    agent_builder = AgentBuilder()
    
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
    </style>
    """
    
    with gr.Blocks(
        title="🏗️ AI Agent Builder",
        css=minimal_css
    ) as interface:
        # Main Header
        with gr.Row():
            gr.Markdown("# 🏗️ AI Agent Builder")
        
        with gr.Row():
            # Left Sidebar - Control Panel
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ **Builder Control Center**")
                
                # Status Section
                with gr.Group():
                    gr.Markdown("#### 📊 **Status**")
                    agent_status = gr.HTML(
                        'Builder: Ready',
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
                    
                    gr.Markdown("**Configuration:** agent_creator.json")
                
                # Advanced Parameters
                with gr.Accordion("🔧 **Advanced Parameters**", open=False):
                    temperature = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=1.0,
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
                    "🚀 Initialize Builder",
                    variant="primary",
                    size="lg"
                )
                
                # Builder Actions
                with gr.Group():
                    gr.Markdown("#### 🔧 **Builder Actions**")
                    clear_chat_btn = gr.Button(
                        "🗑️ Clear Chat"
                    )
                    reset_config_btn = gr.Button(
                        "🔄 Reset Config"
                    )
            
            # Main Content Area
            with gr.Column(scale=4):
                with gr.Tabs() as main_tabs:
                    # Agent Builder Chat Tab
                    with gr.TabItem("🤖 Agent Builder", id=0):
                        with gr.Column():
                            # Placeholder for uninitialized state
                            chat_placeholder = gr.HTML(
                                value="""
                                <div style="text-align: center; padding: 100px 20px; background: #f8f9fa; border-radius: 10px; margin: 20px 0;">
                                    <div style="font-size: 48px; margin-bottom: 20px;">🏗️</div>
                                    <h2 style="color: #6c757d; margin-bottom: 15px;">Agent Builder Not Initialized</h2>
                                    <p style="color: #6c757d; font-size: 16px; margin-bottom: 20px;">
                                        Please select a model and click "🚀 Initialize Builder" to start creating your agent.
                                    </p>
                                    <div style="background: #e9ecef; padding: 15px; border-radius: 8px; margin: 20px 0;">
                                        <strong>Steps to get started:</strong><br>
                                        1. Select a model from the dropdown<br>
                                        2. Click "🚀 Initialize Builder"<br>
                                        3. Describe your agent requirements<br>
                                        4. Review and save the configuration!
                                    </div>
                                </div>
                                """,
                                visible=True
                            )
                            
                            # Actual chat interface (hidden initially)
                            chat_interface = gr.Column(visible=False)
                            with chat_interface:
                                # Chat Display - Increased height for more space
                                chatbot = gr.Chatbot(
                                    label="",
                                    height=550,
                                    type="messages",
                                    elem_id="chatbot",
                                    show_label=False,
                                    container=False,
                                    bubble_full_width=False,
                                    avatar_images=None,
                                    show_copy_button=True,
                                    layout="bubble",
                                    placeholder="Describe the AI agent you want to create..."
                                )
                                
                                # Input Area
                                with gr.Row():
                                    with gr.Column(scale=8):
                                        msg = gr.Textbox(
                                            label="",
                                            placeholder="💭 Describe your agent: 'I want an AI agent that helps with customer support...'",
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
                                
                                # JSON Detection & Preview
                                with gr.Accordion("📋 **Detected Configuration**", open=False):
                                    json_preview = gr.HTML(
                                        value="<div>Generated configuration will appear here...</div>",
                                        elem_id="json_preview"
                                    )
                    
                    # Configuration Tab
                    with gr.TabItem("⚙️ Agent Configuration", id=1):
                        with gr.Column():
                            gr.Markdown("### 🛠️ **Generated Agent Configuration**")
                            
                            # Configuration Form
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
                                                value=True,
                                                interactive=True
                                            )
                                    with gr.Column():
                                        slug_input = gr.Textbox(
                                            label="🔗 Slug",
                                            value="",
                                            interactive=True
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
                            
                            # Save Configuration
                            with gr.Row():
                                save_status = gr.HTML(
                                    value="",
                                    elem_id="save_status",
                                    visible=True
                                )
                            
                            save_config_btn = gr.Button(
                                "💾 Save Agent Configuration",
                                variant="primary",
                                size="lg"
                            )
                    
                    # Tools Selection Tab
                    with gr.TabItem("🛠️ Tools Selection", id=2):
                        with gr.Column():
                            gr.Markdown("### 🔧 **MCP Tools Management**")
                            
                            # MCP Tools Section
                            with gr.Accordion("🛠️ **Available Tools**", open=True):
                                gr.HTML("""
                                    <div class="tools-header">
                                        <span>🔧</span>
                                        <span>Tool Configuration</span>
                                    </div>
                                """)
                                
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
                                        gr.Markdown("##### ✅ **Selected Tools**")
                                        selected_tools_df = gr.Dataframe(
                                            headers=["🔧 Tool", "⚡ Action"],
                                            datatype=["str", "str"],
                                            interactive=False,
                                            label=""
                                        )
                                        
                                        selected_tools_state = gr.State([])
                    
                    # Logs & Output Tab
                    with gr.TabItem("📊 Generated JSON", id=3):
                        with gr.Column():
                            gr.Markdown("### 📋 **Generated Configuration JSON**")
                            
                            json_output = gr.JSON(
                                label="Agent Configuration"
                            )
                            
                            with gr.Row():
                                refresh_json_btn = gr.Button(
                                    "🔄 Refresh"
                                )
                                export_json_btn = gr.Button(
                                    "📥 Export JSON"
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
            
            def get_available_tools(server_name, selected_tools):
                if not server_name or not all_tools_cache or server_name not in all_tools_cache:
                    return []
                selected_set = {(t['server'], t['tool']) for t in selected_tools}
                tool_rows = []
                for tool in all_tools_cache[server_name]:
                    tool_name = tool["name"]
                    if (server_name, tool_name) not in selected_set:
                        tool_rows.append([f"{server_name}: {tool_name}", "➕ Add"])
                return tool_rows
            
            def get_selected_tools_display(selected_tools):
                if not selected_tools:
                    return []
                tool_rows = []
                for tool in selected_tools:
                    label = f"{tool.get('server', '')}: {tool.get('tool', '')}"
                    tool_rows.append([label, "❌ Remove"])
                return tool_rows
            
            def initialize_mcp_tools():
                servers = load_mcp_servers()
                selected_tools = []
                
                first_server = servers[0] if servers else None
                available_tools = get_available_tools(first_server, selected_tools)
                selected_tools_display = get_selected_tools_display(selected_tools)
                
                return (
                    gr.update(choices=servers, value=first_server),
                    available_tools,
                    selected_tools_display,
                    selected_tools
                )
            
            def update_available_tools(server_name, selected_tools):
                available_tools = get_available_tools(server_name, selected_tools)
                return available_tools
            
            def add_tool(evt: gr.SelectData, selected_tools, server_name):
                if evt is None or evt.index is None or not all_tools_cache:
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
                
                available_tools = get_available_tools(server_name, selected_tools)
                row_index = evt.index[0] if isinstance(evt.index, list) else evt.index
                if row_index >= len(available_tools):
                    return get_selected_tools_display(selected_tools), available_tools, selected_tools
                
                tool_label = available_tools[row_index][0]
                try:
                    server, tool = tool_label.split(": ", 1)
                except:
                    return get_selected_tools_display(selected_tools), available_tools, selected_tools
                
                for t in selected_tools:
                    if t.get("server") == server and t.get("tool") == tool:
                        return get_selected_tools_display(selected_tools), available_tools, selected_tools
                
                new_selected = selected_tools + [{"server": server, "tool": tool}]
                return (
                    get_selected_tools_display(new_selected),
                    get_available_tools(server_name, new_selected),
                    new_selected
                )
            
            def remove_tool(evt: gr.SelectData, selected_tools, server_name):
                if evt is None or evt.index is None:
                    return get_selected_tools_display(selected_tools), get_available_tools(server_name, selected_tools), selected_tools
                
                selected_display = get_selected_tools_display(selected_tools)
                row_index = evt.index[0] if isinstance(evt.index, list) else evt.index
                if row_index >= len(selected_display):
                    return selected_display, get_available_tools(server_name, selected_tools), selected_tools
                
                tool_label = selected_display[row_index][0]
                try:
                    server, tool = tool_label.split(": ", 1)
                except:
                    return selected_display, get_available_tools(server_name, selected_tools), selected_tools
                
                new_selected = [t for t in selected_tools if not (t.get("server") == server and t.get("tool") == tool)]
                return (
                    get_selected_tools_display(new_selected),
                    get_available_tools(server_name, new_selected),
                    new_selected
                )
            
            # Connect MCP events
            init_btn.click(
                fn=lambda: initialize_mcp_tools(),
                outputs=[server_selector, available_tools_df, selected_tools_df, selected_tools_state]
            )
            
            server_selector.change(
                fn=update_available_tools,
                inputs=[server_selector, selected_tools_state],
                outputs=[available_tools_df]
            )
            
            available_tools_df.select(
                fn=add_tool,
                inputs=[selected_tools_state, server_selector],
                outputs=[selected_tools_df, available_tools_df, selected_tools_state]
            )
            
            selected_tools_df.select(
                fn=remove_tool,
                inputs=[selected_tools_state, server_selector],
                outputs=[selected_tools_df, available_tools_df, selected_tools_state]
            )
            
            # Event Handlers
            async def process_message(message, history):
                if not message:
                    yield history, "", ""
                    return
                
                # Add user message
                history.append({"role": "user", "content": message})
                
                # Add processing animation as temporary assistant message
                processing_content = """🏗️ Building your agent<span class="thinking-dots">
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
                yield history, "", ""
                
                full_response = ""
                json_detected = False
                
                try:
                    async for response in agent_builder.process_query(message):
                        full_response = response
                        
                        # Replace the processing message with the actual response
                        history[-1] = {"role": "assistant", "content": full_response}
                        
                        # Check for JSON configuration
                        json_html = ""
                        if agent_builder.generated_config:
                            json_detected = True
                            json_html = "<div>"
                            json_html += "<div>📋 Configuration detected in response!</div>"
                            json_html += f"<div><pre>{json.dumps(agent_builder.generated_config, indent=2)}</pre></div>"
                            json_html += "</div>"
                        else:
                            json_html = "<div>Generated configuration will appear here...</div>"
                        
                        yield history, "", json_html
                    
                    # Final JSON display when complete
                    final_json_html = ""
                    if agent_builder.generated_config:
                        final_json_html = "<div>"
                        final_json_html += "<div>✅ Configuration ready for review!</div>"
                        final_json_html += f"<div><pre>{json.dumps(agent_builder.generated_config, indent=2)}</pre></div>"
                        final_json_html += "</div>"
                    else:
                        final_json_html = "<div>Generated configuration will appear here...</div>"
                    
                    yield history, "", final_json_html
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    history[-1] = {"role": "assistant", "content": error_msg}
                    error_html = f"<div>Error: {str(e)}</div>"
                    yield history, "", error_html

            def initialize_agent(model):
                if not model:
                    return [
                        gr.update(visible=True),   # chat_placeholder
                        'Builder: Failed to Initialize',
                        '❌ Please select a model',
                        "<div>Generated configuration will appear here...</div>",
                        gr.update(visible=False)   # chat_interface
                    ]
                
                agent_builder.model_params = {
                    "temperature": temperature.value,
                    "max_tokens": max_tokens.value
                }
                success = asyncio.run(agent_builder.initialize_agent(model))
                
                if success:
                    initial_messages = [{"role": "assistant", "content": agent_builder.welcome_message}]
                    return [
                        gr.update(visible=False),  # chat_placeholder
                        'Builder: Ready & Connected',
                        '✅ Agent builder initialized successfully',
                        "<div>Generated configuration will appear here...</div>",
                        gr.update(visible=True)    # chat_interface
                    ]
                return [
                    gr.update(visible=True),   # chat_placeholder
                    'Builder: Failed to Initialize',
                    '❌ Failed to initialize agent builder',
                    "<div>Generated configuration will appear here...</div>",
                    gr.update(visible=False)   # chat_interface
                ]
            
            def update_config_from_json():
                if agent_builder.generated_config:
                    config = agent_builder.generated_config
                    
                    # Also update the JSON preview
                    json_html = "<div>"
                    json_html += "<div>📋 Configuration extracted from conversation</div>"
                    json_html += f"<div><pre>{json.dumps(config, indent=2)}</pre></div>"
                    json_html += "</div>"
                    
                    return {
                        name_input: config.get("name", ""),
                        slug_input: config.get("slug", ""),
                        is_stream: config.get("is_stream", False),
                        is_chat: config.get("is_chat", True),
                        welcome_msg: config.get("welcome_message", ""),
                        background: config.get("background", ""),
                        task_details: config.get("task_details", ""),
                        input_values: config.get("input_values", ""),
                        output_format: config.get("output_format", ""),
                        json_output: config,
                        json_preview: json_html
                    }
                return {
                    name_input: "",
                    slug_input: "",
                    is_stream: False,
                    is_chat: True,
                    welcome_msg: "",
                    background: "",
                    task_details: "",
                    input_values: "",
                    output_format: "",
                    json_output: {},
                    json_preview: "<div>Generated configuration will appear here...</div>"
                }
            
            def save_agent_configuration(name, slug, is_stream, is_chat, welcome, bg, task, inputs, output, selected_tools):
                try:
                    # Clean the name for filename
                    clean_name = name.strip().replace("&","_").replace(" ","_").replace(".","_").replace("-","_").replace("__","_")
                    if not clean_name:
                        return '❌ Please provide an agent name'
                    
                    agent_config = {
                        "name": name,
                        "slug": slug if slug else clean_name.lower(),
                        "welcome_message": welcome,
                        "background": bg,
                        "task_details": task,
                        "input_values": inputs,
                        "output_format": output,
                        "is_stream": is_stream,
                        "is_chat": is_chat
                    }
                    
                    if selected_tools:
                        agent_config["mcp_tools"] = selected_tools
                    
                    # Save to agent_config directory
                    file_name = f"{clean_name.lower()}.json"
                    config_dir = "agent_config"
                    if not os.path.exists(config_dir):
                        os.makedirs(config_dir, exist_ok=True)
                    
                    file_path = os.path.join(config_dir, file_name)
                    with open(file_path, "w") as f:
                        json.dump(agent_config, f, indent=2)
                    
                    agent_builder.generated_config = agent_config
                    return f'✅ Agent configuration saved as {file_name}! \n\n💡 Tip: Use the 🔄 refresh button in Agent Tester to see this new configuration.'
                    
                except Exception as e:
                    return f'❌ Error saving configuration: {str(e)}'
            
            def clear_chat():
                agent_builder.messages = []
                agent_builder.chat_history = []
                if agent_builder.welcome_message:
                    return [{"role": "assistant", "content": agent_builder.welcome_message}], "<div>Generated configuration will appear here...</div>"
                return [], "<div>Generated configuration will appear here...</div>"
            
            def reset_configuration():
                agent_builder.generated_config = {}
                return {
                    name_input: "",
                    slug_input: "",
                    is_stream: False,
                    is_chat: True,
                    welcome_msg: "",
                    background: "",
                    task_details: "",
                    input_values: "",
                    output_format: "",
                    json_output: {},
                    json_preview: "<div>Generated configuration will appear here...</div>"
                }
            
            # Connect all events
            init_btn.click(
                fn=initialize_agent,
                inputs=[model_selector],
                outputs=[chat_placeholder, agent_status, save_status, json_preview, chat_interface]
            ).then(
                fn=lambda: [{"role": "assistant", "content": agent_builder.welcome_message}] if agent_builder.adk_agent else [],
                outputs=[chatbot]
            )
            
            submit_btn.click(
                fn=process_message,
                inputs=[msg, chatbot],
                outputs=[chatbot, msg, json_preview]
            ).then(
                fn=update_config_from_json,
                outputs=[name_input, slug_input, is_stream, is_chat, welcome_msg, background, task_details, input_values, output_format, json_output, json_preview]
            )
            
            msg.submit(
                fn=process_message,
                inputs=[msg, chatbot],
                outputs=[chatbot, msg, json_preview]
            ).then(
                fn=update_config_from_json,
                outputs=[name_input, slug_input, is_stream, is_chat, welcome_msg, background, task_details, input_values, output_format, json_output, json_preview]
            )
            
            save_config_btn.click(
                fn=save_agent_configuration,
                inputs=[
                    name_input, slug_input, is_stream, is_chat, welcome_msg,
                    background, task_details, input_values, output_format, selected_tools_state
                ],
                outputs=[save_status]
            ).then(
                fn=lambda: agent_builder.generated_config if agent_builder.generated_config else {},
                outputs=[json_output]
            )
            
            clear_chat_btn.click(
                fn=clear_chat,
                outputs=[chatbot, json_preview]
            )
            
            reset_config_btn.click(
                fn=reset_configuration,
                outputs=[name_input, slug_input, is_stream, is_chat, welcome_msg, background, task_details, input_values, output_format, json_output, selected_tools_state, json_preview]
            )
            
            refresh_json_btn.click(
                fn=lambda: agent_builder.generated_config if agent_builder.generated_config else {},
                outputs=[json_output]
            )

    return interface

if __name__ == "__main__":
    create_agent_builder_interface().launch(
        server_name="0.0.0.0",
        server_port=7861,
        share=False
    ) 