/** API công khai của mô-đun OCR. Ứng dụng chủ chỉ import từ file này. */
export { OcrPage } from "./components/OcrPage";
export { createHttpOcrApi } from "./api/http";
export { createMockOcrApi } from "./api/mock";
export type * from "./types";
