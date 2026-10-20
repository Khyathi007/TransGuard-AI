import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            location TEXT NOT NULL,
            role TEXT DEFAULT 'Owner',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # 2. Transformers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transformers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transformer_id TEXT UNIQUE NOT NULL,
            location TEXT NOT NULL,
            status TEXT DEFAULT 'SAFE',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    ''')

    # 3. Incidents Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transformer_id TEXT NOT NULL,
            incident_type TEXT NOT NULL,
            detected_time TEXT NOT NULL,
            threat_level TEXT DEFAULT 'PENDING',
            owner_response TEXT DEFAULT 'PENDING',
            status TEXT DEFAULT 'ACTIVE',
            live_feed_status TEXT DEFAULT 'STOPPED',
            evidence_status TEXT DEFAULT 'IN_PROGRESS',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    ''')

    # 4. Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            incident_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE
        );
    ''')

    # 5. Captured Evidence Images Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS captured_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            captured_at TEXT NOT NULL,
            FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE
        );
    ''')

    # 6. Official Reports Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            incident_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (incident_id) REFERENCES incidents (id) ON DELETE CASCADE
        );
    ''')

    # Performance Indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_incidents_user ON incidents(user_id, status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id, status);')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_incident ON captured_images(incident_id);')

    conn.commit()
    conn.close()
    logging.info("TransGuard AI SQLite Database Schema & Performance Indexes Initialized.")

if __name__ == '__main__':
    init_db()