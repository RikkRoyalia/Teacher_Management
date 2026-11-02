from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ChecklistItem,
    EmploymentContract,
    EvidenceDocument,
    Qualification,
    Teacher,
    TeacherChecklistRequirement,
    WorkHistory,
)

MINIMUM_ANOMALY_PROFILES = 20
ANOMALY_FEATURE_LABELS = (
    "Số bằng cấp/chứng chỉ",
    "Số chứng chỉ",
    "Số tài liệu minh chứng",
    "Số hợp đồng",
    "Số giai đoạn công tác",
    "Số tài liệu bắt buộc còn thiếu",
    "Số điều kiện checklist chưa rà soát",
)


def default_checklist_status(item: ChecklistItem) -> str:
    return "optional" if item.classification == "optional" else "review"


def teacher_completeness(
    db: Session,
    teacher: Teacher,
) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    needs_review: list[str] = []
    if not teacher.employee_code:
        missing.append("Mã giảng viên")
    if not teacher.full_name:
        missing.append("Họ và tên")
    if teacher.department_id is None:
        missing.append("Đơn vị công tác")
    requirements = db.execute(
        select(ChecklistItem, TeacherChecklistRequirement.status)
        .outerjoin(
            TeacherChecklistRequirement,
            (TeacherChecklistRequirement.checklist_item_id == ChecklistItem.id)
            & (TeacherChecklistRequirement.teacher_id == teacher.id),
        )
        .where(ChecklistItem.is_active.is_(True))
    )
    uploaded_item_ids = set(
        db.scalars(
            select(EvidenceDocument.checklist_item_id).where(
                EvidenceDocument.teacher_id == teacher.id,
                EvidenceDocument.checklist_item_id.is_not(None),
            )
        )
    )
    for item, status in requirements:
        requirement_status = status or default_checklist_status(item)
        if requirement_status == "review":
            needs_review.append(item.label)
        elif requirement_status == "required" and item.id not in uploaded_item_ids:
            missing.append(item.label)
    return missing, needs_review


def missing_requirements(db: Session, teacher: Teacher) -> list[str]:
    missing, needs_review = teacher_completeness(db, teacher)
    return missing + [f"Cần rà soát điều kiện: {label}" for label in needs_review]


def _anomaly_explanations(features: np.ndarray, population: np.ndarray) -> list[str]:
    medians = np.median(population, axis=0)
    lower = np.percentile(population, 25, axis=0)
    upper = np.percentile(population, 75, axis=0)
    deviations: list[tuple[float, str]] = []
    for index, value in enumerate(features):
        difference = float(value - medians[index])
        if difference == 0:
            continue
        scale = max(float(upper[index] - lower[index]), 1.0)
        direction = "cao" if difference > 0 else "thấp"
        deviations.append(
            (
                abs(difference) / scale,
                f'{ANOMALY_FEATURE_LABELS[index]} {direction} hơn mức giữa của tập hồ sơ',
            )
        )
    deviations.sort(reverse=True)
    return [reason for _, reason in deviations[:3]]


def review_profiles(
    db: Session,
    warning_days: int,
    teacher_id: int | None = None,
) -> dict[str, Any]:
    teachers = list(db.scalars(select(Teacher).order_by(Teacher.id)))
    teacher_ids = [teacher.id for teacher in teachers]
    if not teacher_ids:
        return {
            "model": {
                "status": "insufficient_data",
                "message": f"Cần ít nhất {MINIMUM_ANOMALY_PROFILES} hồ sơ để chạy rà soát bất thường.",
                "profile_count": 0,
            },
            "items": [],
        }

    qualifications_by_teacher: dict[int, list[Qualification]] = defaultdict(list)
    for qualification in db.scalars(
        select(Qualification).where(Qualification.teacher_id.in_(teacher_ids))
    ):
        qualifications_by_teacher[qualification.teacher_id].append(qualification)

    document_counts = dict(
        db.execute(
            select(EvidenceDocument.teacher_id, func.count(EvidenceDocument.id))
            .where(EvidenceDocument.teacher_id.in_(teacher_ids))
            .group_by(EvidenceDocument.teacher_id)
        ).all()
    )
    contract_counts = dict(
        db.execute(
            select(EmploymentContract.teacher_id, func.count(EmploymentContract.id))
            .where(EmploymentContract.teacher_id.in_(teacher_ids))
            .group_by(EmploymentContract.teacher_id)
        ).all()
    )
    history_counts = dict(
        db.execute(
            select(WorkHistory.teacher_id, func.count(WorkHistory.id))
            .where(WorkHistory.teacher_id.in_(teacher_ids))
            .group_by(WorkHistory.teacher_id)
        ).all()
    )

    today = date.today()
    warning_end = today + timedelta(days=warning_days)
    review_rows: list[dict[str, Any]] = []
    feature_rows: list[list[float]] = []
    for teacher in teachers:
        missing, needs_review = teacher_completeness(db, teacher)
        qualifications = qualifications_by_teacher[teacher.id]
        uploaded_item_ids = set(
            db.scalars(
                select(EvidenceDocument.checklist_item_id).where(
                    EvidenceDocument.teacher_id == teacher.id,
                    EvidenceDocument.checklist_item_id.is_not(None),
                )
            )
        )
        requirements = db.execute(
            select(ChecklistItem, TeacherChecklistRequirement.status)
            .outerjoin(
                TeacherChecklistRequirement,
                (TeacherChecklistRequirement.checklist_item_id == ChecklistItem.id)
                & (TeacherChecklistRequirement.teacher_id == teacher.id),
            )
            .where(ChecklistItem.is_active.is_(True))
            .order_by(ChecklistItem.category, ChecklistItem.label)
        )
        suggestions: list[str] = []
        for item, status in requirements:
            requirement_status = status or default_checklist_status(item)
            if requirement_status == "optional" and item.id not in uploaded_item_ids:
                suggestions.append(item.label)

        invalid_data: list[dict[str, str]] = []
        expiring_certificates: list[dict[str, Any]] = []
        certificate_count = 0
        for qualification in qualifications:
            if qualification.qualification_type == "certificate":
                certificate_count += 1
                if (
                    qualification.issued_on
                    and qualification.expires_on
                    and qualification.expires_on < qualification.issued_on
                ):
                    invalid_data.append(
                        {
                            "item": qualification.title,
                            "message": "Ngày hết hạn trước ngày cấp.",
                        }
                    )
                if qualification.expires_on and qualification.expires_on <= warning_end:
                    expiring_certificates.append(
                        {
                            "qualification_id": qualification.id,
                            "title": qualification.title,
                            "expires_on": qualification.expires_on,
                            "days_remaining": (qualification.expires_on - today).days,
                            "status": (
                                "expired" if qualification.expires_on < today else "expiring"
                            ),
                        }
                    )

        findings: list[dict[str, Any]] = []
        findings.extend(
            {"type": "missing_required_document", "message": label}
            for label in missing
        )
        findings.extend(
            {"type": "checklist_review", "message": label}
            for label in needs_review
        )
        findings.extend(
            {"type": "invalid_data", **item}
            for item in invalid_data
        )
        findings.extend(
            {
                "type": "certificate_expiry",
                **item,
                "message": (
                    f'{item["title"]}: '
                    + (
                        f'đã hết hạn {abs(item["days_remaining"])} ngày.'
                        if item["status"] == "expired"
                        else f'còn {item["days_remaining"]} ngày sẽ hết hạn.'
                    )
                ),
            }
            for item in expiring_certificates
        )
        findings.extend(
            {"type": "optional_suggestion", "message": label}
            for label in suggestions
        )
        review_rows.append(
            {
                "teacher_id": teacher.id,
                "employee_code": teacher.employee_code,
                "teacher_name": teacher.full_name,
                "missing": missing,
                "needs_review": needs_review,
                "invalid_data": invalid_data,
                "expiring_certificates": expiring_certificates,
                "suggestions": suggestions,
                "anomaly": None,
                "findings": findings,
            }
        )
        feature_rows.append(
            [
                float(len(qualifications)),
                float(certificate_count),
                float(document_counts.get(teacher.id, 0)),
                float(contract_counts.get(teacher.id, 0)),
                float(history_counts.get(teacher.id, 0)),
                float(len(missing)),
                float(len(needs_review)),
            ]
        )

    model_info: dict[str, Any]
    population = np.asarray(feature_rows, dtype=float)
    if len(teachers) < MINIMUM_ANOMALY_PROFILES:
        model_info = {
            "status": "insufficient_data",
            "message": f"Cần ít nhất {MINIMUM_ANOMALY_PROFILES} hồ sơ để chạy rà soát bất thường.",
            "profile_count": len(teachers),
        }
    elif len({tuple(row) for row in feature_rows}) < 2:
        model_info = {
            "status": "insufficient_variation",
            "message": "Dữ liệu hồ sơ hiện tại chưa có đủ khác biệt để so sánh bất thường.",
            "profile_count": len(teachers),
        }
    else:
        model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=0,
        )
        predictions = model.fit_predict(population)
        scores = model.decision_function(population)
        for row, features, prediction, score in zip(
            review_rows, population, predictions, scores, strict=True
        ):
            if prediction != -1:
                continue
            reasons = _anomaly_explanations(features, population)
            anomaly = {
                "score": round(float(score), 6),
                "reasons": reasons,
            }
            row["anomaly"] = anomaly
            row["findings"].append(
                {
                    "type": "profile_anomaly",
                    "message": "Tổ hợp chỉ số hồ sơ khác biệt so với dữ liệu hiện có; cần HR kiểm tra, không phải kết luận hồ sơ sai.",
                    "score": anomaly["score"],
                    "reasons": reasons,
                }
            )
        model_info = {
            "status": "ready",
            "message": "Cờ bất thường chỉ là gợi ý thống kê để HR kiểm tra.",
            "profile_count": len(teachers),
        }

    items = [
        row
        for row in review_rows
        if (teacher_id is not None and row["teacher_id"] == teacher_id)
        or (teacher_id is None and row["findings"])
    ]
    return {"model": model_info, "items": items}
