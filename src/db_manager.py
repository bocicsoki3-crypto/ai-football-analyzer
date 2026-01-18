import sqlite3
import json
from datetime import datetime

class DBManager:
    def __init__(self, db_path="football_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                full_analysis TEXT,
                predicted_result TEXT,
                actual_result TEXT,
                is_correct BOOLEAN,
                lesson_learned TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_prediction(self, home, away, analysis, predicted_result):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure predicted_result is stored as string (JSON if possible)
        if isinstance(predicted_result, (dict, list)):
            predicted_result = json.dumps(predicted_result)
        else:
            predicted_result = str(predicted_result)

        c.execute('''
            INSERT INTO predictions (date, home_team, away_team, full_analysis, predicted_result)
            VALUES (?, ?, ?, ?, ?)
        ''', (date_str, home, away, json.dumps(analysis), predicted_result))
        conn.commit()
        conn.close()

    def get_all_predictions(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM predictions ORDER BY date DESC, id DESC')
        rows = c.fetchall()
        columns = [desc[0] for desc in c.description]
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
        conn.close()
        return results

    def update_result(self, prediction_id, actual_result, is_correct, lesson):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            UPDATE predictions 
            SET actual_result = ?, is_correct = ?, lesson_learned = ?
            WHERE id = ?
        ''', (actual_result, is_correct, lesson, prediction_id))
        conn.commit()
        conn.close()

    def delete_prediction(self, prediction_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM predictions WHERE id = ?', (prediction_id,))
        conn.commit()
        conn.close()

    def get_lessons(self):
        # Retrieve lessons from incorrect predictions to feed back to the Boss
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT home_team, away_team, lesson_learned 
            FROM predictions 
            WHERE is_correct = 0 AND lesson_learned IS NOT NULL
        ''')
        rows = c.fetchall()
        lessons = [f"{r[0]} vs {r[1]}: {r[2]}" for r in rows]
        conn.close()
        return lessons
