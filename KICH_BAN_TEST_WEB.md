# Kịch bản kiểm thử web

Kịch bản kiểm thử thủ công các chức năng chính của hệ thống. Chỉ chạy trên máy local với dữ liệu giả.

## 1. Chuẩn bị

1. Dùng cơ sở dữ liệu thử nghiệm, không dùng dữ liệu nhân sự thật. Nếu có dữ liệu cần giữ, sao lưu trước.
2. Khởi động ứng dụng theo hướng dẫn trong [README.md](./README.md), rồi mở `http://127.0.0.1:8000/`.
3. Nếu cần dữ liệu và tài khoản mẫu, chạy `.\.venv\Scripts\python.exe scripts\seed_demo.py --base-url http://127.0.0.1:8000`. Ghi lại mật khẩu được in ra; script có ghi dữ liệu vào cơ sở dữ liệu.
4. Chuẩn bị tài khoản admin đã tạo, và các tài khoản demo HR, manager, lecturer. Đăng nhập bằng từng vai trò để kiểm tra quyền.
5. Dùng mã thử riêng, ví dụ `TEST-GV-01`, `TEST-DV-01`; tránh trùng dữ liệu đã có.

## 2. Các bước kiểm thử

| # | Chức năng | Thao tác | Kết quả mong đợi |
|---|---|---|---|
| 1 | Tài khoản và đăng nhập | Đăng nhập bằng mật khẩu đúng; đổi mật khẩu tài khoản thử, đăng xuất rồi đăng nhập mật khẩu mới; thử mật khẩu cũ và mật khẩu sai. | Mật khẩu mới dùng được, mật khẩu cũ/sai không vào được; đăng xuất kết thúc phiên. |
| 2 | Phân quyền | Đăng nhập lần lượt bằng admin, HR, manager và lecturer; thử truy cập chức năng hoặc hồ sơ không thuộc quyền. | Admin quản lý tài khoản và xem nhật ký; HR quản lý dữ liệu nhân sự; manager xem báo cáo và xử lý yêu cầu; lecturer chỉ xem hồ sơ đã liên kết và gửi tài liệu. Không thể dùng giao diện/API để vượt quyền. |
| 3 | Hồ sơ giảng viên | Dùng HR tạo hồ sơ với mã thử; sửa một thông tin; tìm theo mã/tên và lọc theo đơn vị, trình độ, trạng thái. Thử tạo mã trùng và nhập dữ liệu bắt buộc sai/thiếu. | Hồ sơ hợp lệ được lưu và tìm thấy; bộ lọc trả về đúng kết quả; mã trùng hoặc dữ liệu không hợp lệ bị từ chối, không tạo bản ghi lỗi. |
| 4 | Nhập Excel | Dùng HR nhập tệp mẫu `sample_data\mau_nhap_giang_vien.xlsx`, trong đó có dòng hợp lệ và dòng sai. | Dòng hợp lệ được nhập; dòng sai được báo rõ để sửa; không tạo hồ sơ lỗi. |
| 5 | Đơn vị/khoa/bộ môn | Dùng HR tạo một đơn vị thử, dùng đơn vị đó cho hồ sơ; ngừng hoạt động đơn vị. | Mã đơn vị trùng bị từ chối; đơn vị được ngừng hoạt động nhưng hồ sơ/lịch sử liên quan vẫn còn. |
| 6 | Bằng cấp/chứng chỉ | Thêm bằng cấp hoặc chứng chỉ cho hồ sơ thử; nhập ngày hết hạn nếu có. | Thông tin được lưu và hiển thị đúng; cảnh báo hạn (nếu sắp hết) xuất hiện theo cấu hình, không tự sửa trạng thái nghiệp vụ. |
| 7 | Hợp đồng | Thêm hợp đồng có ngày kết thúc hợp lệ; thử nhập ngày kết thúc trước ngày bắt đầu; kiểm tra hợp đồng sắp hết hạn. | Hợp đồng hợp lệ được lưu; khoảng ngày sai bị từ chối; hợp đồng sắp hết hạn được cảnh báo và không tự gia hạn/đổi trạng thái. |
| 8 | Quá trình công tác | Thêm một giai đoạn công tác; thử nhập ngày kết thúc trước ngày bắt đầu. Sau đó đề xuất thay đổi đơn vị qua yêu cầu ở bước 9. | Giai đoạn hợp lệ được lưu; ngày sai bị từ chối; khi thay đổi được duyệt, giai đoạn cũ được giữ trong lịch sử và đơn vị hiện tại được cập nhật. |
| 9 | Yêu cầu thay đổi | HR tạo yêu cầu gắn với hồ sơ, có nội dung và lý do. Thử để trống lý do; đăng nhập manager khác để duyệt. Thử tự duyệt yêu cầu của chính người tạo; thử từ chối/yêu cầu bổ sung mà không ghi lý do; thử xử lý lại yêu cầu đã kết thúc. | Yêu cầu hợp lệ được tạo; thiếu thông tin hoặc tự duyệt/thiếu lý do/xử lý lại đều bị chặn; duyệt mới cập nhật dữ liệu chính thức và lưu người xử lý, thời điểm, lịch sử. |
| 10 | Checklist và tài liệu | Dùng HR cấu hình một mục bắt buộc cho hồ sơ. Lecturer đăng nhập tài khoản đã liên kết, tải tệp PDF/DOCX/PNG/JPEG hợp lệ; HR duyệt hoặc từ chối. Thử tệp sai định dạng hoặc quá 10 MB. | Tệp hợp lệ được gửi ở trạng thái chờ rà soát; chưa được duyệt thì mục bắt buộc chưa hoàn tất; quyết định của HR cập nhật checklist; tệp không hợp lệ bị từ chối. Lecturer không xem/sửa hồ sơ người khác hoặc tài liệu đã được xử lý. |
| 11 | Báo cáo và xuất Excel | Dùng manager mở báo cáo; lọc theo đơn vị/thời gian (nếu có); xuất Excel. Thử mở chức năng chi tiết hồ sơ bằng manager. | Số liệu và tệp xuất phù hợp điều kiện lọc, chỉ gồm dữ liệu được phép; manager không xem được danh sách/phát hiện chi tiết dành cho HR. |
| 12 | Quản trị tài khoản | Dùng admin tạo tài khoản thử, gán vai trò, khóa rồi mở khóa tài khoản. Thử dùng tài khoản bị khóa đăng nhập; thử dùng HR thao tác quản trị. | Vai trò và trạng thái tài khoản được lưu; tài khoản bị khóa không đăng nhập được; HR không có quyền quản trị tài khoản; không thể tự nâng quyền trái phép. |
| 13 | Nhật ký hoạt động | Sau các thao tác tạo/sửa/duyệt/khóa ở trên, dùng admin mở nhật ký; thử sửa/xóa nhật ký bằng người dùng thường. | Nhật ký thể hiện người thực hiện, thời điểm, thao tác, đối tượng và kết quả; người dùng thường không thể sửa/xóa nhật ký. |
| 14 | Tổng quan và cảnh báo | Mở trang tổng quan bằng HR; kiểm tra số liệu hồ sơ, checklist và cảnh báo hợp đồng/chứng chỉ sau khi tạo dữ liệu thử. | Số liệu phản ánh dữ liệu đã lưu; cảnh báo hiển thị đúng và không tự thay đổi dữ liệu. |
| 15 | Sao lưu/khôi phục | Chỉ trên môi trường thử nghiệm: tạo bản sao lưu; dừng server; khôi phục bản sao theo hướng dẫn README; khởi động lại và kiểm tra một hồ sơ cùng tài liệu mẫu. | Sao lưu được tạo; khôi phục thành công và dữ liệu/tệp mẫu còn truy cập được. Không thử trên cơ sở dữ liệu có dữ liệu cần giữ. |

## 3. Ghi nhận kết quả

Đánh dấu từng bước **Đạt/Không đạt**, ghi lại mã hồ sơ/tài khoản thử, thao tác tái hiện và thông báo lỗi. Kịch bản đạt khi tất cả bước áp dụng đều đạt; bỏ qua bước chỉ khi tính năng/phụ thuộc tương ứng chưa được cấu hình và ghi rõ lý do.

Kiểm thử tự động bổ sung (không thay thế kiểm thử giao diện): `.\.venv\Scripts\python.exe -m unittest discover -v`.
