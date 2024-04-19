from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
from datetime import timedelta
from pymongo import MongoClient
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

default_avatar_url = 'https://static.vecteezy.com/system/resources/previews/009/292/244/original/default-avatar-icon-of-social-media-user-vector.jpg'

client = MongoClient('mongodb://localhost:27017/')
db = client['local']
collection = db['users']
posts_collection = db['posts']


@app.route('/')
def home():
    return render_template('index.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']  # Add this line to retrieve the name from the form
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        class1 = request.form['class']

        existing_user = collection.find_one({'username': username})
        if existing_user:
            return "User already exists. Please choose another username."

        # Set default avatar if user doesn't provide one
        user_avatar = request.form.get('avatar', default_avatar_url)

        # Include the 'name' field when creating the user
        user = {'username': username, 'password': password, 'email': email, 'avatar': user_avatar, 'verified': False, 'name': name, 'class': class1}
        collection.insert_one(user)

        return redirect(url_for('profile', username=username))

    return render_template('register.html')

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    user_data = collection.find_one({'username': username})
    if user_data:
        if 'name' in user_data:
            name = user_data['name']
        else:
            name = "Name Not Available"
        
        if request.method == 'POST' and 'verification_request' in request.form:
            verification_requests = []  # Define verification_requests locally
            verification_requests.append(username)
            return "Verification request sent. The administrator will be notified."
        else:
            # Pass the 'username' and 'email' variables to the template
            return render_template('profile.html', username=user_data['username'], email=user_data['email'], name=name)
    else:
        return "User not found."


@app.route('/profiles')
def profiles():
    all_users = collection.find()
    return render_template('profiles.html', all_users=all_users)

@app.route('/profile/view/<username>')
def view_profile(username):
    """View profile route."""
    user_data = collection.find_one({'username': username})
    if user_data:
        avatar = user_data.get('avatar', default_avatar_url)  # Use default avatar URL if avatar is not provided
        return render_template('view_profile.html', username=username, avatar=avatar)
    else:
        return "User not found."



@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        
        # Проверяем логин и пароль
        if login == 'admin' and password == 'admin1':
            session['admin'] = True  # Устанавливаем сеанс в качестве администратора
            return redirect(url_for('admin_panel'))  # Перенаправляем на админ-панель после успешной аутентификации
        else:
            return render_template('loginad.html', error=True)  # Отображаем форму с сообщением об ошибке

    if 'admin' in session:
        verification_requests = collection.find({'verified': False})
        return render_template('admin.html', verification_requests=verification_requests)
    else:
        return render_template('loginad.html', error=False)
    

@app.route('/admin/add_post', methods=['POST'])
def add_post():
    if 'admin' not in session:
        return "Доступ запрещен", 403

    title = request.form['title']
    content = request.form['content']
    post = {'title': title, 'content': content}
    posts_collection.insert_one(post)

    return redirect(url_for('admin'))


# Маршрут для выхода из админ-панели
@app.route('/admin/logout')
def logout():
    session.pop('admin', None)  # Удаляем административную сессию
    return redirect(url_for('admin_panel'))

@app.route('/games')
def games():
    # Add your logic here if needed
    return render_template('games.html')  # Render the 'games.html' template



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember')  # Check if "Remember Me" is selected
        
        # Query the database to find the user by username
        user = collection.find_one({'username': username})
        if user and user['password'] == password:
            session['username'] = username
            
            # Set a cookie with a longer expiration time if "Remember Me" is selected
            if remember == 'true':
                resp = make_response(redirect(url_for('profile', username=username)))
                resp.set_cookie('username', username, max_age=604800, secure=True, httponly=True, samesite='Strict')
                return resp
            
            return redirect(url_for('profile', username=username))
        else:
            return render_template('login.html', error='Invalid username or password')

    return render_template('login.html')

@app.route('/verify_user/<username>')
def verify_user(username):
    user_data = collection.find_one({'username': username})
    if user_data:
        collection.update_one({'username': username}, {'$set': {'verified': True}})
        return redirect(url_for('admin_panel'))
    else:
        return "Пользователь не найден."
    
    
@app.route('/search', methods=['POST'])
def search():
    # Получение данных из запроса
    data = request.get_json()
    query = data['query']
    users_checked = data['usersChecked']
    posts_checked = data['postsChecked']

    # Поиск пользователей, если соответствующий флажок установлен
    if users_checked:
        users_results = collection.find({'name': {'$regex': query, '$options': 'i'}})  # Находим пользователей по имени
        users_results = [{'name': user['name']} for user in users_results]  # Преобразуем результаты в список словарей
    else:
        users_results = []

    # Поиск постов, если соответствующий флажок установлен
    if posts_checked:
        posts_results = posts_collection.find({'title': {'$regex': query, '$options': 'i'}})  # Находим посты по заголовку
        posts_results = [{'title': post['title']} for post in posts_results]  # Преобразуем результаты в список словарей
    else:
        posts_results = []

    # Возвращаем результаты поиска в формате JSON
    return jsonify(users=users_results, posts=posts_results)

if __name__ == '__main__':
    app.run(debug=True)
