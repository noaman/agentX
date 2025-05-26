import gradio as gr
from agentbuilder import create_agent_builder_interface
from agent_tester import create_agent_tester_interface
from mcptester import create_mcp_tester_interface
def main():
    with gr.Blocks(title="Agent X") as demo:
        gr.Markdown("# Agent X \n\n A complete tool for building and testing agents")
        
        with gr.Tabs() as tabs:
            
            
            with gr.TabItem("Agent Tester"):
                create_agent_tester_interface()

            with gr.TabItem("Agent Builder"):
                create_agent_builder_interface()
            
            with gr.TabItem("MCP Tester"):
                create_mcp_tester_interface()
    
    demo.launch()

if __name__ == "__main__":
    main() 