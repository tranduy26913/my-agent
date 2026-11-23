/** API công khai của mô-đun Tra cứu. Ứng dụng chủ chỉ import từ file này. */
export { LookupPage } from "./components/LookupPage";
export { createHttpLookupApi } from "./api/http";
export { createMockLookupApi } from "./api/mock";
export type * from "./types";
