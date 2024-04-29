from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from pymongo import MongoClient
from bson.objectid import ObjectId
from gridfs import GridFS
import datetime

# Flask и MongoDB настройки
app = Flask(__name__)  # Инициализация Flask-приложения
app.secret_key = "super_secret_key"  # Секретный ключ для сессий
client = MongoClient('mongodb://localhost:27017/')  # Подключение к MongoDB
db = client['local']  # Выбор базы данных
users_collection = db['users']  # Коллекция пользователей
messages_collection = db['messages']  # Коллекция сообщений
fs = GridFS(db)  # Работа с GridFS

# Настройка Flask-Login
login_manager = LoginManager()  # Инициализация менеджера входа
login_manager.init_app(app)  # Привязка к Flask-приложению
login_manager.login_view = 'login'  # Страница для входа при неавторизованном доступе

# Класс пользователя для Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = str(user_id)  # Строковое представление идентификатора
        self.username = username  # Имя пользователя

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})  # Загрузка пользователя
    if user_data:
        return User(str(user_data['_id']), user_data['username'])
    return None

# Главная страница
@app.route('/')
def home():
    return render_template('index.html')  # Отображение шаблона главной страницы

@app.route('/games')
def games():
    return render_template('games.html')

@app.route('/tic-tac')
def tictac():
    return render_template('tic-tac.html')# Отображение шаблона главной страницы

@app.route('/flappy-bird')
def flappybird():
    return render_template('flappybird.html')

@app.route('/2048')
def c2048():
    return render_template('2048.html')

@app.route('/sweet-memory')
def memory():
    return render_template('sweet-memory.html')

# Обработка ошибок
@app.errorhandler(404)  # Обработка ошибки "Страница не найдена"
def page_not_found(e):
    return render_template('404.html'), 404  # Возвращает 404 и отображает шаблон ошибки

@app.errorhandler(500)  # Обработка внутренней ошибки сервера
def internal_server_error(e):
    return render_template('500.html'), 500  # Возвращает 500 и отображает шаблон ошибки

# Маршрут для регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')  # Получение имени из формы
        username = request.form.get('username')  # Получение имени пользователя
        password = request.form.get('password')  # Получение пароля
        email = request.form.get('email')  # Получение электронной почты

        # Проверка, существует ли пользователь
        existing_user = users_collection.find_one({'username': username})
        if existing_user:  # Если пользователь уже существует
            flash("Такое имя пользователя уже занято. Выберите другое.")  # Сообщение об ошибке
            return render_template('register.html')  # Возврат на страницу регистрации

        # Создание нового пользователя
        default_avatar_url = 'https://static.vecteezy.com/system/resources/previews/009/292/244/original/default-avatar-icon-of-social-media-user-vector.jpg'
        new_user = {
            'username': username,
            'password': password,
            'email': email,
            'avatar': default_avatar_url,
            'name': name,
            'verified': False,
        }
        users_collection.insert_one(new_user)  # Сохранение нового пользователя в MongoDB

        flash("Регистрация прошла успешно. Пожалуйста, войдите.")  # Успешное сообщение
        return redirect(url_for('login'))  # Перенаправление на страницу входа

    return render_template('register.html')  # Отображение страницы регистрации

# Маршрут для входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # Если метод POST
        username = request.form['username']  # Имя пользователя
        password = request.form['password']  # Пароль

        user = users_collection.find_one({'username': username})  # Поиск пользователя по имени

        if user and user['password'] == password:  # Если пользователь найден и пароль совпадает
            login_user(User(user['_id'], user['username']))  # Вход с помощью Flask-Login
            session['username'] = username  # Установка имени в сессии

            remember = request.form.get('remember', 'false')  # Проверка "Запомнить меня"
            if remember == 'true':  # Если выбрано
                resp = make_response(redirect(url_for('profile', username=username)))  # Перенаправление на профиль
                resp.set_cookie('username', username, max_age=604800, secure=True, httponly=True, samesite='Strict')
                return resp

            return redirect(url_for('profile', username=username))  # Перенаправление на профиль
        else:
            flash("Неправильное имя пользователя или пароль")  # Сообщение об ошибке

    return render_template('login.html')  # Отображение страницы входа

# Маршрут для выхода
@app.route('/logout')
@login_required  # Только для авторизованных пользователей
def logout():
    logout_user()  # Завершение сеанса пользователя
    session.pop('username', None)  # Удаление имени из сессии
    return redirect(url_for('login'))  # Перенаправление на страницу входа

# Маршрут для профиля пользователя
@app.route('/profile/<username>')
@login_required  # Только для авторизованных пользователей
def profile(username):
    current_username = session.get('username', None)  # Получение текущего пользователя
    
    if current_username != username:  # Если запрашиваемый профиль не принадлежит текущему пользователю
        flash("You do not have permission to view this profile.")  # Сообщение об ошибке
        return redirect(url_for('home'))  # Перенаправление на главную страницу
    
    # Загрузка данных профиля
    user_data = users_collection.find_one({'username': username})

    if not user_data:
        return render_template('404.html'), 404  # Если пользователь не найден, вернуть 404
    
    # Извлекаем список друзей
    friends = user_data.get('friends', [])
    friend_count = len(friends)

    # Возвращаем профиль и другие данные
    return render_template(
        'profile.html', 
        username=user_data['username'], 
        friend_count=friend_count, 
        name=user_data.get('name', 'Name Not Available'), 
        image_url=f"https://example.com/image/{user_data.get('profile_image_id', 'default')}"
    )

# Маршрут для загрузки аватара
@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'image' not in request.files:  # Если файл изображения не передан
        return jsonify({'error': 'Не предоставлено изображение'}), 400

    image_file = request.files['image']  # Получение изображения
    user_id = request.form.get('user_id')  # Получение ID пользователя

    if not image_file or image_file.filename == '':  # Если файл пустой
        return jsonify({'error': 'Нет выбранного изображения'}), 400

    try:
        file_id = fs.put(image_file, content_type=image_file.mimetype)  # Сохранение в GridFS
        users_collection.update_one(
            {'_id': ObjectId(user_id)},  # Обновление документа пользователя
            {'$set': {'profile_image_id': file_id}}
        )

        return jsonify({'success': True}), 200  # Возвращение успеха
    except Exception as e:  # Обработка ошибок
        app.logger.error(f"Ошибка при загрузке изображения профиля: {e}")  # Логирование ошибки
        return jsonify({'error': 'Не удалось загрузить изображение'}), 500

# Маршрут для чата
@app.route('/chat')
@login_required  # Только для авторизованных пользователей
def chat():
    user = users_collection.find_one({'username': session['username']})  # Получение пользователя
    if not user:  # Если пользователь не найден
        flash("Пользователь не найден.")  # Сообщение об ошибке
        return redirect(url_for('login'))

    friends = user.get('friends', [])  # Список друзей
    friends_data = []

    for friend in friends:
        friend_user = users_collection.find_one({'username': friend})
        if friend_user:
            friends_data.append({
                'username': friend_user['username'],
                'name': friend_user.get('name', "Неизвестно"),  # Получение имени
                'avatar': friend_user.get('avatar', 'https://default.avatar.url'),  # Получение аватара
            })

    return render_template('chat.html', friends=friends_data)  # Отображение чата


@app.route('/view_profile/<username>')
def view_other_profile(username):
    user_profile = users_collection.find_one({'username': username})
    
    if not user_profile:
        return render_template('404.html'), 404  # Вернуть страницу 404, если профиль не найден
    
    # Выберите данные, которые хотите отобразить
    return render_template('view_profile.html', user=user_profile)


# Маршрут для истории чатов
@app.route('/chat_history', methods=['GET'])
@login_required
def chat_history():
    friend_username = request.args.get('username')  # Получение имени друга

    if not friend_username:  # Если имя друга не передано
        return jsonify({'error': 'Требуется имя друга'}), 400

    # Получение истории чата между текущим пользователем и указанным другом
    messages = messages_collection.find({
        '$or': [
            {'from': session['username'], 'to': friend_username},
            {'from': friend_username, 'to': session['username']},
        ],
    }).sort('timestamp')  # Сортировка по времени

    history = [{'from': message['from'], 'content': message['content']}]  # Список истории

    return jsonify({'history': history})  # Возвращение истории чатов

# Маршрут для добавления друга
@app.route('/add_friend', methods=['POST'])
@login_required
def add_friend():
    current_user = session['username']  # Текущий пользователь
    friend_username = request.form['friend_username']  # Имя друга

    if not friend_username:  # Если имя друга не передано
        return jsonify({'status': 'error', 'message': 'Требуется имя друга'}), 400

    if current_user == friend_username:  # Если пользователь пытается добавить себя
        return jsonify({'status': 'error', 'message': 'Нельзя добавить себя в друзья'}), 400

    # Добавление запроса на дружбу
    users_collection.update_one(
        {'username': friend_username}, 
        {'$addToSet': {'pending_friend_requests': current_user}}
    )

    return jsonify({'status': 'success', 'message': 'Запрос на дружбу отправлен'})

# Маршрут для принятия запроса на дружбу
@app.route('/accept_friend_request', methods=['POST'])
@login_required
def accept_friend_request():
    current_user = session['username']  # Текущий пользователь
    requester = request.form['requester']  # Пользователь, отправивший запрос

    # Добавление обоих пользователей в друзья и удаление запроса
    users_collection.update_one(
        {'username': current_user}, 
        {'$addToSet': {'friends': requester}, '$pull': {'pending_friend_requests': requester}}
    )

    users_collection.update_one(
        {'username': requester}, 
        {'$addToSet': {'friends': current_user}}
    )

    return jsonify({'status': 'success', 'message': 'Запрос на дружбу принят'})

@app.route('/friends', methods=['GET'])
@login_required
def friends():
    # Ваш код для отображения списка друзей
    username = session.get('username', None)
    if not username:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'username': username})
    if not user:
        return "User not found", 404
    
    friends = user.get('friends', [])
    
    return render_template('friends.html', friends=friends)



@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    requested_username = request.form.get('requested_username')
    current_username = session.get('username')

    if not current_username:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    logging.info(f"Send friend request from {current_username} to {requested_username}")

    if not requested_username:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400

    users_collection.update_one(
        {'username': requested_username},
        {'$addToSet': {'pending_friend_requests': current_username}}
    )

    return jsonify({'status': 'success', 'message': 'Friend request sent'})

@app.route('/search_users', methods=['POST'])
def search_users():
    query = request.form.get('query', '')
    results = users_collection.find({
        '$or': [
            {'username': {'$regex': query, '$options': 'i'}},
            {'name': {'$regex': query, '$options': 'i'}}
        ],
        'username': {'$ne': session['username']}  # Исключаем текущего пользователя
    })
    
    users = []
    for user in results:
        users.append({
            'username': user['username'],
            'name': user['name'],
            'avatar': user.get('avatar', 'https://default.avatar.url'),
        })
    
    return jsonify(users)  # Возвращаем найденных пользователей



# Маршрут для удаления друга
@app.route('/remove_friend', methods=['POST'])
@login_required
def remove_friend():
    current_user = session['username']  # Текущий пользователь
    friend_to_remove = request.form['friend_to_remove']  # Имя друга для удаления

    if not friend_to_remove:  # Если имя друга не передано
        return jsonify({'status': 'error', 'message': 'Недействительный запрос'}), 400

    # Удаление друга из списка друзей текущего пользователя
    users_collection.update_one(
        {'username': current_user}, 
        {'$pull': {'friends': friend_to_remove}}
    )

    return jsonify({'status': 'success', 'message': f'{friend_to_remove} удален из списка друзей'})

# Маршрут для админ-панели
@app.route('/admin_panel', methods=['GET', 'POST'])
@login_required  # Требуется аутентификация
def admin_panel():
    if not session.get('is_admin', False):  # Проверка на администратора
        return redirect(url_for('login'))  # Перенаправление, если не администратор

    if request.method == 'POST':  # Обработка POST-запроса
        title = request.form['title']  # Заголовок поста
        content = request.form['content']  # Содержимое поста
        new_post = {
            'title': title, 
            'content': content, 
            'created_at': datetime.datetime.utcnow()  # Время создания
        }
        messages_collection.insert_one(new_post)  # Добавление в MongoDB
        return redirect(url_for('admin_panel'))

    # Отображение админ-панели
    posts = messages_collection.find().sort('created_at', -1)  # Сортировка по времени
    return render_template('admin_panel.html', posts=posts)  # Отображение панели

# Маршрут для выхода из админ-панели
@app.route('/admin_logout')
@login_required  # Только для авторизованных пользователей
def admin_logout():
    session.pop('is_admin', None)  # Удаление флага администратора
    logout_user()  # Завершение сеанса администратора
    return redirect(url_for('login'))  # Перенаправление на страницу входа

if __name__ == '__main__':
    app.run(debug=True)
