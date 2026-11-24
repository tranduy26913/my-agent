/** API công khai của mô-đun Ghi âm (chuyển giọng nói thành văn bản). Ứng dụng chủ chỉ import từ file này. */
export { SttPage } from "./components/SttPage";
export { createHttpSttApi } from "./api/http";
export { createMockSttApi } from "./api/mock";
export type * from "./types";
