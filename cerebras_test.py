import os
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

load_dotenv()

client = Cerebras(
    api_key=os.getenv("CEREBRAS_API_KEY")
)

completion = client.chat.completions.create(
    messages=[{"role":"user","content":"Cerebrasの特徴を教えてください。"}],
    model="gpt-oss-120b",
    max_completion_tokens=4096,
    temperature=0.2,
    top_p=1,
    stream=True
)

for chunk in completion:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)