# アプリ名 - 大学生向け匿名悩み相談アプリ

大学生が匿名で悩みを相談・共有できるチャンネル別SNSアプリケーション

## 概要

**UniAnon**は、大学生が学業、就活、サークル活動などの悩みを匿名で投稿・相談できるWebアプリケーションです。投稿者の匿名性を完全に保護しながら、チャンネル別に整理された投稿で効率的な情報共有を実現します。

## 主な機能

- **ユーザー登録/ログイン**: アカウント作成とログイン機能（認証のみに使用）
- **匿名投稿機能**: 140文字までの完全匿名テキスト投稿
- **チャンネル別投稿**: 一般・就活・授業・サークルの4つのチャンネルで投稿を分類
- **匿名タイムライン**: 全投稿を匿名ID（ポスト〇〇）で時系列表示
- **匿名コメント機能**: 投稿に対する匿名返信（返信〇〇）
- **いいね機能**: 投稿への匿名評価機能
- **マイページ**: 自分の投稿のみを表示（自分の投稿・コメントは実名表示）
- **投稿削除機能**: 自分の投稿の論理削除

## 匿名性の特徴

- 投稿者は一意な匿名ID（例：ポスト1A2B3C4D）で表示
- 同じユーザーでも投稿ごとに異なる匿名IDを生成
- コメントも独立した匿名ID（例：返信5E6F7G8H）
- 削除による欠番問題を解決するハッシュベース識別

## 技術スタック

- **バックエンド**: Python/Flask
- **データベース**: SQLite + SQLAlchemy
  - 将来的にはRenderのPostgreSQLを外部データベースとして運用することを想定
  - 現時点では開発用のSQLiteを使用
- **認証**: Flask-Login
- **フロントエンド**: HTML/CSS/Jinja2/Bootstrap
- **匿名化**: SHA256ハッシュベース匿名ID生成

## 開発環境セットアップ

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/unianon.git
cd unianon
```

2. 仮想環境を作成し、依存関係をインストール
```bash
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

3. 環境変数を設定（.envファイルを作成）
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///data.db
```

4. アプリケーションを実行
```bash
python app.py
```

5. ブラウザでアクセス: http://127.0.0.1:5000/

## ライセンス

[MIT License](LICENSE)
