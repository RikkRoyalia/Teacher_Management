# Ngữ cảnh dự án

## Mục tiêu

Đây là dự án web quản lý hồ sơ giảng viên và thống kê nhân sự tại trường đại học. Hệ thống hướng tới dữ liệu nhân sự tập trung, hỗ trợ cập nhật và tra cứu hồ sơ, theo dõi quá trình công tác, kiểm soát thay đổi và cung cấp báo cáo phục vụ quản lý.

## Tài liệu yêu cầu

- `requirement.md` mô tả đề xuất ban đầu: quản lý hồ sơ giảng viên, thống kê nhân sự, tài khoản và phân quyền; có lọc theo khoa và trình độ chuyên môn.
- `ltweb.md` mở rộng yêu cầu thành các quy trình và nhóm chức năng chi tiết.
- Khi triển khai, dùng các tài liệu trên làm nguồn yêu cầu chi tiết. Nếu có điểm chưa rõ hoặc khác nhau, không tự suy diễn quy tắc nghiệp vụ; ưu tiên bảo toàn dữ liệu và nêu rõ giả định cần xác nhận.

## Công nghệ dự kiến

Đề xuất ban đầu nêu FastAPI, SQLite, HTML, CSS, JavaScript và Swagger UI. Đây là công nghệ dự kiến, không mặc định là cấu hình đã được cài đặt hoặc kiến trúc đã được chốt. Kiểm tra mã nguồn và cấu hình hiện có trước khi lựa chọn hoặc thay đổi công nghệ.

## Trạng thái triển khai hiện tại

- Backend API dùng FastAPI; dữ liệu lưu qua SQLAlchemy, mặc định dùng SQLite trong `teacher_management.db`.
- Mã backend nằm trong `app/`; `app/main.py` tạo ứng dụng và API, `app/models.py` định nghĩa bảng, `app/schemas.py` định nghĩa dữ liệu vào/ra, `app/database.py` cấu hình kết nối.
- Frontend tĩnh không cần framework nằm trong `app/static/`; `index.html`, `styles.css` và `app.js` được phục vụ tại `/`.
- Đã có API quản lý khoa/đơn vị và hồ sơ giảng viên, gồm tìm kiếm/lọc theo từ khóa, khoa, trình độ và trạng thái; đơn vị được ngừng hoạt động thay vì xóa vật lý.
- Giao diện tĩnh tại `app/static/` cung cấp tổng quan, quản lý hồ sơ và đơn vị, báo cáo, quản trị tài khoản, nhật ký hoạt động và cổng giảng viên.
- Dữ liệu được nâng cấp bằng Alembic khi ứng dụng khởi động; với SQLite hiện có, ứng dụng tạo bản sao trước migration. Xem `app/migrations/` và `app/database.py`.
- Bộ kiểm thử dùng `unittest`, đặt trong `tests/`; lệnh chạy là `python -m unittest discover -v`.
- Đã có xác thực, quản lý tài khoản, RBAC kiểm tra tại backend, session/CSRF, giới hạn truy cập theo hồ sơ, audit, backup/restore và quy trình duyệt thay đổi/tài liệu.
- Tài khoản giảng viên do admin tạo và liên kết với hồ sơ có sẵn; giảng viên chỉ xem/nộp tài liệu cho hồ sơ của mình. Tài liệu upload chờ HR rà soát trước khi được tính là hoàn tất checklist.
- Hệ thống hiện chỉ dành cho chạy local với dữ liệu thử nghiệm, chưa sẵn sàng cho truy cập mạng hoặc dữ liệu nhân sự thật; xem giới hạn và lưu ý bảo mật trong `README.md`.

## Người dùng và quyền hạn

- **Quản trị viên:** quản lý tài khoản và vai trò.
- **Nhân viên nhân sự:** quản lý hồ sơ và dữ liệu nhân sự; tạo yêu cầu thay đổi theo quy trình.
- **Người quản lý:** xem báo cáo và xử lý yêu cầu thay đổi khi được phân quyền.
- **Giảng viên:** xem hồ sơ đã liên kết và nộp tài liệu minh chứng để nhân sự rà soát.

Áp dụng phân quyền theo vai trò (RBAC). Phải kiểm tra quyền ở Backend cho cả chức năng lẫn dữ liệu; không xem việc ẩn nút trên giao diện là kiểm soát quyền. Người dùng không được tự nâng quyền trái phép. Quyền quản trị hệ thống không đồng nghĩa với quyền phê duyệt nghiệp vụ.

## Phạm vi chức năng

1. Đăng nhập, đăng xuất, đổi mật khẩu và phân quyền tài khoản.
2. Quản lý hồ sơ giảng viên: tạo, xem, cập nhật, tra cứu và lọc.
3. Quản lý khoa, bộ môn và đơn vị công tác.
4. Quản lý bằng cấp, chứng chỉ và tài liệu minh chứng.
5. Quản lý hợp đồng lao động và cảnh báo thời hạn.
6. Quản lý lịch sử quá trình công tác.
7. Tạo, theo dõi, phê duyệt, từ chối hoặc yêu cầu bổ sung thông tin thay đổi.
8. Kiểm tra tính đầy đủ của hồ sơ và hiển thị thông tin còn thiếu.
9. Thống kê, báo cáo và lọc số liệu theo đơn vị hoặc thời gian; xuất Excel là chức năng được nêu trong tài liệu chi tiết.
10. Ghi nhật ký các thao tác quan trọng để truy vết.

## Quy tắc nghiệp vụ cần giữ

- Mã giảng viên và mã đơn vị phải duy nhất. Chỉ yêu cầu email duy nhất nếu nghiệp vụ quy định trường này là duy nhất. Kiểm tra dữ liệu bắt buộc và tính hợp lệ trước khi lưu.
- Một giảng viên có một đơn vị công tác chính tại một thời điểm trong phạm vi phiên bản đầu tiên; thay đổi đơn vị phải giữ lại lịch sử.
- Không xóa dữ liệu đang được tham chiếu nếu việc đó làm mất tính toàn vẹn hoặc lịch sử; ưu tiên ngừng hoạt động/lưu trữ khi phù hợp.
- Tài liệu bằng cấp là thông tin được cung cấp; hệ thống không tự kết luận tính xác thực của văn bằng.
- Ngày kết thúc hợp đồng hoặc giai đoạn công tác không được trước ngày bắt đầu. Khoảng thời gian cảnh báo hợp đồng có thể cấu hình, mặc định trước 30 ngày; cảnh báo không tự gia hạn hay tự đổi trạng thái nghiệp vụ.
- Yêu cầu thay đổi phải gắn với hồ sơ, có nội dung đề xuất và lý do. Dữ liệu chính thức chỉ cập nhật sau khi được duyệt; người tạo không tự phê duyệt yêu cầu của mình. Khi từ chối hoặc yêu cầu bổ sung, phải ghi lý do; lưu người xử lý và thời điểm xử lý. Yêu cầu đã kết thúc không được xử lý lại như yêu cầu đang chờ.
- Khi phê duyệt thay đổi liên quan đến công tác, cập nhật dữ liệu chính thức và lưu lịch sử một cách nhất quán; không ghi đè làm mất giai đoạn cũ.
- Trạng thái đầy đủ của hồ sơ phải dựa trên các trường và tài liệu bắt buộc; cần chỉ rõ nội dung còn thiếu.
- Báo cáo và tệp xuất phải tuân theo quyền truy cập, thể hiện điều kiện lọc và chỉ tổng hợp dữ liệu có trong hệ thống.
- Nhật ký cần ghi nhận người thực hiện (nếu xác định được), thời điểm, thao tác, đối tượng và kết quả. Người dùng thông thường không được sửa hoặc xóa nhật ký. Nhật ký thao tác không thay thế lịch sử công tác.

## Hướng dẫn khi thay đổi mã nguồn

- Trước khi sửa chức năng, kiểm tra cấu trúc, quy ước và công nghệ thực tế trong repository; không suy ra cấu trúc mã nguồn chỉ từ công nghệ dự kiến.
- Giữ nhất quán quyền truy cập và các quy tắc bảo toàn lịch sử ở giao diện, API và tầng lưu trữ liên quan.
- Với chức năng chưa được mô tả đủ, giữ phạm vi tối thiểu cần thiết và ghi rõ giả định thay vì tự đặt thêm quy trình nghiệp vụ.
