# 一度だけ実行するマイグレーションスクリプト
from app import app, db

def add_delete_columns():
    with app.app_context():
        # SQLiteの場合の例
        db.engine.execute('ALTER TABLE posts ADD COLUMN is_deleted BOOLEAN DEFAULT 0')
        db.engine.execute('ALTER TABLE posts ADD COLUMN deleted_at DATETIME')
        db.session.commit()
        print("Migration completed successfully")

if __name__ == '__main__':
    add_delete_columns()
