# Sơ đồ lộ trình triển khai AI trong doanh nghiệp (roadmap.tranduyai.id.vn)

`site/index.html` là bản HTML tự chứa (tạo bằng archify, nguồn: `.archify/workflow-lo-trinh-ai-20261124-133812/`).
Chỉ thư mục `site/` được đưa lên Cloudflare Pages; file README này không được đăng.

## Deploy lần đầu

```powershell
npx wrangler@4 login
npx wrangler@4 pages project create lo-trinh-ai --production-branch main
npx wrangler@4 pages deploy roadmap/site --project-name lo-trinh-ai --branch main
```

Gắn subdomain: Cloudflare dashboard → Workers & Pages → `lo-trinh-ai` → Custom domains →
Set up a custom domain → `roadmap.tranduyai.id.vn`. DNS đã ở Cloudflare nên CNAME và HTTPS tự cấp.

## Cập nhật sơ đồ

Chép file HTML mới đè lên `site/index.html`, rồi chạy lại lệnh `pages deploy` ở trên.
