from datetime import datetime

from flask import Blueprint, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import false, func

from extensions import db
from models import (
    Answer,
    AnswerOption,
    Option,
    Question,
    Response,
    Survey,
    generate_share_key,
)


surveys_bp = Blueprint("surveys", __name__, url_prefix="/surveys")

SURVEY_ACCESS_MODES = {"private", "by_key"}


def _current_user_id():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


def _generate_unique_survey_share_key():
    while True:
        share_key = generate_share_key()
        if not Survey.query.filter_by(share_key=share_key).first():
            return share_key


def _serialize_survey(survey, include_private=False):
    data = {
        "id": survey.id,
        "title": survey.title,
        "subject": survey.subject,
        "description": survey.description,
        "status": survey.status,
    }

    if include_private:
        data["share_key"] = survey.share_key
        data["access_mode"] = survey.access_mode

    return data


def _serialize_survey_take_payload(survey):
    questions_data = []

    for question in sorted(survey.question, key=lambda item: item.sequence):
        options = sorted(question.options, key=lambda item: item.position)
        questions_data.append(
            {
                "id": question.id,
                "text": question.text,
                "type": question.type,
                "sequence": question.sequence,
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "position": option.position,
                    }
                    for option in options
                ],
            }
        )

    return {
        "id": survey.id,
        "title": survey.title,
        "subject": survey.subject,
        "description": survey.description,
        "share_key": survey.share_key,
        "questions": questions_data,
    }


def _resolve_access_mode(value):
    if value is None:
        return None

    normalized = value.strip()
    if normalized not in SURVEY_ACCESS_MODES:
        raise ValueError("Invalid access mode")

    return normalized


def _get_survey_for_share_key(share_key):
    return Survey.query.filter_by(
        share_key=share_key,
        status="published",
        access_mode="by_key",
    ).first()


def _submit_survey_response(survey, user_id, data):
    answers_data = data.get("answers")
    if not isinstance(answers_data, list) or not answers_data:
        return {"error": "Invalid or empty answers list"}, 400

    if user_id is not None:
        existing = Response.query.filter_by(survey_id=survey.id, user_id=user_id).first()
        if existing:
            return {"error": "You have already submitted this survey"}, 400

    response = Response(survey_id=survey.id, user_id=user_id)
    db.session.add(response)
    db.session.flush()

    for answer_data in answers_data:
        question_id = answer_data.get("question_id")
        question = Question.query.get(question_id)
        if not question or question.survey_id != survey.id:
            db.session.rollback()
            return {"error": f"Question {question_id} not found in this survey"}, 400

        answer = Answer(response_id=response.id, question_id=question_id)

        if question.type == "text":
            text_answer = answer_data.get("text_answer")
            if not text_answer:
                db.session.rollback()
                return {"error": f"Text answer required for question {question_id}"}, 400
            answer.text_answer = text_answer
            db.session.add(answer)

        elif question.type == "single":
            option_ids = answer_data.get("option_ids")
            if not option_ids or len(option_ids) != 1:
                db.session.rollback()
                return {"error": f"Single choice question {question_id} requires exactly 1 option"}, 400

            option = Option.query.filter_by(id=option_ids[0], question_id=question_id).first()
            if not option:
                db.session.rollback()
                return {"error": f"Invalid option {option_ids[0]} for question {question_id}"}, 400

            db.session.add(answer)
            db.session.flush()
            db.session.add(AnswerOption(answer_id=answer.id, option_id=option.id))

        elif question.type == "multiple":
            option_ids = answer_data.get("option_ids")
            if not option_ids or not isinstance(option_ids, list):
                db.session.rollback()
                return {"error": f"Multiple choice question {question_id} requires option_ids list"}, 400

            db.session.add(answer)
            db.session.flush()
            for option_id in option_ids:
                option = Option.query.filter_by(id=option_id, question_id=question_id).first()
                if not option:
                    db.session.rollback()
                    return {"error": f"Invalid option {option_id} for question {question_id}"}, 400
                db.session.add(AnswerOption(answer_id=answer.id, option_id=option.id))

        else:
            db.session.rollback()
            return {"error": f"Unknown question type for question {question_id}"}, 400

    db.session.commit()
    return {"message": "Response submitted successfully"}, 201


@surveys_bp.post("/")
@jwt_required()
def create_survey():
    user_id = _current_user_id()
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    subject = (data.get("subject") or "").strip()
    description = (data.get("description") or "").strip()

    if not title:
        return {"error": "Title is required"}, 400
    if not subject:
        return {"error": "Subject is required"}, 400

    try:
        access_mode = _resolve_access_mode(data.get("access_mode")) or "by_key"
    except ValueError:
        return {"error": "Invalid access mode"}, 400

    survey = Survey(
        title=title,
        subject=subject,
        description=description,
        share_key=_generate_unique_survey_share_key(),
        access_mode=access_mode,
        author_id=user_id,
    )
    db.session.add(survey)
    db.session.commit()

    return jsonify(_serialize_survey(survey, include_private=True)), 201


@surveys_bp.get("/<int:survey_id>")
@jwt_required()
def get_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    return jsonify(_serialize_survey(survey, include_private=True))


@surveys_bp.put("/<int:survey_id>")
@jwt_required()
def update_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404
    if survey.status != "draft":
        return {"error": "Only draft surveys can be edited"}, 400

    data = request.get_json(silent=True) or {}

    title = data.get("title")
    subject = data.get("subject")
    description = data.get("description")

    if title is not None:
        title = title.strip()
        if not title:
            return {"error": "Title cannot be empty"}, 400
        survey.title = title

    if subject is not None:
        subject = subject.strip()
        if not subject:
            return {"error": "Subject cannot be empty"}, 400
        survey.subject = subject

    if description is not None:
        survey.description = description.strip()

    if "access_mode" in data:
        try:
            survey.access_mode = _resolve_access_mode(data.get("access_mode"))
        except ValueError:
            return {"error": "Invalid access mode"}, 400

    db.session.commit()

    return jsonify(_serialize_survey(survey, include_private=True))


@surveys_bp.delete("/<int:survey_id>")
@jwt_required()
def delete_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404
    if survey.status != "draft":
        return {"error": "Only draft surveys can be deleted"}, 400

    responses = Response.query.filter_by(survey_id=survey.id).all()
    for response in responses:
        answers = Answer.query.filter_by(response_id=response.id).all()
        for answer in answers:
            AnswerOption.query.filter_by(answer_id=answer.id).delete()
            db.session.delete(answer)
        db.session.delete(response)

    questions = Question.query.filter_by(survey_id=survey.id).all()
    for question in questions:
        Option.query.filter_by(question_id=question.id).delete()
        db.session.delete(question)

    db.session.delete(survey)
    db.session.commit()
    return {"message": "Survey deleted"}


@surveys_bp.post("/<int:survey_id>/publish")
@jwt_required()
def publish_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404
    if survey.status != "draft":
        return {"error": "Only draft surveys can be published"}, 400

    survey.status = "published"
    survey.published_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        {
            "id": survey.id,
            "subject": survey.subject,
            "share_key": survey.share_key,
            "access_mode": survey.access_mode,
            "status": survey.status,
            "published_at": survey.published_at,
        }
    )


@surveys_bp.post("/<int:survey_id>/close")
@jwt_required()
def close_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404
    if survey.status != "published":
        return {"error": "Only published surveys can be closed"}, 400

    survey.status = "closed"
    survey.closed_at = datetime.utcnow()
    db.session.commit()

    return jsonify(
        {
            "id": survey.id,
            "subject": survey.subject,
            "share_key": survey.share_key,
            "access_mode": survey.access_mode,
            "status": survey.status,
            "closed_at": survey.closed_at,
        }
    )


@surveys_bp.get("/<int:survey_id>/take")
@jwt_required()
def take_survey(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404

    return jsonify(_serialize_survey_take_payload(survey))


@surveys_bp.get("/access/<string:share_key>")
@jwt_required(optional=True)
def access_survey_by_key(share_key):
    survey = _get_survey_for_share_key(share_key)
    if not survey:
        return {"error": "Survey not found or not available by key"}, 404

    return jsonify(_serialize_survey_take_payload(survey))


@surveys_bp.post("/<int:survey_id>/responses")
@jwt_required()
def submit_response(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, status="published").first()
    if not survey:
        return {"error": "Survey not found or not published"}, 404

    data = request.get_json(silent=True) or {}
    payload, status_code = _submit_survey_response(survey, user_id, data)
    return payload, status_code


@surveys_bp.post("/access/<string:share_key>/responses")
@jwt_required(optional=True)
def submit_response_by_key(share_key):
    survey = _get_survey_for_share_key(share_key)
    if not survey:
        return {"error": "Survey not found or not available by key"}, 404

    data = request.get_json(silent=True) or {}
    payload, status_code = _submit_survey_response(survey, _current_user_id(), data)
    return payload, status_code


@surveys_bp.get("/<int:survey_id>/stats")
@jwt_required()
def survey_stats(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    respondents_count = db.session.query(func.count(Response.id)).filter(Response.survey_id == survey_id).scalar()
    questions_stats = []

    for question in survey.questions:
        if question.type in ("single", "multiple"):
            total = respondents_count if respondents_count else 1
            options_data = []
            for option in question.options:
                count = (
                    db.session.query(func.count(AnswerOption.answer_id))
                    .join(Answer)
                    .filter(
                        AnswerOption.option_id == option.id,
                        Answer.question_id == question.id,
                        Answer.response_id == Response.id,
                        Response.survey_id == survey_id,
                    )
                    .scalar()
                )
                percent = round((count / total) * 100, 2)
                options_data.append(
                    {
                        "option_id": option.id,
                        "text": option.text,
                        "count": count,
                        "percent": percent,
                    }
                )

            questions_stats.append(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "type": question.type,
                    "options": options_data,
                }
            )

        elif question.type == "text":
            answers = (
                Answer.query.join(Response)
                .filter(
                    Answer.question_id == question.id,
                    Response.survey_id == survey_id,
                )
                .all()
            )
            text_answers = [answer.text_answer for answer in answers if answer.text_answer]
            questions_stats.append(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "type": "text",
                    "text_answers": text_answers,
                }
            )

    return jsonify(
        {
            "survey_id": survey.id,
            "title": survey.title,
            "subject": survey.subject,
            "share_key": survey.share_key,
            "access_mode": survey.access_mode,
            "status": survey.status,
            "respondents_count": respondents_count,
            "questions_stats": questions_stats,
        }
    )


@surveys_bp.get("/<int:survey_id>/export")
@jwt_required()
def export_survey_results(survey_id):
    user_id = _current_user_id()
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    respondents_count = db.session.query(func.count(Response.id)).filter(Response.survey_id == survey_id).scalar()
    questions_stats = []

    for question in survey.questions:
        if question.type in ("single", "multiple"):
            total = respondents_count if respondents_count else 1
            options_data = []
            for option in question.options:
                count = (
                    db.session.query(func.count(AnswerOption.answer_id))
                    .join(Answer)
                    .filter(
                        AnswerOption.option_id == option.id,
                        Answer.question_id == question.id,
                        Answer.response_id == Response.id,
                        Response.survey_id == survey_id,
                    )
                    .scalar()
                )
                percent = round((count / total) * 100, 2)
                options_data.append(
                    {
                        "option_id": option.id,
                        "text": option.text,
                        "count": count,
                        "percent": percent,
                    }
                )

            questions_stats.append(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "type": question.type,
                    "options": options_data,
                }
            )

        elif question.type == "text":
            answers = (
                Answer.query.join(Response)
                .filter(
                    Answer.question_id == question.id,
                    Response.survey_id == survey_id,
                )
                .all()
            )
            text_answers = [answer.text_answer for answer in answers if answer.text_answer]
            questions_stats.append(
                {
                    "question_id": question.id,
                    "text": question.text,
                    "type": "text",
                    "text_answers": text_answers,
                }
            )

    data = {
        "survey_id": survey.id,
        "title": survey.title,
        "subject": survey.subject,
        "share_key": survey.share_key,
        "access_mode": survey.access_mode,
        "status": survey.status,
        "respondents_count": respondents_count,
        "questions_stats": questions_stats,
    }

    if request.args.get("download") == "true":
        response = make_response(jsonify(data))
        response.headers["Content-Disposition"] = f"attachment; filename=survey_{survey.id}_results.json"
        response.headers["Content-Type"] = "application/json"
        return response

    return jsonify(data)


@surveys_bp.get("/")
@jwt_required(optional=True)
def list_surveys():
    user_id = _current_user_id()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    filter_param = request.args.get("filter")
    subject = request.args.get("subject", type=str)
    sort_by = request.args.get("sort_by", "date")
    order = request.args.get("order", "desc")

    surveys_query = Survey.query

    if user_id is None:
        surveys_query = surveys_query.filter(false())
    else:
        surveys_query = surveys_query.filter(Survey.author_id == user_id)

        if filter_param == "active":
            surveys_query = surveys_query.filter(Survey.status == "published")
        elif filter_param == "closed":
            surveys_query = surveys_query.filter(Survey.status == "closed")
        elif filter_param in (None, "my"):
            pass

    if subject:
        surveys_query = surveys_query.filter(Survey.subject == subject.strip())

    if sort_by == "date":
        surveys_query = surveys_query.order_by(
            Survey.created_at.desc() if order == "desc" else Survey.created_at.asc()
        )
    elif sort_by == "responses":
        surveys_query = (
            surveys_query
            .outerjoin(Response)
            .group_by(Survey.id)
            .order_by(func.count(Response.id).desc() if order == "desc" else func.count(Response.id))
        )

    pagination = surveys_query.paginate(page=page, per_page=per_page, error_out=False)

    surveys = []
    for survey in pagination.items:
        item = _serialize_survey(survey, include_private=True)
        item["created_at"] = survey.created_at.isoformat()
        item["response_count"] = getattr(survey, "response_count", None)
        surveys.append(item)

    return jsonify(
        {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "surveys": surveys,
        }
    )
