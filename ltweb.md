# 3\. BUSINESS REQUIREMENTS – YÊU CẦU NGHIỆP VỤ

## 3.1. Business Goals – Mục tiêu nghiệp vụ

Hệ thống được xây dựng nhằm nâng cao hiệu quả quản lý hồ sơ và quá trình công tác của giảng viên thông qua việc chuẩn hóa dữ liệu, quy trình xử lý và quyền truy cập.

Các mục tiêu nghiệp vụ cụ thể gồm:

* BG-01 – Tập trung hóa dữ liệu: Toàn bộ thông tin hồ sơ giảng viên được lưu trữ trong một hệ thống thống nhất.  
* BG-02 – Nâng cao hiệu quả xử lý: Giảm thời gian tạo mới, tìm kiếm, cập nhật và tổng hợp thông tin nhân sự.  
* BG-03 – Bảo đảm tính chính xác: Hạn chế dữ liệu trùng lặp, thiếu thông tin và sai lệch giữa các lần cập nhật.  
* BG-04 – Kiểm soát thay đổi: Bảo đảm các thay đổi quan trọng được xem xét, phê duyệt và lưu lại lịch sử.  
* BG-05 – Chủ động theo dõi hồ sơ: Hỗ trợ phát hiện hồ sơ chưa đầy đủ và hợp đồng sắp hết hạn.  
* BG-06 – Nâng cao tính minh bạch: Xác định được người thực hiện, thời điểm và nội dung của các thao tác quan trọng.  
* BG-07 – Hỗ trợ ra quyết định: Cung cấp báo cáo và thống kê nhân sự phục vụ công tác quản lý.

## 3.2. Business Requirements – Yêu cầu nghiệp vụ

### 3.2.1. BR-01 – Quản lý hồ sơ giảng viên

Hệ thống phải cho phép cán bộ nhân sự quản lý thông tin hồ sơ của từng giảng viên trong suốt quá trình công tác tại trường.

Các yêu cầu cụ thể:

* Tạo mới hồ sơ giảng viên dựa trên thông tin và giấy tờ được cung cấp.  
* Xem chi tiết, tìm kiếm, lọc và cập nhật hồ sơ.  
* Lưu các thông tin cơ bản như mã giảng viên, họ tên, ngày sinh, thông tin liên hệ, trình độ chuyên môn, khoa công tác, chức vụ và trạng thái công tác.  
* Kiểm tra các trường bắt buộc trước khi lưu.  
* Kiểm tra mã giảng viên không bị trùng lặp; kiểm tra email nếu trường này được quy định là duy nhất.  
* Cho phép tra cứu hồ sơ theo mã, họ tên, khoa, trình độ hoặc trạng thái công tác.  
* Quản lý trạng thái hồ sơ để phân biệt hồ sơ đang hoạt động, tạm ngừng hoặc đã kết thúc công tác.  
* Không cho phép xóa hồ sơ nếu việc xóa làm mất dữ liệu lịch sử liên quan; ưu tiên sử dụng trạng thái ngừng hoạt động hoặc lưu trữ hồ sơ.

Quy tắc nghiệp vụ:

* BR-01.1: Mỗi giảng viên phải có một mã định danh duy nhất.  
* BR-01.2: Hồ sơ chỉ được lưu khi đáp ứng các điều kiện dữ liệu bắt buộc.  
* BR-01.3: Chỉ người có quyền mới được tạo hoặc cập nhật hồ sơ.  
* BR-01.4: Các thay đổi quan trọng phải được thực hiện thông qua quy trình phê duyệt được quy định tại BR-05 và BR-06.

### 3.2.2. BR-02 – Quản lý khoa, bộ môn và đơn vị công tác

Hệ thống phải cho phép quản lý danh sách các đơn vị công tác để phục vụ việc phân loại và thống kê giảng viên.

Các yêu cầu cụ thể:

* Thêm mới, xem và cập nhật thông tin khoa, bộ môn.  
* Lưu mã đơn vị, tên đơn vị, thông tin mô tả và trạng thái hoạt động.  
* Liên kết hồ sơ giảng viên với đơn vị công tác hiện tại.  
* Cho phép tìm kiếm và thống kê số lượng giảng viên theo từng đơn vị.  
* Không cho phép xóa đơn vị đang được hồ sơ hoặc lịch sử công tác tham chiếu nếu việc xóa gây mất tính toàn vẹn dữ liệu.  
* Hỗ trợ ngừng sử dụng đơn vị mà vẫn giữ lại các thông tin lịch sử liên quan.

Quy tắc nghiệp vụ:

* BR-02.1: Mỗi đơn vị có một mã định danh duy nhất.  
* BR-02.2: Một hồ sơ giảng viên chỉ có một đơn vị công tác chính tại một thời điểm trong phạm vi phiên bản đầu tiên.  
* BR-02.3: Khi đơn vị thay đổi, hệ thống phải bảo toàn lịch sử công tác trước đó.

### 3.2.3. BR-03 – Quản lý bằng cấp và chứng chỉ

Hệ thống phải cho phép lưu trữ và quản lý thông tin bằng cấp, chứng chỉ của giảng viên.

Các yêu cầu cụ thể:

* Thêm mới, xem và cập nhật thông tin bằng cấp hoặc chứng chỉ.  
* Lưu tên văn bằng, loại văn bằng, chuyên ngành, đơn vị cấp, ngày cấp và thông tin liên quan.  
* Liên kết mỗi văn bằng hoặc chứng chỉ với hồ sơ giảng viên tương ứng.  
* Cho phép đính kèm tệp minh chứng.  
* Hiển thị danh sách bằng cấp theo từng giảng viên.  
* Hỗ trợ kiểm tra hồ sơ có thiếu tài liệu theo danh mục yêu cầu.  
* Kiểm soát quyền xem, tải xuống và chỉnh sửa tài liệu.

Quy tắc nghiệp vụ:

* BR-03.1: Một giảng viên có thể có nhiều bằng cấp và chứng chỉ.  
* BR-03.2: Thông tin văn bằng phải gắn với một hồ sơ giảng viên hợp lệ.  
* BR-03.3: Hệ thống chỉ quản lý thông tin và tài liệu được cung cấp, không tự kết luận văn bằng là thật hay giả.  
* BR-03.4: Việc chỉnh sửa hoặc thay thế tài liệu phải tuân theo quyền được cấp và được ghi nhận khi thuộc nhóm thao tác cần kiểm soát.

### 3.2.4. BR-04 – Quản lý hợp đồng lao động

Hệ thống phải hỗ trợ quản lý thông tin hợp đồng của giảng viên nhằm giúp cán bộ nhân sự theo dõi thời hạn và tình trạng hợp đồng.

Các yêu cầu cụ thể:

* Tạo mới và cập nhật thông tin hợp đồng theo quyền được cấp.  
* Lưu mã hợp đồng, loại hợp đồng, ngày bắt đầu, ngày kết thúc và trạng thái hợp đồng.  
* Đính kèm tệp hợp đồng khi có tài liệu.  
* Hiển thị danh sách hợp đồng theo từng giảng viên.  
* Tìm kiếm hợp đồng theo giảng viên, loại hợp đồng hoặc trạng thái.  
* Cảnh báo hợp đồng sắp hết hạn theo khoảng thời gian cấu hình.  
* Phân biệt hợp đồng còn hiệu lực, sắp hết hạn, đã hết hạn và đã chấm dứt.

Quy tắc nghiệp vụ:

* BR-04.1: Ngày kết thúc không được sớm hơn ngày bắt đầu đối với hợp đồng có thời hạn.  
* BR-04.2: Trạng thái hợp đồng phải phù hợp với thời hạn và thông tin nghiệp vụ đã được xác nhận.  
* BR-04.3: Hệ thống cảnh báo trước ngày hết hạn, mặc định 30 ngày.  
* BR-04.4: Cảnh báo không tự động gia hạn hoặc thay đổi hợp đồng.

### 3.2.5. BR-05 – Quản lý yêu cầu thay đổi thông tin nhân sự

Hệ thống phải cung cấp chức năng tạo và theo dõi yêu cầu thay đổi thông tin quan trọng trong hồ sơ giảng viên.

Các loại yêu cầu có thể bao gồm:

* Chuyển khoa hoặc bộ môn.  
* Thay đổi chức vụ.  
* Cập nhật trình độ hoặc thông tin chuyên môn cần được phê duyệt.  
* Điều chỉnh thông tin công tác.  
* Các thay đổi khác được nhà trường quy định.

Các yêu cầu cụ thể:

* Cho phép cán bộ nhân sự tạo yêu cầu và lựa chọn hồ sơ giảng viên liên quan.  
* Ghi nhận loại thay đổi, nội dung hiện tại, nội dung đề xuất, lý do và tài liệu minh chứng nếu cần.  
* Gán trạng thái xử lý cho yêu cầu.  
* Cho phép người tạo theo dõi tiến trình xử lý.  
* Lưu lại người tạo, thời điểm tạo và các lần bổ sung thông tin.  
* Không cập nhật dữ liệu chính thức khi yêu cầu vẫn đang chờ xử lý.

Quy tắc nghiệp vụ:

* BR-05.1: Mỗi yêu cầu phải gắn với một hồ sơ giảng viên.  
* BR-05.2: Yêu cầu phải có nội dung thay đổi và lý do phù hợp.  
* BR-05.3: Một yêu cầu chỉ được xử lý bởi người có quyền phê duyệt.  
* BR-05.4: Một yêu cầu đã được phê duyệt hoặc từ chối không được tiếp tục xử lý như yêu cầu đang chờ; nếu cần thay đổi lại phải tạo yêu cầu mới.

### 3.2.6. BR-06 – Phê duyệt yêu cầu thay đổi thông tin

Hệ thống phải hỗ trợ quy trình xem xét, phê duyệt hoặc từ chối các yêu cầu thay đổi thông tin nhân sự.

Các yêu cầu cụ thể:

* Hiển thị danh sách yêu cầu đang chờ xử lý cho người có thẩm quyền.  
* Cho phép xem thông tin hồ sơ liên quan và nội dung thay đổi được đề xuất.  
* Cho phép phê duyệt, từ chối hoặc yêu cầu bổ sung thông tin.  
* Bắt buộc nhập lý do khi từ chối hoặc yêu cầu bổ sung.  
* Ghi nhận người xử lý, thời điểm xử lý, quyết định và ý kiến.  
* Khi phê duyệt, cập nhật dữ liệu chính thức và lưu lịch sử thay đổi.  
* Khi từ chối, giữ nguyên dữ liệu chính thức hiện tại.  
* Khi yêu cầu bổ sung thông tin, chuyển trạng thái yêu cầu và chờ người tạo cập nhật.

Quy tắc nghiệp vụ:

* BR-06.1: Người tạo yêu cầu không được tự phê duyệt yêu cầu đó trong phiên bản đầu tiên.  
* BR-06.2: Chỉ người có quyền phê duyệt mới được đưa ra quyết định.  
* BR-06.3: Việc cập nhật dữ liệu và lưu lịch sử khi phê duyệt phải được thực hiện nhất quán.  
* BR-06.4: Hệ thống phải ngăn việc phê duyệt lặp lại một yêu cầu đã kết thúc.  
* BR-06.5: Mọi quyết định phê duyệt hoặc từ chối đều phải được lưu lại.

### 3.2.7. BR-07 – Quản lý quá trình công tác

Hệ thống phải lưu lại quá trình công tác của giảng viên theo từng giai đoạn để phục vụ tra cứu và đối chiếu.

Các yêu cầu cụ thể:

* Ghi nhận đơn vị công tác, chức vụ, ngày bắt đầu và ngày kết thúc của từng giai đoạn.  
* Hiển thị lịch sử công tác theo trình tự thời gian.  
* Tự động tạo bản ghi lịch sử tương ứng khi một yêu cầu thay đổi quan trọng được phê duyệt.  
* Giữ lại thông tin của giai đoạn công tác trước đó.  
* Cho phép tìm kiếm và xem chi tiết quá trình công tác của từng giảng viên.  
* Kiểm tra tính hợp lệ của khoảng thời gian để hạn chế dữ liệu mâu thuẫn.

Quy tắc nghiệp vụ:

* BR-07.1: Mỗi bản ghi lịch sử phải liên kết với một hồ sơ giảng viên.  
* BR-07.2: Ngày kết thúc của một giai đoạn không được sớm hơn ngày bắt đầu.  
* BR-07.3: Khi có thay đổi đơn vị hoặc chức vụ, hệ thống không được ghi đè làm mất toàn bộ thông tin cũ.  
* BR-07.4: Lịch sử công tác đã phát sinh phải được bảo vệ theo quyền truy cập.

### 3.2.8. BR-08 – Kiểm tra tính đầy đủ của hồ sơ và cảnh báo thời hạn

Hệ thống phải hỗ trợ kiểm tra hồ sơ theo danh mục thông tin và tài liệu cần có, đồng thời cảnh báo các thời hạn quan trọng.

Các yêu cầu cụ thể:

* Kiểm tra các trường thông tin bắt buộc của hồ sơ.  
* Kiểm tra sự tồn tại của các tài liệu được yêu cầu theo danh mục cấu hình.  
* Hiển thị trạng thái hồ sơ đầy đủ hoặc còn thiếu thông tin.  
* Liệt kê các trường hoặc tài liệu còn thiếu để cán bộ nhân sự bổ sung.  
* Phát hiện hợp đồng sắp hết hạn hoặc đã hết hạn.  
* Hiển thị danh sách cảnh báo trên trang tổng quan.  
* Cập nhật trạng thái kiểm tra khi dữ liệu hoặc tài liệu được bổ sung.

Quy tắc nghiệp vụ:

* BR-08.1: Hồ sơ chỉ được đánh dấu đầy đủ khi đáp ứng các tiêu chí đã cấu hình.  
* BR-08.2: Thiếu một trường bắt buộc hoặc tài liệu bắt buộc phải được thể hiện rõ.  
* BR-08.3: Hợp đồng sắp hết hạn được xác định dựa trên ngày kết thúc và khoảng thời gian cảnh báo.  
* BR-08.4: Cảnh báo chỉ hỗ trợ theo dõi, không tự động thay đổi trạng thái công tác hoặc gia hạn hợp đồng.

### 3.2.9. BR-09 – Quản lý báo cáo và thống kê nhân sự

Hệ thống phải cung cấp các báo cáo tổng hợp giúp cán bộ nhân sự và người quản lý theo dõi tình hình nhân sự.

Các yêu cầu cụ thể:

* Thống kê tổng số giảng viên theo trạng thái công tác.  
* Thống kê số lượng giảng viên theo khoa, bộ môn và trình độ chuyên môn.  
* Thống kê số lượng hồ sơ chưa đầy đủ.  
* Thống kê hợp đồng sắp hết hạn hoặc đã hết hạn.  
* Thống kê yêu cầu thay đổi thông tin theo trạng thái xử lý.  
* Lọc báo cáo theo đơn vị và khoảng thời gian.  
* Hiển thị số liệu bằng bảng và biểu đồ.  
* Hỗ trợ xuất báo cáo Excel nếu chức năng này được triển khai.

Quy tắc nghiệp vụ:

* BR-09.1: Báo cáo phải được tổng hợp từ dữ liệu có trong hệ thống.  
* BR-09.2: Người dùng chỉ được xem dữ liệu nằm trong phạm vi quyền được cấp.  
* BR-09.3: Thời gian và điều kiện lọc phải được thể hiện rõ trên báo cáo.  
* BR-09.4: Dữ liệu xuất ra phải tuân thủ quyền truy cập đối với thông tin nhân sự.

### 3.2.10. BR-10 – Phân quyền người dùng

Hệ thống phải áp dụng cơ chế phân quyền dựa trên vai trò (Role-Based Access Control – RBAC) để kiểm soát chức năng và dữ liệu mà mỗi người dùng được phép truy cập.

Các yêu cầu cụ thể:

* Quản lý tài khoản người dùng.  
* Gán vai trò cho tài khoản.  
* Phân biệt quyền của quản trị viên, cán bộ nhân sự và cán bộ quản lý.  
* Kiểm tra quyền khi người dùng truy cập chức năng hoặc thực hiện thao tác dữ liệu.  
* Hạn chế truy cập hồ sơ và tài liệu ngoài phạm vi được phép.  
* Ngăn người dùng tự nâng quyền hoặc sửa đổi quyền của chính mình trái phép.  
* Ghi nhận các thao tác quản lý tài khoản và phân quyền quan trọng.

Quy tắc nghiệp vụ:

* BR-10.1: Người dùng phải đăng nhập trước khi sử dụng chức năng nội bộ.  
* BR-10.2: Quyền được kiểm tra tại Backend, không chỉ dựa vào việc ẩn hoặc hiện nút trên giao diện.  
* BR-10.3: Người dùng không có quyền phải bị từ chối thao tác.  
* BR-10.4: Quản trị viên có quyền quản lý hệ thống không mặc nhiên có quyền phê duyệt mọi yêu cầu nghiệp vụ.  
* BR-10.5: Tài khoản bị khóa không được tiếp tục truy cập các chức năng yêu cầu đăng nhập.

### 3.2.11. BR-11 – Nhật ký hoạt động hệ thống (Audit Trail)

Hệ thống phải ghi nhận các hoạt động quan trọng để hỗ trợ truy vết, kiểm tra và bảo đảm tính minh bạch trong quản lý dữ liệu.

Các hoạt động cần ghi nhận bao gồm:

* Đăng nhập và các sự kiện bảo mật quan trọng.  
* Tạo mới, cập nhật hoặc thay đổi trạng thái hồ sơ.  
* Tạo và xử lý yêu cầu thay đổi thông tin.  
* Phê duyệt, từ chối hoặc yêu cầu bổ sung thông tin.  
* Thêm, sửa hoặc thay thế tài liệu quan trọng.  
* Tạo tài khoản, khóa tài khoản và thay đổi quyền truy cập.

Mỗi bản ghi nhật ký cần có thông tin người thực hiện, thời điểm, loại thao tác, đối tượng bị tác động và kết quả thực hiện. Với thao tác cập nhật dữ liệu, hệ thống có thể lưu giá trị trước và sau thay đổi đối với những trường phù hợp.

Quy tắc nghiệp vụ:

* BR-11.1: Nhật ký phải gắn với người thực hiện nếu xác định được tài khoản.  
* BR-11.2: Người dùng thông thường không được tự ý sửa hoặc xóa nhật ký.  
* BR-11.3: Các thao tác phê duyệt và thay đổi quyền phải được ghi nhận.  
* BR-11.4: Chỉ người được phân quyền mới được xem nhật ký.  
* BR-11.5: Nhật ký không thay thế cho bản ghi lịch sử công tác; hai loại dữ liệu có mục đích khác nhau.

# **Chi tiết 10 chức năng**

## **1\. Đăng nhập, đăng xuất và phân quyền**

* Đăng nhập bằng tên tài khoản và mật khẩu.  
* Đăng xuất khỏi hệ thống.  
* Phân quyền theo 3 vai trò: Quản trị viên, Nhân viên nhân sự, Người quản lý.  
* Chỉ cho phép người dùng truy cập các chức năng phù hợp với vai trò.  
* Kiểm tra thông tin đăng nhập và thông báo khi sai tài khoản hoặc mật khẩu.  
* Đổi mật khẩu tài khoản.

## **2\. Quản lý hồ sơ giảng viên**

* Thêm hồ sơ giảng viên mới.  
* Xem thông tin chi tiết của từng giảng viên.  
* Chỉnh sửa thông tin hồ sơ.  
* Xóa hồ sơ khi được phép.  
* Tìm kiếm giảng viên theo họ tên hoặc mã giảng viên.  
* Lọc danh sách theo khoa, học vị hoặc trạng thái công tác.

Thông tin hồ sơ gồm: mã giảng viên, họ tên, ngày sinh, giới tính, email, số điện thoại, địa chỉ, khoa, bộ môn, học vị, chức danh và trạng thái công tác.

## **3\. Quản lý khoa và bộ môn**

* Thêm, sửa và xóa thông tin khoa.  
* Thêm, sửa và xóa bộ môn thuộc từng khoa.  
* Xem danh sách giảng viên theo khoa hoặc bộ môn.  
* Tìm kiếm khoa, bộ môn.  
* Kiểm tra dữ liệu liên quan trước khi xóa để tránh làm mất liên kết với hồ sơ giảng viên.

Ví dụ: Khoa Công nghệ thông tin có các bộ môn như Hệ thống thông tin, Khoa học máy tính.

## **4\. Quản lý bằng cấp và chứng chỉ**

* Thêm bằng cấp hoặc chứng chỉ của giảng viên.  
* Cập nhật thông tin văn bằng, chứng chỉ.  
* Xem danh sách bằng cấp của từng giảng viên.  
* Tải lên và lưu đường dẫn đến file minh chứng.  
* Tải xuống hoặc xem lại tài liệu đã lưu.  
* Tìm kiếm, lọc theo loại bằng cấp hoặc trình độ.

Thông tin gồm: tên văn bằng, chuyên ngành, cơ sở đào tạo, năm cấp, loại văn bằng và file minh chứng.

## **5\. Quản lý hợp đồng lao động**

* Thêm hợp đồng cho giảng viên.  
* Cập nhật thông tin hợp đồng.  
* Xem danh sách hợp đồng theo từng giảng viên.  
* Theo dõi ngày bắt đầu và ngày kết thúc hợp đồng.  
* Phân loại hợp đồng theo trạng thái: còn hiệu lực, sắp hết hạn, đã hết hạn.  
* Hiển thị cảnh báo hợp đồng sắp hết hạn.

Thông tin gồm: mã hợp đồng, loại hợp đồng, ngày ký, ngày bắt đầu, ngày kết thúc và trạng thái.

## **6\. Quản lý quá trình công tác**

* Thêm quá trình công tác của giảng viên.  
* Cập nhật thông tin quá trình công tác.  
* Xem lịch sử công tác theo từng giảng viên.  
* Ghi nhận việc chuyển khoa, chuyển bộ môn hoặc thay đổi chức vụ.  
* Sắp xếp lịch sử theo thời gian.  
* Xem quá trình công tác dưới dạng dòng thời gian.

Thông tin gồm: đơn vị công tác, chức vụ, ngày bắt đầu, ngày kết thúc và lý do thay đổi.

Ví dụ: Giảng viên công tác tại Bộ môn A từ năm 2022 đến năm 2024, sau đó chuyển sang Bộ môn B từ năm 2024\.

## **7\. Quản lý yêu cầu thay đổi thông tin**

* Nhân viên nhân sự tạo yêu cầu thay đổi thông tin hồ sơ giảng viên.  
* Ghi rõ thông tin hiện tại, thông tin đề xuất và lý do thay đổi.  
* Người quản lý xem danh sách yêu cầu đang chờ duyệt.  
* Người quản lý có thể phê duyệt hoặc từ chối yêu cầu.  
* Lưu lý do từ chối nếu yêu cầu không được chấp nhận.  
* Chỉ cập nhật hồ sơ chính thức sau khi yêu cầu được phê duyệt.  
* Theo dõi trạng thái: chờ duyệt, đã duyệt, bị từ chối.

Đây là chức năng nâng cao giúp đề tài khác với một website CRUD thông thường.

## **8\. Kiểm tra hồ sơ chưa đầy đủ**

* Kiểm tra hồ sơ thiếu các trường thông tin bắt buộc.  
* Phát hiện giảng viên chưa có thông tin bằng cấp hoặc chứng chỉ cần thiết.  
* Liệt kê các hồ sơ chưa đầy đủ.  
* Hiển thị cụ thể thông tin hoặc tài liệu còn thiếu.  
* Lọc hồ sơ theo khoa và mức độ hoàn thiện.  
* Cập nhật trạng thái hoàn thiện khi thông tin đã được bổ sung.

Ví dụ: Hồ sơ giảng viên Nguyễn Văn A còn thiếu email và file minh chứng bằng thạc sĩ.

## **9\. Thống kê và báo cáo**

* Thống kê tổng số giảng viên.  
* Thống kê số lượng giảng viên theo khoa, bộ môn.  
* Thống kê theo học vị, chức danh và trạng thái công tác.  
* Thống kê số hợp đồng sắp hết hạn hoặc đã hết hạn.  
* Thống kê số hồ sơ chưa đầy đủ.  
* Thống kê số yêu cầu thay đổi đang chờ duyệt.  
* Hiển thị kết quả trên dashboard bằng biểu đồ.  
* Xuất danh sách hoặc báo cáo ra file Excel.

## **10\. Quản lý lịch sử thao tác**

* Ghi lại các thao tác quan trọng của người dùng.  
* Lưu tài khoản thực hiện thao tác.  
* Ghi nhận thời gian thực hiện.  
* Lưu loại thao tác: thêm, sửa, xóa, duyệt hoặc từ chối.  
* Ghi nhận đối tượng dữ liệu bị tác động.  
* Cho phép quản trị viên tìm kiếm lịch sử theo tài khoản, thời gian hoặc loại thao tác.

