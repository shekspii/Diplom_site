from extensions import db
from datetime import datetime
import secrets
import string


SHARE_KEY_ALPHABET = string.ascii_uppercase + string.digits


def generate_share_key(length=10):
    return "".join(secrets.choice(SHARE_KEY_ALPHABET) for _ in range(length))


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("user", "admin", name="user_role"),
        default="user",
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Survey(db.Model):
    __tablename__ = "surveys"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False, default="Без предмета")
    share_key = db.Column(db.String(32), unique=True, nullable=False, default=generate_share_key)
    access_mode = db.Column(
        db.Enum("private", "by_key", name="survey_access_mode"),
        default="by_key",
        nullable=False
    )
    description = db.Column(db.Text)

    status = db.Column(
        db.Enum("draft", "published", "closed", name="survey_status"),
        default="draft",
        nullable=False
    )

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    question = db.relationship("Question", backref=db.backref("surveys", lazy=True))

class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)

    text = db.Column(db.Text, nullable=False)
    type = db.Column(
        db.Enum("single", "multiple", "text", name="question_type"),
        nullable=False
    )
    sequence = db.Column(db.Integer, nullable=False)
    
    survey = db.relationship("Survey", backref=db.backref("questions", lazy=True))
    options = db.relationship(
        "Option",
        back_populates="question",
        cascade="all, delete-orphan"
    )


class Option(db.Model):
    __tablename__ = "options"
    __table_args__ = (
        db.UniqueConstraint("question_id", "position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )
    text = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)

    question = db.relationship("Question", back_populates="options")


class Response(db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("survey_id", "user_id", name="unique_survey_user"),
    )


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)

    text_answer = db.Column(db.Text)


class AnswerOption(db.Model):
    __tablename__ = "answer_options"

    answer_id = db.Column(db.Integer, db.ForeignKey("answers.id"), primary_key=True)
    option_id = db.Column(db.Integer, db.ForeignKey("options.id"), primary_key=True)


class QuestionBankItem(db.Model):
    __tablename__ = "question_bank_items"

    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    exam_task_number = db.Column(db.Integer, nullable=False, default=1)
    correct_text_answer = db.Column(db.Text)
    topic = db.Column(db.String(255))
    difficulty = db.Column(db.String(50))
    text = db.Column(db.Text, nullable=False)
    type = db.Column(
        db.Enum("single", "multiple", "text", name="question_type"),
        nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    options = db.relationship(
        "QuestionBankOption",
        back_populates="question",
        cascade="all, delete-orphan"
    )


class QuestionBankOption(db.Model):
    __tablename__ = "question_bank_options"
    __table_args__ = (
        db.UniqueConstraint("question_id", "position", name="uq_bank_question_option_position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("question_bank_items.id", ondelete="CASCADE"),
        nullable=False
    )
    text = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)

    question = db.relationship("QuestionBankItem", back_populates="options")


class TestSession(db.Model):
    __tablename__ = "test_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    subject = db.Column(db.String(255), nullable=False)
    requested_count = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.Enum("generated", "completed", "cancelled", name="test_session_status"),
        default="generated",
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    questions = db.relationship(
        "TestSessionQuestion",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    submission = db.relationship(
        "TestSubmission",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )


class TestSessionQuestion(db.Model):
    __tablename__ = "test_session_questions"
    __table_args__ = (
        db.UniqueConstraint("session_id", "position", name="uq_test_session_position"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("test_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    bank_question_id = db.Column(
        db.Integer,
        db.ForeignKey("question_bank_items.id"),
        nullable=False
    )
    position = db.Column(db.Integer, nullable=False)

    session = db.relationship("TestSession", back_populates="questions")
    bank_question = db.relationship("QuestionBankItem")


class TestSubmission(db.Model):
    __tablename__ = "test_submissions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("test_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    score = db.Column(db.Integer, nullable=False, default=0)
    total_questions = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship("TestSession", back_populates="submission")
    answers = db.relationship(
        "TestSubmissionAnswer",
        back_populates="submission",
        cascade="all, delete-orphan"
    )


class TestSubmissionAnswer(db.Model):
    __tablename__ = "test_submission_answers"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Integer,
        db.ForeignKey("test_submissions.id", ondelete="CASCADE"),
        nullable=False
    )
    bank_question_id = db.Column(
        db.Integer,
        db.ForeignKey("question_bank_items.id"),
        nullable=False
    )
    text_answer = db.Column(db.Text)

    submission = db.relationship("TestSubmission", back_populates="answers")
    selected_options = db.relationship(
        "TestSubmissionAnswerOption",
        back_populates="answer",
        cascade="all, delete-orphan"
    )


class TestSubmissionAnswerOption(db.Model):
    __tablename__ = "test_submission_answer_options"

    answer_id = db.Column(
        db.Integer,
        db.ForeignKey("test_submission_answers.id", ondelete="CASCADE"),
        primary_key=True
    )
    option_id = db.Column(
        db.Integer,
        db.ForeignKey("question_bank_options.id"),
        primary_key=True
    )

    answer = db.relationship("TestSubmissionAnswer", back_populates="selected_options")
