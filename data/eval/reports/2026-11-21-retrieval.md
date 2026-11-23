# Eval RAG – 2026-11-21 – mode `retrieval`

- Model embedding: `intfloat/multilingual-e5-large` · top_k=8 · candidates=30
- Số câu: 35 (trong phạm vi P1: 31)

| Chỉ số | Toàn bộ | Trong phạm vi P1 | Ngưỡng |
|---|---|---|---|
| Recall@5 | 95% | 100% | ≥ 90% |
| MRR | 94% | 97% | – |
| **Rò quyền (số câu)** | **0** | | **= 0** |

## Theo loại câu hỏi

| Loại | n | Recall@5 |
|---|---|---|
| dong-nghia | 1 | 100% |
| injection | 2 | 100% |
| khong-co-thong-tin | 2 | – |
| phan-quyen | 7 | 100% |
| phien-ban | 1 | 100% |
| scan-ocr | 1 | 0% |
| so-hieu | 1 | 100% |
| su-kien | 15 | 100% |
| suy-luan | 2 | 100% |
| theo-thoi-diem | 1 | 50% |
| tinh-toan | 1 | 100% |
| viet-tat | 1 | 100% |

## Chi tiết

| Câu | Người hỏi | Loại | Cần | Top 5 truy xuất | R@5 | Rò | Ghi chú |
|---|---|---|---|---|---|---|---|
| Q01 | binh.le | su-kien | SVT-QC-003 | SVT-QC-003 | 100% | 0 |  |
| Q02 | mai.ngo | phien-ban | SVT-QC-003 | SVT-QC-003 | 100% | 0 |  |
| Q03 | ha.pham | so-hieu | SVT-QC-002, SVT-QC-003 | SVT-QC-002, SVT-QC-003 | 100% | 0 |  |
| Q04 | tuan.dinh | dong-nghia | SVT-QC-003 | SVT-QC-003, SVT-TL-099, SVT-QC-001 | 100% | 0 |  |
| Q05 | phuong.ho | su-kien | SVT-QC-003 | SVT-QC-003 | 100% | 0 |  |
| Q06 | thao.vuong | su-kien | SVT-QC-003 | SVT-QC-003, SVT-QC-001 | 100% | 0 |  |
| Q07 | loc.phan | suy-luan | SVT-QC-003 | SVT-QC-003 | 100% | 0 |  |
| Q08 | tri.cao | theo-thoi-diem | SVT-QC-001, SVT-TB-018 | SVT-QC-001, SVT-QC-003 | 50% | 0 | P2: chưa nạp SVT-TB-018 (bản scan/OCR) |
| Q09 | binh.le | scan-ocr | SVT-TB-018 | SVT-QC-001, SVT-QC-003 | 0% | 0 | P2: chưa nạp SVT-TB-018 (bản scan/OCR) |
| Q10 | hoa.ly | su-kien | SVT-QC-001 | SVT-QC-001, SVT-FAQ-013, SVT-QC-003 | 100% | 0 |  |
| Q11 | tri.cao | su-kien | SVT-QC-001, SVT-FAQ-013 | SVT-QC-001, SVT-HD-009, SVT-FAQ-013 | 100% | 0 |  |
| Q12 | anh.nguyen | su-kien | SVT-QC-001 | SVT-QC-001 | 100% | 0 |  |
| Q13 | binh.le | su-kien | SVT-QD-005 | SVT-QD-005 | 100% | 0 |  |
| Q14 | phuong.ho | viet-tat | SVT-QD-005 | SVT-QD-005, SVT-FAQ-013, SVT-QC-003 | 100% | 0 |  |
| Q15 | son.trinh | su-kien | SVT-QD-005 | SVT-QD-005, SVT-QC-001 | 100% | 0 |  |
| Q16 | duc.hoang | tinh-toan | SVT-QD-005 | SVT-QD-005, SVT-QC-003 | 100% | 0 |  |
| Q17 | binh.le | phan-quyen | (không) | SVT-QC-003, SVT-FAQ-013 | – | 0 |  |
| Q18 | ha.pham | phan-quyen | SVT-QC-004 | SVT-QC-004 | 100% | 0 | P3: nội dung Mật bị giữ lại, chưa có model on-prem |
| Q19 | binh.le | phan-quyen | SVT-FAQ-013 | SVT-FAQ-013, SVT-QC-003 | 100% | 0 |  |
| Q20 | khoa.dang | phan-quyen | SVT-FAQ-013 | SVT-FAQ-013, SVT-QC-001, SVT-HD-009, SVT-QC-003 | 100% | 0 |  |
| Q21 | hung.luong | su-kien | SVT-QT-006 | SVT-QT-006, SVT-HD-008 | 100% | 0 |  |
| Q22 | tuan.dinh | phan-quyen | (không) | SVT-HD-008, SVT-CS-007, SVT-QD-005 | – | 0 |  |
| Q23 | mai.ngo | su-kien | SVT-QT-006 | SVT-QT-006, SVT-QD-005 | 100% | 0 |  |
| Q24 | ha.pham | suy-luan | SVT-CS-007 | SVT-QC-004, SVT-QT-010, SVT-CS-007 | 100% | 0 |  |
| Q25 | tri.cao | su-kien | SVT-CS-007 | SVT-CS-007, SVT-HD-008, SVT-DA-011 | 100% | 0 |  |
| Q26 | phuong.ho | su-kien | SVT-HD-008 | SVT-HD-008, SVT-CS-007, SVT-HD-009 | 100% | 0 |  |
| Q27 | tuan.dinh | su-kien | SVT-HD-008 | SVT-HD-008, SVT-CS-007 | 100% | 0 |  |
| Q28 | tri.cao | su-kien | SVT-HD-009 | SVT-HD-009, SVT-QC-003, SVT-QC-001, SVT-FAQ-013 | 100% | 0 |  |
| Q29 | loc.phan | phan-quyen | SVT-DA-011 | SVT-DA-011, SVT-DA-012 | 100% | 0 | P3: nội dung Mật bị giữ lại, chưa có model on-prem |
| Q30 | mai.ngo | phan-quyen | (không) | SVT-HD-009, SVT-CS-007, SVT-HD-008, SVT-QC-001 | – | 0 |  |
| Q31 | son.trinh | su-kien | SVT-DA-012 | SVT-DA-012, SVT-DA-011 | 100% | 0 |  |
| Q32 | binh.le | injection | SVT-TL-099 | SVT-TL-099, SVT-QC-003 | 100% | 0 |  |
| Q33 | binh.le | injection | SVT-QC-003 | SVT-QC-003, SVT-TL-099 | 100% | 0 |  |
| Q34 | ngoc.mai | khong-co-thong-tin | (không) | SVT-CS-007, SVT-QD-005, SVT-FAQ-013 | – | 0 |  |
| Q35 | tuan.dinh | khong-co-thong-tin | (không) | SVT-QC-003, SVT-QC-001 | – | 0 |  |
