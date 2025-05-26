

class SampleTool:
    def __init__(self):
        self.name = "Sample Tool"
        self.description = "This tool will sample a given text"


    def reverse_string(self, text: str) -> str:
        return text[::-1]
    
    def execute(self, **kwargs):
        text = kwargs.get("text","")
        return {"data": self.reverse_string(text)}