erDiagram
    USER ||--o{ FAQ_ENTRY : "crée/modifie"
    USER {
        int id PK
        string username
        string password_hash
        string role
        datetime created_at
    }
    
    FAQ_ENTRY {
        int id PK
        string question
        string answer
        string source "IA/Manual"
        int created_by FK
        datetime created_at
        datetime updated_at
        bool is_approved
    }
    
    PDF_DOCUMENT {
        int id PK
        string filename
        string filepath
        int uploaded_by FK
        datetime uploaded_at
        text extracted_text
    }
    
    VISIT_LOG {
        int id PK
        string ip_address
        string page_visited
        datetime visit_time
        string user_agent
    }
    
    PREDICTION_MODEL {
        int id PK
        string model_name
        string model_path
        datetime last_trained
        float accuracy
    }