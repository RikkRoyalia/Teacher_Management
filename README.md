# Teacher Management

Ứng dụng FastAPI, SQLAlchemy, SQLite và giao diện HTML/CSS/JavaScript quản lý hồ sơ giảng viên. Phiên bản này có xác thực/RBAC, đơn vị nhiều cấp, bằng cấp/chứng chỉ, hợp đồng, lịch sử công tác, yêu cầu thay đổi, checklist hồ sơ, báo cáo Excel và audit trail.

## Giới hạn sử dụng hiện tại

- Đây là bản chạy thử **trên một máy cá nhân tại `127.0.0.1`**, không phải hệ thống production nhiều người dùng hoặc dịch vụ truy cập qua mạng.
- Chỉ dùng dữ liệu giả lập. Chưa nhập CCCD, hồ sơ lương/thuế/bảo hiểm hay tài liệu nhân sự thật; cần được trường phê duyệt thiết bị, chính sách lưu trữ, quyền truy cập và sao lưu trước.
- Các bản sao lưu chứa dữ liệu SQLite và tệp đính kèm ở dạng không mã hóa. Bảo vệ máy và thư mục sao lưu; không đồng bộ dữ liệu thử nghiệm/nhạy cảm lên dịch vụ cá nhân.
- Không đổi `--host 127.0.0.1` thành `0.0.0.0` hoặc mở cổng tường lửa để cho phép truy cập mạng.

## Cài đặt và khởi chạy trên Windows

Mở PowerShell tại thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.bootstrap_admin
.\scripts\start_local.ps1
```

Lệnh bootstrap chỉ dùng để tạo tài khoản quản trị viên đầu tiên, yêu cầu nhập mật khẩu tương tác và không tạo tài khoản/mật khẩu mặc định. Sau khi đăng nhập, quản trị viên có thể tạo, chỉnh sửa vai trò và khóa/mở khóa tài khoản trực tiếp trong mục **Quản trị hệ thống**; không cần chạy lệnh terminal để tạo các tài khoản thường. Tài khoản bị khóa được giữ lại để bảo toàn lịch sử và nhật ký.

- Web: <http://127.0.0.1:8000/>
- Health check: <http://127.0.0.1:8000/health>
- OpenAPI docs: <http://127.0.0.1:8000/docs>

Ứng dụng bind loopback, không bật auto-reload. Bảng CSDL được cập nhật bằng Alembic khi ứng dụng khởi động. Khi nâng cấp cơ sở dữ liệu SQLite cũ, ứng dụng tạo bản sao trước migration trong `.backups/`; không xóa tệp `teacher_management.db`.

## Vai trò

- **Quản trị viên (`admin`)**: tạo/khóa tài khoản, gán vai trò và xem nhật ký. Không mặc nhiên có quyền xem/sửa hồ sơ hoặc duyệt thay đổi nghiệp vụ.
- **Nhân viên nhân sự (`hr`)**: quản lý hồ sơ/đơn vị, hợp đồng, bằng cấp, tài liệu và checklist; gửi và theo dõi yêu cầu thay đổi của mình.
- **Người quản lý (`manager`)**: xem số liệu tổng hợp, xem và xử lý yêu cầu đang chờ. Không được duyệt yêu cầu do chính mình tạo.

Quyền được kiểm tra ở API. Tác vụ thay đổi yêu cầu session cookie và CSRF token. Mật khẩu được băm PBKDF2-HMAC-SHA256; sau nhiều lần đăng nhập sai tài khoản sẽ tạm khóa.

## Lưu trữ, tài liệu và dữ liệu

- Mặc định, SQLite là `teacher_management.db` tại thư mục chạy ứng dụng; có thể cấu hình `DATABASE_URL`.
- Tệp minh chứng lưu trong `private_uploads/`, không được mount như tài nguyên tĩnh. API chỉ cho HR tải lên/tải xuống PDF, PNG và JPEG tối đa 10 MB.
- Checklist có danh mục mẫu từ `ho_so_giang_vien.md`, gồm phân loại và điều kiện áp dụng. Khi tạo hồ sơ giảng viên, HR phải rà soát từng mục có điều kiện/bắt buộc để chọn bắt buộc, tùy chọn hoặc không áp dụng; chỉ tài liệu đã xác định là bắt buộc mới ảnh hưởng trạng thái đầy đủ. Mục tùy chọn không bắt buộc mặc định; giấy tờ định danh, bảo hiểm/thuế và ảnh được đánh dấu nhạy cảm. Danh mục và điều kiện có thể cấu hình, không áp dụng cho nhân viên không giảng dạy.
- Hợp đồng sắp hết hạn mặc định được cảnh báo trước 30 ngày; cấu hình bằng `PUT /settings/contract-warning-days`. Cảnh báo không tự gia hạn hoặc đổi trạng thái.
- Nhật ký API không có thao tác sửa/xóa; audit ghi người dùng, thời điểm, loại thao tác, đối tượng và kết quả.

## Sao lưu và khôi phục

Khi đang ở thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -m app.backup backup
```

Mặc định bản sao nằm trong `.backups/` và bao gồm snapshot SQLite cùng `private_uploads/`. Có thể truyền đường dẫn archive làm đối số thứ hai.

Khôi phục yêu cầu dừng ứng dụng trước, sau đó chạy:

```powershell
.\.venv\Scripts\python.exe -m app.backup restore .backups\<ten-ban-sao>.zip
```

Lệnh khôi phục kiểm tra tính toàn vẹn CSDL, yêu cầu gõ `RESTORE`, tự tạo bản sao hiện trạng trước khi thay thế và giữ lại thư mục/tệp cũ với hậu tố `before-restore`. Không xóa các bản sao cũ nếu chưa xác nhận bản khôi phục hoạt động.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

Kiểm thử bao phủ xác thực, phân quyền, migration dữ liệu cũ, luồng phê duyệt, lịch sử công tác, tải tài liệu, checklist, báo cáo Excel và audit.

## Đưa lên mạng hoặc dùng hồ sơ thật

Chưa được xác nhận an toàn cho việc này. Trước khi mở truy cập cho người dùng khác hoặc lưu hồ sơ thật, cần thống nhất máy chủ/hạ tầng do trường quản lý, chính sách bảo vệ thiết bị và khóa mã hóa, HTTPS, lưu trữ/sao lưu được phê duyệt, giới hạn quyền xem hồ sơ và đánh giá bảo mật/quyền riêng tư. SQLite trên máy cá nhân không đáp ứng yêu cầu truy cập đồng thời hoặc vận hành tập trung.
