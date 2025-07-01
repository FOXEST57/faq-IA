# Create Service class for Database operations in order to save, update, delete, and query data to the FAQ database SQLAlchemy and / or PostgreSQL

# Import SQLAlchemy and other necessary modules
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

# Define the Base class for declarative models
Base = declarative_base()

# Define the FAQ model
class FAQ(Base):
    __tablename__ = 'faqs'

    id = Column(Integer, primary_key=True)
    question = Column(String)
    answer = Column(String)

# Define the DatabaseService class  
class DatabaseService:
    def __init__(self, db_path):
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def create_tables(self):
        Base.metadata.create_all(self.engine)
    
    def add_faq(self, question, answer):
        faq = FAQ(question=question, answer=answer)
        self.session.add(faq)
        self.session.commit()

    def get_all_faqs(self):
        return self.session.query(FAQ).all()
    
    def add_faqs(self, faqs):
        for faq in faqs:
            self.add_faq(faq['question'], faq['answer'])
        self.session.commit()
    
    def get_faq_by_question(self, question):
        return self.session.query(FAQ).filter_by(question=question).first()
    
    def get_faqs_by_questions(self, questions):
        return self.session.query(FAQ).filter(FAQ.question.in_(questions)).all()

    
    def update_faq(self, faq_id, new_question, new_answer):
        faq = self.session.query(FAQ).filter_by(id=faq_id).first()
        if faq:
            faq.question = new_question
            faq.answer = new_answer
            self.session.commit()
            return True
        return False
    
    def delete_faq(self, faq_id):
        faq = self.session.query(FAQ).filter_by(id=faq_id).first()
        if faq:
            self.session.delete(faq)
            self.session.commit()
            return True
        return False

    
    def get_faq_by_id(self, faq_id):
        return self.session.query(FAQ).filter_by(id=faq_id).first()

    
    def get_faqs_by_ids(self, faq_ids):
        return self.session.query(FAQ).filter(FAQ.id.in_(faq_ids)).all()

    
    def get_faqs_by_id_range(self, start_id, end_id):
        return self.session.query(FAQ).filter(FAQ.id >= start_id, FAQ.id <= end_id).all()
    

    
