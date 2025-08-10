from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os  
from dotenv import load_dotenv  

load_dotenv() 

# アプリケーションの初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')  # 環境変数から取得
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///data.db')  # 環境変数から取得
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB初期化
db = SQLAlchemy(app)

# ログイン管理初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# モデル定義
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'))

class Channel(db.Model):
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'),nullable=True)  

    posts = db.relationship('Post', backref='channel_obj', lazy='dynamic')
   
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ルート定義
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('timeline'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('timeline'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 既存ユーザーチェック
        if User.query.filter_by(username=username).first():
            flash('そのユーザー名は既に使用されています')
            return redirect(url_for('register'))
        
        # 新規ユーザー作成
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('登録が完了しました！ログインしてください')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('timeline'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('ユーザー名またはパスワードが正しくありません')
            return redirect(url_for('login'))
        
        login_user(user)
        return redirect(url_for('timeline'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/timeline')
@login_required
def timeline():
    selected_channel_name = request.args.get('channel', None)
    channels = Channel.query.all()

    if selected_channel_name:
        channel = Channel.query.filter_by(name=selected_channel_name).first()
        if channel:
            posts = Post.query.filter_by(channel_id=channel.id).order_by(Post.timestamp.desc()).all()
        else:
            posts = []
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
   
    return render_template('timeline.html', posts=posts, channels=channels, selected_channel=selected_channel_name)

@app.route('/post', methods=['GET', 'POST'])
@login_required
def post():
    channels = Channel.query.all()

    if request.method == 'POST':
        content = request.form.get('content')
        channel_id = request.form.get('channel_id')
        
        if not content:
            flash('投稿内容を入力してください')
            return redirect(url_for('post'))
        
        if len(content) > 140:
            flash('投稿は140文字以内にしてください')
            return redirect(url_for('post'))
        
        if not channel_id:
            channel_id = 1

        channel_obj = Channel.query.get(channel_id)
        if not channel_obj:
            flash('指定されたチャンネルは存在しません')
            return redirect(url_for('post'))

        if len(channel_obj.name) > 20:
            flash('チャンネル名は20文字以内にしてください')
            return redirect(url_for('post'))
        
        post = Post(content=content, author=current_user, channel_id=channel_id)
        db.session.add(post)
        db.session.commit()
        
        flash('投稿が完了しました！')
        return redirect(url_for('timeline', channel=channel_obj.name))
    
    return render_template('post.html',channels=channels)

@app.route('/create_channel', methods=['GET', 'POST'])
@login_required
def create_channel():
    if request.method == 'POST':
        name = request.form.get('name')
        
        if not name:
            flash('チャンネル名を入力してください')
            return redirect(url_for('create_channel'))

        if Channel.query.filter_by(name=name).first():
            flash('そのチャンネル名は既に存在します')
            return redirect(url_for('create_channel'))

        channel = Channel(
            name=name,
            created_by=current_user.id
        )
        db.session.add(channel)
        db.session.commit()
        flash('チャンネルを作成しました！')
        return redirect(url_for('timeline', channel=channel.name))

    return render_template('create_channel.html')

@app.route('/mypage')
@login_required
def mypage():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.timestamp.desc()).all()
    return render_template('mypage.html', posts=posts, user=current_user)

@app.template_filter('jst')
def jst(datetime_utc):
    if datetime_utc is None:
        return ''
    
    utc = pytz.utc
    if datetime_utc.tzinfo is None:
        datetime_utc = utc.localize(datetime_utc)
    
    jst = pytz.timezone('Asia/Tokyo')
    datetime_jst = datetime_utc.astimezone(jst)

    return datetime_jst.strftime('%Y/%m/%d %H:%M')


# アプリケーション起動時にDBを作成
with app.app_context():
    db.create_all()

with app.app_context():
    db.create_all()
    # チャンネルがなければ初期チャンネルを作成
    if Channel.query.count() == 0:
        default_channels = ['一般', '就活', '授業', 'サークル']
        for name in default_channels:
            channel = Channel(name=name, created_by=None)  # created_byをNoneにしてもOK
            db.session.add(channel)
        db.session.commit()

if __name__ == '__main__':
    app.run()  # デバッグモードを無効化
