from alembic import op
import sqlalchemy as sa

from app.database import Base
from app import models

revision = "20261030_0002"
down_revision = "20261030_0001"
branch_labels = None
depends_on = None

CHECKLIST_ITEMS = (
    ("application-form", "Phiếu đăng ký dự tuyển theo mẫu NEU", "Tuyển dụng", "required", "Khi đăng ký dự tuyển", False),
    ("personnel-record", "Sơ yếu lý lịch/lý lịch nhân sự", "Cá nhân", "conditional", "Theo mẫu và yêu cầu của giai đoạn tuyển dụng, hoàn thiện hồ sơ", False),
    ("identity-document", "CCCD hoặc giấy tờ định danh", "Cá nhân", "conditional", "Khi hồ sơ hoặc thủ tục nhân sự yêu cầu", True),
    ("bachelor-degree-transcript", "Bằng đại học và bảng điểm", "Bằng cấp", "required", "Bằng cấp phải đáp ứng tiêu chuẩn vị trí; bảng điểm nộp khi được yêu cầu", False),
    ("master-degree", "Bằng thạc sĩ", "Bằng cấp", "required", "Đối với vị trí giảng viên có yêu cầu trình độ thạc sĩ trở lên", False),
    ("doctorate-degree", "Bằng tiến sĩ", "Bằng cấp", "conditional", "Vị trí yêu cầu tiến sĩ, như giảng dạy sau đại học hoặc một số vị trí cao cấp", False),
    ("language-certificate", "Chứng chỉ ngoại ngữ hoặc minh chứng tương đương", "Bằng cấp", "conditional", "Theo chuẩn ngoại ngữ của vị trí và trường hợp miễn", False),
    ("pedagogy-certificate", "Chứng chỉ nghiệp vụ sư phạm", "Bằng cấp", "conditional", "Khi quy định áp dụng cho vị trí cụ thể yêu cầu", False),
    ("computer-certificate", "Chứng chỉ tin học riêng", "Bằng cấp", "conditional", "Khi được yêu cầu; không mặc định bắt buộc nếu đã có minh chứng năng lực tương đương", False),
    ("academic-cv", "Lý lịch khoa học", "Nghiên cứu", "conditional", "Khi tuyển dụng hoặc quản lý học thuật yêu cầu", False),
    ("publication-list", "Danh mục công trình nghiên cứu", "Nghiên cứu", "conditional", "Khi vị trí yêu cầu công bố khoa học hoặc khi đánh giá nghiên cứu", False),
    ("research-evidence", "Minh chứng đề tài nghiên cứu, bài báo, sách, giáo trình", "Nghiên cứu", "optional", "Bổ sung để quản lý thành tích; chuyển thành bắt buộc nếu thông báo yêu cầu", False),
    ("recruitment-contract", "Quyết định tuyển dụng/hợp đồng lao động", "Tuyển dụng", "required", "Khi hoàn thiện hồ sơ nhân sự sau tuyển dụng", False),
    ("appointment-salary-decisions", "Quyết định bổ nhiệm chức danh nghề nghiệp, xếp lương", "Công tác", "conditional", "Khi đã có quyết định tương ứng", False),
    ("teaching-assignment", "Quyết định phân công giảng dạy, đơn vị công tác", "Công tác", "conditional", "Khi có phân công hoặc thay đổi nhiệm vụ", False),
    ("periodic-performance-review", "Hồ sơ đánh giá công việc định kỳ", "Công tác", "conditional", "Khi đến kỳ đánh giá hoặc thực hiện thủ tục nhân sự liên quan", False),
    ("training-certificates", "Chứng nhận đào tạo, bồi dưỡng", "Đào tạo", "optional", "Lưu bổ sung, trừ khi chương trình hoặc quy định yêu cầu", False),
    ("awards", "Giấy khen, bằng khen, giải thưởng", "Thành tích", "optional", "Khi có thành tích", False),
    ("insurance-tax-records", "Hồ sơ bảo hiểm và thuế", "Chế độ", "conditional", "Theo thủ tục lao động, tiền lương và nghĩa vụ pháp luật", True),
    ("commendation-discipline-records", "Hồ sơ khen thưởng, kỷ luật", "Công tác", "conditional", "Khi phát sinh sự kiện tương ứng", False),
    ("portrait-photo", "Ảnh chân dung", "Cá nhân", "conditional", "Theo yêu cầu hồ sơ hoặc cấp thẻ nhân sự", True),
)


def _column_names(connection: sa.Connection, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(connection).get_columns(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    existing_tables = set(sa.inspect(connection).get_table_names())
    had_legacy_required = (
        "checklist_items" in existing_tables
        and "is_required" in _column_names(connection, "checklist_items")
    )

    if "checklist_items" in existing_tables:
        columns = _column_names(connection, "checklist_items")
        if "classification" not in columns:
            op.add_column(
                "checklist_items",
                sa.Column(
                    "classification",
                    sa.String(20),
                    nullable=False,
                    server_default="conditional",
                ),
            )
        if "applicability" not in columns:
            op.add_column(
                "checklist_items",
                sa.Column(
                    "applicability",
                    sa.String(500),
                    nullable=False,
                    server_default="",
                ),
            )
        if "is_active" not in columns:
            op.add_column(
                "checklist_items",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )
        if "is_sensitive" not in columns:
            op.add_column(
                "checklist_items",
                sa.Column(
                    "is_sensitive",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )
        if had_legacy_required:
            op.execute(
                "UPDATE checklist_items SET classification = "
                "CASE WHEN is_required = 1 THEN 'required' ELSE 'optional' END"
            )

    Base.metadata.create_all(bind=connection)
    checklist_table = sa.Table(
        "checklist_items",
        sa.MetaData(),
        autoload_with=connection,
    )
    existing_codes = set(
        connection.scalars(sa.select(checklist_table.c.code)).all()
    )
    for code, label, category, classification, applicability, is_sensitive in CHECKLIST_ITEMS:
        if code in existing_codes:
            continue
        values = {
            "code": code,
            "label": label,
            "category": category,
            "classification": classification,
            "applicability": applicability,
            "is_active": True,
            "is_sensitive": is_sensitive,
        }
        if "is_required" in checklist_table.c:
            values["is_required"] = False
        connection.execute(checklist_table.insert().values(**values))

    if "teacher_checklist_requirements" in set(sa.inspect(connection).get_table_names()):
        legacy_status = (
            "CASE WHEN checklist_items.is_required = 1 THEN 'required' "
            "WHEN checklist_items.classification = 'optional' THEN 'optional' "
            "ELSE 'review' END"
            if had_legacy_required
            else "CASE WHEN checklist_items.classification = 'optional' "
            "THEN 'optional' ELSE 'review' END"
        )
        connection.execute(
            sa.text(
                "INSERT INTO teacher_checklist_requirements "
                "(teacher_id, checklist_item_id, status, reviewed_by, reviewed_at) "
                "SELECT teachers.id, checklist_items.id, "
                + legacy_status
                + ", NULL, NULL FROM teachers CROSS JOIN checklist_items "
                "WHERE NOT EXISTS (SELECT 1 FROM teacher_checklist_requirements "
                "WHERE teacher_checklist_requirements.teacher_id = teachers.id "
                "AND teacher_checklist_requirements.checklist_item_id = checklist_items.id)"
            )
        )


def downgrade() -> None:
    raise NotImplementedError("This data-preserving migration is not reversible.")
