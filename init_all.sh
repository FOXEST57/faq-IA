#!/bin/zsh

# 1. Install dependencies
pip install flask flask-sqlalchemy

# 2. (Optional) Remove existing database if you want a fresh start
# rm backend/instance/faq.db

# 3. Run Alembic migrations (if using Alembic)
# alembic upgrade head

# 4. Run your database initialization and import script
python init_db.py

# 5. (Optional) Check database contents
sqlite3 backend/instance/faq.db "SELECT * FROM faq;"