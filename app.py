from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import random
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app)

USERS_FILE = 'users.json'
MESSAGES_FILE = 'messages.json'

COLORS = ['#FF5733', '#33FF57', '#3357FF', '#F1C40F', '#9B59B6', '#E67E22']

def load_json(filename, default):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_users():
    return load_json(USERS_FILE, [])

def save_users(users):
    save_json(USERS_FILE, users)

def find_user(username):
    users = get_users()
    return next((u for u in users if u['username'] == username), None)

def get_messages():
    return load_json(MESSAGES_FILE, [])

def save_messages(messages):
    save_json(MESSAGES_FILE, messages)

def get_user_colors(users):
    return {u['username']: u.get('color', '#000000') for u in users}

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('register.html', error="Veuillez remplir tous les champs.")
        if len(username) > 30 or len(password) > 50:
            return render_template('register.html', error="Nom d'utilisateur ou mot de passe trop long.")
        if find_user(username):
            return render_template('register.html', error="Nom d'utilisateur déjà pris.")

        color = random.choice(COLORS)
        hashed_pw = generate_password_hash(password)

        users = get_users()
        users.append({'username': username, 'password': hashed_pw, 'color': color})
        save_users(users)

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = find_user(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error="Nom d'utilisateur ou mot de passe incorrect.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    users = get_users()
    user_colors = get_user_colors(users)
    messages = get_messages()

    return render_template('chat.html',
                           username=username,
                           messages=messages,
                           user_colors=user_colors)

# SocketIO event handlers
@socketio.on('send_message')
def handle_send_message(data):
    username = session.get('username')
    if not username:
        return
    message_text = data.get('message', '').strip()
    if not message_text:
        return
    messages = get_messages()
    messages.append({'username': username, 'message': message_text})
    save_messages(messages)
    users = get_users()
    user_colors = get_user_colors(users)
    emit('receive_message', {
        'username': username,
        'message': message_text,
        'color': user_colors.get(username, '#FFFFFF')
    }, broadcast=True)

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 8080
    print(f"Serveur lancé. Accédez à http://localhost:{port} dans votre navigateur.")
    socketio.run(app, host=host, port=port, debug=True)
