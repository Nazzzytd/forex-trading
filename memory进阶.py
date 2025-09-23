from langchain.memory import EntityMemory, ConversationBufferMemory
from langchain_openai import ChatOpenAI

def simple_entity_memory():
    """最简单的实体记忆演示"""
    llm = ChatOpenAI(temperature=0)
    memory = EntityMemory(llm=llm)
    
    # 保存一条对话
    memory.save_context(
        {"input": "我叫小明，是程序员"}, 
        {"output": "你好小明！程序员是很棒的职业。"}
    )
    
    # 查看记忆
    result = memory.load_memory_variables({})
    print("实体记忆内容:")
    print(result)
    return memory

def simple_combined_memory():
    """最简单的组合记忆演示"""
    llm = ChatOpenAI(temperature=0)
    
    # 创建两种记忆并组合
    memory = CombinedMemory(memories=[
        ConversationBufferMemory(memory_key="chat"),
        EntityMemory(llm=llm, memory_key="entities")
    ])
    
    # 保存对话
    memory.save_context(
        {"input": "我喜欢编程和音乐"}, 
        {"output": "很好的爱好！"}
    )
    
    # 查看结果
    result = memory.load_memory_variables({})
    print("\n组合记忆内容:")
    for key, value in result.items():
        print(f"{key}: {value}")
    
    return memory

# 运行最简单的演示
if __name__ == "__main__":
    print("开始简单演示...\n")
    simple_entity_memory()
    simple_combined_memory()
    print("\n演示结束！")



# 查询 1: {'input': '我的信息是什么？'}
# 响应: {'history': '实体信息: 李四(人物)-在北京工作'}

# 查询 2: {'input': '李四是谁？'}
# 响应: {'history': '实体信息: 李四-28岁-软件工程师-喜欢篮球'}