# AI智能出题配置说明

## 配置步骤

### 1. 获取API Key

支持以下AI服务：

#### DeepSeek（推荐，便宜好用）
1. 访问 https://platform.deepseek.com/
2. 注册账号并登录
3. 在"API密钥"页面创建新的API Key
4. 复制API Key备用

#### 其他兼容服务
- OpenAI API
- 智谱AI
- 百度文心一言
- 阿里通义千问

### 2. 修改配置文件

编辑 `/home/wh/math_site/app.py`，找到以下配置：

```python
# AI配置
app.config['AI_API_URL'] = 'https://api.deepseek.com/v1/chat/completions'
app.config['AI_API_KEY'] = ''  # 需要配置你的API Key
app.config['AI_MODEL'] = 'deepseek-chat'
```

#### DeepSeek配置示例
```python
app.config['AI_API_URL'] = 'https://api.deepseek.com/v1/chat/completions'
app.config['AI_API_KEY'] = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'
app.config['AI_MODEL'] = 'deepseek-chat'
```

#### OpenAI配置示例
```python
app.config['AI_API_URL'] = 'https://api.openai.com/v1/chat/completions'
app.config['AI_API_KEY'] = 'sk-xxxxxxxxxxxxxxxxxxxxxxxx'
app.config['AI_MODEL'] = 'gpt-3.5-turbo'
```

#### 智谱AI配置示例
```python
app.config['AI_API_URL'] = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'
app.config['AI_API_KEY'] = 'xxxxxxxxxxxxxxxxxxxxxxxx'
app.config['AI_MODEL'] = 'glm-4'
```

### 3. 重启服务

```bash
cd /home/wh/math_site
python3 app.py
```

## 使用说明

### 出题模式

1. **离线模式**（默认）
   - 无需网络连接
   - 使用本地随机算法生成题目
   - 速度快，随时可用

2. **AI智能模式**
   - 需要网络连接和API Key
   - 根据学生薄弱知识点个性化出题
   - 题目更多样化

### AI智能出题特点

1. **个性化**：根据学生历史答题数据，针对薄弱知识点出题
2. **多样化**：每次生成的题目都不相同
3. **自适应**：如果某类题型错误率高，会适当增加比例
4. **自动降级**：如果AI调用失败，自动切换到离线模式

### 费用说明

以DeepSeek为例：
- 每次出题约消耗500-1000 tokens
- 价格：约0.001-0.002元/次
- 非常便宜，适合日常使用

## 故障排除

### 问题1：AI出题失败
**可能原因：**
- API Key未配置或已过期
- 网络连接问题
- API服务不可用

**解决方法：**
- 检查API Key是否正确
- 检查网络连接
- 系统会自动降级到离线模式

### 问题2：出题速度慢
**可能原因：**
- 网络延迟
- API服务响应慢

**解决方法：**
- 耐心等待（通常5-10秒）
- 或切换到离线模式

### 问题3：题目质量不佳
**可能原因：**
- AI模型理解偏差

**解决方法：**
- 刷新重新生成
- 或使用离线模式

## 安全提示

⚠️ **请勿将API Key泄露给他人！**

⚠️ **建议定期更换API Key！**

⚠️ **可以设置API使用限额，防止滥用！**
