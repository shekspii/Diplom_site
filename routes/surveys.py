from flask import Blueprint, request, jsonify, make_response
from extensions import db
from models import Survey, User, Answer, Question, Option, Response, AnswerOption
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func
surveys_bp = Blueprint("surveys", __name__, url_prefix="/surveys")

@surveys_bp.post("/")
@jwt_required()
def create_survey():
    user_id = int(get_jwt_identity())  # авторизация пользователя
    data = request.get_json()
    title = data.get("title")
    description = data.get("description", "")

    if not title:
        return {"error": "Title is required"}, 400

    survey = Survey(title=title, description=description, author_id=user_id)
    db.session.add(survey)
    db.session.commit()

    return jsonify({
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "status": survey.status
    }), 201


@surveys_bp.get("/<int:survey_id>")
@jwt_required()
def get_survey(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    return jsonify({
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "status": survey.status
    })

@surveys_bp.put("/<int:survey_id>")
@jwt_required()
def update_survey(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404

    if survey.status != "draft":
        return {"error": "Only draft surveys can be edited"}, 400

    data = request.get_json()
    survey.title = data.get("title", survey.title)
    survey.description = data.get("description", survey.description)
    db.session.commit()

    return jsonify({
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "status": survey.status
    })

@surveys_bp.delete("/<int:survey_id>")
@jwt_required()
def delete_survey(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404

    db.session.delete(survey)
    db.session.commit()
    return {"message": "Survey deleted"}


@surveys_bp.post("/<int:survey_id>/publish")
@jwt_required()
def publish_survey(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404

    if survey.status != "draft":
        return {"error": "Only draft surveys can be published"}, 400

    survey.status = "published"
    survey.published_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "id": survey.id,
        "status": survey.status,
        "published_at": survey.published_at
    })

@surveys_bp.post("/<int:survey_id>/close")
@jwt_required()
def close_survey(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()

    if not survey:
        return {"error": "Survey not found"}, 404

    if survey.status != "published":
        return {"error": "Only published surveys can be closed"}, 400

    survey.status = "closed"
    survey.closed_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "id": survey.id,
        "status": survey.status,
        "closed_at": survey.closed_at
    })

@surveys_bp.get("/<int:survey_id>/take")
@jwt_required()
def take_survey(survey_id):

    survey = Survey.query.filter_by(id=survey_id, status="published").first()

    if not survey:
        return {"error": "Survey not found or not published"}, 404

    questions_data = []

    for q in sorted(survey.question, key=lambda x: x.sequence):

        options = sorted(q.options, key=lambda x: x.position)

        questions_data.append({
            "id": q.id,
            "text": q.text,
            "type": q.type,
            "sequence": q.sequence,
            "options": [
                {
                    "id": o.id,
                    "text": o.text,
                    "position": o.position
                }
                for o in options
            ]
        })

    return jsonify({
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "questions": questions_data
    })

@surveys_bp.post("/<int:survey_id>/responses")
@jwt_required()
def submit_response(survey_id):
    user_id = int(get_jwt_identity())

    # Только опубликованные опросы
    survey = Survey.query.filter_by(id=survey_id, status="published").first()
    if not survey:
        return {"error": "Survey not found or not published"}, 404

    data = request.get_json()
    answers_data = data.get("answers")
    print(answers_data)
    if not isinstance(answers_data, list) or not answers_data:
        return {"error": "Invalid or empty answers list"}, 400

    # Проверка, что пользователь ещё не отправлял ответы
    existing = Response.query.filter_by(survey_id=survey_id, user_id=user_id).first()
    if existing:
        return {"error": "You have already submitted this survey"}, 400

    # Создаём Response
    response = Response(survey_id=survey_id, user_id=user_id)
    db.session.add(response)
    db.session.flush()  # чтобы получить response.id

    for ans in answers_data:
        question_id = ans.get("question_id")
        question = Question.query.get(question_id)
        if not question or question.survey_id != survey_id:
            db.session.rollback()
            return {"error": f"Question {question_id} not found in this survey"}, 400

        answer = Answer(response_id=response.id, question_id=question_id)

        if question.type == "text":
            text_answer = ans.get("text_answer")
            if not text_answer:
                db.session.rollback()
                return {"error": f"Text answer required for question {question_id}"}, 400
            answer.text_answer = text_answer
            db.session.add(answer)

        elif question.type == "single":
            option_ids = ans.get("option_ids")
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
            option_ids = ans.get("option_ids")
            if not option_ids or not isinstance(option_ids, list):
                db.session.rollback()
                return {"error": f"Multiple choice question {question_id} requires option_ids list"}, 400

            db.session.add(answer)
            db.session.flush()
            for oid in option_ids:
                option = Option.query.filter_by(id=oid, question_id=question_id).first()
                if not option:
                    db.session.rollback()
                    return {"error": f"Invalid option {oid} for question {question_id}"}, 400
                db.session.add(AnswerOption(answer_id=answer.id, option_id=option.id))

        else:
            db.session.rollback()
            return {"error": f"Unknown question type for question {question_id}"}, 400

    db.session.commit()
    return {"message": "Response submitted successfully"}

@surveys_bp.get("/<int:survey_id>/stats")
@jwt_required()
def survey_stats(survey_id):
    # Проверяем, что опрос существует
    survey = Survey.query.get(survey_id)
    if not survey:
        return {"error": "Survey not found"}, 404

    # Подсчёт уникальных респондентов
    respondents_count = db.session.query(func.count(Response.user_id.distinct())) \
        .filter(Response.survey_id == survey_id).scalar()

    questions_stats = []

    for question in survey.questions:
        if question.type in ("single", "multiple"):
            # Статистика для вопросов с выбором
            total = respondents_count if respondents_count else 1
            options_data = []
            for option in question.options:
                count = db.session.query(func.count(AnswerOption.answer_id)) \
                    .join(Answer) \
                    .filter(
                        AnswerOption.option_id == option.id,
                        Answer.question_id == question.id,
                        Answer.response_id == Response.id,
                        Response.survey_id == survey_id
                    ).scalar()
                percent = round((count / total) * 100, 2)
                options_data.append({
                    "option_id": option.id,
                    "text": option.text,
                    "count": count,
                    "percent": percent
                })
            questions_stats.append({
                "question_id": question.id,
                "text": question.text,
                "type": question.type,
                "options": options_data
            })

        elif question.type == "text":
            # Список текстовых ответов
            answers = Answer.query.join(Response) \
                .filter(
                    Answer.question_id == question.id,
                    Response.survey_id == survey_id
                ).all()
            text_answers = [a.text_answer for a in answers if a.text_answer]
            questions_stats.append({
                "question_id": question.id,
                "text": question.text,
                "type": "text",
                "text_answers": text_answers
            })

    return jsonify({
        "survey_id": survey.id,
        "title": survey.title,
        "status": survey.status,
        "respondents_count": respondents_count,
        "questions_stats": questions_stats
    })

@surveys_bp.get("/<int:survey_id>/export")
@jwt_required()
def export_survey_results(survey_id):
    # Получаем опрос
    survey = Survey.query.get(survey_id)
    if not survey:
        return {"error": "Survey not found"}, 404

    # Подсчёт уникальных респондентов
    respondents_count = db.session.query(func.count(Response.user_id.distinct())) \
        .filter(Response.survey_id == survey_id).scalar()

    questions_stats = []

    for question in survey.questions:
        if question.type in ("single", "multiple"):
            total = respondents_count if respondents_count else 1
            options_data = []
            for option in question.options:
                count = db.session.query(func.count(AnswerOption.answer_id)) \
                    .join(Answer) \
                    .filter(
                        AnswerOption.option_id == option.id,
                        Answer.question_id == question.id,
                        Answer.response_id == Response.id,
                        Response.survey_id == survey_id
                    ).scalar()
                percent = round((count / total) * 100, 2)
                options_data.append({
                    "option_id": option.id,
                    "text": option.text,
                    "count": count,
                    "percent": percent
                })
            questions_stats.append({
                "question_id": question.id,
                "text": question.text,
                "type": question.type,
                "options": options_data
            })

        elif question.type == "text":
            answers = Answer.query.join(Response) \
                .filter(
                    Answer.question_id == question.id,
                    Response.survey_id == survey_id
                ).all()
            text_answers = [a.text_answer for a in answers if a.text_answer]
            questions_stats.append({
                "question_id": question.id,
                "text": question.text,
                "type": "text",
                "text_answers": text_answers
            })

    data = {
        "survey_id": survey.id,
        "title": survey.title,
        "status": survey.status,
        "respondents_count": respondents_count,
        "questions_stats": questions_stats
    }

    # Проверяем, хотим ли скачать как файл
    if request.args.get("download") == "true":
        response = make_response(jsonify(data))
        response.headers["Content-Disposition"] = f'attachment; filename=survey_{survey.id}_results.json'
        response.headers["Content-Type"] = "application/json"
        return response

    return jsonify(data)

from flask import request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

@surveys_bp.get("/")
@jwt_required(optional=True)  # Если нужно видеть все опросы без логина
def list_surveys():
    # Получаем user_id из токена (если есть)
    user_id = get_jwt_identity()
    if user_id:
        user_id = int(user_id)

    # Параметры запроса
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    filter_param = request.args.get("filter")  # my, active, closed
    sort_by = request.args.get("sort_by", "date")  # date / responses
    order = request.args.get("order", "desc")      # asc / desc

    # Базовый query
    surveys_query = Survey.query

    # Фильтрация
    if filter_param == "my" and user_id:
        surveys_query = surveys_query.filter(Survey.author_id == user_id)
    elif filter_param == "active":
        surveys_query = surveys_query.filter(Survey.status == "published")
    elif filter_param == "closed":
        surveys_query = surveys_query.filter(Survey.status == "closed")
    else:
        # Если пользователь не залогинен и filter_param нет — показываем только опубликованные
        if not user_id:
            surveys_query = surveys_query.filter(Survey.status == "published")

    # Сортировка
    if sort_by == "date":
        surveys_query = surveys_query.order_by(
            Survey.created_at.desc() if order == "desc" else Survey.created_at.asc()
        )
    elif sort_by == "responses":
        # Считаем количество ответов через outerjoin с Response
        surveys_query = (
            surveys_query
            .outerjoin(Response)
            .group_by(Survey.id)
            .order_by(func.count(Response.id).desc() if order == "desc" else func.count(Response.id))
        )

    # Пагинация
    pagination = surveys_query.paginate(page=page, per_page=per_page, error_out=False)

    # Формируем результат
    surveys = [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "status": s.status,
            "created_at": s.created_at.isoformat(),
            # Добавляем количество ответов, если нужно
            "response_count": getattr(s, "response_count", None)  
        }
        for s in pagination.items
    ]

    return jsonify({
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_pages": pagination.pages,
        "total_items": pagination.total,
        "surveys": surveys
    })