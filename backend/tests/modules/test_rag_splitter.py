from __future__ import annotations

from app.modules.rag.splitter import TextSplitter


def test_text_splitter_keeps_short_near_boundary_document_as_single_chunk() -> None:
    splitter = TextSplitter(chunk_size=900, chunk_overlap=150)
    content = "星途智能AI大模型" * 103

    chunks = splitter.split(content)

    assert len(chunks) == 1
    assert chunks[0].content == content


def test_text_splitter_prefers_semantic_company_profile_chunks() -> None:
    splitter = TextSplitter(chunk_size=450, chunk_overlap=80)
    profile = "\n".join(
        [
            "星途智能科技有限公司是国家级高新技术企业，总部坐落于北京海淀人工智能产业核心集聚区，在深圳、杭州设有两大研发及产业赋能中心。公司秉持技术自主可控理念，聚焦国产全栈式大模型技术攻坚，助力各行业实现数智化转型升级。",
            "公司核心创始及研发团队源自国内顶尖高校AI实验室与头部科技企业核心技术部门，深耕自然语言处理、多模态融合、深度学习算法、模型安全治理等领域十余年。企业人员结构精炼高效，研发人员占比超75%。",
            "星途智能核心自研“星枢”系列通用认知大模型，涵盖基础通用大模型、行业专属微调模型、轻量化终端适配模型三大产品矩阵。公司构建B端产业赋能与C端智能应用双向业务布局，B端提供MaaS模型即服务、行业定制化AI解决方案及智能化系统搭建服务；C端推出轻量化智能交互、内容创作、智能办公等便民AI产品。",
        ]
    )
    content = f"{profile}\n{profile}"

    chunks = splitter.split(content)

    assert len(chunks) >= 2
    assert "北京海淀" in chunks[0].content
    assert any("研发人员占比超75%" in chunk.content for chunk in chunks)
    assert any("星枢" in chunk.content for chunk in chunks)
    assert any("MaaS" in chunk.content for chunk in chunks)
