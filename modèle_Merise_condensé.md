flowchart TD
    A[Documents PDF] -->|Extraction| B(Traitement NLP)
    B --> C{Base de Connaissances}
    C --> D[(FAQ Générée)]
    D --> E[Validation Admin]
    E --> F[(FAQ Validée)]
    
    G[Visiteurs] -->|Consultation| F
    G -->|Log| H[Analyse Visites]
    H --> I[Prédictions ML]
    
    J[Admin] -->|Gestion| F
    J -->|Configuration| B
    J -->|Monitoring| I