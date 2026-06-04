from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import random
import json
from datetime import datetime, timedelta
import os

# ==================== 配置管理 ====================

def load_config():
    """加载配置，优先级：环境变量 > .env文件 > config.json > 默认值"""
    config = {
        'SECRET_KEY': 'math-practice-secret-key',
        'DATABASE_URI': 'sqlite:///math_practice.db',
        'AI_API_URL': 'https://api.deepseek.com/v1/chat/completions',
        'AI_API_KEY': '',
        'AI_MODEL': 'deepseek-chat',
        'ADMIN_PASSWORD': 'admin123',  # 管理后台密码
    }
    
    # 1. 从 config.json 加载
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            print(f'读取config.json失败: {e}')
    
    # 2. 从 .env 文件加载（简易实现，不依赖python-dotenv）
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key in config:
                            config[key] = value
        except Exception as e:
            print(f'读取.env失败: {e}')
    
    # 3. 环境变量覆盖（最高优先级）
    for key in config:
        env_value = os.environ.get(key)
        if env_value is not None:
            config[key] = env_value
    
    return config

# 加载配置
_config = load_config()

app = Flask(__name__)
app.config['SECRET_KEY'] = _config['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = _config['DATABASE_URI']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# AI配置
app.config['AI_API_URL'] = _config['AI_API_URL']
app.config['AI_API_KEY'] = _config['AI_API_KEY']
app.config['AI_MODEL'] = _config['AI_MODEL']
app.config['ADMIN_PASSWORD'] = _config['ADMIN_PASSWORD']

# 全局配置对象（用于运行时修改）
runtime_config = {
    'AI_API_URL': _config['AI_API_URL'],
    'AI_API_KEY': _config['AI_API_KEY'],
    'AI_MODEL': _config['AI_MODEL'],
}

db = SQLAlchemy(app)

# ==================== 数据库模型 ====================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    points = db.Column(db.Integer, default=0)  # 总积分
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    answers = db.relationship('Answer', backref='user', lazy=True)
    mistakes = db.relationship('Mistake', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    point_logs = db.relationship('PointLog', backref='user', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(50), nullable=False)
    options = db.Column(db.Text)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.Integer, default=1)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user_answer = db.Column(db.String(50))
    is_correct = db.Column(db.Boolean)
    answered_at = db.Column(db.DateTime, default=datetime.now)
    practice_set = db.Column(db.Integer)

class Mistake(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    wrong_answer = db.Column(db.String(50))
    correct_answer = db.Column(db.String(50))
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    reviewed = db.Column(db.Boolean, default=False)

class Achievement(db.Model):
    """成就定义"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 成就名称
    icon = db.Column(db.String(10), nullable=False)   # 图标emoji
    description = db.Column(db.String(200))            # 成就描述
    condition_type = db.Column(db.String(30))          # 条件类型
    condition_value = db.Column(db.Integer)            # 条件值
    points_reward = db.Column(db.Integer, default=0)   # 奖励积分
    is_hidden = db.Column(db.Boolean, default=False)   # 是否隐藏成就

class UserAchievement(db.Model):
    """用户获得的成就"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.now)
    
    achievement = db.relationship('Achievement', backref='user_achievements')

class PointLog(db.Model):
    """积分记录"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # 正数增加，负数减少
    reason = db.Column(db.String(100))               # 积分原因
    created_at = db.Column(db.DateTime, default=datetime.now)

class Message(db.Model):
    """留言板"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)      # 留言内容
    category = db.Column(db.String(20), default='feedback')  # feedback/suggestion/question
    is_anonymous = db.Column(db.Boolean, default=False)  # 是否匿名
    is_approved = db.Column(db.Boolean, default=True)   # 是否审核通过
    is_deleted = db.Column(db.Boolean, default=False)    # 是否删除
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='messages')


# ==================== 敏感词过滤 ====================

class SensitiveFilter:
    """敏感词过滤器"""
    
    # 敏感词库（可根据需要扩展）
    SENSITIVE_WORDS = {
        # 不文明用语
        '傻逼', '操你', '妈的', '去死', '垃圾', '废物', '白痴', '蠢货',
        '混蛋', '王八蛋', '狗屁', '放屁', '滚蛋', '你妈', '他妈',
        '卧槽', '我靠', '特么的', '尼玛', '草泥马', '马勒戈壁',
        # 攻击性词汇
        '打你', '打死', '杀', '砍', '暴力', '威胁',
        # 色情相关
        '性交', '做爱', '裸体', '色情', '淫秽',
        # 广告spam
        '加微信', '加QQ', '代开发票', '办证', '赌博',
    }
    
    # 替换词表（拼音/谐音变体）
    VARIANTS = {
        'sb': '傻逼',
        'nmsl': '你妈死了',
        'cnm': '操你妈',
        'woc': '我操',
        'mdzz': '妈的智障',
        'zz': '智障',
        'lj': '垃圾',
    }
    
    @classmethod
    def contains_sensitive(cls, text):
        """检查是否包含敏感词"""
        if not text:
            return False, ''
        
        text_lower = text.lower()
        
        # 检查原始敏感词
        for word in cls.SENSITIVE_WORDS:
            if word in text_lower:
                return True, word
        
        # 检查变体
        for variant, meaning in cls.VARIANTS.items():
            if variant in text_lower:
                return True, meaning
        
        return False, ''
    
    @classmethod
    def filter_text(cls, text):
        """过滤敏感词，返回过滤后的文本"""
        if not text:
            return text, []
        
        filtered_words = []
        result = text
        
        text_lower = text.lower()
        
        # 替换敏感词
        for word in cls.SENSITIVE_WORDS:
            if word in text_lower:
                filtered_words.append(word)
                result = result.replace(word, '*' * len(word))
                # 不区分大小写替换
                import re
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                result = pattern.sub('*' * len(word), result)
        
        # 替换变体
        for variant, meaning in cls.VARIANTS.items():
            if variant in text_lower:
                filtered_words.append(variant)
                result = result.replace(variant, '**')
        
        return result, filtered_words


# ==================== 积分系统 ====================

class PointSystem:
    """积分管理系统"""
    
    # 积分规则
    RULES = {
        'practice_complete': 10,   # 完成一套练习
        'score_90_plus': 20,       # 90分以上
        'score_100': 50,           # 满分
        'practice_streak_3': 30,   # 连续3天练习
        'practice_streak_7': 100,  # 连续7天练习
        'review_mistake': 5,       # 复习错题
        'share': 10,               # 分享成绩
    }
    
    @staticmethod
    def add_points(user_id, points, reason):
        """添加积分"""
        user = User.query.get(user_id)
        if user:
            user.points += points
            log = PointLog(user_id=user_id, points=points, reason=reason)
            db.session.add(log)
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def get_points_history(user_id, limit=20):
        """获取积分历史"""
        return PointLog.query.filter_by(user_id=user_id)\
            .order_by(PointLog.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def calculate_practice_points(score, user_id):
        """计算练习获得的积分"""
        points = PointSystem.RULES['practice_complete']
        reasons = ['完成练习 +10']
        
        if score >= 100:
            points += PointSystem.RULES['score_100']
            reasons.append('满分大奖 +50')
        elif score >= 90:
            points += PointSystem.RULES['score_90_plus']
            reasons.append('高分奖励 +20')
        
        # 检查连续练习
        streak = PointSystem.check_practice_streak(user_id)
        if streak >= 7:
            points += PointSystem.RULES['practice_streak_7']
            reasons.append('连续7天 +100')
        elif streak >= 3:
            points += PointSystem.RULES['practice_streak_3']
            reasons.append('连续3天 +30')
        
        return points, reasons
    
    @staticmethod
    def check_practice_streak(user_id):
        """检查连续练习天数"""
        today = datetime.now().date()
        streak = 0
        
        for i in range(30):  # 最多检查30天
            check_date = today - timedelta(days=i)
            day_start = datetime.combine(check_date, datetime.min.time())
            day_end = datetime.combine(check_date, datetime.max.time())
            
            has_practice = Answer.query.filter(
                Answer.user_id == user_id,
                Answer.answered_at >= day_start,
                Answer.answered_at <= day_end
            ).first()
            
            if has_practice:
                streak += 1
            else:
                break
        
        return streak


# ==================== 成就系统 ====================

class AchievementSystem:
    """成就管理系统"""
    
    # 成就定义
    ACHIEVEMENTS = [
        {'name': '初次挑战', 'icon': '🌟', 'desc': '完成第一次练习', 'type': 'practice_count', 'value': 1, 'points': 10},
        {'name': '三战三胜', 'icon': '🎯', 'desc': '连续3次80分以上', 'type': 'score_streak_80', 'value': 3, 'points': 30},
        {'name': '满分王者', 'icon': '💯', 'desc': '获得1次满分', 'type': 'perfect_score', 'value': 1, 'points': 50},
        {'name': '坚持不懈', 'icon': '🔥', 'desc': '连续练习7天', 'type': 'practice_streak', 'value': 7, 'points': 100},
        {'name': '错题克星', 'icon': '📖', 'desc': '复习10道错题', 'type': 'review_count', 'value': 10, 'points': 50},
        {'name': '计算达人', 'icon': '🧮', 'desc': '计算题正确率90%+', 'type': 'calc_accuracy', 'value': 90, 'points': 80},
        {'name': '规律大师', 'icon': '🔍', 'desc': '找规律题全部正确', 'type': 'pattern_perfect', 'value': 1, 'points': 40},
        {'name': '应用高手', 'icon': '💡', 'desc': '应用题正确率80%+', 'type': 'word_accuracy', 'value': 80, 'points': 60},
        {'name': '练习达人', 'icon': '📚', 'desc': '完成50套练习', 'type': 'practice_count', 'value': 50, 'points': 200},
        {'name': '学习之星', 'icon': '⭐', 'desc': '总积分达到500', 'type': 'total_points', 'value': 500, 'points': 0},
    ]
    
    @staticmethod
    def init_achievements():
        """初始化成就数据"""
        for ach in AchievementSystem.ACHIEVEMENTS:
            existing = Achievement.query.filter_by(name=ach['name']).first()
            if not existing:
                new_ach = Achievement(
                    name=ach['name'],
                    icon=ach['icon'],
                    description=ach['desc'],
                    condition_type=ach['type'],
                    condition_value=ach['value'],
                    points_reward=ach['points']
                )
                db.session.add(new_ach)
        db.session.commit()
    
    @staticmethod
    def check_achievements(user_id):
        """检查并授予成就"""
        new_achievements = []
        user = User.query.get(user_id)
        if not user:
            return new_achievements
        
        # 获取用户已获得的成就
        earned_ids = [ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()]
        
        # 获取所有成就
        all_achievements = Achievement.query.all()
        
        for ach in all_achievements:
            if ach.id in earned_ids:
                continue  # 已获得
            
            # 检查条件
            if AchievementSystem.check_condition(user_id, ach.condition_type, ach.condition_value):
                # 授予成就
                ua = UserAchievement(user_id=user_id, achievement_id=ach.id)
                db.session.add(ua)
                
                # 奖励积分
                if ach.points_reward > 0:
                    PointSystem.add_points(user_id, ach.points_reward, f'获得成就：{ach.name}')
                
                new_achievements.append({
                    'name': ach.name,
                    'icon': ach.icon,
                    'description': ach.description,
                    'points': ach.points_reward
                })
        
        db.session.commit()
        return new_achievements
    
    @staticmethod
    def check_condition(user_id, condition_type, condition_value):
        """检查成就条件是否满足"""
        if condition_type == 'practice_count':
            # 练习次数（每次提交算一次）
            count = db.session.query(Answer.practice_set).filter_by(user_id=user_id)\
                .distinct().count()
            return count >= condition_value
        
        elif condition_type == 'perfect_score':
            # 满分次数 - 检查最近的练习批次
            return AchievementSystem.check_perfect_scores(user_id, condition_value)
        
        elif condition_type == 'practice_streak':
            streak = PointSystem.check_practice_streak(user_id)
            return streak >= condition_value
        
        elif condition_type == 'review_count':
            count = Mistake.query.filter_by(user_id=user_id, reviewed=True).count()
            return count >= condition_value
        
        elif condition_type == 'total_points':
            user = User.query.get(user_id)
            return user.points >= condition_value if user else False
        
        elif condition_type == 'score_streak_80':
            return AchievementSystem.check_score_streak(user_id, 80, condition_value)
        
        return False
    
    @staticmethod
    def check_perfect_scores(user_id, count):
        """检查满分次数"""
        # 获取所有练习批次
        practice_sets = db.session.query(Answer.practice_set).filter_by(user_id=user_id)\
            .distinct().all()
        
        perfect_count = 0
        for (ps,) in practice_sets:
            if ps is None:
                continue
            answers = Answer.query.filter_by(user_id=user_id, practice_set=ps).all()
            if answers and all(a.is_correct for a in answers):
                perfect_count += 1
        
        return perfect_count >= count
    
    @staticmethod
    def check_score_streak(user_id, min_score, streak_count):
        """检查连续高分"""
        practice_sets = db.session.query(Answer.practice_set).filter_by(user_id=user_id)\
            .order_by(Answer.answered_at.desc()).distinct().limit(streak_count + 5).all()
        
        streak = 0
        for (ps,) in practice_sets:
            if ps is None:
                continue
            answers = Answer.query.filter_by(user_id=user_id, practice_set=ps).all()
            if not answers:
                continue
            
            correct = sum(1 for a in answers if a.is_correct)
            score = round(correct / len(answers) * 100)
            
            if score >= min_score:
                streak += 1
                if streak >= streak_count:
                    return True
            else:
                streak = 0
        
        return False
    
    @staticmethod
    def get_user_achievements(user_id):
        """获取用户成就列表"""
        user_achs = UserAchievement.query.filter_by(user_id=user_id)\
            .order_by(UserAchievement.earned_at.desc()).all()
        
        result = []
        for ua in user_achs:
            result.append({
                'id': ua.achievement.id,
                'name': ua.achievement.name,
                'icon': ua.achievement.icon,
                'description': ua.achievement.description,
                'earned_at': ua.earned_at.strftime('%Y-%m-%d %H:%M')
            })
        return result
    
    @staticmethod
    def get_all_achievements(user_id):
        """获取所有成就（含未解锁状态）"""
        all_achs = Achievement.query.all()
        earned_ids = [ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()]
        
        result = []
        for ach in all_achs:
            result.append({
                'id': ach.id,
                'name': ach.name,
                'icon': ach.icon,
                'description': ach.description,
                'points': ach.points_reward,
                'earned': ach.id in earned_ids
            })
        return result


# ==================== 排行榜系统 ====================

class LeaderboardSystem:
    """排行榜系统"""
    
    @staticmethod
    def get_top_users(limit=10):
        """获取积分排行榜"""
        users = User.query.order_by(User.points.desc()).limit(limit).all()
        
        result = []
        for i, user in enumerate(users, 1):
            # 计算练习次数
            practice_count = db.session.query(Answer.practice_set).filter_by(user_id=user.id)\
                .distinct().count()
            
            result.append({
                'rank': i,
                'name': user.name,
                'points': user.points,
                'practice_count': practice_count
            })
        return result
    
    @staticmethod
    def get_user_rank(user_id):
        """获取用户排名"""
        user = User.query.get(user_id)
        if not user:
            return None
        
        rank = User.query.filter(User.points > user.points).count() + 1
        total = User.query.count()
        
        return {
            'rank': rank,
            'total': total,
            'points': user.points
        }


# ==================== 题目生成器 ====================

class QuestionGenerator:
    @staticmethod
    def generate_calc_questions(count=20):
        questions = []
        for i in range(10):
            if random.choice([True, False]):
                a, b = random.randint(1, 9), random.randint(1, 9)
                questions.append({
                    'type': 'calc',
                    'content': f'{a} + {b} = ____',
                    'answer': str(a + b),
                    'explanation': f'{a} + {b} = {a + b}'
                })
            else:
                a, b = random.randint(2, 18), random.randint(1, 9)
                a = max(a, b)
                questions.append({
                    'type': 'calc',
                    'content': f'{a} - {b} = ____',
                    'answer': str(a - b),
                    'explanation': f'{a} - {b} = {a - b}'
                })
        for i in range(10):
            if random.choice([True, False]):
                a, b = random.randint(10, 90), random.randint(1, 50)
                questions.append({
                    'type': 'calc',
                    'content': f'{a} + {b} = ____',
                    'answer': str(a + b),
                    'explanation': f'{a} + {b} = {a + b}'
                })
            else:
                a, b = random.randint(20, 99), random.randint(1, 50)
                a = max(a, b)
                questions.append({
                    'type': 'calc',
                    'content': f'{a} - {b} = ____',
                    'answer': str(a - b),
                    'explanation': f'{a} - {b} = {a - b}'
                })
        return questions
    
    @staticmethod
    def generate_pattern_questions(count=3):
        patterns = [
            {'seq': [2, 4, 6, 8], 'next': 10, 'rule': '每次加2'},
            {'seq': [5, 10, 15, 20], 'next': 25, 'rule': '每次加5'},
            {'seq': [100, 90, 80, 70], 'next': 60, 'rule': '每次减10'},
            {'seq': [1, 3, 5, 7], 'next': 9, 'rule': '每次加2（奇数）'},
            {'seq': [3, 6, 9, 12], 'next': 15, 'rule': '每次加3'},
        ]
        selected = random.sample(patterns, min(count, len(patterns)))
        questions = []
        for p in selected:
            questions.append({
                'type': 'pattern',
                'content': f"{'，'.join(map(str, p['seq']))}，____",
                'answer': str(p['next']),
                'explanation': f"规律：{p['rule']}，所以下一个是{p['next']}"
            })
        return questions
    
    @staticmethod
    def generate_compare_questions(count=2):
        questions = []
        for _ in range(count):
            a, b = random.randint(5, 50), random.randint(5, 50)
            op = random.choice(['+', '-'])
            if op == '+':
                left = a + b
                content = f'{a} + {b} ○ {random.randint(10, 80)}'
            else:
                left = a - b
                content = f'{a} - {b} ○ {random.randint(1, 40)}'
            right_num = int(content.split('○')[1].strip())
            if left > right_num:
                answer = '>'
            elif left < right_num:
                answer = '<'
            else:
                answer = '='
            questions.append({
                'type': 'compare',
                'content': content,
                'answer': answer,
                'explanation': f'{content.split("○")[0].strip()} = {left}，所以填{answer}'
            })
        return questions
    
    @staticmethod
    def generate_count_questions(count=2):
        shapes = [
            {'shape': '△', 'name': '三角形', 'count': random.randint(3, 8)},
            {'shape': '○', 'name': '圆形', 'count': random.randint(3, 8)},
            {'shape': '□', 'name': '正方形', 'count': random.randint(3, 8)},
            {'shape': '★', 'name': '五角星', 'count': random.randint(3, 6)},
        ]
        selected = random.sample(shapes, min(count, len(shapes)))
        questions = []
        for s in selected:
            questions.append({
                'type': 'count',
                'content': f"数一数，下图中有几个{s['name']}？\n{' '.join([s['shape']] * s['count'])}",
                'answer': str(s['count']),
                'explanation': f'一共有{s["count"]}个{s["shape"]}（{s["name"]}）'
            })
        return questions
    
    @staticmethod
    def generate_word_questions(count=3):
        templates = [
            {'template': '小明有{a}颗糖，又买了{b}颗，现在有多少颗糖？', 'calc': lambda a, b: a + b, 'op': '+'},
            {'template': '树上有{a}只鸟，飞走了{b}只，还剩多少只？', 'calc': lambda a, b: a - b, 'op': '-'},
            {'template': '小红有{a}本书，借给小明{b}本，还剩多少本？', 'calc': lambda a, b: a - b, 'op': '-'},
            {'template': '妈妈买了{a}个苹果，小明吃了{b}个，爸爸吃了{c}个，还剩多少个？', 'calc': lambda a, b, c: a - b - c, 'op': '-'},
            {'template': '教室里有{a}个小朋友，又来了{b}个，现在有多少个小朋友？', 'calc': lambda a, b: a + b, 'op': '+'}
        ]
        questions = []
        for _ in range(count):
            template = random.choice(templates)
            if 'c' in template['template']:
                a, b, c = random.randint(15, 30), random.randint(3, 8), random.randint(2, 5)
                content = template['template'].format(a=a, b=b, c=c)
                answer = template['calc'](a, b, c)
                explanation = f'{a} - {b} - {c} = {answer}'
            else:
                a, b = random.randint(10, 30), random.randint(3, 10)
                if template['op'] == '-':
                    a = max(a, b)
                content = template['template'].format(a=a, b=b)
                answer = template['calc'](a, b)
                explanation = f'{a} {template["op"]} {b} = {answer}'
            questions.append({
                'type': 'word',
                'content': content,
                'answer': str(answer),
                'explanation': explanation
            })
        return questions
    
    @classmethod
    def generate_full_set(cls, mode='offline', user_id=None):
        """生成完整题目集
        
        Args:
            mode: 'offline' 离线模式 | 'ai' AI模式
            user_id: 用户ID（AI模式需要）
        """
        if mode == 'ai' and user_id:
            try:
                return cls.generate_ai_set(user_id)
            except Exception as e:
                print(f"AI出题失败，降级到离线模式: {e}")
                # 降级到离线模式
                pass
        
        # 离线模式
        questions = []
        questions.extend(cls.generate_calc_questions(20))
        questions.extend(cls.generate_pattern_questions(3))
        questions.extend(cls.generate_compare_questions(2))
        questions.extend(cls.generate_count_questions(2))
        questions.extend(cls.generate_word_questions(3))
        for i, q in enumerate(questions, 1):
            q['num'] = i
        return questions
    
    @classmethod
    def generate_ai_set(cls, user_id):
        """AI智能出题"""
        import requests
        import json
        
        # 获取用户薄弱知识点
        weak_types = cls.get_user_weak_types(user_id)
        
        # 构建提示词
        prompt = cls.build_ai_prompt(weak_types)
        
        # 调用AI API
        api_url = app.config.get('AI_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        api_key = app.config.get('AI_API_KEY', '')
        model = app.config.get('AI_MODEL', 'deepseek-chat')
        
        if not api_key:
            raise Exception('未配置AI API Key')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一位幼小衔接数学教育专家，请根据要求生成数学练习题。请严格按照JSON格式返回。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }
        
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # 解析AI返回的题目
        questions = cls.parse_ai_response(content)
        
        # 添加题号
        for i, q in enumerate(questions, 1):
            q['num'] = i
        
        return questions
    
    @staticmethod
    def get_user_weak_types(user_id):
        """获取用户薄弱知识点"""
        # 获取最近的答题记录
        recent_answers = Answer.query.filter_by(user_id=user_id) \
            .order_by(Answer.answered_at.desc()).limit(100).all()
        
        # 按题型统计正确率
        type_stats = {}
        type_ranges = {
            'calc': (1, 20),
            'pattern': (21, 23),
            'compare': (24, 25),
            'count': (26, 27),
            'word': (28, 30)
        }
        
        for ans in recent_answers:
            q_id = ans.question_id
            for q_type, (start, end) in type_ranges.items():
                if start <= q_id <= end:
                    if q_type not in type_stats:
                        type_stats[q_type] = {'total': 0, 'correct': 0}
                    type_stats[q_type]['total'] += 1
                    if ans.is_correct:
                        type_stats[q_type]['correct'] += 1
                    break
        
        # 找出正确率低于60%的题型
        weak_types = []
        for q_type, stats in type_stats.items():
            if stats['total'] >= 5:  # 至少做过5题
                accuracy = stats['correct'] / stats['total']
                if accuracy < 0.6:
                    weak_types.append(q_type)
        
        return weak_types
    
    @staticmethod
    def build_ai_prompt(weak_types):
        """构建AI提示词"""
        type_names = {
            'calc': '计算题',
            'pattern': '找规律题',
            'compare': '比较大小题',
            'count': '数一数题',
            'word': '应用题'
        }
        
        weak_desc = ''
        if weak_types:
            weak_names = [type_names.get(t, t) for t in weak_types]
            weak_desc = f'\n该学生的薄弱知识点是：{"、".join(weak_names)}，请适当增加这些题型的比例。'
        
        return f"""请为幼小衔接阶段（5-7岁）的小朋友生成一套30道数学练习题。

要求：
1. 计算题（20题）：10以内/20以内/100以内加减法
2. 找规律题（3题）：简单的等差数列
3. 比较大小题（2题）：使用>、<、=
4. 数一数题（2题）：数图形个数
5. 应用题（3题）：生活场景应用题
{weak_desc}
请严格按照以下JSON格式返回：
{{
    "questions": [
        {{
            "type": "calc",
            "content": "5 + 3 = ____",
            "answer": "8",
            "explanation": "5 + 3 = 8"
        }},
        ...
    ]
}}

注意：
- 题目难度适合5-7岁儿童
- 数字范围：10以内、20以内、100以内
- 应用题要有清晰的生活场景
- explanation要简洁明了"""
    
    @staticmethod
    def parse_ai_response(content):
        """解析AI返回的题目"""
        import json
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise Exception('无法解析AI返回的JSON')
        
        data = json.loads(json_match.group())
        
        if 'questions' not in data:
            raise Exception('AI返回格式错误')
        
        questions = []
        valid_types = ['calc', 'pattern', 'compare', 'count', 'word']
        
        for q in data['questions']:
            if q.get('type') in valid_types and 'content' in q and 'answer' in q:
                questions.append({
                    'type': q['type'],
                    'content': q['content'],
                    'answer': str(q['answer']),
                    'explanation': q.get('explanation', '')
                })
        
        # 确保题目数量正确
        if len(questions) < 20:
            raise Exception('AI生成的题目数量不足')
        
        # 确保每种题型都有
        types_present = set(q['type'] for q in questions)
        if len(types_present) < 4:
            raise Exception('AI生成的题型不完整')
        
        return questions[:30]  # 最多返回30题


# ==================== 路由 ====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('practice'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    name = request.form.get('name')
    
    if not username or not name:
        return jsonify({'success': False, 'message': '请输入用户名和姓名'})
    
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, name=name)
        db.session.add(user)
        db.session.commit()
    
    session['user_id'] = user.id
    session['user_name'] = user.name
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/practice')
def practice():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    return render_template('practice.html', user_name=session['user_name'], user_points=user.points if user else 0)

@app.route('/achievements')
def achievements():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    user_achievements = AchievementSystem.get_user_achievements(session['user_id'])
    all_achievements = AchievementSystem.get_all_achievements(session['user_id'])
    
    return render_template('achievements.html', 
                         user_name=session['user_name'],
                         user_points=user.points if user else 0,
                         user_achievements=user_achievements,
                         all_achievements=all_achievements)

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    top_users = LeaderboardSystem.get_top_users(10)
    user_rank = LeaderboardSystem.get_user_rank(session['user_id'])
    
    return render_template('leaderboard.html',
                         user_name=session['user_name'],
                         user_points=user.points if user else 0,
                         top_users=top_users,
                         user_rank=user_rank)

@app.route('/api/generate_questions')
def generate_questions():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    # 获取出题模式
    mode = request.args.get('mode', 'offline')  # offline | ai
    
    try:
        questions = QuestionGenerator.generate_full_set(mode=mode, user_id=session['user_id'])
        return jsonify({
            'questions': questions,
            'mode': mode
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit_all', methods=['POST'])
def submit_all():
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    data = request.json
    answers = data.get('answers', [])
    
    # 获取当前最大practice_set
    max_set = db.session.query(db.func.max(Answer.practice_set)).filter_by(user_id=session['user_id']).scalar()
    practice_set = (max_set or 0) + 1
    
    results = []
    for ans in answers:
        question_num = ans.get('question_num')
        user_answer = ans.get('answer')
        correct_answer = ans.get('correct_answer')
        explanation = ans.get('explanation')
        
        is_correct = str(user_answer).strip() == str(correct_answer).strip()
        
        answer = Answer(
            user_id=session['user_id'],
            question_id=question_num,
            user_answer=user_answer,
            is_correct=is_correct,
            practice_set=practice_set
        )
        db.session.add(answer)
        
        if not is_correct:
            mistake = Mistake(
                user_id=session['user_id'],
                question_id=question_num,
                wrong_answer=user_answer,
                correct_answer=correct_answer,
                explanation=explanation
            )
            db.session.add(mistake)
        
        results.append({
            'question_num': question_num,
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer
        })
    
    db.session.commit()
    
    correct_count = sum(1 for r in results if r['correct'])
    score = round(correct_count / len(results) * 100) if results else 0
    
    # 计算积分
    points_earned, point_reasons = PointSystem.calculate_practice_points(score, session['user_id'])
    PointSystem.add_points(session['user_id'], points_earned, '完成练习')
    
    # 检查成就
    new_achievements = AchievementSystem.check_achievements(session['user_id'])
    
    # 获取更新后的用户信息
    user = User.query.get(session['user_id'])
    
    return jsonify({
        'results': results,
        'total': len(results),
        'correct_count': correct_count,
        'score': score,
        'points_earned': points_earned,
        'point_reasons': point_reasons,
        'total_points': user.points if user else 0,
        'new_achievements': new_achievements
    })

@app.route('/mistakes')
def mistakes():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    user_mistakes = Mistake.query.filter_by(user_id=session['user_id']).order_by(Mistake.created_at.desc()).all()
    return render_template('mistakes.html', mistakes=user_mistakes, user_name=session['user_name'], user_points=user.points if user else 0)

@app.route('/api/mark_reviewed/<int:mistake_id>', methods=['POST'])
def mark_reviewed(mistake_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    mistake = Mistake.query.filter_by(id=mistake_id, user_id=session['user_id']).first()
    if mistake:
        mistake.reviewed = True
        db.session.commit()
        
        # 复习错题奖励积分
        PointSystem.add_points(session['user_id'], PointSystem.RULES['review_mistake'], '复习错题')
        
        # 检查成就
        AchievementSystem.check_achievements(session['user_id'])
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '错题不存在'})

@app.route('/api/delete_mistake/<int:mistake_id>', methods=['POST'])
def delete_mistake(mistake_id):
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    mistake = Mistake.query.filter_by(id=mistake_id, user_id=session['user_id']).first()
    if mistake:
        db.session.delete(mistake)
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': '错题不存在'})

@app.route('/api/user_stats')
def user_stats():
    """获取用户统计数据"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    # 练习次数
    practice_count = db.session.query(Answer.practice_set).filter_by(user_id=session['user_id']).distinct().count()
    
    # 平均分
    practice_sets = db.session.query(Answer.practice_set).filter_by(user_id=session['user_id']).distinct().all()
    scores = []
    for (ps,) in practice_sets:
        if ps is None:
            continue
        answers = Answer.query.filter_by(user_id=session['user_id'], practice_set=ps).all()
        if answers:
            correct = sum(1 for a in answers if a.is_correct)
            scores.append(round(correct / len(answers) * 100))
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    
    # 连续练习天数
    streak = PointSystem.check_practice_streak(session['user_id'])
    
    # 错题数量
    mistake_count = Mistake.query.filter_by(user_id=session['user_id']).count()
    reviewed_count = Mistake.query.filter_by(user_id=session['user_id'], reviewed=True).count()
    
    # 成就数量
    achievement_count = UserAchievement.query.filter_by(user_id=session['user_id']).count()
    
    # 积分排名
    rank_info = LeaderboardSystem.get_user_rank(session['user_id'])
    
    return jsonify({
        'points': user.points,
        'practice_count': practice_count,
        'avg_score': avg_score,
        'streak': streak,
        'mistake_count': mistake_count,
        'reviewed_count': reviewed_count,
        'achievement_count': achievement_count,
        'rank': rank_info['rank'] if rank_info else 0,
        'total_users': rank_info['total'] if rank_info else 0
    })

@app.route('/api/points_history')
def points_history():
    """获取积分历史"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    logs = PointSystem.get_points_history(session['user_id'])
    return jsonify({
        'history': [{
            'points': log.points,
            'reason': log.reason,
            'time': log.created_at.strftime('%m-%d %H:%M')
        } for log in logs]
    })


# ==================== 家长看板 ====================

@app.route('/parent')
def parent_dashboard():
    """家长看板页面"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    return render_template('parent.html', 
                         user_name=session['user_name'],
                         user_points=user.points if user else 0)

@app.route('/api/learning_report')
def learning_report():
    """获取学习报告"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # 获取今天的日期
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # 今日练习
    today_practices = Answer.query.filter(
        Answer.user_id == user_id,
        Answer.answered_at >= datetime.combine(today, datetime.min.time())
    ).distinct(Answer.practice_set).count()
    
    # 本周练习
    week_practices = Answer.query.filter(
        Answer.user_id == user_id,
        Answer.answered_at >= datetime.combine(week_start, datetime.min.time())
    ).distinct(Answer.practice_set).count()
    
    # 本月练习
    month_practices = Answer.query.filter(
        Answer.user_id == user_id,
        Answer.answered_at >= datetime.combine(month_start, datetime.min.time())
    ).distinct(Answer.practice_set).count()
    
    # 计算平均分（最近10次）
    recent_sets = db.session.query(Answer.practice_set).filter_by(user_id=user_id) \
        .order_by(Answer.answered_at.desc()).distinct().limit(10).all()
    
    scores = []
    for (ps,) in recent_sets:
        if ps is None:
            continue
        answers = Answer.query.filter_by(user_id=user_id, practice_set=ps).all()
        if answers:
            correct = sum(1 for a in answers if a.is_correct)
            scores.append(round(correct / len(answers) * 100))
    
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    
    # 获取错题统计
    total_mistakes = Mistake.query.filter_by(user_id=user_id).count()
    reviewed_mistakes = Mistake.query.filter_by(user_id=user_id, reviewed=True).count()
    
    # 计算进步趋势（最近5次平均分 vs 之前5次平均分）
    trend = 0
    if len(scores) >= 10:
        recent_avg = sum(scores[:5]) / 5
        previous_avg = sum(scores[5:10]) / 5
        trend = round(recent_avg - previous_avg)
    
    return jsonify({
        'today_practices': today_practices,
        'week_practices': week_practices,
        'month_practices': month_practices,
        'avg_score': avg_score,
        'total_mistakes': total_mistakes,
        'reviewed_mistakes': reviewed_mistakes,
        'trend': trend,
        'user_name': user.name,
        'user_points': user.points,
        'streak': PointSystem.check_practice_streak(user_id)
    })

@app.route('/api/learning_trends')
def learning_trends():
    """获取学习趋势（最近30天）"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session['user_id']
    today = datetime.now().date()
    
    # 获取最近30天每天的练习次数和平均分
    trends = []
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())
        
        # 当天的练习批次
        practice_sets = db.session.query(Answer.practice_set).filter(
            Answer.user_id == user_id,
            Answer.answered_at >= day_start,
            Answer.answered_at <= day_end
        ).distinct().all()
        
        day_scores = []
        for (ps,) in practice_sets:
            if ps is None:
                continue
            answers = Answer.query.filter_by(user_id=user_id, practice_set=ps).all()
            if answers:
                correct = sum(1 for a in answers if a.is_correct)
                day_scores.append(round(correct / len(answers) * 100))
        
        trends.append({
            'date': date.strftime('%m-%d'),
            'practice_count': len(practice_sets),
            'avg_score': round(sum(day_scores) / len(day_scores)) if day_scores else 0
        })
    
    return jsonify({'trends': trends})

@app.route('/api/knowledge_mastery')
def knowledge_mastery():
    """获取知识点掌握情况"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session['user_id']
    
    # 获取所有答题记录
    answers = Answer.query.filter_by(user_id=user_id).all()
    
    # 按题型分类统计
    type_stats = {
        'calc': {'total': 0, 'correct': 0},
        'pattern': {'total': 0, 'correct': 0},
        'compare': {'total': 0, 'correct': 0},
        'count': {'total': 0, 'correct': 0},
        'word': {'total': 0, 'correct': 0}
    }
    
    # 题型名称映射
    type_names = {
        'calc': '计算题',
        'pattern': '找规律',
        'compare': '比较大小',
        'count': '数一数',
        'word': '应用题'
    }
    
    # 题号范围映射
    type_ranges = {
        'calc': (1, 20),
        'pattern': (21, 23),
        'compare': (24, 25),
        'count': (26, 27),
        'word': (28, 30)
    }
    
    for ans in answers:
        q_id = ans.question_id
        for q_type, (start, end) in type_ranges.items():
            if start <= q_id <= end:
                type_stats[q_type]['total'] += 1
                if ans.is_correct:
                    type_stats[q_type]['correct'] += 1
                break
    
    # 计算正确率
    mastery = []
    for q_type, stats in type_stats.items():
        if stats['total'] > 0:
            accuracy = round(stats['correct'] / stats['total'] * 100)
        else:
            accuracy = 0
        
        mastery.append({
            'type': q_type,
            'name': type_names.get(q_type, q_type),
            'total': stats['total'],
            'correct': stats['correct'],
            'accuracy': accuracy
        })
    
    # 按正确率排序
    mastery.sort(key=lambda x: x['accuracy'], reverse=True)
    
    return jsonify({'mastery': mastery})

@app.route('/api/weak_points')
def weak_points():
    """获取薄弱知识点分析"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session['user_id']
    
    # 获取最近100道错题
    mistakes = Mistake.query.filter_by(user_id=user_id) \
        .order_by(Mistake.created_at.desc()).limit(100).all()
    
    # 按题型分类
    type_mistakes = {}
    type_names = {
        'calc': '计算题',
        'pattern': '找规律',
        'compare': '比较大小',
        'count': '数一数',
        'word': '应用题'
    }
    
    type_ranges = {
        'calc': (1, 20),
        'pattern': (21, 23),
        'compare': (24, 25),
        'count': (26, 27),
        'word': (28, 30)
    }
    
    for mistake in mistakes:
        q_id = mistake.question_id
        for q_type, (start, end) in type_ranges.items():
            if start <= q_id <= end:
                if q_type not in type_mistakes:
                    type_mistakes[q_type] = []
                type_mistakes[q_type].append({
                    'question_id': mistake.question_id,
                    'wrong_answer': mistake.wrong_answer,
                    'correct_answer': mistake.correct_answer,
                    'explanation': mistake.explanation
                })
                break
    
    # 生成薄弱点分析
    weak_points = []
    for q_type, mistakes_list in type_mistakes.items():
        if len(mistakes_list) >= 3:  # 错题超过3个算薄弱
            weak_points.append({
                'type': q_type,
                'name': type_names.get(q_type, q_type),
                'count': len(mistakes_list),
                'examples': mistakes_list[:3]  # 前3个示例
            })
    
    # 按错题数排序
    weak_points.sort(key=lambda x: x['count'], reverse=True)
    
    return jsonify({'weak_points': weak_points})

@app.route('/api/generate_suggestions')
def generate_suggestions():
    """生成学习建议"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # 获取统计信息
    practice_count = db.session.query(Answer.practice_set).filter_by(user_id=user_id).distinct().count()
    
    # 计算平均分
    practice_sets = db.session.query(Answer.practice_set).filter_by(user_id=user_id).distinct().all()
    scores = []
    for (ps,) in practice_sets:
        if ps is None:
            continue
        answers = Answer.query.filter_by(user_id=user_id, practice_set=ps).all()
        if answers:
            correct = sum(1 for a in answers if a.is_correct)
            scores.append(round(correct / len(answers) * 100))
    
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    
    # 获取薄弱知识点
    weak_response = weak_points()
    weak_data = weak_response.get_json() if hasattr(weak_response, 'get_json') else {}
    
    suggestions = []
    
    # 根据练习次数生成建议
    if practice_count < 5:
        suggestions.append({
            'type': 'practice',
            'icon': '📝',
            'title': '坚持练习',
            'content': '你才刚开始，每天坚持练习一套题，很快就能看到进步！'
        })
    elif practice_count < 20:
        suggestions.append({
            'type': 'practice',
            'icon': '💪',
            'title': '保持节奏',
            'content': f'你已经完成了{practice_count}次练习，继续保持每天练习的好习惯！'
        })
    
    # 根据平均分生成建议
    if avg_score < 60:
        suggestions.append({
            'type': 'score',
            'icon': '📚',
            'title': '加强基础',
            'content': '建议多复习错题，巩固基础知识。可以从简单的题目开始，逐步提高难度。'
        })
    elif avg_score < 80:
        suggestions.append({
            'type': 'score',
            'icon': '📈',
            'title': '稳步提升',
            'content': '成绩在进步中！可以尝试挑战更高难度的题目，突破自己！'
        })
    elif avg_score >= 90:
        suggestions.append({
            'type': 'score',
            'icon': '🌟',
            'title': '表现优秀',
            'content': '太棒了！你的成绩非常优秀，可以尝试帮助其他小朋友一起进步哦！'
        })
    
    # 根据薄弱知识点生成建议
    if weak_data.get('weak_points'):
        weak_names = [wp['name'] for wp in weak_data['weak_points'][:2]]
        suggestions.append({
            'type': 'weakness',
            'icon': '🎯',
            'title': '重点突破',
            'content': f"{ '和'.join(weak_names)}是你的薄弱环节，建议多花时间练习这些题型。"
        })
    
    # 根据连续练习生成建议
    streak = PointSystem.check_practice_streak(user_id)
    if streak >= 7:
        suggestions.append({
            'type': 'streak',
            'icon': '🔥',
            'title': '坚持不懈',
            'content': f'你已经连续练习{streak}天了，这种坚持的精神值得表扬！'
        })
    elif streak == 0:
        suggestions.append({
            'type': 'streak',
            'icon': '📅',
            'title': '开始打卡',
            'content': '今天还没有练习哦，赶紧开始今天的练习吧！'
        })
    
    return jsonify({'suggestions': suggestions})


# ==================== 留言板 ====================

@app.route('/messages')
def messages_page():
    """留言板页面"""
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    return render_template('messages.html',
                         user_name=session['user_name'],
                         user_points=user.points if user else 0)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """获取留言列表"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', '')
    
    # 构建查询
    query = Message.query.filter_by(is_deleted=False, is_approved=True)
    
    if category and category != 'all':
        query = query.filter_by(category=category)
    
    # 分页
    pagination = query.order_by(Message.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    messages = []
    for msg in pagination.items:
        user = User.query.get(msg.user_id)
        messages.append({
            'id': msg.id,
            'content': msg.content,
            'category': msg.category,
            'is_anonymous': msg.is_anonymous,
            'author': '匿名用户' if msg.is_anonymous else (user.name if user else '未知'),
            'is_owner': msg.user_id == session['user_id'],
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return jsonify({
        'messages': messages,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@app.route('/api/messages', methods=['POST'])
def create_message():
    """创建留言"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    data = request.json
    content = data.get('content', '').strip()
    category = data.get('category', 'feedback')
    is_anonymous = data.get('is_anonymous', False)
    
    # 验证内容
    if not content:
        return jsonify({'success': False, 'message': '留言内容不能为空'}), 400
    
    if len(content) < 5:
        return jsonify({'success': False, 'message': '留言内容至少5个字'}), 400
    
    if len(content) > 500:
        return jsonify({'success': False, 'message': '留言内容不能超过500字'}), 400
    
    # 敏感词过滤
    has_sensitive, word = SensitiveFilter.contains_sensitive(content)
    if has_sensitive:
        return jsonify({
            'success': False, 
            'message': f'留言包含不当内容，请修改后重试'
        }), 400
    
    # 创建留言
    message = Message(
        user_id=session['user_id'],
        content=content,
        category=category,
        is_anonymous=is_anonymous
    )
    db.session.add(message)
    db.session.commit()
    
    # 奖励积分
    PointSystem.add_points(session['user_id'], 5, '发布留言')
    
    return jsonify({
        'success': True, 
        'message': '留言成功！感谢您的反馈！',
        'points_earned': 5
    })

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    """删除留言（软删除）"""
    if 'user_id' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    message = Message.query.get(message_id)
    if not message:
        return jsonify({'success': False, 'message': '留言不存在'}), 404
    
    # 只能删除自己的留言
    if message.user_id != session['user_id']:
        return jsonify({'success': False, 'message': '无权删除此留言'}), 403
    
    message.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': '留言已删除'})


# ==================== 管理后台 ====================

@app.route('/admin')
def admin_page():
    """管理后台页面"""
    return render_template('admin.html')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理后台登录"""
    data = request.json
    password = data.get('password', '')
    
    if password == app.config['ADMIN_PASSWORD']:
        session['is_admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '密码错误'})

@app.route('/api/admin/config', methods=['GET'])
def get_config():
    """获取当前AI配置"""
    if not session.get('is_admin'):
        return jsonify({'error': '请先登录管理后台'}), 401
    
    return jsonify({
        'ai_api_url': runtime_config['AI_API_URL'],
        'ai_model': runtime_config['AI_MODEL'],
        'ai_api_key_set': bool(runtime_config['AI_API_KEY']),  # 不返回实际Key
    })

@app.route('/api/admin/config', methods=['POST'])
def update_config():
    """更新AI配置"""
    if not session.get('is_admin'):
        return jsonify({'error': '请先登录管理后台'}), 401
    
    data = request.json
    
    if 'ai_api_url' in data:
        runtime_config['AI_API_URL'] = data['ai_api_url']
        app.config['AI_API_URL'] = data['ai_api_url']
    
    if 'ai_api_key' in data:
        runtime_config['AI_API_KEY'] = data['ai_api_key']
        app.config['AI_API_KEY'] = data['ai_api_key']
    
    if 'ai_model' in data:
        runtime_config['AI_MODEL'] = data['ai_model']
        app.config['AI_MODEL'] = data['ai_model']
    
    return jsonify({'success': True, 'message': '配置已更新'})

@app.route('/api/admin/test_ai', methods=['POST'])
def test_ai():
    """测试AI连接"""
    if not session.get('is_admin'):
        return jsonify({'error': '请先登录管理后台'}), 401
    
    try:
        import requests as req
        
        api_url = runtime_config['AI_API_URL']
        api_key = runtime_config['AI_API_KEY']
        model = runtime_config['AI_MODEL']
        
        if not api_key:
            return jsonify({'success': False, 'message': '未配置API Key'})
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': '请回复"连接成功"两个字'}
            ],
            'max_tokens': 20
        }
        
        response = req.post(api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        reply = result['choices'][0]['message']['content']
        
        return jsonify({
            'success': True, 
            'message': f'AI连接成功！回复：{reply}'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'连接失败：{str(e)}'
        })

@app.route('/api/admin/save_config', methods=['POST'])
def save_config_to_file():
    """保存配置到文件"""
    if not session.get('is_admin'):
        return jsonify({'error': '请先登录管理后台'}), 401
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        save_data = {
            'AI_API_URL': runtime_config['AI_API_URL'],
            'AI_API_KEY': runtime_config['AI_API_KEY'],
            'AI_MODEL': runtime_config['AI_MODEL'],
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': '配置已保存到config.json'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败：{str(e)}'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        AchievementSystem.init_achievements()
    
    print('=' * 50)
    print('🌱 数苗乐园 - 幼小衔接思维训练平台')
    print('=' * 50)
    print('📍 访问地址: http://localhost:5000')
    print('📍 管理后台: http://localhost:5000/admin')
    ai_status = '已配置' if runtime_config['AI_API_KEY'] else '未配置（离线模式）'
    print(f'🤖 AI模式: {ai_status}')
    print('=' * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
