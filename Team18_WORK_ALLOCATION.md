# Work Allocation Report — Team 18

## 1. Team Members

| Full Name | Student ID | GitHub Username | Email |
|-----------|-----------|----------------|-------|
| 張茗崴 | [113403547] | [MingWei174] | [w45166148@gmail.com] |
| 吳絃紘 | [113403032] | [cool804] | [xwu83581@gmail.com] |
| 施竑宇 | [請填寫學號] | [Airwavessss9487] | [請填寫信箱] |

---

## 2. Task Ownership

### Code Repository

| Task | Primary Owner | Supporting Member(s) | Notes |
|------|--------------|---------------------|-------|
| **Task 1** — Relational schema design (`schema.sql`) | 張茗崴 | 全體組員 | 共同討論設計後，由張茗崴主責實作，並成功重構 Junction Tables 達成 1NF/3NF 嚴格正規化。 |
| **Task 2a** — Core availability & fare queries | 張茗崴 | | |
| **Task 2b** — Seat & user queries | 張茗崴 | | |
| **Task 2c** — Write operations | 張茗崴 | | 負責實作 Loyalty Points (常客點數) 更新邏輯與 Transaction 包裝 |
| **Task 2d** — Authentication queries | 張茗崴, 施竑宇 | | 一起實作 bcrypt 密碼雜湊與驗證邏輯 |
| **Task 3** — PostgreSQL seeding (`seed_postgres.py`) | 施竑宇 | | |
| **Task 4** — Neo4j graph design & seeding | 吳絃紘 | 全體組員 | 共同討論圖形節點與關聯設計，由吳絃紘主責實作 |
| **Task 5** — Neo4j query functions | 吳絃紘 | | 負責跨網轉乘與最短路徑規劃 |
| **Task 6** *(if attempted)* — Optional extension | 張茗崴, 施竑宇 | 張茗崴負責將 Loyalty Points 點數查詢功能整合進 Agent (End-to-End LLM Tool Calling)，施竑宇負責 UI (My History 面板) 測試與整合 |
| **其他** — Vector Policy / RAG 整合與測試 | 張茗崴 | | 負責 RAG 政策文件檢索與系統 UI 最終測試。也負責 Debug 並成功修復 Windows 環境下 `seed_vectors.py` 導致的資料庫建立與 Unicode 編碼崩潰問題。 |

### Design Document

| Section | Primary Author | Supporting Member(s) | Notes |
|---------|--------------|---------------------|-------|
| Section 1 — ER Diagram | 張茗崴 | | |
| Section 2 — Normalisation Justification | 張茗崴 | | 解釋 Schema 正規化與密碼安全考量 |
| Section 3 — Graph Database Design Rationale | 吳絃紘 | | 解釋圖形資料庫演算法優勢與跨網轉乘設計 |
| Section 4 — Vector / RAG Design | 施竑宇 | | 解釋 Cosine Similarity 與維度影響 |
| Section 5 — AI Tool Usage Evidence | 全體組員 | | 每位組員各自提供其負責部分的 AI 除錯與生成範例 |
| Section 6 — Reflection & Trade-offs | 全體組員 | | |
| Section 7 — Optional Extension *(if applicable)* | 張茗崴, 施竑宇 | | 撰寫點數系統動機、SQL 範例與截圖證據 |

---

## 3. Estimated Contribution Percentages

| Member | Estimated % | Brief justification |
|--------|-----------|---------------------|
| 張茗崴 | 34% | 主責關聯式資料庫 (PostgreSQL) 的 Schema 設計、複雜查詢與寫入 (Transaction)、資安 (bcrypt)、以及 Task 6 點數功能。 |
| 吳絃紘 | 33% | 主責圖形資料庫 (Neo4j) 的設計與查詢，處理高難度的路網圖形遍歷與跨網轉乘 (Interchange) 查詢。 |
| 施竑宇 | 33% | 主責向量資料庫 (Vector/RAG) 的設計、Gradio UI 的整合與測試、以及 Task 6 的 My History 面板功能確認。 |
| **Total** | **100%** | |

---

## 4. Mid-Project Changes

| Change | Original plan | Revised plan | Reason |
|--------|--------------|-------------|--------|
| 新增 Task 6 選擇性加分題 | 未定 | 由張茗崴與施竑宇共同實作加分題功能 | 為了取得加分 Bonus，額外在 Schema 與 UI 實作常客點數與歷史訂單面板。張茗崴補足了點數查詢的 End-to-End Agent 整合。 |

---

## 5. Team Declaration

We confirm that this work allocation accurately reflects how responsibilities were divided within our team.

| Name | Signature / Typed name | Date |
|------|----------------------|------|
| 張茗崴 | 張茗崴 | 2026-06-11 |
| 吳絃紘 | 吳絃紘 | 2026-06-11 |
| 施竑宇 | 施竑宇 | 2026-06-11 |
