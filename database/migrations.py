"""
Database Migration System
Handles SQLite to PostgreSQL migration and schema versioning
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Manages database schema migrations and SQLite to PostgreSQL conversion"""
    
    def __init__(self, sqlite_path: str = "labeled_data.db"):
        self.sqlite_path = Path(sqlite_path)
        self.current_version = 0
        self.migrations = self._get_migrations()
    
    def _get_migrations(self) -> List[Dict]:
        """Define all schema migrations"""
        return [
            {
                'version': 1,
                'description': 'Initial schema',
                'sqlite': self._migration_v1_sqlite,
                'postgres': self._migration_v1_postgres
            },
            {
                'version': 2,
                'description': 'Add user management tables',
                'sqlite': self._migration_v2_sqlite,
                'postgres': self._migration_v2_postgres
            },
            {
                'version': 3,
                'description': 'Add backup and alert tables',
                'sqlite': self._migration_v3_sqlite,
                'postgres': self._migration_v3_postgres
            }
        ]
    
    def get_current_version(self, conn) -> int:
        """Get current schema version"""
        try:
            if self._is_postgres(conn):
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except:
            return 0
    
    def _is_postgres(self, conn) -> bool:
        """Check if connection is PostgreSQL"""
        return hasattr(conn, 'get_dsn_parameters')
    
    def apply_migrations(self, conn):
        """Apply all pending migrations"""
        current_version = self.get_current_version(conn)
        is_postgres = self._is_postgres(conn)
        
        logger.info(f"Current schema version: {current_version}")
        logger.info(f"Database type: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        for migration in self.migrations:
            if migration['version'] > current_version:
                logger.info(f"Applying migration {migration['version']}: {migration['description']}")
                
                try:
                    if is_postgres:
                        migration['postgres'](conn)
                    else:
                        migration['sqlite'](conn)
                    
                    self._record_migration(conn, migration['version'], migration['description'])
                    logger.info(f"✓ Migration {migration['version']} applied")
                    
                except Exception as e:
                    logger.error(f"❌ Migration {migration['version']} failed: {e}")
                    conn.rollback()
                    raise
    
    def _record_migration(self, conn, version: int, description: str):
        """Record successful migration"""
        if self._is_postgres(conn):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schema_version (version, description, applied_at)
                VALUES (%s, %s, NOW())
            """, (version, description))
        else:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schema_version (version, description, applied_at)
                VALUES (?, ?, datetime('now'))
            """, (version, description))
        
        conn.commit()
    
    # Migration v1: Initial schema
    def _migration_v1_sqlite(self, conn):
        cursor = conn.cursor()
        
        # Schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Labeled data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labeled_data (
                review_id TEXT PRIMARY KEY,
                disease_type TEXT NOT NULL,
                image_path TEXT NOT NULL,
                ai_prediction TEXT NOT NULL,
                confidence REAL,
                radiologist_label TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        """)
        
        # Audit logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        conn.commit()
    
    def _migration_v1_postgres(self, conn):
        cursor = conn.cursor()
        
        # Schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id SERIAL PRIMARY KEY,
                version INTEGER NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Labeled data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS labeled_data (
                review_id TEXT PRIMARY KEY,
                disease_type TEXT NOT NULL,
                image_path TEXT NOT NULL,
                ai_prediction TEXT NOT NULL,
                confidence REAL,
                radiologist_label TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                reviewed_at TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labeled_data_status ON labeled_data(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labeled_data_created ON labeled_data(created_at)")
        
        # Audit logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)")
        
        conn.commit()
    
    # Migration v2: User management
    def _migration_v2_sqlite(self, conn):
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                hospital_id TEXT,
                full_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                UNIQUE(role, resource, action)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_jti TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_revoked BOOLEAN DEFAULT 0,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
    
    def _migration_v2_postgres(self, conn):
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                hospital_id TEXT,
                full_name TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_hospital ON users(hospital_id)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                UNIQUE(role, resource, action)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_jti TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP NOT NULL,
                is_revoked BOOLEAN DEFAULT FALSE,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_jti)")
        
        conn.commit()
    
    # Migration v3: Backup and alerts
    def _migration_v3_sqlite(self, conn):
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at TIMESTAMP,
                notified BOOLEAN DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_history (
                backup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'success',
                error_message TEXT
            )
        """)
        
        conn.commit()
    
    def _migration_v3_postgres(self, conn):
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_alerts (
                alert_id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT NOW(),
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMP,
                notified BOOLEAN DEFAULT FALSE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON system_alerts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_level ON system_alerts(level)")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_history (
                backup_id SERIAL PRIMARY KEY,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size BIGINT,
                created_at TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'success',
                error_message TEXT
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_backup_created ON backup_history(created_at)")
        
        conn.commit()
    
    def migrate_sqlite_to_postgres(self, postgres_url: str) -> bool:
        """
        Migrate data from SQLite to PostgreSQL
        
        Args:
            postgres_url: PostgreSQL connection string
        
        Returns:
            True if successful
        """
        try:
            import psycopg2
            
            logger.info("Starting SQLite to PostgreSQL migration...")
            
            # Connect to both databases
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            postgres_conn = psycopg2.connect(postgres_url)
            
            # Apply PostgreSQL schema
            self.apply_migrations(postgres_conn)
            
            # Migrate tables
            tables_to_migrate = [
                'labeled_data',
                'audit_logs',
                'users',
                'permissions',
                'user_sessions',
                'system_alerts',
                'backup_history'
            ]
            
            for table in tables_to_migrate:
                self._migrate_table(sqlite_conn, postgres_conn, table)
            
            postgres_conn.commit()
            
            sqlite_conn.close()
            postgres_conn.close()
            
            logger.info("✓ Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
    
    def _migrate_table(self, sqlite_conn, postgres_conn, table_name: str):
        """Migrate single table from SQLite to PostgreSQL"""
        try:
            sqlite_cursor = sqlite_conn.cursor()
            postgres_cursor = postgres_conn.cursor()
            
            # Check if table exists in SQLite
            sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not sqlite_cursor.fetchone():
                logger.info(f"  Skipping {table_name} (not found in SQLite)")
                return
            
            # Get all rows
            sqlite_cursor.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"  {table_name}: No data to migrate")
                return
            
            # Get column names
            columns = [description[0] for description in sqlite_cursor.description]
            
            # Insert into PostgreSQL
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            count = 0
            for row in rows:
                try:
                    postgres_cursor.execute(insert_sql, tuple(row))
                    count += 1
                except Exception as e:
                    logger.warning(f"  Failed to insert row in {table_name}: {e}")
            
            logger.info(f"  ✓ {table_name}: Migrated {count}/{len(rows)} rows")
            
        except Exception as e:
            logger.error(f"  ❌ {table_name}: Migration failed - {e}")

def get_database_connection(database_url: str = None):
    """
    Get database connection (SQLite or PostgreSQL)
    
    Args:
        database_url: Database URL (sqlite:/// or postgresql://)
    
    Returns:
        Database connection
    """
    import os
    
    if database_url is None:
        database_url = os.getenv('DATABASE_URL', 'sqlite:///./labeled_data.db')
    
    if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
        import psycopg2
        # Parse PostgreSQL URL
        url = database_url.replace('postgresql://', '').replace('postgres://', '')
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        return conn
    else:
        # SQLite
        db_path = database_url.replace('sqlite:///', '').replace('sqlite://', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

def initialize_database(database_url: str = None):
    """Initialize database with latest schema"""
    conn = get_database_connection(database_url)
    migrator = DatabaseMigrator()
    migrator.apply_migrations(conn)
    conn.close()
    logger.info("✓ Database initialized with latest schema")
