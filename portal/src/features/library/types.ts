/**
 * Hợp đồng của trang Văn bản với backend (GET /api/kb/library, backend/app/api/library.py). JSON camelCase.
 * Mọi nhân viên đang làm việc gọi được. Backend CHỈ trả tài liệu người gọi được xem (ADR-001), chỉ metadata: không có
 * nội dung, đường dẫn tệp, người nạp hay danh sách phòng/vai trò được xem.
 */

export type LibraryStatus = "hieu-luc" | "het-hieu-luc" | "chua-hieu-luc";

export interface LibraryDoc {
  docId: string;
  soHieu: string | null;
  title: string;
  docType: string | null;
  department: string;
  /** Mật: người có quyền biết nó tồn tại, nhưng Trợ lý không đọc nội dung (SVT-CS-007) */
  classified: boolean;
  /** YYYY-MM-DD */
  effectiveFrom: string | null;
  effectiveTo: string | null;
  /** Chỉ có khi văn bản kia cũng nằm trong quyền xem của người gọi */
  supersedes: string | null;
  supersededBy: string | null;
  version: string | null;
  status: LibraryStatus;
}

export interface Facet {
  value: string;
  count: number;
}

export interface Library {
  items: LibraryDoc[];
  /** Số văn bản người này được xem, trước khi lọc */
  totalVisible: number;
  /** Số đếm cho ô lọc: tính trên tập được xem, không đổi theo bộ lọc đang chọn */
  docTypes: Facet[];
  departments: Facet[];
  statuses: Facet[];
  /** Ngày hôm nay theo máy chủ (YYYY-MM-DD), mốc tính trạng thái hiệu lực */
  today: string;
}

export interface LibraryQuery {
  /** "" = tất cả */
  type: string;
  department: string;
  status: LibraryStatus | "";
  /** Một phần tiêu đề, số hiệu hoặc mã */
  q: string;
}

export interface LibraryApi {
  list(query: LibraryQuery): Promise<Library>;
}
