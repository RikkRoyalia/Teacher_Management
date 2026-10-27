# Teacher Management

Nền tảng API ban đầu cho hệ thống quản lý hồ sơ giảng viên, xây dựng với FastAPI và SQLite theo tài liệu dự án.

## Yêu cầu

- Python 3.10 trở lên

## Cài đặt và chạy local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1
```

Mặc định, SQLite tạo file `teacher_management.db` tại thư mục chạy ứng dụng. Có thể đặt biến môi trường `DATABASE_URL` để chọn URL cơ sở dữ liệu khác.

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>
- Web giao diện: <http://127.0.0.1:8000/>

## API hiện có

- `POST /departments`, `GET /departments`, `PATCH /departments/{department_id}`
- `POST /teachers`, `GET /teachers`, `GET /teachers/{teacher_id}`, `PATCH /teachers/{teacher_id}`
- Lọc giảng viên bằng `q`, `department_id`, `academic_degree` và `employment_status`.
- Giao diện web responsive tại `app/static/` cung cấp bảng tổng quan, tra cứu/lọc, tạo và sửa hồ sơ giảng viên, tạo/sửa/ngừng khoa và bộ môn.

Hồ sơ giảng viên không có API xóa vật lý để tránh mất dữ liệu lịch sử. Khoa/bộ môn có thể chuyển sang không hoạt động thay vì xóa.

## Kiểm thử

```powershell
python -m unittest discover -v
```

## Phạm vi và lưu ý

Đây là lát cắt đầu tiên: nền tảng API và giao diện cho dữ liệu khoa và hồ sơ giảng viên. Xác thực/phân quyền, bằng cấp, hợp đồng, lịch sử công tác, quy trình phê duyệt, kiểm tra hồ sơ, báo cáo và audit trail chưa được triển khai.

API hiện chưa có xác thực. Chỉ chạy local với dữ liệu thử nghiệm; không đưa lên mạng hoặc dùng với dữ liệu nhân sự thật trước khi bổ sung xác thực, phân quyền và kiểm soát truy cập phù hợp.
