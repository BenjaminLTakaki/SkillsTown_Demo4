#!/usr/bin/env python3
"""
Ultimate fix for SkillsTown database issues
This will handle both SQLite and PostgreSQL databases
"""

import os
import sys

def load_env_file():
    """Load environment variables from .env file"""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Loaded environment variables from .env file")

def ultimate_fix():
    """Complete fix for all database issues"""
    print("🔧 ULTIMATE FIX for SkillsTown Database Issues")
    print("=" * 60)
    
    # Load environment variables first
    load_env_file()
    
    # First, let's figure out what database you're using
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print(f"📊 Detected PostgreSQL database: {database_url[:50]}...")
        return fix_postgresql()
    else:
        print("📊 Using SQLite database")
        return fix_sqlite()

def fix_postgresql():
    """Fix PostgreSQL database issues"""
    print("\n🐘 Fixing PostgreSQL Database...")
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse database URL
        database_url = os.environ.get('DATABASE_URL')
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://')
        
        parsed = urlparse(database_url)
        
        # Connect directly to PostgreSQL
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:]  # Remove leading /
        )
        
        cursor = conn.cursor()
        
        print("📝 Adding quiz_user_uuid column to students table...")
        try:
            cursor.execute("""
                ALTER TABLE students 
                ADD COLUMN quiz_user_uuid VARCHAR(36)
            """)
            print("✅ Successfully added quiz_user_uuid column")
        except Exception as e:
            if "already exists" in str(e):
                print("✅ quiz_user_uuid column already exists")
            else:
                print(f"❌ Error: {e}")
        
        print("📝 Creating quiz tables...")
        
        # Create quiz tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skillstown_course_quizzes (
                id SERIAL PRIMARY KEY,
                user_course_id INTEGER NOT NULL,
                quiz_api_id VARCHAR(100) NOT NULL,
                quiz_title VARCHAR(255),
                quiz_description TEXT,
                questions_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skillstown_quiz_attempts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                course_quiz_id INTEGER NOT NULL,
                attempt_api_id VARCHAR(100) NOT NULL,
                score INTEGER,
                total_questions INTEGER,
                correct_answers INTEGER,
                feedback_strengths TEXT,
                feedback_improvements TEXT,
                user_answers TEXT,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ PostgreSQL database fixed!")
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL fix failed: {e}")
        return False

def fix_sqlite():
    """Fix SQLite database issues"""
    print("\n💾 Fixing SQLite Database...")
    
    try:
        # First, let's use the Flask app to create all tables properly
        print("📝 Creating all tables using Flask app...")
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app import create_app
        
        app = create_app()
        with app.app_context():
            from models import db
            
            # Get the actual database path from app config
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            print(f"📝 Database URI: {db_uri}")
            
            # Create all tables
            db.create_all()
            print("✅ Created all tables with proper schema")
        
        print("✅ SQLite database fixed!")
        return True
        
    except Exception as e:
        print(f"❌ SQLite fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_app_issues():
    """Fix the app.py datetime issue"""
    print("\n🔧 Checking app.py for issues...")
    
    app_file = "app.py"
    if not os.path.exists(app_file):
        print("❌ app.py not found")
        return False
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for datetime issues
    if 'datetime.datetime.now()' in content:
        print("📝 Fixing datetime issue...")
        content = content.replace('datetime.datetime.now()', 'datetime.now()')
        
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Fixed datetime issue")
    
    return True

def main():
    """Main fix function"""
    print("🎯 SkillsTown Ultimate Database Fix")
    print("This will resolve all database and app issues")
    print("=" * 60)
    
    # Load environment variables first
    load_env_file()
    
    # Step 1: Fix app.py issues
    fix_app_issues()
    
    # Step 2: Fix database
    if ultimate_fix():
        print("\n🎉 Database fixed successfully!")
        print("\n🚀 Your app should now work!")
        print("Next steps:")
        print("1. Start your app: python app.py")
        print("2. Register/login to test")
        print("3. Try the quiz integration")
    else:
        print("\n❌ Database fix failed")
        print("Please check the error messages above and try again.")

if __name__ == '__main__':
    main()