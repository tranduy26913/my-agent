/**
 * Nội dung trang Lộ trình đưa AI vào doanh nghiệp (/roadmap, công khai, không cần đăng nhập).
 * Chỉ là dữ liệu tĩnh: đổi nội dung thì sửa file này, không đụng vào component.
 */

export type LaneId = "gov" | "people" | "tools";

export interface Lane {
  id: LaneId;
  title: string;
  /** Tên ngắn dùng trong chú giải, kèm mục của kế hoạch gốc. */
  legend: string;
  owner: string;
}

export const LANES: Lane[] = [
  { id: "gov", title: "Quản trị & an toàn", legend: "Quản trị & an toàn (mục 3)", owner: "Ban chỉ đạo, Bảo mật, Pháp chế" },
  { id: "people", title: "Con người & phương pháp", legend: "Con người & phương pháp (mục 1)", owner: "Phòng ban, AI Champion" },
  { id: "tools", title: "Công cụ & nền tảng", legend: "Công cụ & nền tảng (mục 2)", owner: "Phòng CNTT" },
];

export interface Phase {
  n: number;
  title: string;
  time: string;
  /** Cổng duyệt đặt ở cuối giai đoạn này. */
  gate?: { code: string; text: string };
}

export const PHASES: Phase[] = [
  {
    n: 1,
    title: "Khởi động & nền móng",
    time: "Tháng 1",
    gate: { code: "G0", text: "chính sách được duyệt, gateway sẵn sàng thì mới cấp tài khoản" },
  },
  { n: 2, title: "Đào tạo & thí điểm", time: "Tháng 2 – 4" },
  { n: 3, title: "Đánh giá kết quả", time: "Tháng 5", gate: { code: "G1", text: "đạt tiêu chí ở 3.4 mới mở rộng" } },
  { n: 4, title: "Mở rộng toàn doanh nghiệp", time: "Tháng 6 – 9" },
  { n: 5, title: "Vận hành & cải tiến liên tục", time: "Từ tháng 10" },
];

export interface RoadmapCard {
  id: string;
  lane: LaneId;
  /** Giai đoạn (n của PHASES). */
  phase: number;
  title: string;
  bullets: string[];
  /** Ý bổ sung ngoài kế hoạch gốc. */
  added?: boolean;
  /** Nhãn cảnh báo thứ tự làm. */
  early?: string;
  /** Hiện trạng đã có sẵn của hệ thống. */
  now?: string;
}

export const CARDS: RoadmapCard[] = [
  // GĐ 1
  {
    id: "3.1", lane: "gov", phase: 1, added: true,
    title: "Ban chỉ đạo AI và lãnh đạo bảo trợ",
    bullets: ["Một lãnh đạo cấp cao đứng tên dự án", "Nhóm điều phối: CNTT, Bảo mật, Pháp chế, đại diện nghiệp vụ", "Chốt mục tiêu, ngân sách, phạm vi thí điểm"],
  },
  {
    id: "3.2", lane: "gov", phase: 1, added: true,
    title: "Chính sách sử dụng AI và phân loại dữ liệu",
    bullets: ["Ba mức dữ liệu: Công khai, Nội bộ, Mật", "Danh sách công cụ được phép và việc không được làm", "Đối chiếu Luật Bảo vệ dữ liệu cá nhân 2025"],
  },
  {
    id: "1.6", lane: "people", phase: 1, added: true,
    title: "Khảo sát nhu cầu và đo mốc ban đầu",
    bullets: ["Phỏng vấn từng phòng ban, liệt kê việc lặp lại tốn giờ", "Đo thời gian xử lý hiện tại của 3 đến 5 việc tiêu biểu", "Không có mốc này thì bước 1.4 không chứng minh được hiệu quả"],
  },
  {
    id: "2.4", lane: "tools", phase: 1, added: true,
    title: "Chọn nền tảng và nhà cung cấp",
    bullets: ["Gói doanh nghiệp Claude, ChatGPT: cam kết không dùng dữ liệu để huấn luyện, có SSO, có hợp đồng xử lý dữ liệu", "Mô hình chạy nội bộ cho dữ liệu Mật", "Đăng nhập một lần dùng chung cho mọi công cụ"],
  },
  // GĐ 2
  {
    id: "3.3", lane: "gov", phase: 2, added: true,
    title: "Giám sát thí điểm",
    bullets: ["Rà log gateway 2.2 hằng tuần: dữ liệu bị chặn, truy cập bất thường", "Quy trình báo và xử lý sự cố rò rỉ dữ liệu"],
  },
  {
    id: "1.1", lane: "people", phase: 2,
    title: "Workshop và training công cụ AI (Claude, ChatGPT)",
    bullets: ["Viết prompt, kiểm tra kết quả, giới hạn của AI", "Ví dụ theo nghiệp vụ từng phòng ban"],
  },
  {
    id: "1.2", lane: "people", phase: 2,
    title: "Tập huấn cách sử dụng và bảo mật",
    bullets: ["Dạy theo chính sách 3.2: dữ liệu nào được đưa vào AI", "Tình huống rò rỉ thật, cách nhận biết AI bịa thông tin", "Đạt bài kiểm tra cuối khóa mới được cấp tài khoản"],
  },
  {
    id: "1.3", lane: "people", phase: 2,
    title: "Mỗi phòng ban cử đại diện (AI Champion)",
    bullets: ["Học sâu, dùng thử tool, app, web do CNTT phát triển", "Ghi lại việc nào AI giúp được vào danh sách đề xuất chung", "Gửi phản hồi lỗi và yêu cầu tính năng cho CNTT"],
  },
  {
    id: "2.2", lane: "tools", phase: 2, early: "Làm trước khi cấp tài khoản",
    title: "Gateway quản lý tài khoản AI, audit và log",
    bullets: ["Cấp, thu hồi tài khoản, hạn mức theo phòng ban", "Lọc dữ liệu nhạy cảm trước khi gửi ra ngoài (CCCD, số tài khoản, hợp đồng)", "Ghi nhật ký và lưu lượng, chi phí theo người, theo phòng"],
  },
  {
    id: "2.1", lane: "tools", phase: 2,
    title: "Tool, MCP, RAG, chat nội bộ tích hợp vào portal",
    bullets: ["Chat nội bộ, tra cứu kho tri thức có trích dẫn nguồn", "MCP để AI đọc được hệ thống nội bộ theo quyền người dùng", "Tài liệu Mật chỉ xử lý bằng mô hình nội bộ"],
    now: "Đã có nền: portal, kho tri thức RAG, chat nội bộ, SSO, OCR.",
  },
  // GĐ 3
  {
    id: "3.4", lane: "gov", phase: 3, added: true,
    title: "Cổng quyết định mở rộng",
    bullets: ["Ban chỉ đạo duyệt dựa trên số liệu của 1.4", "Ví dụ tiêu chí: 60% Champion dùng hằng tuần, tiết kiệm 20% thời gian ở ít nhất 3 việc, không có sự cố với dữ liệu Mật", "Chưa đạt thì quay lại GĐ 2 với nhóm việc khác"],
  },
  {
    id: "1.4", lane: "people", phase: 3,
    title: "Phân tích kết quả, ghi nhận mức độ hiệu quả",
    bullets: ["Số liệu dùng thật lấy từ gateway: người dùng, tần suất, chi phí", "Khảo sát Champion: thời gian tiết kiệm, chất lượng đầu ra", "So với mốc 1.6, xếp hạng việc nào nên làm tiếp"],
  },
  {
    id: "2.5", lane: "tools", phase: 3, added: true,
    title: "Đánh giá chất lượng công cụ",
    bullets: ["Bộ câu hỏi chuẩn cho RAG: tỉ lệ trả lời đúng, có dẫn nguồn", "Chọn 2 đến 3 quy trình có lợi ích rõ nhất để làm Agent ở 2.3"],
  },
  // GĐ 4
  {
    id: "3.5", lane: "gov", phase: 4, added: true,
    title: "Hỗ trợ và quản lý thay đổi",
    bullets: ["Kênh hỗ trợ AI, câu hỏi thường gặp", "Truyền thông nội bộ các ca thành công", "Ghi nhận, khen thưởng sáng kiến"],
  },
  {
    id: "1.5", lane: "people", phase: 4,
    title: "Triển khai rộng rãi",
    bullets: ["Theo đợt, mỗi đợt vài phòng ban", "Champion hướng dẫn đồng nghiệp trong phòng", "Thư viện prompt, hướng dẫn mẫu theo nghiệp vụ", "Đưa vào chương trình nhập môn nhân viên mới"],
  },
  {
    id: "2.3", lane: "tools", phase: 4,
    title: "Quy trình tự động, workflow Agent theo nghiệp vụ",
    bullets: ["Lấy từ danh sách đề xuất đã được 1.4 và 2.5 xếp hạng", "Người duyệt ở các bước quan trọng: gửi ra ngoài, chi tiền, sửa dữ liệu", "Agent chỉ có quyền của người đang dùng, mọi lệnh gọi đi qua gateway"],
  },
  // GĐ 5
  {
    id: "3.6", lane: "gov", phase: 5, added: true,
    title: "Rà soát định kỳ hằng quý",
    bullets: ["Cập nhật chính sách theo công cụ và quy định mới", "Kiểm tra quyền truy cập, thu hồi tài khoản không dùng", "Báo cáo lãnh đạo: sử dụng, chi phí, rủi ro"],
  },
  {
    id: "1.7", lane: "people", phase: 5, added: true,
    title: "Đào tạo nâng cao và cộng đồng nội bộ",
    bullets: ["Lớp nâng cao cho người dùng nhiều, chứng nhận nội bộ", "Buổi chia sẻ định kỳ giữa các Champion"],
  },
  {
    id: "2.6", lane: "tools", phase: 5, added: true,
    title: "Vận hành hệ thống AI",
    bullets: ["Theo dõi chi phí, độ trễ, lỗi của từng công cụ", "Thay hoặc nâng mô hình, chạy lại bộ đánh giá 2.5 trước khi đổi", "Cập nhật kho tri thức khi tài liệu thay đổi"],
  },
];

/**
 * Mũi tên giữa các thẻ. `r` là kiểu đường đi:
 * down = xuống hàng dưới · gutter = đi vòng qua rãnh giữa hai làn rồi vào cạnh trái đích · side = sang làn bên cạnh
 * right = ra lề phải rồi xuống · back = vòng lên bằng lề trái (vòng lặp).
 * sa/ta = điểm neo dọc cạnh nguồn/đích (0..1); o = lệch độ cao trong khe giữa hai hàng; gx = lệch trong rãnh giữa hai làn;
 * l = nhãn; lf = vị trí nhãn trên đoạn đường; main = mạch chính; ret = đường quay lại.
 */
export interface RoadmapEdge {
  f: string;
  t: string;
  r: "down" | "gutter" | "side" | "right" | "back";
  sa?: number;
  ta?: number;
  o?: number;
  gx?: number;
  l?: string;
  lf?: number;
  main?: boolean;
  ret?: boolean;
}

export const EDGES: RoadmapEdge[] = [
  { f: "3.1", t: "3.2", r: "down", l: "giao soạn" },
  { f: "3.2", t: "3.3", r: "down", l: "áp dụng khi thí điểm" },
  { f: "3.2", t: "1.2", r: "gutter", sa: 0.72, o: 8, gx: 12, l: "nội dung tập huấn", lf: 0.3, main: true },
  { f: "3.2", t: "2.2", r: "down", sa: 0.88, ta: 0.22, o: -18, l: "luật lọc dữ liệu" },
  { f: "2.4", t: "2.2", r: "down", l: "nhà cung cấp, SSO" },
  { f: "1.6", t: "1.3", r: "gutter", sa: 0.3, o: -4, gx: -12, l: "danh sách việc", lf: 0.82 },
  { f: "1.1", t: "1.2", r: "down" },
  { f: "1.2", t: "1.3", r: "down", l: "đạt kiểm tra", main: true },
  { f: "1.2", t: "2.2", r: "side", gx: 0, l: "cấp tài khoản" },
  { f: "1.3", t: "2.1", r: "side", gx: 0, l: "yêu cầu tool, phản hồi" },
  { f: "1.3", t: "1.4", r: "down", l: "kết quả dùng thử", main: true },
  { f: "2.2", t: "1.4", r: "right", ta: 0.8, o: 2, l: "số liệu dùng thật" },
  { f: "2.1", t: "2.5", r: "down", l: "chấm điểm" },
  { f: "1.4", t: "3.4", r: "side", gx: 0, l: "báo cáo", main: true },
  { f: "3.4", t: "1.5", r: "down", l: "đạt: mở rộng", main: true },
  { f: "2.5", t: "2.3", r: "down", l: "quy trình ưu tiên" },
  { f: "1.5", t: "3.5", r: "side", gx: 0, l: "cần hỗ trợ" },
  { f: "1.5", t: "2.3", r: "side", gx: 0, l: "đề xuất tự động hóa" },
  { f: "1.5", t: "1.7", r: "down", main: true },
  { f: "2.3", t: "2.6", r: "down", l: "đưa vào vận hành" },
  { f: "3.5", t: "3.6", r: "down" },
  { f: "3.6", t: "3.2", r: "back", l: "cập nhật chính sách mỗi quý", ret: true },
];

export const LOOP_TEXT = {
  lead: "Vòng lặp:",
  body: "mỗi quý, rà soát 3.6 cập nhật lại chính sách 3.2, còn danh sách việc mới từ Champion và số liệu gateway đưa trở lại GĐ 2 cho đợt thí điểm tiếp theo. Nếu cổng G1 chưa đạt, cũng quay về GĐ 2 với nhóm việc khác.",
};

export const METRICS = {
  title: "Khung chỉ số đo hiệu quả",
  intro: "Đo từ GĐ 1 để có mốc, chốt tại cổng G1, theo dõi tiếp trong GĐ 5.",
  note: "Ngưỡng ở thẻ 3.4 là ví dụ. Ban chỉ đạo đặt ngưỡng thật sau khi có số liệu mốc.",
  rows: [
    { group: "Mức độ sử dụng", metric: "Người dùng hoạt động hằng tuần trên tổng số được cấp", source: "Gateway 2.2", usedIn: "1.4, 3.6" },
    { group: "Hiệu quả", metric: "Số giờ tiết kiệm mỗi người mỗi tuần cho từng việc", source: "Mốc 1.6 + khảo sát", usedIn: "1.4, cổng G1" },
    { group: "Chất lượng", metric: "Tỉ lệ câu trả lời đúng và có dẫn nguồn, tỉ lệ phải sửa lại", source: "Bộ đánh giá 2.5", usedIn: "2.5, 2.6" },
    { group: "An toàn", metric: "Số lần bộ lọc chặn dữ liệu nhạy cảm, số sự cố", source: "Gateway 2.2, 3.3", usedIn: "3.3, 3.6" },
    { group: "Chi phí", metric: "Chi phí AI mỗi người dùng mỗi tháng, theo phòng ban", source: "Gateway 2.2", usedIn: "1.4, 2.6" },
    { group: "Tác động", metric: "Số quy trình đã tự động hóa và đang chạy thật", source: "Portal, workflow 2.3", usedIn: "3.6" },
  ],
};

export const ROLES = {
  title: "Ai làm gì",
  items: [
    { title: "Ban lãnh đạo", text: "Bảo trợ dự án, duyệt ngân sách, ra quyết định ở cổng G0 và G1." },
    { title: "Phòng CNTT", text: "Chọn nền tảng, dựng gateway, tool, RAG, chat, Agent. Vận hành và đo đạc." },
    { title: "Bảo mật và Pháp chế", text: "Soạn chính sách, phân loại dữ liệu, rà log, xử lý sự cố, kiểm tra hợp đồng nhà cung cấp." },
    { title: "Trưởng phòng ban", text: "Cử Champion, dành thời gian cho thí điểm, xác nhận lợi ích thực tế của phòng mình." },
    { title: "AI Champion", text: "Dùng thử, ghi nhận việc AI làm được, phản hồi cho CNTT, hướng dẫn đồng nghiệp khi mở rộng." },
    { title: "Nhân viên", text: "Học, tuân thủ chính sách, dùng công cụ được cấp, báo lại khi gặp vấn đề." },
  ],
};

export const RISKS = {
  title: "Rủi ro cần kiểm soát",
  items: [
    { title: "Rò rỉ dữ liệu ra dịch vụ bên ngoài", text: "Nhân viên dán tài liệu nội bộ vào tài khoản AI cá nhân.", control: "3.2 · 1.2 · 2.2 · chỉ dùng tài khoản do công ty cấp" },
    { title: "AI trả lời sai nhưng nghe hợp lý", text: "Kết quả được dùng mà không kiểm tra lại.", control: "1.2 · RAG có dẫn nguồn ở 2.1 · đánh giá 2.5" },
    { title: "Lệnh độc giấu trong tài liệu", text: "Văn bản hoặc email chứa câu lệnh khiến Agent làm việc ngoài ý muốn.", control: "2.3 có người duyệt · quyền tối thiểu · lọc nội dung đầu vào" },
    { title: "Chi phí tăng không kiểm soát", text: "Dùng mô hình đắt cho việc đơn giản, không có hạn mức.", control: "hạn mức ở 2.2 · theo dõi ở 2.6" },
    { title: "Thí điểm xong rồi bỏ", text: "Không có số liệu chứng minh nên không ai đầu tư tiếp.", control: "mốc 1.6 · phân tích 1.4 · cổng 3.4" },
    { title: "Người dùng không đổi thói quen", text: "Được cấp công cụ nhưng vẫn làm theo cách cũ.", control: "Champion 1.3 · hỗ trợ 3.5 · thư viện mẫu 1.5" },
  ],
};
