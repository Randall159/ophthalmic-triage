# 部署指南 - Ophthalmic Triage System

## 本地测试

1. 启动后端：
```bash
python3 backend/main.py
```

2. 打开前端：
```bash
open frontend/index.html
```

## 在线部署方案

### 方案1: Vercel (推荐 - 免费)

**后端部署 (FastAPI):**
1. 安装 Vercel CLI: `npm i -g vercel`
2. 在项目根目录创建 `vercel.json`:
```json
{
  "builds": [{"src": "backend/main.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "backend/main.py"}]
}
```
3. 部署: `vercel --prod`
4. 设置环境变量: `vercel env add DASHSCOPE_API_KEY`

**前端部署:**
1. 修改 `frontend/app.js` 中的 `API_BASE` 为后端URL
2. 部署前端: `vercel frontend --prod`

### 方案2: Railway (推荐 - 简单)

1. 访问 https://railway.app
2. 连接GitHub仓库
3. 添加环境变量 `DASHSCOPE_API_KEY`
4. Railway自动检测FastAPI并部署
5. 获取公开URL，更新前端 `API_BASE`

### 方案3: Render (免费)

**后端:**
1. 访问 https://render.com
2. 新建 Web Service，连接仓库
3. 设置:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. 添加环境变量 `DASHSCOPE_API_KEY`

**前端:**
1. 新建 Static Site
2. Build Command: 留空
3. Publish Directory: `frontend`

## 分享链接

部署完成后，你会获得类似这样的URL：
- 前端: `https://your-app.vercel.app`
- 后端: `https://your-api.railway.app`

将前端URL分享给其他人即可使用。

## 注意事项

1. 确保API密钥有足够余额
2. 前端需要更新 `API_BASE` 指向部署的后端URL
3. 建议启用HTTPS（部署平台默认提供）
4. 考虑添加访问限制或认证（可选）
