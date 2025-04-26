import sqlite3
from website import app, db
from website.models import LearningPath, Course, User, CSInterest, CSInterestSurvey
from flask import Flask

def check_table_structure(db_path, table_name):
    """Print the structure of a table in SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print(f"Table structure for '{table_name}':")
    print("=" * 50)
    print("CID | Name | Type | NotNull | DefaultValue | PK")
    print("-" * 50)
    
    for col in columns:
        print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
    
    # Check also for the CSInterestSurvey table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cs_interest_survey'")
    if cursor.fetchone():
        print("\nTable 'cs_interest_survey' exists")
        # Get table info
        cursor.execute("PRAGMA table_info(cs_interest_survey)")
        columns = cursor.fetchall()
        
        print(f"\nTable structure for 'cs_interest_survey':")
        print("=" * 50)
        print("CID | Name | Type | NotNull | DefaultValue | PK")
        print("-" * 50)
        
        for col in columns:
            print(f"{col[0]} | {col[1]} | {col[2]} | {col[3]} | {col[4]} | {col[5]}")
    else:
        print("\nTable 'cs_interest_survey' does not exist")
    
    conn.close()

if __name__ == "__main__":
    check_table_structure('instance/database.db', 'user')

# Run this inside the Flask app context
with app.app_context():
    # Check if tables exist
    print("\n=== Database Status ===")
    print('Users:', User.query.count())
    
    try:
        print('Learning Paths:', LearningPath.query.count())
    except Exception as e:
        print('Learning Paths: ERROR -', str(e))
    
    try:
        print('Courses:', Course.query.count())
    except Exception as e:
        print('Courses: ERROR -', str(e))

    try:
        print('CS Interest Survey:', CSInterestSurvey.query.count())
    except Exception as e:
        print('CS Interest Survey: ERROR -', str(e))

    try:
        print('CS Interest:', CSInterest.query.count())
    except Exception as e:
        print('CS Interest: ERROR -', str(e))

    # Create all tables that don't exist
    print("\n=== Creating missing tables ===")
    db.create_all()
    print("All tables have been created.")
    
    # Check again to verify
    print("\n=== Database Status After Table Creation ===")
    print('Users:', User.query.count())
    print('Learning Paths:', LearningPath.query.count())
    print('Courses:', Course.query.count())
    print('CS Interest Survey:', CSInterestSurvey.query.count())
    print('CS Interest:', CSInterest.query.count()) 