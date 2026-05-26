from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL_CHAT")



client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)
model = "text-embedding-v3"

def get_embedding(text: str,client: OpenAI,model: str) -> list[float]:
    """单文本向量化：返回一个浮点数列表"""
    response = client.embeddings.create(
        model=model,
        input=text
    )
    return response.data[0].embedding

def get_embeddings_batch(text: [str],client: OpenAI,model: str) -> list[list[float]]:
    """批量文本的向量化多文本向量化：返回一个浮点数列表的列表"""
    response = client.embeddings.create(
        model=model,
        input=text
    )
    return [item.embedding for item in response.data]

"""
测试embedding api向量化
"""
"""
注释掉测试embedding api的函数
def embedding_test():
    embedding = get_embedding("你叫什么名字",client,model)
    print(f"embedding: {embedding[:10]}") # 只打印前10个元素
    print(f"embedding 长度: {len(embedding)}")

    embeddings = get_embeddings_batch(["你叫什么名字","你能做什么"],client,model)
    for embedding,text in zip(embeddings,["你叫什么名字","你能做什么"]):
        print(f"{text} 的 embedding: {embedding[:10]}")

# 调用测试
embedding_test()
"""