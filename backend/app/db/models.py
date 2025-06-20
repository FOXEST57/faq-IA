from sqlalchemy import UUID, Column, String, Text, ForeignKey, Integer, Float, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from .base import Base, TimestampMixin
import uuid

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    
    questions = relationship('Question', back_populates='user')

class Question(Base, TimestampMixin):
    __tablename__ = 'questions'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    session_id = Column(String(36), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    user = relationship('User', back_populates='questions')
    answers = relationship('Answer', back_populates='question')

class Answer(Base, TimestampMixin):
    __tablename__ = 'answers'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    question_id = Column(PG_UUID(as_uuid=True), ForeignKey('questions.id'))
    sources = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=False)
    rating = Column(Integer, default=0)
    
    question = relationship('Question', back_populates='answers')

class Document(Base, TimestampMixin):
    __tablename__ = 'documents'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    content = Column(Text, nullable=True)
    embedding_model = Column(String(50), nullable=False)
    usage_count = Column(Integer, default=0)