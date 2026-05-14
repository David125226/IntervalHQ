import json
import os

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='.')


def db_connect():
    url = os.environ.get('DATABASE_URL', '')
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return psycopg2.connect(url, connect_timeout=10)


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS timers (
            name TEXT PRIMARY KEY,
            data JSONB NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('Strength', 'Cardio', 'Core'))
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS circuits (
            name TEXT PRIMARY KEY,
            data JSONB NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)


# --- Timers ---

@app.route('/api/timers', methods=['GET'])
def list_timers():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT name FROM timers ORDER BY name')
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(names)


@app.route('/api/timers/<name>', methods=['GET'])
def get_timer(name):
    conn = db_connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT data FROM timers WHERE name = %s', (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(row['data'])


@app.route('/api/timers/<name>', methods=['PUT'])
def save_timer(name):
    data = request.get_json()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO timers (name, data) VALUES (%s, %s) '
        'ON CONFLICT (name) DO UPDATE SET data = EXCLUDED.data',
        (name, json.dumps(data))
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/timers/<name>', methods=['DELETE'])
def delete_timer(name):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DELETE FROM timers WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


# --- Exercises ---

@app.route('/api/exercises', methods=['GET'])
def list_exercises():
    category = request.args.get('category')
    conn = db_connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if category:
        cur.execute(
            'SELECT id, name, category FROM exercises WHERE category = %s ORDER BY category, name',
            (category,)
        )
    else:
        cur.execute('SELECT id, name, category FROM exercises ORDER BY category, name')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/exercises', methods=['POST'])
def add_exercise():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    category = data.get('category', '')
    if not name or category not in ('Strength', 'Cardio', 'Core'):
        return jsonify({'error': 'Invalid data'}), 400
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO exercises (name, category) VALUES (%s, %s) RETURNING id',
        (name, category)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'id': new_id, 'name': name, 'category': category}), 201


@app.route('/api/exercises/<int:exercise_id>', methods=['PUT'])
def update_exercise(exercise_id):
    data = request.get_json()
    name = (data.get('name') or '').strip()
    category = data.get('category', '')
    if not name or category not in ('Strength', 'Cardio', 'Core'):
        return jsonify({'error': 'Invalid data'}), 400
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        'UPDATE exercises SET name = %s, category = %s WHERE id = %s',
        (name, category, exercise_id)
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/exercises/<int:exercise_id>', methods=['DELETE'])
def delete_exercise(exercise_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DELETE FROM exercises WHERE id = %s', (exercise_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


# --- Circuits ---

@app.route('/api/circuits', methods=['GET'])
def list_circuits():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT name FROM circuits ORDER BY name')
    names = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(names)


@app.route('/api/circuits/<name>', methods=['GET'])
def get_circuit(name):
    conn = db_connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT data FROM circuits WHERE name = %s', (name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(row['data'])


@app.route('/api/circuits/<name>', methods=['PUT'])
def save_circuit(name):
    data = request.get_json()
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO circuits (name, data) VALUES (%s, %s) '
        'ON CONFLICT (name) DO UPDATE SET data = EXCLUDED.data',
        (name, json.dumps(data))
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/circuits/<name>', methods=['DELETE'])
def delete_circuit(name):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DELETE FROM circuits WHERE name = %s', (name,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'ok': True})


_db_initialized = False


@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
        except Exception as e:
            print(f'Warning: could not initialise database — {e}')
        _db_initialized = True


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
