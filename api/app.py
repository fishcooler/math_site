"""
Vercel Serverless Function 入口
新版 Vercel Python 运行时原生支持 Flask，无需额外适配器
"""
import os
import sys

# 将项目根目录加入 Python 路径（使模板、静态文件等可被找到）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel 环境下确保 /tmp 目录存在（SQLite 数据库存放位置）
if os.environ.get('VERCEL') == '1':
    os.makedirs(os.path.join(os.sep, 'tmp'), exist_ok=True)

# 导入 Flask 应用 — Vercel 自动检测名为 app 的 Flask 实例
from app import app, db

# 在 Vercel 环境中，__main__ 块不会执行
# 需要在此处确保数据库表已创建
with app.app_context():
    db.create_all()
    # 初始化成就和贴纸数据
    from app import AchievementSystem, StickerSystem
    AchievementSystem.init_achievements()
    StickerSystem.init_stickers()

# 导出给 Vercel 使用（新版运行时自动处理，无需 handler 函数）
# 但保留兼容写法
__all__ = ['app']
