
import asyncio
import json
import os
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP

from tools.sample_tool import SampleTool
from tools.youtube_script_analyzer import YoutubeScriptAnalyzer
# Initialize FastMCP server
mcp = FastMCP("ingr8")
env = os.environ.copy()



@mcp.tool(
    name="string_reverser_tool",
    description="Tool to reverse a given string"
)
def string_reverser_tool(text: str) -> Dict[str, Any]:
    """
    Reverse a given string.
    """
    sample_tool = SampleTool()
    result = sample_tool.execute(text=text)
    return {"data": result}

@mcp.tool(
    name="youtube_script_analyzer_tool",
    description="Tool to analyze a Youtube script"
)
def youtube_script_analyzer(url: str) -> Dict[str, Any]:
    """
    Analyze a Youtube script.
    """
    try:
        youtube_script_analyzer = YoutubeScriptAnalyzer()
        result = youtube_script_analyzer.execute(url=url)
        return {"data": result}
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    #Run the server
    # print("Running the server")
    mcp.run()

