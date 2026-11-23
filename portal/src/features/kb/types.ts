/**
 * Kiểu dữ liệu và hợp đồng API của mô-đun Kho tri thức.
 * Ánh xạ 1-1 với bảng `documents` / `chunks` ở backend/app/models.py
 * và quy tắc phân quyền ở backend/app/rag/acl.py.
 */

export type DocStatus = "ready" | "processing" | "error" | "quarantined";
/** cong-khai: mọi nhân viên · phong-ban: thuộc phòng HOẶC có vai trò · han-che: thuộc phòng VÀ có vai trò */
export type Visibility = "cong-khai" | "phong-ban" | "han-che";
export type FileKind = "md" | "pdf" | "docx" | "image" | "other";

export interface KbDocument {
  docId: string;
  soHieu: string | null;
  title: string;
  docType: string | null;
  fileKind: FileKind;
  department: string;
  visibility: Visibility;
  allowedDepartments: string[];
  allowedRoles: string[];
  /** classification = "Mat" */
  classified: boolean;
  /** ISO yyyy-mm-dd */
  effectiveFrom: string | null;
  effectiveTo: string | null;
  supersedes: string | null;
  supersededBy: string | null;
  version: string | null;
  status: DocStatus;
  /** Lý do khi status là processing / error / quarantined */
  statusNote?: string;
  chunkCount: number;
  ocrPages: number;
  source: string;
  uploadedBy: string | null;
  /** ISO datetime */
  createdAt: string;
}

export interface KbChunk {
  ordinal: number;
  page: number | null;
  /** "Chương II > Điều 5. ..." — dùng làm trích dẫn */
  section: string;
  content: string;
}

export interface KbHistoryEntry {
  at: string;
  by: string;
  text: string;
}

export interface KbDocumentDetail extends KbDocument {
  chunks: KbChunk[];
  history: KbHistoryEntry[];
  /** true khi lượt xem này đã được ghi nhật ký (tài liệu Mật, ADR-004 mục 4) */
  accessLogged?: boolean;
}

/** Thông tin người nạp điền tay. `null` khi tệp Markdown đã có đủ frontmatter. */
export interface UploadMeta {
  title?: string;
  docType: string;
  department: string;
  visibility: Visibility;
  allowedDepartments: string[];
  allowedRoles: string[];
  classified: boolean;
  effectiveFrom?: string;
  supersedes?: string | null;
}

export interface AccessCheck {
  allowed: boolean;
  reason: string;
  /** Tên nhân viên nếu tìm thấy */
  person: string | null;
}

/** Mọi thứ mô-đun cần từ backend. Có hai bản cài: api/mock.ts và api/http.ts. */
export interface KbApi {
  listDocuments(): Promise<KbDocument[]>;
  getDocument(docId: string): Promise<KbDocumentDetail>;
  uploadDocument(
    file: File,
    meta: UploadMeta | null,
    onProgress: (percent: number) => void,
  ): Promise<KbDocument>;
  reindex(docIds: string[]): Promise<void>;
  setQuarantine(docId: string, on: boolean): Promise<void>;
  deleteDocuments(docIds: string[]): Promise<void>;
  checkAccess(docId: string, email: string): Promise<AccessCheck>;
}
