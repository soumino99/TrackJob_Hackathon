from datetime import datetime, timedelta
import pytz
from flask import Flask, render_template, request, redirect, url_for, flash, session
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
import hashlib
import secrets
import random

load_dotenv()

# アプリケーションの初期化
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ダミーデータ生成フラグ（開発・デモ用）
# True: ダミーデータを自動生成、False: 生成しない
GENERATE_DUMMY_DATA = True  # 本番環境では False に変更

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
    channel = db.Column(db.String(20), nullable=False, default="general", index=True)
    # 削除フラグを追加
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def get_anonymous_id(self):
        """投稿IDベースの匿名ID生成（投稿ごとに一意）"""
        secret_key = app.config["SECRET_KEY"]
        raw_string = f"post-{self.id}-{secret_key}"
        hash_obj = hashlib.sha256(raw_string.encode())
        return hash_obj.hexdigest()[:8].upper()

    def get_display_name(self):
        """表示用の匿名名前を取得"""
        return f"ポスト{self.get_anonymous_id()}"


# いいねモデル
class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True
    )

    user = db.relationship("User", backref=db.backref("likes", lazy="dynamic"))
    post = db.relationship("Post", backref=db.backref("likes", lazy="dynamic"))


# コメントモデル
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow, nullable=False
    )
    # user_idを復活（内部管理用、表示は匿名ID）
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    session_id = db.Column(
        db.String(128), nullable=True, index=True
    )  # セッション識別用（予備）
    post_id = db.Column(
        db.Integer, db.ForeignKey("posts.id"), nullable=False, index=True
    )

    # userとの関連を復活
    user = db.relationship("User", backref=db.backref("comments", lazy="joined"))
    post = db.relationship("Post", backref=db.backref("comments", lazy="dynamic"))

    def get_anonymous_id(self):
        """コメントIDベースの匿名ID生成（コメントごとに一意）"""
        secret_key = app.config["SECRET_KEY"]
        raw_string = f"comment-{self.post_id}-{self.id}-{secret_key}"
        hash_obj = hashlib.sha256(raw_string.encode())
        return hash_obj.hexdigest()[:8].upper()

    def get_display_name(self):
        """表示用の匿名名前を取得"""
        return f"返信{self.get_anonymous_id()}"


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

        flash("アカウントの登録が完了しました。ログインしてください。")
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
            Post.query.filter_by(channel=selected_channel, is_deleted=False)
            .order_by(Post.timestamp.desc())
            .all()
        )
    else:
        posts = (
            Post.query.filter_by(is_deleted=False).order_by(Post.timestamp.desc()).all()
        )
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
        Post.query.filter_by(user_id=current_user.id, is_deleted=False)
        .order_by(Post.timestamp.desc())
        .all()
    )
    return render_template("mypage.html", posts=posts, user=current_user)


@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # 投稿者本人のみ削除可能
    if post.author != current_user:
        flash("他のユーザーの投稿は削除できません")
        return redirect(url_for("timeline"))

    # 論理削除（削除フラグを立てる）
    post.is_deleted = True
    post.deleted_at = datetime.utcnow()
    db.session.commit()

    flash("投稿を削除しました")

    # リファラーがあればそこに戻る、なければタイムラインに戻る
    referer = request.headers.get("Referer")
    if referer and "mypage" in referer:
        return redirect(url_for("mypage"))
    else:
        return redirect(url_for("timeline"))


# 管理者用：削除された投稿を確認する機能（将来的に追加可能）
@app.route("/admin/deleted_posts")
@login_required
def admin_deleted_posts():
    # 管理者権限チェックは別途実装
    deleted_posts = (
        Post.query.filter_by(is_deleted=True).order_by(Post.deleted_at.desc()).all()
    )
    return render_template("admin/deleted_posts.html", posts=deleted_posts)


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


# いいね（トグル）
@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    existing = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if existing:
        db.session.delete(existing)  # 解除
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
    db.session.commit()
    # 元のチャンネルを保つ
    return redirect(request.referrer or url_for("timeline", channel=post.channel))


# コメント投稿
@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = (request.form.get("content") or "").strip()
    if not content:
        flash("コメント内容を入力してください")
        return redirect(request.referrer or url_for("timeline", channel=post.channel))

    # セッションIDを生成（予備用）
    comment_session_id = secrets.token_urlsafe(32)

    # コメントの作成（user_idも保存、表示は匿名ID）
    new_comment = Comment(
        content=content,
        post_id=post.id,
        user_id=current_user.id,
        session_id=comment_session_id,
    )
    db.session.add(new_comment)
    db.session.commit()

    return redirect(request.referrer or url_for("timeline", channel=post.channel))


def create_dummy_data():
    """ダミーデータを生成する"""
    if not GENERATE_DUMMY_DATA:
        return

    # 既にデータが存在する場合はスキップ
    if Post.query.first():
        return

    print("Generating dummy data...")

    # ダミーユーザーを作成
    dummy_users = []
    for i in range(5):
        username = f"user{i+1}"
        if not User.query.filter_by(username=username).first():
            user = User(username=username)
            user.set_password("password123")
            db.session.add(user)
            dummy_users.append(user)

    db.session.commit()

    # 各チャンネルのダミー投稿データ
    dummy_posts = {
        "general": [
            "大学生活、思ってたより忙しいです...",
            "今日は図書館で勉強してきました！",
            "来週からテスト期間、がんばろう",
            "新しいサークルに入るか迷っています",
            "大学の食堂のメニュー、もう少し増えてほしい",
            "友達と遊ぶ時間がなかなか取れない",
            "一人暮らし始めて3ヶ月、慣れました",
            "朝起きるのが本当に辛い...",
            "大学の授業、どれも面白いです",
            "バイトと勉強の両立が大変",
        ],
        "job": [
            "就活って何から始めればいいんでしょうか？",
            "エントリーシート書くの難しい...",
            "面接で緊張しすぎてしまいます",
            "IT業界に興味があるんですが、どうでしょうか？",
            "インターンシップの選び方教えてください",
            "自己分析がうまくできません",
            "業界研究の進め方がわからない",
            "就活の軸が定まらなくて困ってます",
            "SPIの対策、どうしてますか？",
            "就活と学業の両立が大変です",
        ],
        "class": [
            "レポートの書き方がわかりません",
            "この授業、単位取るの難しそう...",
            "プレゼンが来週あって緊張してます",
            "グループワークが苦手です",
            "教授に質問するタイミングがわからない",
            "授業についていけなくて困ってます",
            "テスト勉強のコツ教えてください",
            "出席は取る授業ですか？",
            "この科目、面白いですよ！",
            "期末レポートのテーマが決まらない",
        ],
        "circle": [
            "新歓でサークル勧誘されました！",
            "テニスサークルって忙しいですか？",
            "軽音楽部に興味があります",
            "サークル掛け持ちってどうでしょう？",
            "合宿の準備が大変です",
            "サークルの人間関係が難しい...",
            "部費が思ったより高くて驚きました",
            "文化祭でサークル発表します",
            "OBの先輩方とのつながりが心強いです",
            "サークル辞めるタイミングがわからない",
        ],
    }

    # ダミーコメントデータ
    dummy_comments = [
        "わかります！同じ状況です",
        "頑張ってください！応援してます",
        "私も経験しました、大丈夫ですよ",
        "そうですね、難しい問題ですね",
        "参考になります、ありがとう",
        "同感です！",
        "いい考えですね",
        "私も気になってました",
        "情報共有ありがとうございます",
        "お疲れ様です",
    ]

    # ダミー投稿を作成
    all_posts = []
    for channel, posts in dummy_posts.items():
        for content in posts:
            user = random.choice(dummy_users)
            post = Post(
                content=content,
                author=user,
                channel=channel,
                timestamp=datetime.utcnow()
                - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                ),
            )
            db.session.add(post)
            all_posts.append(post)

    db.session.commit()

    # ダミーコメントを作成
    for post in all_posts:
        # 各投稿に0〜5個のコメントをランダムに追加
        comment_count = random.randint(0, 5)
        for _ in range(comment_count):
            commenter = random.choice(dummy_users)
            comment_content = random.choice(dummy_comments)
            comment = Comment(
                content=comment_content,
                user_id=commenter.id,
                post_id=post.id,
                session_id=secrets.token_urlsafe(32),
                timestamp=post.timestamp + timedelta(hours=random.randint(1, 48)),
            )
            db.session.add(comment)

    # ダミーいいねを作成
    for post in all_posts:
        # 各投稿に0〜8個のいいねをランダムに追加
        like_count = random.randint(0, 8)
        users_who_liked = random.sample(dummy_users, min(like_count, len(dummy_users)))
        for user in users_who_liked:
            like = Like(user_id=user.id, post_id=post.id)
            db.session.add(like)

    db.session.commit()
    print(f"Generated {len(all_posts)} dummy posts with comments and likes!")


# アプリケーション起動時にDBを作成（初回のみテーブル作成）
with app.app_context():
    db.create_all()
    create_dummy_data()  # ダミーデータ生成

if __name__ == "__main__":
    app.run()  # 開発中のみ debug=True を検討
