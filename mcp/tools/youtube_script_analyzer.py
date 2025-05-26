import re
import os
import sys
from typing import Any, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api.formatters import JSONFormatter

from youtube_transcript_api import YouTubeTranscriptApi


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)




class YoutubeScriptAnalyzer():
    def __init__(self):
        self.name = "Youtube Script Analyzer"
        self.description = "This tool will analyze a given Youtube script and provide a summary of the script."
        
    


    def execute(self, **kwargs):

        url = kwargs.get("url","")
        if not url or "youtube.com" not in url:
            return "Invalid URL"

        # Extract Video ID from URL
        video_id_match = re.search(r"v=([A-Za-z0-9_-]{11})", url)
    

        video_id = video_id_match.group(1)

        formatter = TextFormatter()
        text = "Text not found"

        try:
            ytt_api = YouTubeTranscriptApi()

            # retrieve the available transcripts
            transcript_list = ytt_api.list(video_id)

            for transcript in transcript_list:
                if transcript.language_code == 'en':
                    text = transcript.fetch()
                    text = formatter.format_transcript(text)
                    
                    return text
            
            return "Text not found in any of the specified languages."

           
        except Exception as e:
            # Handle exceptions specifically for incorrect fallback behavior
            return "Text not found or unavailable in the specified languages. Error: {str(e)}. Please verify that the content is available and is not restricted."

        # If transcript is retrieved successfully, return it without any fallback behavior
        return text
    

if __name__ == "__main__":
    youtube_script_analyzer = YoutubeScriptAnalyzer()
    print(youtube_script_analyzer.execute(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"))