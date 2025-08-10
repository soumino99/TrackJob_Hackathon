from datetime import datetime
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

# アプリケーションの初期化
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# DB初期化
db = SQLAlchemy(app)

# ログイン管理初期化
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 利用可能なチャンネル
ALLOWED_CHANNELS = {"general", "job", "class", "circle"}

# チャンネル名の日本語変換辞書
CHANNEL_NAMES_JP = {
    "general": "一般",
    "job": "就活",
    "class": "授業",
    "circle": "サークル",
}


def get_channel_display_name(channel_code):
    """チャンネルコードから表示名を取得"""
    return CHANNEL_NAMES_JP.get(channel_code, channel_code)


# モデル定義
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    posts = db.relationship("Post", backref="author", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow, nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # 既存DBに追加する場合はマイグレーションが必要
    channel = db.Column(db.String(20), nullable=False, default="general", index=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ルート定義
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("timeline"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("timeline"))

    if request.method == "POST":
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""

        if not username or not password:
            flash("ユーザー名とパスワードを入力してください")
            return redirect(url_for("register"))

        # 既存ユーザーチェック
        if User.query.filter_by(username=username).first():
            flash("そのユーザー名は既に使用されています")
            return redirect(url_for("register"))

        # 新規ユーザー作成
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("登録が完了しました。ログインしてください。")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("timeline"))

    if request.method == "POST":
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("ユーザー名またはパスワードが正しくありません")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("timeline"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/timeline")
@login_required
def timeline():
    # クエリパラメータ ?channel=general などで絞り込み
    selected_channel = request.args.get("channel", None)
    if selected_channel in ALLOWED_CHANNELS:
        posts = (
            Post.query.filter_by(channel=selected_channel)
            .order_by(Post.timestamp.desc())
            .all()
        )
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        selected_channel = None  # 無効値は未選択扱い

    return render_template(
        "timeline.html", posts=posts, selected_channel=selected_channel
    )


@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    if request.method == "POST":
        content = (request.form.get("content") or "").strip()
        channel = request.form.get("channel", "general")

        if not content:
            flash("投稿内容を入力してください")
            return redirect(url_for("post"))

        if len(content) > 140:
            flash("投稿は140文字以内にしてください")
            return redirect(url_for("post"))

        if channel not in ALLOWED_CHANNELS:
            channel = "general"

        # 投稿の作成
        new_post = Post(content=content, author=current_user, channel=channel)
        db.session.add(new_post)
        db.session.commit()

        flash("投稿が完了しました。")
        # 投稿後は投稿したチャンネルのタイムラインに戻る
        return redirect(url_for("timeline", channel=channel))

    # GETリクエスト時：クエリパラメータからチャンネルを取得
    default_channel = request.args.get("channel", "general")
    if default_channel not in ALLOWED_CHANNELS:
        default_channel = "general"

    return render_template("post.html", default_channel=default_channel)


@app.route("/mypage")
@login_required
def mypage():
    posts = (
        Post.query.filter_by(user_id=current_user.id)
        .order_by(Post.timestamp.desc())
        .all()
    )
    return render_template("mypage.html", posts=posts, user=current_user)


@app.template_filter("jst")
def jst(datetime_utc):
    if datetime_utc is None:
        return ""

    utc = pytz.utc
    if datetime_utc.tzinfo is None:
        datetime_utc = utc.localize(datetime_utc)

    jst = pytz.timezone("Asia/Tokyo")
    datetime_jst = datetime_utc.astimezone(jst)

    return datetime_jst.strftime("%Y/%m/%d %H:%M")


@app.template_filter("channel_jp")
def channel_jp(channel_code):
    """テンプレート用チャンネル名変換フィルター"""
    return get_channel_display_name(channel_code)


@app.template_global()
def get_all_channels():
    """すべてのチャンネル情報を取得（将来の動的チャンネル対応）"""
    return [
        {"code": code, "name": get_channel_display_name(code)}
        for code in ALLOWED_CHANNELS
    ]


# アプリケーション起動時にDBを作成（初回のみテーブル作成）
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()  # 開発中のみ debug=True を検討
