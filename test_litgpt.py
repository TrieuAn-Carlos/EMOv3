import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load env from backend/.env
load_dotenv("backend/.env")

api_base = os.getenv("LITGPT_API_BASE")
print(f"Testing connection to: {api_base}")

try:
    llm = ChatOpenAI(
        openai_api_base=api_base,
        openai_api_key="dummy",
        model_name="iJoshNh/EmoN3",
        temperature=0.7
    )

    print("Sending request...")
    response = llm.invoke("Hello, are you online? Answer in 5 words.")
    print(f"\nResponse: {response.content}")
    print("\n✅ API Connection Successful!")

except Exception as e:
    print(f"\n❌ Connection Failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check if the Lightning Studio server is running.")
    print("2. Verify the URL in backend/.env")
    print("3. Ensure the server script is using OpenAISpec.")
