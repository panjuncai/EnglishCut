import os
from openai import OpenAI
from dotenv import load_dotenv
import gradio as gr
from logger import LOG
import pathlib

# 加载环境变量
project_root = pathlib.Path(__file__).parent.parent  # 获取项目根目录
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path,override=True)


# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

def translate_text(english_text, model="gpt-4o-mini"):
    """
    使用 OpenAI API 将英文翻译成中文
    
    参数:
    - english_text: 要翻译的英文文本
    - model: 使用的模型，默认为 gpt-4o-mini
    
    返回:
    - 翻译后的中文文本
    """
    try:
        if not english_text or not english_text.strip():
            return "请输入要翻译的英文文本"
        
        LOG.info(f"[翻译请求] 原文: {english_text[:100]}...")
        
        # 构建翻译提示
        system_prompt = """你是一个专业的英中翻译助手。请将用户输入的英文文本翻译成自然流畅的中文。
要求：
1. 翻译要准确、自然、符合中文表达习惯
2. 保持原文的语气和风格
3. 如果是专业术语，请提供准确的中文对应词汇
4. 只返回翻译结果，不要添加额外说明"""
        
        user_prompt = f"请将以下英文翻译成中文：\n\n{english_text}"
        
        # 调用 OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        
        translated_text = response.choices[0].message.content.strip()
        LOG.info(f"[翻译结果] 译文: {translated_text[:100]}...")
        
        return translated_text
        
    except Exception as e:
        error_msg = f"翻译失败: {str(e)}"
        LOG.error(f"[翻译错误] {error_msg}")
        
        # 添加详细的错误诊断
        if "Connection error" in str(e) or "connection" in str(e).lower():
            detailed_msg = f"""连接错误: {str(e)}"""
            LOG.error(detailed_msg)
            return detailed_msg
        else:
            return error_msg

def batch_translate(text_list, model="gpt-4o-mini"):
    """
    批量翻译多个文本
    
    参数:
    - text_list: 要翻译的英文文本列表
    - model: 使用的模型
    
    返回:
    - 翻译结果列表
    """
    results = []
    for text in text_list:
        try:
            result = translate_text(text, model)
            results.append(result)
        except Exception as e:
            results.append(f"翻译失败: {str(e)}")
    
    return results

# 创建 Gradio 界面
def create_translate_interface():
    """创建翻译界面"""
    
    def translate_with_model_selection(english_text, model_choice):
        """带模型选择的翻译函数"""
        return translate_text(english_text, model_choice)
    
    # 创建翻译界面
    translate_interface = gr.Interface(
        fn=translate_with_model_selection,
        inputs=[
            gr.Textbox(
                label="英文文本",
                placeholder="请输入要翻译的英文文本...",
                lines=5,
                max_lines=10
            ),
            gr.Dropdown(
                choices=["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
                label="选择模型",
                value="gpt-4o-mini"
            )
        ],
        outputs=gr.Textbox(
            label="中文翻译",
            lines=5,
            max_lines=10
        ),
        title="英文到中文翻译工具",
        description="使用 OpenAI API 将英文文本翻译成中文",
        examples=[
            ["Hello, how are you today?", "gpt-4o-mini"],
            ["The weather is beautiful today.", "gpt-4o-mini"],
            ["I love programming and artificial intelligence.", "gpt-4o-mini"]
        ]
    )
    
    return translate_interface

# 仅当此脚本作为主程序运行时，启动 Gradio 应用
if __name__ == "__main__":
    # 检查 API 密钥
    if not os.getenv("OPENAI_API_KEY"):
        print("错误: 请设置 OPENAI_API_KEY 环境变量")
        print("您可以在 .env 文件中设置: OPENAI_API_KEY=your_api_key_here")
        exit(1)
    
    # 创建并启动界面
    demo = create_translate_interface()
    demo.queue().launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7861
    )
