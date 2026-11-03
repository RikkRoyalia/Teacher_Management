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
- **Giảng viên (`lecturer`)**: admin tạo tài khoản và liên kết với hồ sơ có sẵn; giảng viên chỉ xem hồ sơ của mình, nộp/tải tài liệu minh chứng và không sửa dữ liệu chính thức.

Quyền được kiểm tra ở API. Tác vụ thay đổi yêu cầu session cookie và CSRF token. Mật khẩu được băm PBKDF2-HMAC-SHA256; sau nhiều lần đăng nhập sai tài khoản sẽ tạm khóa.

## Lưu trữ, tài liệu và dữ liệu

- Mặc định, SQLite là `teacher_management.db` tại thư mục chạy ứng dụng; có thể cấu hình `DATABASE_URL`.
- Tệp minh chứng lưu trong `private_uploads/`, không được mount như tài nguyên tĩnh. HR có thể tải lên/tải xuống; giảng viên chỉ tải lên theo checklist và truy cập tài liệu thuộc hồ sơ đã liên kết. Chỉ PDF, PNG và JPEG tối đa 10 MB được chấp nhận. Tài liệu giảng viên nộp chờ HR xác nhận; tài liệu chưa được xác nhận không hoàn tất checklist.
- Checklist có danh mục mẫu từ `ho_so_giang_vien.md`, gồm phân loại và điều kiện áp dụng. Khi tạo hồ sơ giảng viên, HR phải rà soát từng mục có điều kiện/bắt buộc để chọn bắt buộc, tùy chọn hoặc không áp dụng; chỉ tài liệu đã xác định là bắt buộc mới ảnh hưởng trạng thái đầy đủ. Mục tùy chọn không bắt buộc mặc định; giấy tờ định danh, bảo hiểm/thuế và ảnh được đánh dấu nhạy cảm. Danh mục và điều kiện có thể cấu hình, không áp dụng cho nhân viên không giảng dạy.
- Hợp đồng sắp hết hạn mặc định được cảnh báo trước 30 ngày; cấu hình bằng `PUT /settings/contract-warning-days`. Cảnh báo không tự gia hạn hoặc đổi trạng thái.
- Bằng cấp/chứng chỉ có thể lưu ngày hết hạn; cảnh báo chứng chỉ mặc định trước 30 ngày, HR có thể cấu hình trong trang tổng quan hoặc qua `PUT /settings/certificate-warning-days`.
- Rà soát hồ sơ dùng checklist và kiểm tra dữ liệu làm căn cứ; Isolation Forest của scikit-learn chỉ gắn cờ tổ hợp chỉ số tổng hợp khác biệt để HR xem lại. Mô hình không đọc tệp, không dùng dữ liệu định danh, không tự kết luận/sửa hồ sơ và sẽ báo chưa đủ dữ liệu nếu có dưới 20 hồ sơ hoặc không có biến thiên. Tác vụ xử lý cục bộ, không gọi LLM hay dịch vụ AI bên ngoài.
- Danh sách phát hiện hồ sơ và cảnh báo chi tiết chỉ dành cho HR qua API; vai trò quản lý tiếp tục chỉ xem báo cáo tổng hợp theo quyền hiện có.
- Nhật ký API không có thao tác sửa/xóa; audit ghi người dùng, thời điểm, loại thao tác, đối tượng và kết quả.

## Dữ liệu mẫu

Chỉ chạy với server demo trên máy cá nhân. Script đăng nhập bằng tài khoản admin hiện có, sau đó tạo dữ liệu qua API với CSRF; script không ghi trực tiếp vào SQLite. Mở PowerShell tại thư mục dự án, khởi chạy server bằng `.\scripts\start_local.ps1`, rồi chạy:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo.py --base-url http://127.0.0.1:8000
```

Script hỏi thông tin đăng nhập admin nếu chưa có biến môi trường `SEED_ADMIN_USER` và `SEED_ADMIN_PASSWORD`. Có thể thêm `--yes` để bỏ qua xác nhận ghi dữ liệu. Nếu server không chạy, script thoát và hướng dẫn khởi động server. Chỉ dùng dữ liệu giả; không chạy trên hệ thống hoặc cơ sở dữ liệu có dữ liệu thật.

Script tạo khoa/bộ môn, 32 hồ sơ giảng viên, bằng cấp/chứng chỉ, hợp đồng, quá trình công tác, checklist, tài liệu minh chứng, yêu cầu thay đổi, thông báo và nhật ký hoạt động. Mã hồ sơ và mã dữ liệu có tiền tố `DEMO-`; chạy lại sẽ nhận diện các bản ghi demo đã có thay vì tạo bản sao. Mật khẩu cho các tài khoản demo được tạo ngẫu nhiên và in ở cuối mỗi lần chạy. Để bảo đảm mật khẩu có thể xem lại, mỗi lần chạy script sẽ đặt lại mật khẩu các tài khoản demo; lưu lại kết quả trước khi thoát.

Các tài khoản được tạo: `hr_demo1`, `hr_demo2` (nhân sự); `manager_demo1`, `manager_demo2` (quản lý); `hr_demolocked` (nhân sự đã khóa); và `lecturer_demo1` (giảng viên). Tài khoản giảng viên được liên kết với hồ sơ `DEMO-GV-001` — Nguyễn An Bình — có sẵn trong dữ liệu demo, không tạo hồ sơ trùng. Mật khẩu không được lưu trong script hoặc repository. Đăng nhập bằng từng tài khoản đang hoạt động để xem đúng giao diện theo vai trò.

Tệp [sample_data/mau_nhap_giang_vien.xlsx](sample_data/mau_nhap_giang_vien.xlsx) dùng đúng hàng tiêu đề tải từ API mẫu nhập, gồm 10 dòng hợp lệ và 3 dòng lỗi có chủ ý để thử chức năng **Nhập Excel**. Script tạo mới/cập nhật tệp này trong mỗi lần chạy. Để xem dữ liệu: mở **Tổng quan** và **Báo cáo thống kê** để xem biểu đồ/cảnh báo; dùng tài khoản HR mở **Hồ sơ giảng viên** và các tab chi tiết; vào **Khoa & bộ môn**, **Yêu cầu thay đổi**, **Quản trị hệ thống** và **Nhật ký hoạt động** để xem các nhóm còn lại. Quản lý xem báo cáo và xử lý yêu cầu; tài khoản admin chỉ quản trị tài khoản và xem nhật ký theo quyền hiện có.

### Làm sạch dữ liệu demo

Dừng server trước khi làm sạch. Nếu cơ sở dữ liệu chỉ chứa dữ liệu demo, xóa đúng tệp SQLite đang được cấu hình (mặc định `teacher_management.db` ở thư mục dự án), sau đó chạy lại `.\.venv\Scripts\python.exe -m app.bootstrap_admin` để tạo admin ban đầu và khởi động server. Xóa `private_uploads/` chỉ khi muốn xóa cả các tệp minh chứng demo và đã xác nhận thư mục đó không chứa tệp cần giữ. Nếu `DATABASE_URL` trỏ tới nơi khác, kiểm tra đường dẫn trước khi xóa; xóa SQLite sẽ xóa toàn bộ dữ liệu trong cơ sở dữ liệu đó.

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
