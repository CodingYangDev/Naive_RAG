from document_loader_api import load_document
from text_spliter import split_text
from embedding_api import get_embeddings_batch
from openai import OpenAI
from vector_store import build_faiss_index,save_index,load_index

# rag 全流程。 把文档保存到向量库
def offline_document_load(document_path: str,model:str,client: OpenAI):
    # {content:"",metadata:{}}
    ## 1. 加载文档
    doc = load_document(document_path)

    ## 2. 切分文档
    chunks = split_text(text=doc["content"], metadata=doc["metadata"])

    ## 3. 生成向量
    text = [chunk["content"] for chunk in chunks]
    embeddings = get_embeddings_batch(text=text,model=model,client=client)


    ## 4. 创建向量库索引
    index = build_faiss_index(embeddings=embeddings)

    ## 5. 保存向量库索引
    save_index(index,chunks,
               index_path="./faiss_data/faiss_index.idx",
               metadata_path="./faiss_data/faiss_metadata.json")

    # 重新加载，验证一致性
    index2, chunks2 = load_index("./faiss_data/faiss_index.idx", "./faiss_data/faiss_metadata.json")
    assert index2.ntotal == len(chunks2), "❌ 索引和 chunks 数量不匹配！"
    print(f"✅ 索引持久化验证通过：{index2.ntotal} 条向量 = {len(chunks2)} 个 chunks")


from dotenv import load_dotenv
import os
load_dotenv()

api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL_CHAT")

from openai import OpenAI

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

## 离线阶段保存数据；
offline_document_load(document_path="./测试文件/员工假期管理制度.pdf"
                      ,model="text-embedding-v3",client=client)



