import os
import datetime
from flask import Flask, request, render_template, flash, redirect, url_for, session, logging
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import pbkdf2_sha256
from functools import wraps
from flask_ckeditor import CKEditor

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "chickensoup.db"))

app = Flask(__name__)
ckeditor = CKEditor(app)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

app.secret_key = "C6H12O6"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80),nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    register_date = db.Column(db.DateTime, default=datetime.datetime.now)

    #def __repr__(self):
        #return "<Name {}, Email {}, Username {}, Password {}, Register Date {}>".format(self.name, self.email, self.username, self.password, self.register_date)

    def __str__(self, name, email, username, password):
        self.name = name.title()
        self.email = email.lower()
        self.username = username
        self.password = password

class Articles(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(80), nullable=False)
    author = db.Column(db.String(80), nullable=False)
    body = db.Column(db.Text)
    create_date = db.Column(db.DateTime, default=datetime.datetime.now)
    
    def __str__(self, title, author, body):
        self.title = title
        self.author = author
        self.body = body
  
@app.route("/")
def index():
    return render_template('home.html')

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/articles")
def articles():
    articles = Articles.query.all()
    return render_template("articles.html",articles=articles)

@app.route("/article/<string:id>/")
def article(id):
    article = Articles.query.filter_by(id=id).first()
    return render_template('article.html', article=article)


class RegisterForm(Form):
    name = StringField('Name:', [validators.length(min=1, max=50)])
    username = StringField('Username:', [validators.length(min=4, max=25)])
    email = StringField('Email:', [validators.length(min=6, max=50)])
    password = PasswordField('Password:', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message="Passwords do not match")
    ])
    confirm = PasswordField('Confirm Password:')

# User register

@app.route("/register", methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        if User.query.filter_by(username=request.form['username']).first():          
            username = User.query.filter_by(username=request.form['username']).first().username
            if form.username.data == username:
                flash("Username exists.",'danger')
                return redirect(url_for('register'))    
        if User.query.filter_by(email=request.form['email']).first():          
            email = User.query.filter_by(email=request.form['email']).first().email
            if form.email.data == email:
                flash("Email exists.",'danger')
                return redirect(url_for('register'))
        else:        
            user = User(name = form.name.data, email = form.email.data, username = form.username.data, password = pbkdf2_sha256.hash(str(form.password.data)))
            db.session.add(user)
            db.session.commit()

            flash('Your are now registered.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html',form=form)

# User login

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form['username']).first():          
            hash = User.query.filter_by(username=request.form['username']).first().password
            username = User.query.filter_by(username=request.form['username']).first().username
            if pbkdf2_sha256.verify(request.form['password'], hash):
                session['logged_in'] = True
                session['username'] = username
                flash('Your are now logged in.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Wrong password.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Invalid username and password', 'danger')
            return redirect(url_for('login'))
    else:
        return render_template('login.html')



# Check if user logged in, not to display dashboard

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Access denied, Please login to continue.', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("You are logged out.", 'success')
    return redirect(url_for('index'))

@app.route("/dashboard")
@is_logged_in
def dashboard():
    articles = Articles.query.filter_by(author=session['username']).all()
    return render_template("dashboard.html",articles=articles)

# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.length(min=1, max=200)])
    body = TextAreaField('Description', [validators.length(min=30)])
    
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        article = Articles(title = form.title.data, author = session['username'], body = form.body.data)
        db.session.add(article)
        db.session.commit()

        flash('Article created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html',form=form)


# Edir article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):

    form = ArticleForm(request.form)
    oldtitle = Articles.query.filter_by(id=id).first()
    form.title.data = oldtitle.title
    oldbody = Articles.query.filter_by(id=id).first()
    form.body.data = oldbody.body


    if request.method == "POST" and form.validate():

        oldtitle.title = request.form['title']
        oldbody.body = request.form['body']
        db.session.commit()

        flash('Article Edited Successfully', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html',form=form)

# Delete Article

@app.route("/delete_article/<string:id>", methods=['POST'])
@is_logged_in
def delete_article(id):
    articles = Articles.query.filter_by(id=id).first()
    db.session.delete(articles)
    db.session.commit()

    flash("Article deleted", 'success')
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True)