import os
import shutil

from flask_login import LoginManager, logout_user, login_required, current_user, login_user
from flask import Flask, render_template, url_for, redirect, request, make_response, session, abort, jsonify
from werkzeug.utils import secure_filename

import news_resources
from data.news import News
from data.users import User
from forms.loginform import LoginForm
from forms.news import NewsForm
from forms.user import RegisterForm
from forms.profile import ProfileForm
from data import db_session, news_api
from flask_restful import abort, Api

MAX_FILE_SIZE = 1024 * 1024 + 1

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
api = Api(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/')
@app.route('/index')
def index():
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        news = db_sess.query(News).filter(
            (News.user == current_user) | (News.is_private == True) | (News.is_private != True))
    else:
        news = db_sess.query(News).filter(News.is_private != True)
    return render_template("index.html", news=news)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/project3/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/odd_even')
def odd_even():
    return render_template('odd_even.html', number=2)


@app.route('/variable')
def variable():
    return render_template('variable.html', title='Переменная')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/project3/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/profile/<int:id>', methods=['GET', 'POST'])
@login_required
def profile(id):
    form = ProfileForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == id).first()
        if user:
            form.email.data = user.email
            form.name.data = user.name
            form.about.data = user.about
        else:
            abort(404)

    elif form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == id).first()
        if user:
            user.email = form.email.data
            user.name = form.name.data
            user.about = form.about.data
            db_sess.commit()

            if 'file' not in request.files:  # файл нету
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':  # файл не выбран пользолвателем
                return redirect("/project3/")

            if file:
                if os.path.exists(f'static/img/{id}'):
                    shutil.rmtree(f'static/img/{id}')

                child_folder = os.path.join('static/img/', str(id))
                os.makedirs(child_folder)

                filename = secure_filename(file.filename)
                file.save(f'static/img/{id}/{filename}')
                user.photo = f'img/{id}/{filename}'
                db_sess.commit()
                #return render_template('profile.html', form=form, filename=filename)
            return redirect("/project3/")

            db_sess.commit()
        else:
            abort(404)
    return render_template('profile.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/project3/")


@app.route('/news', methods=['GET', 'POST'])
@login_required
def add_news():
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = News()
        news.title = form.title.data
        news.content = form.content.data
        news.is_private = form.is_private.data
        current_user.news.append(news)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/project3/')
    return render_template('news.html', title='Добавление новости',
                           form=form)


@app.route('/news/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_news(id):
    form = NewsForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            form.title.data = news.title
            form.content.data = news.content
            form.is_private.data = news.is_private
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.id == id,
                                          News.user == current_user
                                          ).first()
        if news:
            news.title = form.title.data
            news.content = form.content.data
            news.is_private = form.is_private.data
            db_sess.commit()
            return redirect('/project3/')
        else:
            abort(404)
    return render_template('news.html',
                           title='Редактирование новости',
                           form=form
                           )


@app.route('/news_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def news_delete(id):
    db_sess = db_session.create_session()
    news = db_sess.query(News).filter(News.id == id,
                                      News.user == current_user
                                      ).first()
    if news:
        db_sess.delete(news)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/project3/')


@app.route('/new_new')
def new_new():
    db_sess = db_session.create_session()
    user = db_sess.query(User).first()

    news = News(title="Личная запись", content="Эта запись личная",
                is_private=True)
    user.news.append(news)
    db_sess.commit()
    return user.name


@app.route('/update_user')
def update_user():
    db_sess = db_session.create_session()
    user = db_sess.query(User).first()
    if user:
        user.name = "Пользователь 2"
        db_sess.commit()
    return user.name


@app.route('/new_user')
def new_user():
    db_sess = db_session.create_session()
    user = db_sess.query(User).first()
    if not user:
        user = User()
        user.name = "Пользователь 1"
        user.about = "биография пользователя 1"
        user.email = "email@email.ru"

        db_sess.add(user)
        db_sess.commit()
    print(user.name)
    return user.name


@app.route("/cookie_test")
def cookie_test():
    visits_count = int(request.cookies.get("visits_count", 0))
    if visits_count:
        res = make_response(
            f"Вы пришли на эту страницу {visits_count + 1} раз")
        res.set_cookie("visits_count", str(visits_count + 1),
                       max_age=60 * 60 * 24 * 365 * 2)
    else:
        res = make_response(
            "Вы пришли на эту страницу в первый раз за последние 2 года")
        res.set_cookie("visits_count", '1',
                       max_age=60 * 60 * 24 * 365 * 2)
    return res


@app.route("/session_test")
def session_test():
    visits_count = session.get('visits_count', 0)
    session['visits_count'] = visits_count + 1
    return make_response(
        f"Вы пришли на эту страницу {visits_count + 1} раз")


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': '404'}), 404)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


if __name__ == '__main__':
    db_session.global_init("db/blogs.db")
    app.register_blueprint(news_api.blueprint)
    # для списка объектов
    api.add_resource(news_resources.NewsListResource, '/api/v2/news')

    # для одного объекта
    api.add_resource(news_resources.NewsResource, '/api/v2/news/<int:news_id>')
    app.run(port=8080, host='0.0.0.0')
