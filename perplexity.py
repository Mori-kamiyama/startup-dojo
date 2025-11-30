from openai import OpenAI
import os
from dotenv import load_dotenv


load_dotenv()

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

response = client.chat.completions.create(
    model="sonar-pro",  # Perplexityのモデル名を指定
    messages=[
        {"role": "user", "content": "PythonでのPerplexity APIの使い方を教えて"}
    ]
)

print(response.choices[0].message.content)
