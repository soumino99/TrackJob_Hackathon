# アプリ名 - 大学生向け悩み相談アプリ

アプリの説明

## 概要

アプリの説明

## 主な機能

- **ユーザー登録/ログイン**: アカウント作成とログイン機能
- **投稿機能**: 140文字までのテキスト投稿
- **タイムライン**: 全ユーザーの投稿を時系列で表示
- **マイページ**: 自分の投稿のみを表示
- **チャンネル別投稿機能**: チャンネル別に投稿を作成、表示

## 技術スタック

- **バックエンド**: Python/Flask
- **データベース**: ~~PostgreSQLSQLite~~ + SQLAlchemy
  - 将来的にはRenderのPostgreSQLを外部データベースとして運用することを想定
  - 現時点では無料のLiteDBを使用
- **認証**: Flask-Login
- **フロントエンド**: HTML/CSS/Jinja2/Bootstrap

## 開発環境セットアップ

1. リポジトリをクローン
```
git clone https://github.com/yourusername/unichat.git
cd unichat
```

2. 仮想環境を作成し、依存関係をインストール
```
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

3. アプリケーションを実行
```
flask run
```

4. ブラウザでアクセス: http://127.0.0.1:5000/

## ライセンス

[MIT License](LICENSE)
