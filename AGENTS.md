# Ngữ cảnh dự án

## Mục tiêu

Đây là dự án web quản lý hồ sơ giảng viên và thống kê nhân sự tại trường đại học. Hệ thống hướng tới dữ liệu nhân sự tập trung, hỗ trợ cập nhật và tra cứu hồ sơ, theo dõi quá trình công tác, kiểm soát thay đổi và cung cấp báo cáo phục vụ quản lý.

## Tài liệu yêu cầu

- `requirement.md` mô tả đề xuất ban đầu: quản lý hồ sơ giảng viên, thống kê nhân sự, tài khoản và phân quyền; có lọc theo khoa và trình độ chuyên môn.
- `LẬP TRÌNH WEB.md` mở rộng yêu cầu thành các quy trình và mười nhóm chức năng bên dưới.
- Khi triển khai, dùng các tài liệu trên làm nguồn yêu cầu chi tiết. Nếu có điểm chưa rõ hoặc khác nhau, không tự suy diễn quy tắc nghiệp vụ; ưu tiên bảo toàn dữ liệu và nêu rõ giả định cần xác nhận.

## Công nghệ dự kiến

Đề xuất ban đầu nêu FastAPI, SQLite, HTML, CSS, JavaScript và Swagger UI. Đây là công nghệ dự kiến, không mặc định là cấu hình đã được cài đặt hoặc kiến trúc đã được chốt. Kiểm tra mã nguồn và cấu hình hiện có trước khi lựa chọn hoặc thay đổi công nghệ.

## Trạng thái triển khai hiện tại

- Backend API dùng FastAPI; dữ liệu lưu qua SQLAlchemy, mặc định dùng SQLite trong `teacher_management.db`.
- Mã backend nằm trong `app/`; `app/main.py` tạo ứng dụng và API, `app/models.py` định nghĩa bảng, `app/schemas.py` định nghĩa dữ liệu vào/ra, `app/database.py` cấu hình kết nối.
- Frontend tĩnh không cần framework nằm trong `app/static/`; `index.html`, `styles.css` và `app.js` được phục vụ tại `/`.
- Đã có API tạo/liệt kê/cập nhật khoa và tạo/liệt kê/xem/cập nhật hồ sơ giảng viên. Hồ sơ có thể lọc theo từ khóa, khoa, trình độ và trạng thái.
- Giao diện hiện có bảng tổng quan, danh sách/lọc, tạo/sửa hồ sơ và quản lý khoa/bộ môn; đơn vị có thể ngừng hoạt động thay vì xóa vật lý.
- Bảng được khởi tạo bằng SQLAlchemy khi ứng dụng khởi động; hiện chưa có hệ thống migration.
- Bộ kiểm thử dùng `unittest`, đặt trong `tests/`; lệnh chạy là `python -m unittest discover -v`.
- Giao diện web cơ bản đã có; xác thực và phân quyền chưa được triển khai. API và frontend hiện chỉ dành cho local với dữ liệu thử nghiệm; xem lưu ý bảo mật trong `README.md`.

## Người dùng và quyền hạn

- **Quản trị viên:** quản lý tài khoản và vai trò.
- **Nhân viên nhân sự:** quản lý hồ sơ và dữ liệu nhân sự; tạo yêu cầu thay đổi theo quy trình.
- **Người quản lý:** xem báo cáo và xử lý yêu cầu thay đổi khi được phân quyền.

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
