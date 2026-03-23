from flask import Blueprint, request, jsonify
from extensions import db
from datetime import datetime
from models import User, Survey, Question, Option
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)



questions_bp = Blueprint("questions", __name__, url_prefix="/questions")



@questions_bp.get("/<int:question_id>/options")
@jwt_required()
def get_options(question_id):
    question = Question.query.get(question_id)
    if not question:
        return {"error": "Question not found"}, 404
    return jsonify([{"id": o.id, "text": o.text, "position": o.position} for o in question.options])

@questions_bp.route("/<int:question_id>/options", methods=["POST"])
@jwt_required()
def add_option(question_id):
    question = Question.query.get(question_id)

    if not question:
        return jsonify({"error": "Question not found"}), 404

    if question.type == "text":
        return jsonify({"error": "Text questions cannot have options"}), 400
    
    if question.survey.status != "draft":
        return jsonify({"error": "Cannot modify options in non-draft survey"}), 400

    data = request.get_json()

    text = data.get("text")
    position = data.get("position")

    if not text or position is None:
        return jsonify({"error": "text and position required"}), 400

    option = Option(
        question_id=question.id,
        text=text,
        position=position
    )

    try:
        db.session.add(option)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Position already exists"}), 400

    return jsonify({
        "id": option.id,
        "text": option.text,
        "position": option.position
    }), 201

@questions_bp.post("/<int:survey_id>")
@jwt_required()
def add_question(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    if survey.status != "draft":
        return {"error": "Cannot add question to non-draft survey"}, 400

    data = request.get_json()
    text = data.get("text")
    q_type = data.get("type")
    sequence = data.get("sequence")

    if not text or not q_type or sequence is None:
        return {"error": "text, type and sequence are required"}, 400

    if q_type not in ["single", "multiple", "text"]:
        return {"error": "Invalid question type"}, 400

    question = Question(
        survey_id=survey_id,
        text=text,
        type=q_type,
        sequence=sequence
    )
    db.session.add(question)
    db.session.commit()

    return jsonify({
        "id": question.id,
        "survey_id": question.survey_id,
        "text": question.text,
        "type": question.type,
        "sequence": question.sequence
    }), 201

@questions_bp.get("/<int:survey_id>")
@jwt_required()
def get_questions(survey_id):
    user_id = int(get_jwt_identity())
    survey = Survey.query.filter_by(id=survey_id, author_id=user_id).first()
    if not survey:
        return {"error": "Survey not found"}, 404

    questions = Question.query.filter_by(survey_id=survey_id).order_by(Question.sequence).all()
    return jsonify([{
        "id": q.id,
        "text": q.text,
        "type": q.type,
        "sequence": q.sequence
    } for q in questions])

@questions_bp.put("/<int:question_id>")
@jwt_required()
def update_question(question_id):
    user_id = int(get_jwt_identity())
    question = Question.query.get(question_id)
    if not question or question.survey.author_id != user_id:
        return {"error": "Question not found"}, 404

    if question.survey.status != "draft":
        return {"error": "Cannot edit question in non-draft survey"}, 400

    data = request.get_json()
    question.text = data.get("text", question.text)
    q_type = data.get("type")
    if q_type in ["single", "multiple", "text"]:
        question.type = q_type
    sequence = data.get("sequence")
    if sequence is not None:
        question.sequence = sequence

    db.session.commit()
    return jsonify({
        "id": question.id,
        "text": question.text,
        "type": question.type,
        "sequence": question.sequence
    })

@questions_bp.delete("/<int:question_id>")
@jwt_required()
def delete_question(question_id):
    user_id = int(get_jwt_identity())
    question = Question.query.get(question_id)
    if not question or question.survey.author_id != user_id:
        return {"error": "Question not found"}, 404

    if question.survey.status != "draft":
        return {"error": "Cannot delete question from non-draft survey"}, 400

    db.session.delete(question)
    db.session.commit()
    return {"message": "Question deleted"}

