"""Unit test phần logic thuần của RAG (không cần DB, không cần model)."""

from app.rag.acl import Principal, can_read
from app.rag.chunking import chunk_markdown
from app.rag.query import analyze, unaccent
from app.rag.retriever import rrf_fuse


def P(dept, *roles, active=True):
    return Principal(email="x@cty-a.example", department=dept, roles=frozenset(roles), active=active)


# ---------------------------------------------------------------- ACL (ADR-001)

def test_public_doc_visible_to_active_only():
    assert can_read(P("KD", "employee"), "cong-khai", [], [])
    assert not can_read(P("KD", "employee", active=False), "cong-khai", [], [])


def test_phong_ban_is_dept_or_role():
    # QT-010 tuyển dụng: [HCNS, BGD] hoặc vai trò manager
    assert can_read(P("HCNS", "employee"), "phong-ban", ["HCNS", "BGD"], ["manager"])
    assert can_read(P("KD", "manager"), "phong-ban", ["HCNS", "BGD"], ["manager"])
    assert not can_read(P("KD", "employee"), "phong-ban", ["HCNS", "BGD"], ["manager"])


def test_han_che_is_dept_and_role():
    # QC-004 lương: phải thuộc [HCNS, BGD] VÀ có vai trò [hr, executive]
    args = ("han-che", ["HCNS", "BGD"], ["hr", "executive"])
    assert can_read(P("HCNS", "hr"), *args)
    assert can_read(P("BGD", "executive"), *args)
    assert not can_read(P("HCNS", "employee"), *args)  # cùng phòng nhưng không có vai trò
    assert not can_read(P("CNTT", "manager", "admin"), *args)  # admin KHÔNG có ngoại lệ


def test_han_che_misconfigured_fails_closed():
    assert not can_read(P("BGD", "executive"), "han-che", [], [])
    assert not can_read(P("BGD", "executive"), "gia-tri-la", ["BGD"], [])


# ---------------------------------------------------------------- phân tích câu hỏi

def test_unaccent_vietnamese():
    assert unaccent("Đi công tác được nghỉ phép") == "Di cong tac duoc nghi phep"


def test_detects_document_number_and_id():
    plan = analyze("Quyết định 12/2023/QĐ-CTA và CTA-QC-003 còn hiệu lực không?")
    assert "12/2023/QĐ-CTA" in plan.doc_refs
    assert "CTA-QC-003" in plan.doc_refs


def test_abbreviation_expansion():
    plan = analyze("CTP trong nước mỗi ngày bao nhiêu?")
    assert "cong tac phi" in plan.expansions
    assert "(cong <-> tac)" in plan.tsquery


def test_synonym_requires_word_boundary():
    # "om" (ốm) không được khớp bên trong "phòng" -> "phong"... hay "nom"
    assert "nghi om" not in analyze("Phòng nào quản lý?").expansions
    assert "nghi om" in analyze("Bị ốm thì sao?").expansions


def test_stopwords_dropped_and_bigram_only_for_adjacent():
    plan = analyze("Tôi được nghỉ phép bao nhiêu ngày?")
    assert "duoc" not in plan.tsquery.split(" | ")
    assert "(nghi <-> phep)" in plan.tsquery


# ---------------------------------------------------------------- chunking

DOC = """# QUY CHẾ
## Chương II. THƯỞNG
### Điều 4. Thưởng tháng 13
Đủ 12 tháng được 01 tháng lương.

### Điều 5. Thưởng KPI
| Xếp loại | Mức |
|---|---|
| A | 02 tháng |
| B | 01 tháng |

Tỷ lệ A không quá 15%.

**H1. Câu hỏi in đậm?**
Trả lời.
"""


def test_one_chunk_per_article_with_heading_path():
    chunks = chunk_markdown(DOC)
    sections = [c.section for c in chunks]
    assert sections[0] == "Chương II. THƯỞNG > Điều 4. Thưởng tháng 13"
    assert sections[1] == "Chương II. THƯỞNG > Điều 5. Thưởng KPI"
    assert "Đủ 12 tháng" not in chunks[1].content  # không gộp hai Điều


def test_bold_line_is_pseudo_heading():
    assert chunk_markdown(DOC)[-1].section.endswith("H1. Câu hỏi in đậm?")


def test_long_table_split_repeats_header():
    rows = "\n".join(f"| L{i} | {'x' * 40} |" for i in range(30))
    doc = f"### Điều 1. Bảng\n| Cấp | Mô tả |\n|---|---|\n{rows}\n"
    chunks = chunk_markdown(doc, size=400)
    assert len(chunks) > 1
    for c in chunks:
        assert c.content.startswith("| Cấp | Mô tả |\n|---|---|")
        assert all(line.startswith("|") and line.endswith("|") for line in c.content.splitlines())


# ---------------------------------------------------------------- RRF

def test_rrf_rewards_agreement_between_branches():
    fused = dict(rrf_fuse([[1, 2, 3], [3, 1, 4], [3]]))
    assert max(fused, key=fused.get) == 3
    assert fused[1] > fused[2] > 0
