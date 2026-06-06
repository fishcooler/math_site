"""
Vercel Serverless Function 入口
将 Flask 应用适配到 Vercel 环境
"""
import os
import sys

# 将项目根目录加入 Python 路径（使模板、静态文件等可被找到）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel 环境下确保 /tmp 目录存在（SQLite 数据库存放位置）
if os.environ.get('VERCEL') == '1':
    os.makedirs(os.path.join(os.sep, 'tmp'), exist_ok=True)

# 导入 Flask 应用
from app import app, db

# 在 Vercel 环境中，__main__ 块不会执行
# 需要在此处确保数据库表已创建
with app.app_context():
    db.create_all()
    # 初始化成就和贴纸数据
    from app import AchievementSystem, StickerSystem
    AchievementSystem.init_achievements()
    StickerSystem.init_stickers()

# 使用 WSGI 适配器将 Flask app 桥接到 Vercel
from vercel_wsgi import handle_wsgi_app


def handler(request):
    return handle_wsgi_app(app, request)
