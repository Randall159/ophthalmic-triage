# 快速部署指南

## 方式1: Railway (推荐 - 最简单)

### 步骤：

1. 访问 https://railway.app 并登录（使用GitHub账号）

2. 点击 "New Project" → "Deploy from GitHub repo"

3. 如果还没有GitHub仓库，先创建：
```bash
cd /Users/shihao/Desktop/Claude秘书工作/ophthalmic-triage
git init
git add .
git commit -m "Initial commit"
gh repo create ophthalmic-triage --public --source=. --push
```

4. 在Railway选择你的仓库

5. 添加环境变量：
   - 点击 "Variables"
   - 添加 `DASHSCOPE_API_KEY` = `sk-sflcpctwfzrcpeyebbynvypltxohsqsqswcjqfuejmfsqsss`

6. Railway会自动检测并部署，等待几分钟

7. 部署完成后，点击 "Settings" → "Generate Domain" 获取后端URL

8. 复制后端URL（例如：https://your-app.railway.app）

9. 修改前端配置：
   - 打开 `frontend/app.js`
   - 将第6行的 `API_BASE` 改为你的后端URL

10. 部署前端到Vercel：
```bash
cd frontend
vercel --prod
```

完成！你会得到一个可分享的前端URL。

---

## 方式2: 使用Vercel部署全栈

详见下一页...
