from functools import wraps

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from extensions import db
from models import (
    QuestionBankItem,
    QuestionBankOption,
    Response,
    Survey,
    TestSession,
    User,
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
QUESTION_TYPES = {"single", "multiple", "text"}


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(int(user_id))

        if not user or user.role != "admin":
            return {"error": "Доступ разрешен только администратору."}, 403

        return fn(*args, **kwargs)

    return wrapper


def _get_admin_user():
    user_id = get_jwt_identity()
    return User.query.get(int(user_id))


def _serialize_bank_question(question):
    return {
        "id": question.id,
        "subject": question.subject,
        "exam_task_number": question.exam_task_number,
        "correct_text_answer": question.correct_text_answer,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "text": question.text,
        "type": question.type,
        "is_active": question.is_active,
        "created_by": question.created_by,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
        "options": [
            {
                "id": option.id,
                "text": option.text,
                "position": option.position,
                "is_correct": option.is_correct,
            }
            for option in sorted(question.options, key=lambda item: item.position)
        ],
    }


@admin_bp.get("/overview")
@admin_required
def admin_overview():
    users_count = db.session.query(func.count(User.id)).scalar()
    admins_count = db.session.query(func.count(User.id)).filter(User.role == "admin").scalar()
    surveys_count = db.session.query(func.count(Survey.id)).scalar()
    published_surveys_count = (
        db.session.query(func.count(Survey.id))
        .filter(Survey.status == "published")
        .scalar()
    )
    responses_count = db.session.query(func.count(Response.id)).scalar()
    bank_questions_count = db.session.query(func.count(QuestionBankItem.id)).scalar()
    active_bank_questions_count = (
        db.session.query(func.count(QuestionBankItem.id))
        .filter(QuestionBankItem.is_active.is_(True))
        .scalar()
    )
    test_sessions_count = db.session.query(func.count(TestSession.id)).scalar()

    recent_surveys = (
        Survey.query.order_by(Survey.created_at.desc()).limit(5).all()
    )
    recent_users = (
        User.query.order_by(User.created_at.desc()).limit(5).all()
    )

    return {
        "stats": {
            "users_count": users_count,
            "admins_count": admins_count,
            "surveys_count": surveys_count,
            "published_surveys_count": published_surveys_count,
            "responses_count": responses_count,
            "bank_questions_count": bank_questions_count,
            "active_bank_questions_count": active_bank_questions_count,
            "test_sessions_count": test_sessions_count,
        },
        "recent_surveys": [
            {
                "id": survey.id,
                "title": survey.title,
                "subject": survey.subject,
                "status": survey.status,
                "share_key": survey.share_key,
                "created_at": survey.created_at.isoformat(),
            }
            for survey in recent_surveys
        ],
        "recent_users": [
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
            }
            for user in recent_users
        ],
    }


@admin_bp.get("/question-bank")
@admin_required
def list_question_bank():
    subject = request.args.get("subject", type=str)

    query = QuestionBankItem.query.order_by(
        QuestionBankItem.created_at.desc(),
        QuestionBankItem.id.desc(),
    )

    if subject:
        query = query.filter(QuestionBankItem.subject == subject.strip())

    questions = query.all()

    return {
        "items": [_serialize_bank_question(question) for question in questions]
    }


@admin_bp.post("/question-bank")
@admin_required
def create_question_bank_item():
    admin_user = _get_admin_user()
    data = request.get_json(silent=True) or {}

    subject = (data.get("subject") or "").strip()
    exam_task_number = data.get("exam_task_number")
    text = (data.get("text") or "").strip()
    question_type = (data.get("type") or "").strip()
    correct_text_answer = (data.get("correct_text_answer") or "").strip() or None
    topic = (data.get("topic") or "").strip() or None
    difficulty = (data.get("difficulty") or "").strip() or None
    is_active = bool(data.get("is_active", True))
    options_data = data.get("options") or []

    if not subject:
        return {"error": "Subject is required"}, 400
    if not isinstance(exam_task_number, int) or not 1 <= exam_task_number <= 100:
        return {"error": "Exam task number must be an integer between 1 and 100"}, 400
    if not text:
        return {"error": "Question text is required"}, 400
    if question_type not in QUESTION_TYPES:
        return {"error": "Invalid question type"}, 400

    normalized_options = []
    if question_type in {"single", "multiple"}:
        if not isinstance(options_data, list) or len(options_data) < 2:
            return {"error": "Choice questions require at least two options"}, 400

        for index, option in enumerate(options_data, start=1):
            option_text = (option.get("text") or "").strip()
            if not option_text:
                return {"error": f"Option #{index} text is required"}, 400

            normalized_options.append(
                {
                    "text": option_text,
                    "is_correct": bool(option.get("is_correct")),
                    "position": index,
                }
            )

        correct_count = sum(1 for option in normalized_options if option["is_correct"])
        if question_type == "single" and correct_count != 1:
            return {"error": "Single choice question must have exactly one correct option"}, 400
        if question_type == "multiple" and correct_count < 1:
            return {"error": "Multiple choice question must have at least one correct option"}, 400
    else:
        if not correct_text_answer:
            return {"error": "Text question must have a correct text answer"}, 400
        normalized_options = []

    question = QuestionBankItem(
        subject=subject,
        exam_task_number=exam_task_number,
        correct_text_answer=correct_text_answer if question_type == "text" else None,
        topic=topic,
        difficulty=difficulty,
        text=text,
        type=question_type,
        is_active=is_active,
        created_by=admin_user.id,
    )
    db.session.add(question)
    db.session.flush()

    for option in normalized_options:
        db.session.add(
            QuestionBankOption(
                question_id=question.id,
                text=option["text"],
                position=option["position"],
                is_correct=option["is_correct"],
            )
        )

    db.session.commit()
    question = QuestionBankItem.query.get(question.id)

    return _serialize_bank_question(question), 201
