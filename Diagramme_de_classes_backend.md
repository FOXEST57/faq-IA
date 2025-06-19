classDiagram
    class UserController {
        +register()
        +login()
        +get_profile()
    }
    
    class FAQController {
        +get_all_entries()
        +search_entries()
        +add_entry()
        +update_entry()
    }
    
    class AdminController {
        +generate_ai_entries()
        +approve_entry()
        +view_stats()
    }
    
    class AIService {
        +process_pdf()
        +generate_embeddings()
        +generate_qa_pair()
    }
    
    class PredictionService {
        +log_visit()
        +train_model()
        +predict_visits()
    }
    
    UserController --> FAQController
    AdminController --> AIService
    AdminController --> PredictionService
    AIService --> PDFDocumentModel
    FAQController --> FAQEntryModel