#!/usr/bin/env python3
"""
Run this script to fix the database schema for SkillsTown
"""

import os
import sys
from sqlalchemy import text

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def run_migration():
    """Run the database migration within Flask app context"""
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        from app import db
        
        print("Running SkillsTown database migration...")
        
        try:
            # Create all tables first
            db.create_all()
            print("✓ Created/verified all tables")
            
            # Check if job_description column exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='skillstown_user_profiles' 
                AND column_name='job_description'
            """))
            
            if not result.fetchone():
                print("Adding job_description column...")
                try:
                    # For PostgreSQL
                    db.session.execute(text("""
                        ALTER TABLE skillstown_user_profiles 
                        ADD COLUMN job_description TEXT
                    """))
                    db.session.commit()
                    print("✓ Successfully added job_description column")
                except Exception as e:
                    print(f"PostgreSQL failed, trying SQLite approach: {e}")
                    db.session.rollback()
                    
                    # For SQLite - recreate table approach
                    try:
                        # Check if we're using SQLite
                        db.session.execute(text("SELECT sqlite_version()"))
                        
                        print("Detected SQLite - using recreate approach...")
                        
                        # Create new table with correct structure
                        db.session.execute(text("""
                            CREATE TABLE skillstown_user_profiles_new (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER NOT NULL,
                                cv_text TEXT,
                                job_description TEXT,
                                skills TEXT,
                                skill_analysis TEXT,
                                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        
                        # Copy existing data
                        db.session.execute(text("""
                            INSERT INTO skillstown_user_profiles_new 
                            (id, user_id, cv_text, skills, skill_analysis, uploaded_at)
                            SELECT id, user_id, cv_text, skills, skill_analysis, uploaded_at
                            FROM skillstown_user_profiles
                        """))
                        
                        # Drop old table and rename new one
                        db.session.execute(text("DROP TABLE skillstown_user_profiles"))
                        db.session.execute(text("ALTER TABLE skillstown_user_profiles_new RENAME TO skillstown_user_profiles"))
                        
                        db.session.commit()
                        print("✓ Successfully recreated table with job_description column")
                        
                    except Exception as sqlite_error:
                        print(f"SQLite approach also failed: {sqlite_error}")
                        db.session.rollback()
                        
                        # Last resort - just recreate all tables
                        print("Using last resort - recreating all SkillsTown tables...")
                        db.session.execute(text("DROP TABLE IF EXISTS skillstown_user_profiles CASCADE"))
                        db.session.execute(text("DROP TABLE IF EXISTS skillstown_user_courses CASCADE"))
                        db.session.commit()
                        
                        db.create_all()
                        print("✓ Recreated all tables from scratch")
            else:
                print("✓ job_description column already exists")
            
            print("\n🎉 Migration completed successfully!")
            print("Your SkillsTown application should now work properly.")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False
            
        return True

def column_exists(db, table_name, column_name):
    """Check if a column exists in a table (works for both SQLite and PostgreSQL)"""
    try:
        # Try SQLite approach first
        result = db.session.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        return column_name in columns
    except:
        try:
            # PostgreSQL approach
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            return result.fetchone() is not None
        except:
            return False

def add_column_if_missing(db, table_name, column_name, column_type="TEXT"):
    """Add a column to a table if it doesn't exist"""
    if not column_exists(db, table_name, column_name):
        print(f"Adding {column_name} column to {table_name}...")
        try:
            db.session.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {column_name} {column_type}
            """))
            db.session.commit()
            print(f"✓ Successfully added {column_name} column")
            return True
        except Exception as e:
            print(f"Error adding {column_name} column: {e}")
            db.session.rollback()
            return False
    else:
        print(f"✓ {column_name} column already exists in {table_name}")
        return True

# Usage in your migration script:
def run_migration():
    """Run the database migration within Flask app context"""
    from app import create_app
    
    app = create_app()
    
    with app.app_context():
        from app import db
        
        print("Running SkillsTown database migration...")
        
        try:
            # Create all tables first
            db.create_all()
            print("✓ Created/verified all tables")
            
            # Add missing columns
            add_column_if_missing(db, "skillstown_user_profiles", "job_description")
            add_column_if_missing(db, "skillstown_course_details", "quiz_results")
            
            print("\n🎉 Migration completed successfully!")
            print("Your SkillsTown application should now work properly.")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False
            
        return True       

if __name__ == '__main__':
    success = run_migration()
    if not success:
        sys.exit(1)