# 手动部署指南

## 准备工作

你的项目已经准备好部署了！所有必要的文件都已创建：
- ✅ requirements.txt
- ✅ railway.json
- ✅ backend/main.py
- ✅ frontend/

## 部署步骤

### 1. 上传到GitHub

由于本地缺少git工具，请手动上传：

1. 访问 https://github.com/new
2. 创建新仓库，命名为 `ophthalmic-triage`
3. 选择 "Public"
4. 点击 "uploading an existing file"
5. 将整个项目文件夹拖拽上传

### 2. 部署后端到Railway

1. 访问 https://railway.app
2. 使用GitHub登录
3. 点击 "New Project"
4. 选择 "Deploy from GitHub repo"
5. 选择你刚创建的 `ophthalmic-triage` 仓库
6. Railway会自动检测Python项目并开始部署

### 3. 配置环境变量

在Railway项目中：
1. 点击 "Variables" 标签
2. 添加变量：
   - Name: `DASHSCOPE_API_KEY`
   - Value: `sk-sflcpctwfzrcpeyebbynvypltxohsqsqswcjqfuejmfsqsss`
3. 点击 "Add"

### 4. 获取后端URL

1. 等待部署完成（约2-3分钟）
2. 点击 "Settings" 标签
3. 找到 "Domains" 部分
4. 点击 "Generate Domain"
5. 复制生成的URL（例如：`https://ophthalmic-triage-production.up.railway.app`）

### 5. 更新前端配置

打开 `frontend/app.js`，修改第6行：
```javascript
const API_BASE = "你的Railway后端URL";  // 替换这里
```

### 6. 部署前端

**选项A - 使用Vercel（推荐）**:
1. 访问 https://vercel.com
2. 使用GitHub登录
3. 点击 "Add New" → "Project"
4. 选择你的仓库
5. 配置：
   - Framework Preset: Other
   - Root Directory: `frontend`
   - Build Command: 留空
   - Output Directory: `.`
6. 点击 "Deploy"
7. 等待完成，获取前端URL

**选项B - 使用Netlify**:
1. 访问 https://netlify.com
2. 拖拽 `frontend` 文件夹到页面
3. 自动部署完成

## 完成！

你现在有两个URL：
- 后端: Railway提供的URL
- 前端: Vercel/Netlify提供的URL

将前端URL分享给其他人即可使用！

## 注意事项

- 确保前端的 `API_BASE` 指向正确的后端URL
- Railway免费版有使用限制，注意监控
- 如需更新代码，推送到GitHub后Railway会自动重新部署
