# 眼科多智能体电话分诊系统

## 🎯 系统概述

基于阿里云 Qwen3-4B 模型的智能眼科分诊系统，采用多智能体并行架构，实现高效、准确的患者电话分诊。

## 🏗️ 系统架构

### 后端技术栈
- **框架**: FastAPI + Uvicorn
- **AI模型**: Qwen3-4B (DashScope API)
- **通信**: Server-Sent Events (SSE) 流式响应
- **端口**: 8000

### 4-Agent 流水线

1. **Safety Monitor (Pre-Check)** 🛡️
   - 检测连接问题、人工转接请求、非眼科问题
   - 旁路异步扫描，毫秒级响应

2. **Recipient Agent** 📋
   - 轻量级信息提取
   - 增量更新 EMR（电子病历）
   - 只提取患者明确陈述的事实

3. **Assessor Agent** 🔬
   - 基于 AAO 临床指南的深度推理
   - EMR 不完整时休眠节省算力
   - 输出 Gap Analysis（缺失临床鉴别点）

4. **Inquirer Agent** 💬
   - 自然对话的分诊护士
   - 自治模式：追问基础信息
   - 临床模式：基于 Gap Analysis 深度问诊

5. **Safety Monitor (Post-Check)** 🛡️
   - 拦截越权治疗建议
   - 允许症状解释

## 🚀 快速启动

### 方式一：使用启动脚本
```bash
cd /Users/shihao/Desktop/Claude秘书工作/ophthalmic-triage
./start.sh
```

### 方式二：手动启动
```bash
# 1. 安装依赖
cd backend
pip3 install -r requirements.txt

# 2. 启动后端
python3 -m uvicorn main:app --port 8000 --host 0.0.0.0

# 3. 打开前端
open frontend/index.html
```

## 📱 使用界面

### 患者交互界面
打开 `frontend/index.html` 即可使用完整的患者聊天界面。

**功能特性**:
- 实时对话流
- 分诊等级徽章（紧急/尽快/常规）
- 实时 EMR 状态显示
- Agent 流水线可视化
- 分诊逻辑报告

### 测试页面
打开 `test.html` 进行系统功能测试。

## 🔧 API 接口

### 健康检查
```bash
GET http://localhost:8000/health
```

### 聊天接口
```bash
POST http://localhost:8000/chat
Content-Type: application/json

{
  "message": "我的左眼突然看不清了",
  "conversation_history": [],
  "current_emr": null
}
```

## 📊 EMR 字段说明

### 基础四大支柱（优先级最高）
- `laterality`: 患眼（左/右/双）
- `onset_when`: 发病时间
- `recent_surgery`: 近期手术史
- `burn_injury`: 外伤/化学烧伤史

### 症状分支
- **视力变化**: vision_changed, vision_loss, flashes, floaters, peripheral_shadow
- **疼痛**: eye_pain, pain_progression, nausea_vomiting, other_pain
- **红肿分泌物**: redness, discharge, eyelids_stick

## 🎨 前端界面说明

### 左侧：患者聊天区
- 对话历史
- 输入框（Enter 发送，Shift+Enter 换行）
- 分诊等级徽章

### 右侧：系统监控面板
1. **电子病历 (EMR)**: 实时更新的患者信息
2. **分诊逻辑报告**: AAO 指南匹配结果
3. **Agent 流水线状态**: 5步流程实时可视化

## ⚙️ 配置说明

### API 密钥
编辑 `backend/config.py`:
```python
DASHSCOPE_API_KEY = "sk-your-api-key"
MODEL = "qwen3-4b"
```

### 前端 API 地址
编辑 `frontend/app.js`:
```javascript
const API_BASE = "http://localhost:8000";
```

## 📝 工作流程

1. 用户发送症状描述
2. Safety Monitor 预检查（连接/人工转接/非眼科）
3. Recipient 提取信息更新 EMR
4. Assessor 评估（EMR 完整时启动）
5. Inquirer 生成护士回复
6. Safety Monitor 后检查（拦截治疗建议）
7. 返回最终回复 + EMR + 分诊等级

## 🔒 安全机制

- 双重 Safety Monitor 护栏
- 不提供治疗方案（仅分诊）
- 自动识别紧急情况
- 人工转接触发机制

## 📄 文件结构

```
ophthalmic-triage/
├── backend/
│   ├── main.py          # FastAPI 主程序
│   ├── agents.py        # 4个Agent实现
│   ├── config.py        # API配置
│   └── requirements.txt
├── frontend/
│   ├── index.html       # 患者界面
│   ├── app.js          # 前端逻辑
│   └── style.css       # 样式
├── test.html           # 测试页面
├── start.sh            # 启动脚本
└── A工作流.md          # 详细设计文档
```

## ✅ 验证清单

- [x] 后端 API 正常启动
- [x] 健康检查通过
- [x] SSE 流式响应正常
- [x] EMR 增量更新正确
- [x] Agent 流水线完整执行
- [x] 前端界面正常显示
- [x] 实时状态更新正常
- [x] 分诊等级正确显示

## 🎯 系统特点

1. **极速响应**: 并行架构 + 智能休眠
2. **医学严谨**: 基于 AAO 官方指南
3. **自然交互**: 共情对话 + 单问题追问
4. **安全可靠**: 双重护栏 + 人工转接
5. **实时可视**: 全流程透明展示

---

**状态**: ✅ 已验证可正常运行
**最后更新**: 2026-03-23
