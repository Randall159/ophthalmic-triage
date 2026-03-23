# 安全性与费用说明

## 一、代码和API安全性

### 1. 代码泄漏情况

**已公开的内容：**
- ✅ GitHub仓库是Public（公开），任何人都可以看到你的代码
- ✅ 前端代码（HTML/CSS/JS）在浏览器中可以被查看
- ✅ 后端代码（Python）在GitHub上可见

**受保护的内容：**
- ❌ API密钥（`DASHSCOPE_API_KEY`）**不会泄漏**
  - 存储在Railway的环境变量中
  - 不在代码中，不会被推送到GitHub
  - 只有后端服务器能访问

### 2. API密钥安全性

**当前状态：安全 ✅**

你的硅基流动API密钥（`sk-sflcpctwfzrcpeyebbynvypltxohsqsqswcjqfuejmfsqsss`）：
- 存储在Railway环境变量中
- 不在GitHub代码中
- 前端无法直接访问
- 只有后端服务器使用

**潜在风险：**
- 如果有人恶意大量调用你的网站，会消耗你的API额度
- 建议在硅基流动后台设置每日调用限额

---

## 二、费用说明

### Railway（后端托管）

**免费额度：**
- 每月 $5 免费额度
- 约500小时运行时间
- 足够个人使用和演示

**超出后：**
- 按使用量计费
- 约 $0.000463/分钟
- 可以设置预算上限防止超支

**如何监控：**
1. 登录 https://railway.app
2. 点击项目 → Usage 标签
3. 查看当前使用量

### Vercel（前端托管）

**免费额度：**
- 100GB带宽/月
- 无限部署次数
- 个人使用完全免费

**超出后：**
- 自动升级到Pro计划（$20/月）
- 可以在设置中禁用自动升级

### 硅基流动API

**费用：**
- 按token计费
- Qwen3.5-4B: 约 ¥0.0001/1K tokens
- Qwen3.5-397B: 约 ¥0.01/1K tokens

**当前消耗：**
- 取决于对话轮数和长度
- 建议在硅基流动后台查看余额

---

## 三、如何关闭/删除部署

### 1. 关闭Railway后端

**临时暂停（不删除）：**
1. 登录 https://railway.app
2. 进入项目
3. Settings → Sleep Mode → Enable

**永久删除：**
1. 登录 https://railway.app
2. 进入项目
3. Settings → Danger → Delete Project
4. 输入项目名确认删除

### 2. 关闭Vercel前端

**临时暂停：**
- Vercel免费版无暂停功能，但不访问就不产生费用

**永久删除：**
1. 登录 https://vercel.com
2. 进入项目
3. Settings → General → Delete Project
4. 输入项目名确认删除

### 3. 删除GitHub仓库

**如果想完全移除代码：**
1. 登录 https://github.com
2. 进入仓库 Randall159/ophthalmic-triage
3. Settings → Danger Zone → Delete this repository
4. 输入 `Randall159/ophthalmic-triage` 确认删除

**注意：** 删除GitHub仓库后，Railway和Vercel的部署仍会运行，需要分别删除

### 4. 撤销GitHub Token

**如果担心token泄漏：**
1. 访问 https://github.com/settings/tokens
2. 找到 `ophthalmic-triage-deploy`
3. 点击 Delete
4. 确认删除

---

## 四、如何保护API密钥

### 当前已做的保护 ✅

1. API密钥存储在环境变量中
2. 不在代码中硬编码
3. 不推送到GitHub

### 额外保护措施（可选）

**1. 设置API调用限额**
- 登录硅基流动后台
- 设置每日/每月调用上限
- 防止恶意消耗

**2. 添加访问限制（需要修改代码）**
- 添加用户认证
- 限制IP访问
- 添加验证码

**3. 监控使用情况**
- 定期检查Railway使用量
- 定期检查硅基流动余额
- 设置预算告警

---

## 五、总结

### 当前状态

| 项目 | 状态 | 费用 | 安全性 |
|------|------|------|--------|
| GitHub代码 | 公开 | 免费 | 代码可见，API密钥安全 |
| Railway后端 | 运行中 | 免费额度内 | API密钥受保护 |
| Vercel前端 | 运行中 | 免费 | 无敏感信息 |
| 硅基流动API | 按量计费 | 按使用付费 | 密钥安全 |

### 建议

1. **定期监控费用**：每周检查Railway和硅基流动使用量
2. **设置预算上限**：防止意外超支
3. **不分享给太多人**：避免大量并发消耗资源
4. **定期检查日志**：发现异常访问及时处理

### 如果只是演示/测试

- 当前配置完全够用
- 费用基本为0
- 不需要额外保护措施

### 如果要公开给很多人使用

- 建议添加用户认证
- 设置API调用限额
- 考虑升级到付费计划
