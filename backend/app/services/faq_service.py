from backend.models import FAQ, db
from typing import List, Dict

class FAQService:
    @staticmethod
    def get_faq_stats() -> Dict:
        """Get FAQ statistics"""
        return {
            'total': FAQ.query.count(),
            'ai_generated': FAQ.query.filter_by(source='ai').count(),
            'manual': FAQ.query.filter_by(source='manual').count()
        }

    @staticmethod
    def create_faq(faq_data: Dict, source: str = 'manual') -> FAQ:
        """Create FAQ with source tracking"""
        faq = FAQ(
            question=faq_data.get('question'),
            answer=faq_data.get('answer'),
            source=source
        )
        db.session.add(faq)
        db.session.commit()
        return faq