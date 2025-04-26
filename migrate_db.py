from website import db, create_app
from website.models import User, CSInterestSurvey
import sqlite3

def add_column(database_path, table_name, column_name, column_type):
    """Add a new column to a SQLite database table if it doesn't exist"""
    try:
        # Connect to the database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        
        if column_name not in columns:
            # Add column
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            print(f"Column '{column_name}' added to {table_name}")
        else:
            print(f"Column '{column_name}' already exists in {table_name}")
        
        # Commit and close
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding column: {e}")
        return False

def main():
    """Run database migrations"""
    # Get app context
    app = create_app()
    with app.app_context():
        # 1. Add is_survey_completed column to user table
        db_path = 'instance/database.db'
        result = add_column(db_path, 'user', 'is_survey_completed', 'BOOLEAN DEFAULT 0')
        
        if result:
            print("Successfully added is_survey_completed column to user table")
        
        # 2. Create the CSInterestSurvey table if it doesn't exist
        db.create_all()
        print("Database tables created/updated")
        
        print("Migration completed successfully!")

if __name__ == "__main__":
    main() 