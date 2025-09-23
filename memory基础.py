from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain_openai import ChatOpenAI
import os

api_key=os.environ.get("OPENAI_API_KEY")
base_url=os.environ.get("OPENAI_BASE_URL")

# 1. ConversationBufferMemory - 最基础的记忆
def learn_buffer_memory():
    """学习缓冲区记忆"""
    memory = ConversationBufferMemory(
        memory_key="chat_history", #memory_key为记忆变量名称
        return_messages=True,  # 返回Message对象而非字符串
        input_key="input"      # 指定输入键名
    )
    
    # 保存对话
    memory.save_context(
        {"input": "你好，我叫张三"}, 
        {"output": "你好张三！很高兴认识你。"}
    )
    memory.save_context(
        {"input": "我今年25岁"}, 
        {"output": "25岁是很棒的年龄！"}
    )
    
    # 查看内存内容
    print("缓冲区记忆内容:")
    print(memory.load_memory_variables({}))
    return memory

# 2. ConversationSummaryMemory - 摘要记忆
def learn_summary_memory():
    """学习摘要记忆（适合长对话）"""
    llm = ChatOpenAI(temperature=0)
    memory = ConversationSummaryMemory(
        llm=llm,
        memory_key="summary",
        return_messages=True
    )
    
    # 模拟长对话
    conversations = [
        ("我喜欢编程和音乐", "很好的爱好！编程和音乐都需要创造力。"),
        ("我使用Python和JavaScript", "这两种语言都很流行，各有优势。"),
        ("我还喜欢打篮球", "运动对身体很好，篮球是很好的团队运动。")
    ]
    
    for user, assistant in conversations:
        memory.save_context({"input": user}, {"output": assistant})
    
    print("\n摘要记忆内容:")
    print(memory.load_memory_variables({}))
    return memory

def main():
    """主函数"""
    print("开始测试LangChain记忆模块...")
    
    try:
        # 测试缓冲区记忆
        buffer_mem = learn_buffer_memory()
        
        # 测试摘要记忆
        summary_mem = learn_summary_memory()
    
    except Exception as e:
        print(f"运行出错: {e}")
        print("请检查: 1. API密钥是否正确 2. 网络连接是否正常")

if __name__ == "__main__":
    main()

# 缓冲区记忆内容:
# {'chat_history': [HumanMessage(content='你好，我叫张三', additional_kwargs={}, response_metadata={}), AIMessage(content='你好张三！很高兴认识你。', additional_kwargs={}, response_metadata={}), HumanMessage(content='我今年25岁', additional_kwargs={}, response_metadata={}), AIMessage(content='25岁是很棒的年龄！', additional_kwargs={}, response_metadata={})]}


# 摘要记忆内容:
# {'summary': [SystemMessage(content='The human expresses their love for programming and music, mentioning their use of Python and JavaScript. The AI responds positively, noting the creativity required for both hobbies and acknowledging the popularity and advantages of both programming languages. The human then mentions their love for playing basketball, to which the AI responds by highlighting the physical benefits of sports and the positive aspects of basketball as a team sport.', additional_kwargs={}, response_metadata={})]}