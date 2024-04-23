from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify, abort, flash
from datetime import timedelta
from pymongo import MongoClient
from flask_login import LoginManager, login_user, current_user, login_required
from flask_login import UserMixin
from gridfs import GridFS
from bson.objectid import ObjectId
import secrets


app = Flask(__name__)
secret_key = secrets.token_hex(16)
app.secret_key = secret_key
app.config['SECRET_KEY'] = secret_key

login_manager = LoginManager()
login_manager.init_app(app)

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

class User(UserMixin):
    def __init__(self, id, username, name):
        self.id = id
        self.username = username
        self.name = name
        
        
        
@app.route('/edit')
def edit():
    return render_template('edit.html')

@app.route('/tic-tac')
def tictac():
    return render_template('tic-tac.html')

@app.route('/sweet-memory')
def sweet():
    return render_template('sweet-memory.html')



@login_manager.user_loader
def load_user(user_id):
    # Query the MongoDB collection to find the user by user ID
    user_data = collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        # Create a User object with the retrieved user data
        user = User(user_data['_id'], user_data['username'], user_data['email'])
        return user
    return None



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        class1 = request.form['class']

        existing_user = collection.find_one({'username': username})
        if existing_user:
            return "User already exists. Please choose another username."

        # Set default avatar if user doesn't provide one
        user_avatar = request.form.get('avatar', default_avatar_url)

        user = {'username': username, 'password': password, 'email': email, 'avatar': user_avatar, 'verified': False, 'name': name, 'class': class1}
        collection.insert_one(user)

        return redirect(url_for('profile', username=username))

    return render_template('register.html')

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    if 'username' not in session:
        return redirect(url_for('login'))

    user_data = collection.find_one({'username': username})
    friends = user_data.get("friends", [])
    
    if session['username'] != username:
        abort(403, "You do not have permission to view this profile")

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
            return render_template('profile.html', username=user_data['username'], email=user_data['email'], name=name, friends=friends)
    else:
        return "User not found."


@app.route('/profiles')
def profiles():
    all_users = collection.find()
    return render_template('profiles.html', all_users=all_users)

@app.route('/upload_profile_image', methods=['POST'])
def upload_profile_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    image_file = request.files['image']
    user_id = request.form['user_id']

    if image_file.filename == '':
        return jsonify({'error': 'No selected image'}), 400
    
    if image_file:
        # Save image to MongoDB GridFS
        file_id = fs.put(image_file, user_id=user_id)

        # Optionally, update user profile with image file id
        mongo.db.users.update_one({'_id': user_id}, {'$set': {'profile_image_id': file_id}})

        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Failed to upload image'}), 500


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


def get_user_profile(username):
    return collection.find_one({"username": username})  # Получение профиля по имени пользователя



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember', 'false')  # Check if "Remember Me" is selected
        
        # Query the database to find the user by username
        user = collection.find_one({'username': username})
        if user and user['password'] == password:
            # Save the username in session
            session['username'] = username
            
            # If "Remember Me" is checked, set a longer-lasting cookie
            if remember == 'true':
                resp = make_response(redirect(url_for('profile', username=username)))
                # Set a cookie to remember the user for a week (604800 seconds)
                resp.set_cookie('username', username, max_age=604800, secure=True, httponly=True, samesite='Strict')
                return resp
            
            return redirect(url_for('profile', username=username))
        
        # If login fails, render the login page with an error message
        return render_template('login.html', error='Invalid username or password')
    
    # For GET requests, render the login page
    return render_template('login.html')


@app.route('/view_profile/<username>')
def view_other_profile(username):
    if 'username' not in session:  # Если пользователь не вошел, перенаправьте на страницу входа
        flash("You need to be logged in to view profiles.")  # Дополнительное сообщение
        return redirect(url_for('login'))

    user_profile = get_user_profile(username)  # Получаем профиль пользователя из MongoDB
    if not user_profile:  # Если профиль не найден, верните ошибку 404
        abort(404, description="Profile not found")

    # Проверка, является ли текущий пользователь другом с профилем, который он просматривает
    current_username = session['username']
    is_friend = current_username in user_profile.get('friends', [])

    return render_template('view_profile.html', user=user_profile, is_friend=is_friend)

@app.route('/verify_user/<username>')
def verify_user(username):
    user_data = collection.find_one({'username': username})
    if user_data:
        collection.update_one({'username': username}, {'$set': {'verified': True}})
        return redirect(url_for('admin_panel'))
    else:
        return "Пользователь не найден."
    
    
@app.route('/search_users', methods=['POST'])
def search_users():
    current_user = session.get('username')  # Имя текущего пользователя
    query = request.form.get('query')  # Получаем запрос из формы
    
    # Поиск пользователей, чье имя или имя пользователя совпадает с запросом
    if query:
        results = collection.find({
            '$or': [
                {'username': {'$regex': query, '$options': 'i'}},
                {'name': {'$regex': query, '$options': 'i'}}
            ],
            'username': {'$ne': current_user}  # Исключаем текущего пользователя
        })
        
        users = []
        for user in results:
            users.append({
                'username': user['username'],
                'name': user['name'],
                'avatar': user['avatar']
            })
        
        return jsonify(users)  # Возвращаем найденных пользователей
    
    return jsonify([])

@app.route('/friends', methods=['GET', 'POST'])
def friends():
    if 'username' not in session:
        # If the user isn't logged in, redirect to the login page or show an error message
        return redirect(url_for('login'))  # Or render a different template

    username = session['username']
    user = collection.find_one({'username': username})

    if not user:
        # If the user does not exist in the database, handle accordingly
        return "User not found in the database", 404

    friends_list = user.get('friends', [])

    if request.method == 'POST':
        search_user = request.form.get('search_user')
        if search_user:
            # Add friend request
            send_friend_request(username, search_user)
    
    return render_template('friends.html', friends=friends_list)



@app.route('/send_friend_request', methods=['POST'])
def send_friend_request():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    current_username = session['username']
    requested_username = request.form.get('requested_username')  # Правильное имя ключа для поиска

    if not requested_username:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400

    requested_user = collection.find_one({'username': requested_username})

    if not requested_user:
        return jsonify({'status': 'error', 'message': f"User {requested_username} not found"}), 404

    # Добавить запрос в список ожидающих запросов
    collection.update_one(
        {'username': requested_username},
        {'$addToSet': {'pending_friend_requests': current_username}}
    )

    return jsonify({'status': 'success', 'message': 'Friend request sent'})  # Возвращаем JSON-ответ


@app.route('/accept_friend_request', methods=['POST'])
def accept_friend_request():
    current_user = session['username']
    requester = request.form['requester']
    
    # Обновите записи обоих пользователей, добавив в друзья и удалив запрос
    collection.update_one(
        {"username": current_user},
        {
            "$addToSet": {"friends": requester},
            "$pull": {"friend_requests": requester}
        }
    )
    
    collection.update_one(
        {"username": requester},
        {
            "$addToSet": {"friends": current_user}
        }
    )
    
    return redirect(url_for('profile', username=current_user))

@app.route('/remove_friend', methods=['POST'])
def remove_friend():
    if 'username' not in session:
        return redirect(url_for('login'))

    friend_to_remove = request.form.get('friend_to_remove')
    if not friend_to_remove:
        return "Invalid request", 400

    current_username = session['username']

    # Check if the current user exists
    current_user = collection.find_one({'username': current_username})
    if not current_user:
        return "Current user not found in the database", 404

    # Check if the friend exists in the current user's friend list
    friend_exists = friend_to_remove in [f.get('username') for f in current_user.get('friends', [])]

    if not friend_exists:
        return f"{friend_to_remove} is not your friend", 404

    # Remove the friend from the current user's list
    collection.update_one(
        {'username': current_username},
        {'$pull': {'friends': {'username': friend_to_remove}}}
    )
    
    return redirect(url_for('friends'))


@app.route('/update_bio', methods=['POST'])
def update_bio():
    if 'username' not in session:
        return jsonify({'error': 'You need to log in to update your bio'}), 401
    
    username = session['username']
    new_bio = request.json.get('bio')

    if not new_bio:
        return jsonify({'error': 'Bio cannot be empty'}), 400
    
    # Обновляем биографию пользователя в базе данных
    users.update_one({'username': username}, {'$set': {'bio': new_bio}})
    
    return jsonify({'success': True, 'bio': new_bio}), 200

if __name__ == '__main__':
    app.run(debug=True)
