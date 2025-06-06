from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path
# 强制使用项目根目录的 .env 文件
project_root = Path(__file__).parent  # 获取项目根目录
env_path = project_root / '.env'

# 加载环境变量
load_dotenv(dotenv_path=env_path,override=True)

print(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
print(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL')}")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://aihubmix.com/v1")
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "How are you?",
        }
    ],
    model="gpt-4o-mini",
)

print(chat_completion)