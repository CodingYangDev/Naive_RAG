import os
from pypdf import PdfReader
# 注意：pypdf 是 PyPDF2 的官方继任者（PyPDF2 已停止维护），
# 如果你在网上搜到的教程使用 import PyPDF2，请改为 import pypdf，API 基本兼容


def load_txt(file_path: str) -> dict:
    """加载 TXT / Markdown 文件，统一编码为 utf-8"""

    # 根据 path 获取文件名
    file_name = os.path.basename(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        return {
            "content": f.read(),
            "metadata": {"source": file_path, "type": "txt", "name": file_name}
        }


def load_pdf(file_path: str) -> dict:
    """加载 PDF 文件：逐页提取文本，用换行符拼接各页内容"""
    reader = PdfReader(file_path)
    # 根据 path 获取文件名
    file_name = os.path.basename(file_path)
    # 读取pdf
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return {
        "content": text,
        "metadata": {"source": file_path, "type": "pdf", "pages": len(reader.pages), "name": file_name}
    }


def load_document(file_path: str) -> dict:
    """统一入口：根据扩展名自动选择加载器 以后便于扩展只需要在loaders中添加对应的扩展名和对应的处理函数即可"""
    ext = os.path.splitext(file_path)[1].lower()
    loaders = {".txt": load_txt, ".md": load_txt, ".pdf": load_pdf}
    loader = loaders.get(ext)
    if not loader:
        raise ValueError(f"不支持的文件格式: {ext}（当前支持：.txt .md .pdf）")
    return loader(file_path)


# 测试文档加载的函数
"""
def load_test():
    file_name1 = r".\测试文件\python_faq.txt"
    file_name2 = r".\测试文件\员工假期管理制度.pdf"
    file_name3 = r".\测试文件\Agent平台说明书.md"

    doc1 = load_document(file_name1)
    print(f"txt文档，字符数：{len(doc1['content'])} \n 内容：{doc1['content']} \n 元数据：{doc1['metadata']}")
    print("=" * 50)
    doc2 = load_document(file_name2)
    print(f"pdf文档，页码数：{doc2['metadata']['pages']} \n 内容：{doc2['content']} \n 元数据：{doc2['metadata']}")
    print("=" * 50)
    doc3 = load_document(file_name3)
    print(f"md文档，字符数：{len(doc3['content'])} \n 内容：{doc3['content']} \n 元数据：{doc3['metadata']}")

load_test()

这里需要优化的地方是 对与多模态的数据要进行正确的加载 并不只是提取对应的文字 对于表格 图片 以及像一些复印件等
要结合特定的工具 以及ocr技术 和vlm模型等来解决 后续在Modular_RAG项目中会有完整的解决方案
"""
