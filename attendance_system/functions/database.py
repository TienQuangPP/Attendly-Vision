import sqlite3
from datetime import datetime, date

class Database:

    def __init__(self, db_path='attendance.db'):
        self.db_path = db_path
        self._create_tables()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                student_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                slot INTEGER DEFAULT 0
            )
        ''')
        try:
            cursor.execute('ALTER TABLE attendance ADD COLUMN slot INTEGER DEFAULT 0')
        except Exception:
            pass
        conn.commit()
        conn.close()
        print('[INFO] Database initialized.')

    def save_attendance(self, class_name, subject, student_id, student_name, confidence=0.0, slot=0):
        today = date.today().isoformat()
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN IMMEDIATE')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                '''INSERT INTO attendance
                   (class_name, subject, student_id, student_name, timestamp, date, confidence, slot)
                   SELECT ?, ?, ?, ?, ?, ?, ?, ?
                   WHERE NOT EXISTS (
                       SELECT 1 FROM attendance
                       WHERE class_name=? AND subject=? AND student_id=? AND date=? AND slot=?
                   )''',
                (class_name, subject, student_id, student_name, timestamp, today, confidence, slot,
                 class_name, subject, student_id, today, slot),
            )
            inserted = cursor.rowcount == 1
            conn.commit()
            return inserted
        finally:
            conn.close()

    def is_already_recorded(self, class_name, subject, student_id, check_date=None):
        if check_date is None:
            check_date = date.today().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM attendance WHERE class_name=? AND subject=? AND student_id=? AND date=?', (class_name, subject, student_id, check_date))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def get_attendance_today(self, class_name=None, subject=None, slot=None):
        today = date.today().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT class_name, subject, student_id, student_name, timestamp, confidence FROM attendance WHERE date = ?'
        params = [today]
        if class_name:
            query += ' AND class_name = ?'
            params.append(class_name)
        if subject:
            query += ' AND subject = ?'
            params.append(subject)
        if slot is not None:
            query += ' AND slot = ?'
            params.append(slot)
        query += ' ORDER BY timestamp DESC'
        cursor.execute(query, tuple(params))
        records = cursor.fetchall()
        conn.close()
        return records

    def get_today_count(self, class_name=None, subject=None, slot=None):
        today = date.today().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT COUNT(*) FROM attendance WHERE date = ?'
        params = [today]
        if class_name:
            query += ' AND class_name = ?'
            params.append(class_name)
        if subject:
            query += ' AND subject = ?'
            params.append(subject)
        if slot is not None:
            query += ' AND slot = ?'
            params.append(slot)
        cursor.execute(query, tuple(params))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def update_student_info(self, old_id, new_class, new_id, new_name):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('UPDATE attendance SET class_name=?, student_id=?, student_name=? WHERE student_id=?', (new_class, new_id, new_name, old_id))
        conn.commit()
        conn.close()

    def get_student_history(self, student_id, class_name=None, subject=None):
        conn = self._get_conn()
        cursor = conn.cursor()
        query = 'SELECT date, confidence FROM attendance WHERE student_id=?'
        params = [student_id]
        if class_name:
            query += ' AND class_name=?'
            params.append(class_name)
        if subject:
            query += ' AND subject=?'
            params.append(subject)
        query += ' ORDER BY date ASC'
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return rows
