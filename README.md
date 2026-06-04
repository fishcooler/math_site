# 幼小衔接数学练习网站

## 快速开始

### 方法一：双击启动（推荐）
1. 双击 `启动.bat` 文件
2. 等待安装依赖完成
3. 浏览器打开 http://localhost:5000

### 方法二：命令行启动
```bash
# 1. 安装依赖
pip install flask flask-sqlalchemy

# 2. 启动
python app.py

# 3. 浏览器打开
# http://localhost:5000
```

## 功能说明

| 功能 | 描述 |
|------|------|
| 用户管理 | 支持多个小朋友独立账号 |
| 30道题目 | 计算题、找规律、比较大小、数一数、应用题 |
| 重新生成 | 每次生成全新题目 |
| 自动批改 | 提交后显示对错和正确答案 |
| 错题本 | 自动记录错题，带解答说明 |

## 环境要求
- Python 3.7 或以上
- 无需其他依赖，启动脚本会自动安装

## 文件结构
```
math_site/
├── app.py              # 主程序
├── 启动.bat             # Windows 一键启动
├── static/
│   └── css/
│       └── style.css   # 样式文件
└── templates/
    ├── index.html       # 登录页
    ├── practice.html    # 练习页
    └── mistakes.html    # 错题本
```
