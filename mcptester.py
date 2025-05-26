import gradio as gr
import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
sys.path.append(project_root)

from mcp_client import MCPCLient


class MCPTesterInterface:
    def __init__(self):
        self.mcp_client = MCPCLient()
        self.all_tools = {}
        self.servers_loaded = False
        self.temp_server_config = None  # Store temporary server config for testing
        self.temp_server_name = None
        self.temp_server_tools = []  # Store tools from tested online server
        self.temp_client = None  # Store temporary client for online server
        
    async def load_servers(self):
        """Load MCP servers from config file"""
        config_path = "mcp/mcp_config.json"
        if os.path.exists(config_path):
            self.mcp_client.load_servers(config_path)
            self.all_tools = await self.mcp_client.load_all_tools()
            self.servers_loaded = True
            return True
        return False
    
    async def test_online_server(self, server_config_text: str):
        """Test an online MCP server configuration"""
        try:
            # Parse the JSON configuration
            config_data = json.loads(server_config_text.strip())
            
            # Extract server configuration
            if "mcpServers" not in config_data:
                return False, "Invalid config format. Expected 'mcpServers' key."
            
            mcp_servers = config_data["mcpServers"]
            if not mcp_servers:
                return False, "No servers found in configuration."
            
            # Get the first server (assuming single server config for testing)
            server_name = list(mcp_servers.keys())[0]
            server_config = mcp_servers[server_name]
            
            # Store for potential addition to config later
            self.temp_server_config = server_config
            self.temp_server_name = server_name
            
            # Create a temporary MCP client to test this server
            self.temp_client = MCPCLient()
            self.temp_client.load_single_server(server_name, server_config)
            
            # Try to load tools to verify the server works
            tools = await self.temp_client.load_all_tools()
            
            if server_name in tools and tools[server_name]:
                self.temp_server_tools = tools[server_name]
                return True, {
                    "server_name": server_name,
                    "tools": tools[server_name],
                    "config": server_config
                }
            else:
                return False, f"Server '{server_name}' loaded but no tools found or server failed to start."
                
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"
        except Exception as e:
            return False, f"Error testing server: {str(e)}"
    
    async def execute_temp_tool(self, tool_name: str, input_data: Dict[str, Any]):
        """Execute a tool from the temporary online server"""
        try:
            if not self.temp_client or not self.temp_server_name:
                raise ValueError("No temporary server available")
            
            result = await self.temp_client.call_tool(self.temp_server_name, tool_name, input_data)
            return True, result
        except Exception as e:
            return False, str(e)
    
    async def add_server_to_config(self):
        """Add the tested server to the main configuration"""
        if not self.temp_server_config or not self.temp_server_name:
            return False, "No server configuration to add. Please test a server first."
        
        try:
            config_path = "mcp/mcp_config.json"
            
            # Load current config
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    current_config = json.load(f)
            else:
                current_config = {"mcpServers": {}}
            
            # Check if server already exists
            if self.temp_server_name in current_config["mcpServers"]:
                return False, f"Server '{self.temp_server_name}' already exists in configuration."
            
            # Add the new server
            current_config["mcpServers"][self.temp_server_name] = self.temp_server_config
            
            # Save the updated config
            with open(config_path, 'w') as f:
                json.dump(current_config, f, indent=2)
            
            # Reload servers to include the new one
            await self.load_servers()
            
            # Clear temp config
            self.temp_server_config = None
            self.temp_server_name = None
            self.temp_server_tools = []
            self.temp_client = None
            
            return True, f"Server added successfully to configuration."
            
        except Exception as e:
            return False, f"Error adding server to config: {str(e)}"
    
    def get_server_list(self):
        """Get list of available servers"""
        if hasattr(self.mcp_client, 'servers'):
            return [server.name for server in self.mcp_client.servers]
        return []
    
    def get_tools_for_server(self, server_name: str):
        """Get tools for a specific server"""
        if server_name and server_name in self.all_tools:
            return self.all_tools[server_name]
        return []
    
    def get_temp_server_tools(self):
        """Get tools for the temporary online server"""
        return self.temp_server_tools
    
    async def execute_tool(self, server_name: str, tool_name: str, input_data: Dict[str, Any]):
        """Execute a tool with given parameters"""
        try:
            result = await self.mcp_client.call_tool(server_name, tool_name, input_data)
            return True, result
        except Exception as e:
            return False, str(e)


def create_mcp_tester_interface():
    mcp_tester = MCPTesterInterface()
    
    with gr.Blocks(title="MCP Tools Manager", theme=gr.themes.Soft(), css="""
        .header-container { 
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header-title { 
            color: white; 
            font-size: 2em; 
            font-weight: bold; 
            margin: 0;
        }
        .server-panel {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            border: 2px solid #e1e5e9;
            max-height: 600px;
            overflow-y: auto;
        }
        .tool-panel {
            background: #fff;
            border-radius: 10px;
            padding: 15px;
            border: 2px solid #e1e5e9;
        }
        .online-server-panel {
            background: #fff3cd;
            border-radius: 10px;
            padding: 15px;
            border: 2px solid #ffeaa7;
            margin-top: 15px;
        }
        .tool-details {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            font-size: 0.85em;
        }
        .tool-name-detail {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 4px;
        }
        .tool-desc-detail {
            color: #5a6c7d;
            line-height: 1.3;
        }
        .status-success { color: #27ae60; font-weight: bold; }
        .status-error { color: #e74c3c; font-weight: bold; }
        .loading { color: #f39c12; }
        .executing {
            background: linear-gradient(45deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
            background-size: 400% 400%;
            animation: gradient 2s ease infinite;
            color: white;
        }
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    """) as interface:
        
        # Header
        gr.HTML("""
            <div class="header-container">
                <h1 class="header-title">🛠️ MCP Tools Manager</h1>
                <p style="color: white; margin: 5px 0 0 0; opacity: 0.9;">Test and explore Model Context Protocol tools</p>
            </div>
        """)
        
        # Status display
        status_display = gr.Markdown("🔄 Initializing MCP servers...", elem_classes=["loading"])
        
        with gr.Row():
            # Left Panel - Servers and Tool Details
            with gr.Column(scale=1):
                # Tabs for different modes
                with gr.Tabs():
                    # Tab 1: Existing Servers
                    with gr.TabItem("📡 My Servers"):
                        with gr.Group():
                            server_radio = gr.Radio(
                                label="Select Server",
                                choices=[],
                                value=None,
                                interactive=True
                            )
                            
                            # Server info
                            server_info = gr.Markdown("Select a server to view details")
                            
                            # Tool details section
                            gr.Markdown("### 🔧 **Tool Details**")
                            tool_details_container = gr.HTML("Select a server to view tool details", elem_classes=["server-panel"])
                    
                    # Tab 2: Online Server Testing
                    with gr.TabItem("🌐 Test Online Server"):
                        with gr.Group():
                            gr.Markdown("### Test MCP Server Configuration")
                            gr.Markdown("_Paste an MCP server configuration to test it before adding to your config_")
                            
                            online_server_config = gr.Textbox(
                                label="MCP Server Configuration (JSON)",
                                placeholder='''Paste server config here, e.g.:
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}''',
                                lines=10,
                                max_lines=15
                            )
                            
                            with gr.Row():
                                test_online_btn = gr.Button("🧪 Test Server", variant="primary", size="sm")
                                clear_online_btn = gr.Button("🔄 Clear", variant="secondary", size="sm")
                            
                            online_test_status = gr.Markdown("")
                            
                            # Online server details (when successfully tested)
                            with gr.Group(visible=False) as online_server_details_group:
                                online_server_info = gr.Markdown("")
                                add_to_config_btn = gr.Button("➕ Add to My Servers", variant="primary", size="lg")
            
            # Right Panel - Tool Selection and Execution
            with gr.Column(scale=2):
                with gr.Group():
                    # Mode indicator
                    current_mode = gr.State("existing")  # "existing" or "online"
                    current_server = gr.State("")
                    
                    mode_indicator = gr.Markdown("### 🚀 **Tool Selection & Execution**")
                    
                    # Tools list (shared between both modes)
                    tools_list = gr.Radio(
                        label="Select Tool to Execute",
                        choices=[],
                        value=None,
                        interactive=True,
                        visible=False
                    )
                    
                    tools_placeholder = gr.Markdown("Select a server to view available tools")
                    
                    # Tool execution area (shared between both modes)
                    with gr.Group(visible=False) as tool_execution_group:
                        gr.Markdown("#### 🎯 **Tool Execution**")
                        
                        tool_title = gr.Markdown("")
                        tool_description = gr.Markdown("")
                        
                        # Dynamic form container
                        form_inputs = gr.State([])
                        
                        # Parameter inputs (will be populated dynamically)
                        param_components = []
                        for i in range(10):  # Support up to 10 parameters
                            param_input = gr.Textbox(
                                label=f"Parameter {i+1}",
                                visible=False,
                                interactive=True
                            )
                            param_components.append(param_input)
                        
                        # Execution controls
                        with gr.Row():
                            execute_btn = gr.Button(
                                "🚀 Execute Tool", 
                                variant="primary", 
                                size="lg",
                                elem_id="execute_btn"
                            )
                            clear_btn = gr.Button("🔄 Clear Results", variant="secondary")
                        
                        # Loading indicator
                        loading_indicator = gr.HTML("", visible=False)
                        
                        # Results
                        execution_status = gr.Markdown("")
                        execution_result = gr.Code(
                            label="Execution Result",
                            language="json",
                            interactive=False,
                            visible=False
                        )
        
        # Initialize on load
        async def initialize_on_load():
            """Initialize servers automatically when the interface loads"""
            try:
                success = await mcp_tester.load_servers()
                if success:
                    servers = mcp_tester.get_server_list()
                    if servers:
                        return (
                            gr.Radio(choices=servers, value=servers[0]),
                            "✅ **MCP servers loaded successfully!** Select a server to explore tools.",
                            create_server_info(servers[0]),
                            create_tool_details_html(servers[0]),
                            gr.Radio(choices=create_tool_choices(servers[0]), value=None, visible=True),
                            "**Select a tool from the list above to execute**"
                        )
                    else:
                        return (
                            gr.Radio(choices=[]),
                            "⚠️ **No servers found** - Check your MCP configuration.",
                            "No servers configured",
                            "No tool details available",
                            gr.Radio(choices=[], visible=False),
                            "No tools available"
                        )
                else:
                    return (
                        gr.Radio(choices=[]),
                        "❌ **Failed to load servers** - Check if `mcp/mcp_config.json` exists.",
                        "Configuration error",
                        "Unable to load tool details",
                        gr.Radio(choices=[], visible=False),
                        "Unable to load tools"
                    )
            except Exception as e:
                return (
                    gr.Radio(choices=[]),
                    f"❌ **Error:** {str(e)}",
                    "Error occurred",
                    "Unable to load tool details",
                    gr.Radio(choices=[], visible=False),
                    "Unable to load tools"
                )
        
        async def test_online_server_handler(config_text):
            """Handle testing of online MCP server"""
            if not config_text.strip():
                return (
                    "⚠️ Please paste a server configuration to test.",
                    gr.Group(visible=False),
                    gr.Button("➕ Add to My Servers", visible=False)
                )
            
            try:
                success, result = await mcp_tester.test_online_server(config_text)
                
                if success:
                    server_name = result["server_name"]
                    tools = result["tools"]
                    config = result["config"]
                    
                    # Create server info display
                    server_info_text = f"""
**🎉 Server "{server_name}" tested successfully!**

**Configuration:**
- **Command:** `{config.get('command', 'N/A')}`
- **Args:** `{', '.join(config.get('args', []))}`
{f"- **Environment:** {len(config.get('env', {}))} variables" if config.get('env') else ""}
- **Tools Found:** {len(tools)}

✅ Server is ready to use! You can now test its tools on the right panel.
                    """
                    
                    return (
                        f"✅ **Server '{server_name}' is working!** Found {len(tools)} tools. Check the right panel to test tools.",
                        gr.Group(visible=True),
                        gr.Button("➕ Add to My Servers", visible=True, variant="primary")
                    )
                else:
                    return (
                        f"❌ **Server test failed:** {result}",
                        gr.Group(visible=False),
                        gr.Button("➕ Add to My Servers", visible=False)
                    )
                    
            except Exception as e:
                return (
                    f"❌ **Error testing server:** {str(e)}",
                    gr.Group(visible=False),
                    gr.Button("➕ Add to My Servers", visible=False)
                )
        
        def update_online_server_info():
            """Update the online server info display"""
            if mcp_tester.temp_server_name and mcp_tester.temp_server_config:
                server_name = mcp_tester.temp_server_name
                config = mcp_tester.temp_server_config
                tools = mcp_tester.temp_server_tools
                
                info_text = f"""
**🎉 Server "{server_name}" tested successfully!**

**Configuration:**
- **Command:** `{config.get('command', 'N/A')}`
- **Args:** `{', '.join(config.get('args', []))}`
{f"- **Environment:** {len(config.get('env', {}))} variables" if config.get('env') else ""}
- **Tools Found:** {len(tools)}

✅ Server is ready to use! You can test its tools on the right panel.
                """
                return info_text
            return ""
        
        def clear_online_server():
            """Clear online server testing"""
            mcp_tester.temp_server_config = None
            mcp_tester.temp_server_name = None
            mcp_tester.temp_server_tools = []
            mcp_tester.temp_client = None
            
            return (
                "",  # Clear config text
                "",  # Clear status
                gr.Group(visible=False),  # Hide details group
                gr.Button("➕ Add to My Servers", visible=False),  # Hide add button
                gr.Radio(choices=[], value=None, visible=False),  # Clear tools list
                "Select a server to view available tools",  # Reset placeholder
                gr.Group(visible=False),  # Hide execution group
                *[gr.Textbox(visible=False) for _ in range(10)]  # Hide all parameter inputs
            )
        
        async def add_to_config_handler():
            """Handle adding tested server to configuration"""
            try:
                success, message = await mcp_tester.add_server_to_config()
                
                if success:
                    # Refresh the server list
                    servers = mcp_tester.get_server_list()
                    return (
                        f"✅ **{message}** You can now find it in the 'My Servers' tab.",
                        gr.Radio(choices=servers, value=servers[-1] if servers else None),  # Select the newly added server
                        gr.Button("➕ Add to My Servers", visible=False),  # Hide the button after adding
                        gr.Group(visible=False)  # Hide the server details
                    )
                else:
                    return (
                        f"❌ **{message}**",
                        gr.Radio(),  # No change to server list
                        gr.Button("➕ Add to My Servers", visible=True),  # Keep button visible
                        gr.Group()  # No change to server details
                    )
                    
            except Exception as e:
                return (
                    f"❌ **Error:** {str(e)}",
                    gr.Radio(),
                    gr.Button("➕ Add to My Servers", visible=True),
                    gr.Group()
                )
        
        def create_server_info(server_name):
            """Create server information display"""
            if not server_name:
                return "No server selected"
            
            tools = mcp_tester.get_tools_for_server(server_name)
            tool_count = len(tools) if tools else 0
            
            return f"""
            **Server:** `{server_name}`  
            **Tools Available:** {tool_count}  
            **Status:** ✅ Active
            """
        
        def create_tool_details_html(server_name):
            """Create detailed tool information for left panel"""
            if not server_name:
                return "Select a server to view tool details"
            
            tools = mcp_tester.get_tools_for_server(server_name)
            if not tools:
                return f"No tools available for server: **{server_name}**"
            
            html_content = f"""
            <div style="max-height: 400px; overflow-y: auto;">
                <p><strong>{len(tools)} tools available:</strong></p>
            """
            
            for tool in tools:
                description = tool.get('description', 'No description available')
                # Truncate very long descriptions
                if len(description) > 120:
                    description = description[:120] + "..."
                
                html_content += f"""
                <div class="tool-details">
                    <div class="tool-name-detail">📋 {tool['name']}</div>
                    <div class="tool-desc-detail">{description}</div>
                </div>
                """
            
            html_content += "</div>"
            return html_content
        
        def create_tool_choices(server_name):
            """Create tool choices for radio selection"""
            if not server_name:
                return []
            
            tools = mcp_tester.get_tools_for_server(server_name)
            if not tools:
                return []
            
            return [f"📋 {tool['name']}" for tool in tools]
        
        def on_server_change(server_name):
            """Handle server selection change"""
            if server_name:
                return (
                    create_server_info(server_name),
                    create_tool_details_html(server_name),
                    gr.Radio(choices=create_tool_choices(server_name), value=None, visible=True),
                    "**Select a tool from the list above to execute**",
                    gr.Group(visible=False),  # Hide tool execution until tool is selected
                    *[gr.Textbox(visible=False) for _ in range(10)]  # Hide all parameter inputs
                )
            return (
                "No server selected",
                "Select a server to view tool details", 
                gr.Radio(choices=[], visible=False),
                "Select a server to view tools", 
                gr.Group(visible=False),
                *[gr.Textbox(visible=False) for _ in range(10)]
            )
        
        def on_tool_change(tool_selection, server_name):
            """Handle tool selection change"""
            # Check if we're dealing with online server or existing server
            if mcp_tester.temp_server_name and mcp_tester.temp_server_tools:
                # Online server mode
                if not tool_selection:
                    return (
                        gr.Group(visible=False),
                        "",
                        "",
                        [],
                        *[gr.Textbox(visible=False) for _ in range(10)]
                    )
                
                # Extract tool name from selection
                tool_name = tool_selection.replace("📋 ", "")
                
                # Get tool details from temp server tools
                tools = mcp_tester.temp_server_tools
                tool = next((t for t in tools if t['name'] == tool_name), None)
                
                if not tool:
                    return (
                        gr.Group(visible=False),
                        "",
                        "",
                        [],
                        *[gr.Textbox(visible=False) for _ in range(10)]
                    )
                
                # Create form based on tool schema
                input_schema = tool.get('input_schema', {})
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])
                
                title = f"### 🛠️ **{tool_name}** (🌐 Online Server: {mcp_tester.temp_server_name})"
                description = f"_{tool.get('description', 'No description available')}_"
                
                # Prepare form inputs
                form_data = []
                param_inputs = []
                
                param_index = 0
                for prop_name, prop_attrs in properties.items():
                    if param_index >= 10:  # Limit to 10 parameters
                        break
                    
                    prop_type = prop_attrs.get('type', 'string')
                    title_text = prop_attrs.get('title', prop_name)
                    default = prop_attrs.get('default', '')
                    is_required = prop_name in required
                    
                    label = f"{title_text} {'*' if is_required else ''}"
                    placeholder = f"Enter {title_text.lower()}"
                    info = f"Type: {prop_type}" + (" (Required)" if is_required else " (Optional)")
                    
                    form_data.append({
                        'name': prop_name,
                        'type': prop_type,
                        'required': is_required,
                        'default': default
                    })
                    
                    param_inputs.append(gr.Textbox(
                        label=label,
                        placeholder=placeholder,
                        value=str(default) if default else "",
                        info=info,
                        visible=True
                    ))
                    
                    param_index += 1
                
                # Hide remaining parameter inputs
                while param_index < 10:
                    param_inputs.append(gr.Textbox(visible=False))
                    param_index += 1
                
                return (
                    gr.Group(visible=True),
                    title,
                    description,
                    form_data,
                    *param_inputs
                )
            
            else:
                # Existing server mode
                if not tool_selection or not server_name:
                    return (
                        gr.Group(visible=False),
                        "",
                        "",
                        [],
                        *[gr.Textbox(visible=False) for _ in range(10)]
                    )
                
                # Extract tool name from selection
                tool_name = tool_selection.replace("📋 ", "")
                
                # Get tool details
                tools = mcp_tester.get_tools_for_server(server_name)
                tool = next((t for t in tools if t['name'] == tool_name), None)
                
                if not tool:
                    return (
                        gr.Group(visible=False),
                        "",
                        "",
                        [],
                        *[gr.Textbox(visible=False) for _ in range(10)]
                    )
                
                # Create form based on tool schema
                input_schema = tool.get('input_schema', {})
                properties = input_schema.get('properties', {})
                required = input_schema.get('required', [])
                
                title = f"### 🛠️ **{tool_name}** (📡 Server: {server_name})"
                description = f"_{tool.get('description', 'No description available')}_"
                
                # Prepare form inputs
                form_data = []
                param_inputs = []
                
                param_index = 0
                for prop_name, prop_attrs in properties.items():
                    if param_index >= 10:  # Limit to 10 parameters
                        break
                    
                    prop_type = prop_attrs.get('type', 'string')
                    title_text = prop_attrs.get('title', prop_name)
                    default = prop_attrs.get('default', '')
                    is_required = prop_name in required
                    
                    label = f"{title_text} {'*' if is_required else ''}"
                    placeholder = f"Enter {title_text.lower()}"
                    info = f"Type: {prop_type}" + (" (Required)" if is_required else " (Optional)")
                    
                    form_data.append({
                        'name': prop_name,
                        'type': prop_type,
                        'required': is_required,
                        'default': default
                    })
                    
                    param_inputs.append(gr.Textbox(
                        label=label,
                        placeholder=placeholder,
                        value=str(default) if default else "",
                        info=info,
                        visible=True
                    ))
                    
                    param_index += 1
                
                # Hide remaining parameter inputs
                while param_index < 10:
                    param_inputs.append(gr.Textbox(visible=False))
                    param_index += 1
                
                return (
                    gr.Group(visible=True),
                    title,
                    description,
                    form_data,
                    *param_inputs
                )
        
        async def execute_tool_handler(server_name, tool_selection, form_data, *param_values):
            """Handle tool execution with loading states for both existing and online servers"""
            if not tool_selection:
                yield (
                    "❌ Please select a tool first", 
                    gr.Code(visible=False),
                    gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                    gr.HTML("", visible=False)
                )
                return
            
            tool_name = tool_selection.replace("📋 ", "")
            
            # Determine if we're using online server or existing server
            is_online_server = mcp_tester.temp_server_name and mcp_tester.temp_server_tools
            current_server = mcp_tester.temp_server_name if is_online_server else server_name
            
            if not current_server:
                yield (
                    "❌ No server available for execution", 
                    gr.Code(visible=False),
                    gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                    gr.HTML("", visible=False)
                )
                return
            
            # Show loading state
            server_type = "🌐 Online" if is_online_server else "📡 Configured"
            yield (
                f"🔄 **Executing tool on {server_type} server '{current_server}'...** Please wait.", 
                gr.Code(visible=False),
                gr.Button("⏳ Executing...", variant="secondary", interactive=False, elem_classes=["executing"]),
                gr.HTML('<div class="spinner"></div> <span style="margin-left: 10px;">Tool is running...</span>', visible=True)
            )
            
            try:
                # Build parameters from form data and values
                parameters = {}
                if form_data:
                    for i, field_info in enumerate(form_data):
                        if i < len(param_values):
                            value = param_values[i]
                            if value:  # Only include non-empty values
                                field_name = field_info['name']
                                field_type = field_info['type']
                                
                                # Convert value to appropriate type
                                if field_type == 'integer':
                                    try:
                                        parameters[field_name] = int(value)
                                    except ValueError:
                                        yield (
                                            f"❌ Invalid integer value for {field_name}: {value}", 
                                            gr.Code(visible=False),
                                            gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                                            gr.HTML("", visible=False)
                                        )
                                        return
                                elif field_type == 'number':
                                    try:
                                        parameters[field_name] = float(value)
                                    except ValueError:
                                        yield (
                                            f"❌ Invalid number value for {field_name}: {value}", 
                                            gr.Code(visible=False),
                                            gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                                            gr.HTML("", visible=False)
                                        )
                                        return
                                elif field_type == 'boolean':
                                    parameters[field_name] = value.lower() in ('true', '1', 'yes', 'on')
                                else:
                                    parameters[field_name] = value
                
                # Execute tool based on server type
                if is_online_server:
                    success, result = await mcp_tester.execute_temp_tool(tool_name, parameters)
                else:
                    success, result = await mcp_tester.execute_tool(current_server, tool_name, parameters)
                
                if success:
                    # Format result for display
                    if isinstance(result, (dict, list)):
                        formatted_result = json.dumps(result, indent=2)
                    else:
                        formatted_result = str(result)
                    
                    yield (
                        f"✅ **Tool executed successfully on {server_type} server '{current_server}'!**\n\n**Parameters used:** {json.dumps(parameters, indent=2)}",
                        gr.Code(value=formatted_result, visible=True),
                        gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                        gr.HTML("", visible=False)
                    )
                else:
                    yield (
                        f"❌ **Tool execution failed on {server_type} server '{current_server}':** {result}", 
                        gr.Code(visible=False),
                        gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                        gr.HTML("", visible=False)
                    )
                    
            except Exception as e:
                yield (
                    f"❌ **Unexpected error:** {str(e)}", 
                    gr.Code(visible=False),
                    gr.Button("🚀 Execute Tool", variant="primary", interactive=True),
                    gr.HTML("", visible=False)
                )
        
        def update_tools_display_for_online():
            """Update tools display when online server is tested"""
            if mcp_tester.temp_server_name and mcp_tester.temp_server_tools:
                tools = mcp_tester.temp_server_tools
                server_name = mcp_tester.temp_server_name
                
                tool_choices = [f"📋 {tool['name']}" for tool in tools]
                
                return (
                    gr.Radio(choices=tool_choices, value=None, visible=True),
                    f"**🌐 Testing Online Server: {server_name}** - Select a tool to test its functionality",
                    gr.Group(visible=False),  # Hide execution until tool selected
                    *[gr.Textbox(visible=False) for _ in range(10)]  # Hide all parameter inputs
                )
            return (
                gr.Radio(choices=[], visible=False),
                "Select a server to view available tools",
                gr.Group(visible=False),
                *[gr.Textbox(visible=False) for _ in range(10)]
            )
        
        def clear_results():
            """Clear execution results"""
            return "", gr.Code(value="", visible=False)
        
        # Initialize interface on load
        interface.load(
            fn=initialize_on_load,
            outputs=[server_radio, status_display, server_info, tool_details_container, tools_list, tools_placeholder]
        )
        
        # Handle server selection
        server_radio.change(
            fn=on_server_change,
            inputs=[server_radio],
            outputs=[server_info, tool_details_container, tools_list, tools_placeholder, tool_execution_group] + param_components
        )
        
        # Handle tool selection
        tools_list.change(
            fn=on_tool_change,
            inputs=[tools_list, server_radio],
            outputs=[tool_execution_group, tool_title, tool_description, form_inputs] + param_components
        )
        
        # Handle online server testing
        test_online_btn.click(
            fn=test_online_server_handler,
            inputs=[online_server_config],
            outputs=[online_test_status, online_server_details_group, add_to_config_btn]
        ).then(
            fn=update_tools_display_for_online,
            outputs=[tools_list, tools_placeholder, tool_execution_group] + param_components
        ).then(
            fn=update_online_server_info,
            outputs=[online_server_info]
        )
        
        # Handle clearing online server
        clear_online_btn.click(
            fn=clear_online_server,
            outputs=[
                online_server_config, 
                online_test_status, 
                online_server_details_group, 
                add_to_config_btn,
                tools_list,
                tools_placeholder,
                tool_execution_group
            ] + param_components
        )
        
        # Handle adding server to config
        add_to_config_btn.click(
            fn=add_to_config_handler,
            outputs=[online_test_status, server_radio, add_to_config_btn, online_server_details_group]
        )
        
        # Handle tool execution with loading states
        execute_btn.click(
            fn=execute_tool_handler,
            inputs=[server_radio, tools_list, form_inputs] + param_components,
            outputs=[execution_status, execution_result, execute_btn, loading_indicator]
        )
        
        # Handle clear results
        clear_btn.click(
            fn=clear_results,
            outputs=[execution_status, execution_result]
        )
    
    return interface


if __name__ == "__main__":
    interface = create_mcp_tester_interface()
    interface.launch(share=True, debug=True)
       