import random
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from models import (
    QuestionBankItem,
    QuestionBankOption,
    TestSession,
    TestSessionQuestion,
    TestSubmission,
    TestSubmissionAnswer,
    TestSubmissionAnswerOption,
)


tests_bp = Blueprint("tests", __name__, url_prefix="/tests")


def _current_user_id():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return int(identity)


def _normalize_text_answer(value):
    return " ".join((value or "").strip().lower().split())


def _group_questions_by_task_number(questions):
    grouped = {}

    for question in questions:
        grouped.setdefault(question.exam_task_number, []).append(question)

    return grouped


def _serialize_selected_option_texts(question, option_ids):
    option_texts = []

    for option in sorted(question.options, key=lambda item: item.position):
        if option.id in option_ids:
            option_texts.append(option.text)

    return option_texts


def _serialize_correct_answer(question):
    if question.type == "text":
        return question.correct_text_answer

    return _serialize_selected_option_texts(
        question,
        {option.id for option in question.options if option.is_correct},
    )


def _serialize_submission_breakdown(session, submission):
    answer_map = {answer.bank_question_id: answer for answer in submission.answers}
    breakdown = []

    for session_question in sorted(session.questions, key=lambda item: item.position):
        question = session_question.bank_question
        answer = answer_map.get(question.id)
        selected_option_ids = set()
        user_answer = None
        is_correct = False
        is_answered = False

        if answer:
            selected_option_ids = {selected.option_id for selected in answer.selected_options}

            if question.type == "text":
                user_answer = answer.text_answer
                is_answered = bool(answer.text_answer)
                is_correct = _normalize_text_answer(answer.text_answer) == _normalize_text_answer(question.correct_text_answer)
            else:
                user_answer = _serialize_selected_option_texts(question, selected_option_ids)
                is_answered = bool(user_answer)
                if question.type == "single":
                    is_correct = any(option.id in selected_option_ids and option.is_correct for option in question.options)
                else:
                    is_correct = selected_option_ids == {option.id for option in question.options if option.is_correct}

        breakdown.append(
            {
                "question_id": question.id,
                "sequence": session_question.position,
                "exam_task_number": question.exam_task_number,
                "text": question.text,
                "type": question.type,
                "is_answered": is_answered,
                "is_correct": is_correct,
                "user_answer": user_answer,
                "correct_answer": _serialize_correct_answer(question),
            }
        )

    return {
        "score": submission.score,
        "total_questions": submission.total_questions,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "breakdown": breakdown,
    }


def _serialize_test_session(session):
    questions = []

    for session_question in sorted(session.questions, key=lambda item: item.position):
        bank_question = session_question.bank_question
        questions.append(
            {
                "id": bank_question.id,
                "text": bank_question.text,
                "type": bank_question.type,
                "sequence": session_question.position,
                "exam_task_number": bank_question.exam_task_number,
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "position": option.position,
                    }
                    for option in sorted(bank_question.options, key=lambda item: item.position)
                ],
            }
        )

    return {
        "id": session.id,
        "title": f"{session.subject} — тренировочный тест",
        "subject": session.subject,
        "description": "Случайно собранный вариант из банка вопросов по выбранному предмету.",
        "status": session.status,
        "requested_count": session.requested_count,
        "source_type": "generated_test",
        "questions": questions,
        "submission": _serialize_submission_breakdown(session, session.submission) if session.submission else None,
    }


@tests_bp.post("/generate")
@jwt_required(optional=True)
def generate_test():
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    requested_count = data.get("question_count")

    if not subject:
        return {"error": "Subject is required"}, 400
    if not isinstance(requested_count, int) or requested_count < 1:
        return {"error": "Question count must be a positive integer"}, 400

    available_questions = (
        QuestionBankItem.query.filter_by(subject=subject, is_active=True).all()
    )

    questions_by_task_number = _group_questions_by_task_number(available_questions)
    missing_task_numbers = [
        task_number
        for task_number in range(1, requested_count + 1)
        if not questions_by_task_number.get(task_number)
    ]

    if missing_task_numbers:
        missing_numbers_text = ", ".join(str(number) for number in missing_task_numbers)
        return {
            "error": (
                "Недостаточно вопросов для последовательного варианта. "
                f"Не найдены задания: {missing_numbers_text}"
            )
        }, 400

    selected_questions = [
        random.choice(questions_by_task_number[task_number])
        for task_number in range(1, requested_count + 1)
    ]

    session = TestSession(
        user_id=_current_user_id(),
        subject=subject,
        requested_count=requested_count,
    )
    db.session.add(session)
    db.session.flush()

    for position, question in enumerate(selected_questions, start=1):
        db.session.add(
            TestSessionQuestion(
                session_id=session.id,
                bank_question_id=question.id,
                position=position,
            )
        )

    db.session.commit()

    return {
        "session_id": session.id,
        "status": session.status,
        "subject": session.subject,
        "question_count": requested_count,
    }, 201


@tests_bp.get("/sessions/<int:session_id>")
@jwt_required(optional=True)
def get_test_session(session_id):
    session = TestSession.query.get(session_id)
    if not session:
        return {"error": "Test session not found"}, 404

    return jsonify(_serialize_test_session(session))


@tests_bp.post("/sessions/<int:session_id>/submit")
@jwt_required(optional=True)
def submit_test_session(session_id):
    session = TestSession.query.get(session_id)
    if not session:
        return {"error": "Test session not found"}, 404

    if session.submission:
        return {"error": "Этот тест уже был отправлен"}, 400

    data = request.get_json(silent=True) or {}
    answers_data = data.get("answers")
    if not isinstance(answers_data, list) or not answers_data:
        return {"error": "Invalid or empty answers list"}, 400

    session_questions = {
        session_question.bank_question_id: session_question.bank_question
        for session_question in session.questions
    }

    submission = TestSubmission(
        session_id=session.id,
        user_id=_current_user_id(),
        total_questions=len(session.questions),
        score=0,
    )
    db.session.add(submission)
    db.session.flush()

    correct_answers = 0
    answered_question_ids = set()

    for answer_data in answers_data:
        question_id = answer_data.get("question_id")
        question = session_questions.get(question_id)
        if not question:
            db.session.rollback()
            return {"error": f"Question {question_id} not found in this test"}, 400
        if question_id in answered_question_ids:
            db.session.rollback()
            return {"error": f"Question {question_id} submitted more than once"}, 400
        answered_question_ids.add(question_id)

        submission_answer = TestSubmissionAnswer(
            submission_id=submission.id,
            bank_question_id=question.id,
        )

        is_correct = False

        if question.type == "text":
            text_answer = (answer_data.get("text_answer") or "").strip()
            if not text_answer:
                db.session.rollback()
                return {"error": f"Text answer required for question {question_id}"}, 400

            submission_answer.text_answer = text_answer
            is_correct = _normalize_text_answer(text_answer) == _normalize_text_answer(question.correct_text_answer)
            db.session.add(submission_answer)

        elif question.type == "single":
            option_ids = answer_data.get("option_ids")
            if not isinstance(option_ids, list) or len(option_ids) != 1:
                db.session.rollback()
                return {"error": f"Single choice question {question_id} requires exactly 1 option"}, 400

            selected_option = QuestionBankOption.query.filter_by(
                id=option_ids[0],
                question_id=question_id,
            ).first()
            if not selected_option:
                db.session.rollback()
                return {"error": f"Invalid option {option_ids[0]} for question {question_id}"}, 400

            db.session.add(submission_answer)
            db.session.flush()
            db.session.add(
                TestSubmissionAnswerOption(
                    answer_id=submission_answer.id,
                    option_id=selected_option.id,
                )
            )
            is_correct = selected_option.is_correct

        elif question.type == "multiple":
            option_ids = answer_data.get("option_ids")
            if not isinstance(option_ids, list) or not option_ids:
                db.session.rollback()
                return {"error": f"Multiple choice question {question_id} requires option_ids list"}, 400

            valid_options = (
                QuestionBankOption.query.filter(
                    QuestionBankOption.question_id == question_id,
                    QuestionBankOption.id.in_(option_ids),
                ).all()
            )
            if len(valid_options) != len(set(option_ids)):
                db.session.rollback()
                return {"error": f"Invalid options for question {question_id}"}, 400

            db.session.add(submission_answer)
            db.session.flush()
            for option in valid_options:
                db.session.add(
                    TestSubmissionAnswerOption(
                        answer_id=submission_answer.id,
                        option_id=option.id,
                    )
                )

            selected_ids = {option.id for option in valid_options}
            correct_ids = {option.id for option in question.options if option.is_correct}
            is_correct = selected_ids == correct_ids

        else:
            db.session.rollback()
            return {"error": f"Unknown question type for question {question_id}"}, 400

        if is_correct:
            correct_answers += 1

    submission.score = correct_answers
    session.status = "completed"
    session.completed_at = datetime.utcnow()
    db.session.commit()

    breakdown_payload = _serialize_submission_breakdown(session, submission)

    return {
        "message": f"Тест отправлен. Результат: {correct_answers} из {len(session.questions)}.",
        "score": correct_answers,
        "total_questions": len(session.questions),
        "submission": breakdown_payload,
    }, 201
