from extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Survey(db.Model):
    __tablename__ = "surveys"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
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