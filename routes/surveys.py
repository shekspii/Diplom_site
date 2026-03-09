# surveys.py
from flask import Blueprint, request, jsonify
from extensions import db
from models import Survey
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

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

@surveys_bp.get("/")
@jwt_required()
def get_surveys():
    user_id = int(get_jwt_identity())
    surveys = Survey.query.filter_by(author_id=user_id).all()
    return jsonify([{
        "id": s.id,
        "title": s.title,
        "description": s.description,
        "status": s.status
    } for s in surveys])

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
