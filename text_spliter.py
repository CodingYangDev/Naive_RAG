def split_text(text: str, chunk_size: int = 500, overlap: int = 100,
               separators: list[str] = None, metadata: dict = None) -> list[dict]:
    """
    文本切分函数

    Args:
        text: 要切分的文本
        chunk_size: 每个chunk的最大长度
        overlap: 相邻chunk的重叠长度
        separators: 分隔符列表，默认为常见标点和换行
        metadata: 基础元数据

    Returns:
        切分后的chunk列表，每个chunk包含content和metadata
    """
    # 处理默认参数
    if separators is None:
        separators = ['\n\n', '\n', '。', '！', '？', ';', '；', ',', '，', ' ']

    # 处理空文本
    if not text:
        return []

    # 短文本直接返回
    if len(text) <= chunk_size:
        base_metadata = metadata.copy() if metadata else {}
        base_metadata.update({"chunk_index": 0, "chunk_total": 1})
        return [{"content": text, "metadata": base_metadata}]

    # 步骤1：按分隔符分割文本为小片段
    segments = [text]
    for sep in separators:
        new_segments = []
        for seg in segments:
            if sep in seg:
                parts = seg.split(sep)
                for i, part in enumerate(parts):
                    new_segments.append(part)
                    if i < len(parts) - 1:
                        new_segments.append(sep)
            else:
                new_segments.append(seg)
        segments = new_segments

    # 步骤2：合并小片段，避免产生过小的chunk
    merged_segments = []
    current_segment = ""
    for seg in segments:
        if len(current_segment) + len(seg) <= chunk_size:
            current_segment += seg
        else:
            if current_segment:
                merged_segments.append(current_segment)
            current_segment = seg
    if current_segment:
        merged_segments.append(current_segment)

    # 步骤3：切分合并后的段落，处理重叠
    chunks = []
    for seg in merged_segments:
        if len(seg) <= chunk_size:
            chunks.append(seg)
        else:
            # 无分隔符的长文本，兜底按字符截断
            start = 0
            while start < len(seg):
                end = min(start + chunk_size, len(seg))
                chunks.append(seg[start:end])
                start = end - overlap if end < len(seg) else end

    # 处理相邻chunk之间的重叠 这里采用的固定分块不管怎么样的话都是会可能在处理块重叠的时候 对应当前块的前面内容或者后面的内容进行截断
    if len(chunks) > 1 and overlap > 0:
        overlapped_chunks = [chunks[0]]
        for i in range(1, len(chunks)):
            # 从上个chunk末尾取overlap长度的文本，添加到当前chunk开头
            prev_chunk = overlapped_chunks[-1]
            overlap_text = prev_chunk[-overlap:] if len(prev_chunk) >= overlap else prev_chunk
            current_chunk = overlap_text + chunks[i]
            # 确保当前chunk不超过chunk_size
            if len(current_chunk) > chunk_size:
                current_chunk = current_chunk[-chunk_size:]
            overlapped_chunks.append(current_chunk)
        chunks = overlapped_chunks

    # 步骤4：生成最终结果，添加元数据
    result = []
    base_metadata = metadata.copy() if metadata else {}
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        chunk_metadata = base_metadata.copy()
        chunk_metadata.update({"chunk_index": i, "chunk_total": total_chunks})
        result.append({"content": chunk, "metadata": chunk_metadata})

    return result

"""
# ── 测试用例 ──────────────────────────────────────────────────
def run_tests():
    # ── 测试文本准备 ──────────────────────────────────────────────
    sample_text = "人工智能（AI）正在深刻改变各个行业。

    机器学习是人工智能的核心子领域。它通过算法让计算机从数据中自动学习规律，无需人工显式编程。常见的机器学习算法包括线性回归、决策树、随机森林和神经网络等。

    深度学习是机器学习的一个分支，使用多层神经网络来处理复杂的模式识别任务。它在图像识别、语音识别和自然语言处理领域取得了突破性进展。典型的深度学习模型有卷积神经网络（CNN）、循环神经网络（RNN）和Transformer架构。

    大语言模型（LLM）是基于Transformer架构的超大规模语言模型。GPT、BERT、LLaMA等都是代表性的大语言模型。它们通过在海量文本上进行预训练，获得了强大的语言理解和生成能力。在实际应用中，LLM被用于问答、摘要、翻译、代码生成等多种任务。"

    print("=" * 60)

    # ── Case 1：基础切分（验证 chunk 大小不超限）──
    print("【Case 1】基础切分，chunk_size=100, overlap=0")
    chunks = split_text(sample_text, chunk_size=100, overlap=0)
    for c in chunks:
        content = c["content"]
        status = "✅" if len(content) <= 100 else "❌ 超长!"
        print(f"  [{c['metadata']['chunk_index'] + 1}/{c['metadata']['chunk_total']}] "
              f"len={len(content)} {status} | {content[:30].strip()}...")
    print()

    # ── Case 2：带 overlap（验证相邻 chunk 存在重叠内容）──
    print("【Case 2】overlap 验证，chunk_size=150, overlap=30")
    chunks = split_text(sample_text, chunk_size=100, overlap=20)
    for i, c in enumerate(chunks):
        print(f"  chunk[{i}] 内容: {c['content'][:30].strip()}")
    print()

    # ── Case 3：短文本（不应切分）──
    print("【Case 3】短文本，不应被切分")
    short_text = "这是一段很短的文字，不需要切分。"
    chunks = split_text(short_text, chunk_size=500)
    assert len(chunks) == 1, f"❌ 期望1个chunk，实际{len(chunks)}个"
    print(f"  ✅ 仅产生 1 个 chunk，len={len(chunks[0]['content'])}")
    print()

    # ── Case 4：无分隔符的长文本（兜底强制截断）──
    print("【Case 4】纯长字符串，无自然分隔符，兜底按字符截断")
    no_sep_text = "A" * 350  # 350个字符，chunk_size=100 → 应产生4个chunk
    chunks = split_text(no_sep_text, chunk_size=100, overlap=0)
    print(f"  chunk 数量: {len(chunks)}（期望: 4）{'✅' if len(chunks) == 4 else '❌'}")
    for c in chunks:
        print(f"    len={len(c['content'])} {'✅' if len(c['content']) <= 100 else '❌'}")
    print()

    # ── Case 5：小片段合并验证（核心改动）──
    print("【Case 5】小片段合并验证，多个小段落应合并为一个 chunk")
    # 每行约15字，chunk_size=100，3行合计约45字应合并为1个chunk
    small_para_text = "第一段内容很短。\n第二段内容也很短。\n第三段内容同样很短。"
    chunks = split_text(small_para_text, chunk_size=100, overlap=0)
    print(f"  chunk 数量: {len(chunks)}（期望: 1，若>1说明合并逻辑失效）"
          f"  {'✅' if len(chunks) == 1 else '❌ 合并失效!'}")
    for c in chunks:
        print(f"    len={len(c['content'])} | {c['content']}")
    print()

    print("=" * 60)
    print("✅ 全部测试完成")


run_tests()


"""

"""
优化方案:  可以不用采用这个overlap的方式或者结合语义切分 不用固定长度来切分 因为即使有这overlap的存在 也有可能出现
    overlap 强行截断式保留上下文，甚至导致歧义。 比如之前是 不可以xxx，overlap 后成为 可以xxx
    上下文增强技术（智谱）； 生成当前片段的上下摘要报告； 摘要 + 片段 = 完整语义；
    问题：分chunk的时候，每个chunk都要调用模型总结
"""