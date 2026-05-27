import faiss
import numpy as np
import json

# 返回 FAISS 索引对象。
def build_faiss_index(embeddings: list[list[float]]) -> faiss.IndexFlatIP:
    """
    构建 FAISS 内积索引。
    通过对向量进行 L2 归一化，使得内积计算等价于余弦相似度。

    Args:
        embeddings: 嵌入向量列表，每个元素为一个浮点数列表。

    Returns:
        faiss.IndexFlatIP: 构建好的 FAISS 索引对象。
    """
    # 获取向量维度（特征长度）1024
    dim = len(embeddings[0])

    # 将输入列表转换为 float32 类型的 numpy 数组，这是 FAISS 指定的数值类型
    vectors = np.array(embeddings, dtype=np.float32)

    # 执行原地 L2 归一化：||v|| = 1。归一化后的向量点积即为余弦相似度
    faiss.normalize_L2(vectors)

    # 创建暴力搜索的内积索引 (IndexFlatIP)
    index = faiss.IndexFlatIP(dim)

    # 将处理后的向量添加到索引库中
    index.add(vectors)

    return index

def save_index(index: faiss.IndexFlatIP, chunks: list[dict],
               index_path: str, metadata_path: str) -> None:
    """
    持久化索引与元数据双文件方案。
    index_path 存储 FAISS 向量索引数据，metadata_path 存储对应的文本块及原始信息。

    Args:
        index: FAISS 索引对象。
        chunks: 包含 "content" 和 "metadata" 的原始文本块列表。
        index_path: 索引文件的保存路径（二进制格式）。
        metadata_path: 元数据文件的保存路径（JSON 格式）。
    """
    # 将向量索引二进制流写入磁盘
    faiss.write_index(index, index_path)

    # 将文本块及元数据序列化为 JSON，确保非 ASCII 字符（如中文）正常显示
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"✅ 索引保存成功：{index_path}（包含 {index.ntotal} 条向量）")
    print(f"✅ 元数据保存成功：{metadata_path}")

def load_index(index_path: str, metadata_path: str) -> tuple[faiss.IndexFlatIP, list[dict]]:
    """
    从磁盘恢复索引和关联的文本块数据。

    Args:
        index_path: 索引二进制文件路径。
        metadata_path: 元数据 JSON 文件路径。

    Returns:
        tuple: (index, chunks) 包含加载后的 FAISS 索引和对应的文本块列表。
    """
    # 读取二进制索引文件
    index = faiss.read_index(index_path)

    # 读取 JSON 格式的文本元数据
    with open(metadata_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    return index, chunks