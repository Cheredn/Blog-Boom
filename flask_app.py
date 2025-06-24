from flask import Flask, render_template, request,redirect, url_for
import jinja2
import sqlite3
app = Flask(__name__)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app.config['SECRET_KEY'] = '123123A'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def set_password(self,password):
        self.password_hash = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    user = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,
                                                               )).fetchone()
    if user is not None:
        return User(user[0], user[1], user[2])
    return None
def close_db(connection=None):
    if connection is not None:
        connection.close()

@app.teardown_appcontext
def close_connection(exception):
    close_db()

def user_is_liking(user_id, post_id):
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    like = cursor.execute(
        'SELECT * FROM likes WHERE user_id = ? AND post_id = ?',
        (user_id, post_id)).fetchone()
    return bool(like)


@app.route('/like/<int:post_id>')
@login_required
def like_post(post_id):
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    post = cursor.execute('SELECT * FROM posts WHERE id = ?',
                          (post_id,)).fetchone()
    if post:
        if user_is_liking(current_user.id, post_id):
            cursor.execute(
                'DELETE FROM likes WHERE user_id = ? AND post_id = ?',
                (current_user.id, post_id))
            connection.commit()
            print('User unliked post.')
        else:
            cursor.execute(
                'INSERT INTO likes (user_id, post_id) VALUES (?,?)',
                (current_user.id, post_id))
            connection.commit()
            print('User liked post.')
        return redirect(url_for('index'))
    return 'Post not found', 404

@app.route('/createpost/', methods=['GET','POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form['name_post']
        content = request.form['text_post']
        connection = sqlite3.connect("sqlite.db")
        cursor = connection.cursor()
        cursor.execute('INSERT INTO posts(name_post, text_post, author_id) VALUES (?,?,?)',
                       (title, content, current_user.id))
        connection.commit()
        return redirect(url_for('index'))
    return render_template('add_post.html')

@app.route('/delete/<int:post_id>/', methods=['POST'])
@login_required
def delete_post(post_id):
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    post = cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    print(post, post[3], current_user.id)
    if post and (post[3] == current_user.id or current_user.id == 7):
        cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        connection.commit()
        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))

@app.route('/')
def index():
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    cursor.execute('''
            SELECT
                posts.id,
                posts.name_post,
                posts.text_post,
                posts.author_id,
                users.username,
                COUNT(likes.id) AS likes
            FROM
                posts
            JOIN
                users ON posts.author_id = users.id
            LEFT JOIN
                likes ON posts.id = likes.post_id
            GROUP BY
                posts.id, posts.name_post, posts.text_post, posts.author_id, users.username
             ''')
    result = cursor.fetchall()
    posts = []
    for post in reversed(result):
        posts.append({
                'id': post[0],
                'title': post[1],
                'text': post[2],
                'author_id': post[3],
                'username': post[4],
                'likes': post[5]
            })
        if current_user.is_authenticated:
            cursor.execute('SELECT post_id FROM likes WHERE user_id = ?', (current_user.id,))
            likes_result = cursor.fetchall()
            liked_posts = []
            for like in likes_result:
                liked_posts.append(like[0])
            posts[-1]['liked_posts'] = liked_posts
    context = {
    'posts': posts
    }
    connection.close()
    return render_template('Blog_main.html', **context)


@app.route('/post/<post_id>')
def post_view(post_id):
    print(type(post_id))
    connection = sqlite3.connect("sqlite.db")
    cursor = connection.cursor()
    result = cursor.execute('SELECT * FROM posts JOIN users ON posts.author_id = users.id WHERE posts.id=?',
                            (post_id,)).fetchone()
    # username = cursor.execute('SELECT * FROM posts JOIN users ON posts.author_id = users.id').fetchone()
    post_dict = {'id': result[0], 'title': result[1], 'content': result[2], 'author_id': result[3], 'username': result[5]}
    connection.close()
    return render_template('post_view.html', post=post_dict)

@app.route('/signin/',methods=['GET','POST'])
def sign_in():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        connection = sqlite3.connect("sqlite.db")
        cursor = connection.cursor()
        try:
            cursor.execute('INSERT INTO users(username, password_hash, email) VALUES (?,?,?)',
                           (username, generate_password_hash(password), email))
            connection.commit()
            print('Регистрация  пользователя прошла успешно!')
            return redirect(url_for('log_in'))
        except sqlite3.IntegrityError:
            return render_template('register.html',
                                   message='Username or email already exists!')
    return render_template('register.html')

@app.route('/login/',methods=['GET','POST'])
def log_in():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = sqlite3.connect("sqlite.db")
        cursor = connection.cursor()
        user = cursor.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and User(user[0], user[1], user[2]).check_password(password):
            login_user(User(user[0], user[1], user[2]))
            print('Вход пользователя прошел успешно!')
            return redirect(url_for('index'))
        else:
            return render_template('login.html',
                                   message='Invalid username or password')
    return render_template('login.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()