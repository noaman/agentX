# Example configuration file for Agent X
# Copy this file to constants.py and add your actual API keys

ALL_MODELS=[
    "gemini:gemini-1.5-flash-8b",
    "gemini:gemini-1.5-flash",
    "gemini:gemini-1.5-pro",
    "gemini:gemini-2.0-flash-lite",
    "gemini:gemini-2.0-flash",
    "gemini:gemini-2.5-flash-preview-04-17",
    "gemini:gemini-2.5-pro-preview-03-25",
    "openai:gpt-4.1-nano",
    "openai:gpt-4.1-mini",
    "openai:o4-mini",
    "openai:gpt-4",
    "openai:o1",
    "openai:o3",
    "openai:o1-pro",
    "lm_studio:gemma-3-1B-it-qat",
    "lm_studio:gemma-3-12b-it",
    "lm_studio:stable-code-instruct-3b",
    "lm_studio:text-embedding-nomic-embed-text-v1.5",
    "lm_studio:granite-3.1-8b-instruct",
    "lm_studio:mistral-nemo-instruct-2407",
    "lm_studio:mistral-7b-instruct-v0.3",
    "lm_studio:llama-3-groq-8b-tool-use",
    "lm_studio:janus-pro-7b-lm",
    "lm_studio:DeepSeek-R1-Distill-Llama-8B",
]

# API Base URLs
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENAI_BASE_URL = "https://api.openai.com/chat/completions/v1"
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"

# API Keys - Replace with your actual keys
GEMINI_API_KEY = "your-gemini-api-key-here"
OPENAI_API_KEY = "your-openai-api-key-here"
LM_STUDIO_API_KEY = "lm-studio"

# Instructions:
# 1. Copy this file to constants.py
# 2. Replace the placeholder API keys with your actual keys
# 3. Get API keys from:
#    - Gemini: https://makersuite.google.com/app/apikey
#    - OpenAI: https://platform.openai.com/api-keys
#    - LM Studio: Use "lm-studio" as the key (default) 