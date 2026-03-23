# Ophthalmic Triage System - 完整项目文档

## 项目概述

这是一个基于AI的眼科电话分诊系统，使用多Agent架构实现智能问诊和分诊。系统遵循AAO（美国眼科学会）临床指南，将患者分为EMERGENT（紧急）、URGENT（尽快）、ROUTINE（常规）三个等级。

## 技术栈

- **后端**: Python + FastAPI + OpenAI SDK
- **前端**: 原生 HTML/CSS/JavaScript
- **AI模型**: Qwen系列（通过硅基流动API）
- **通信**: Server-Sent Events (SSE) 实时流式传输

## 核心架构

### 多Agent流水线

系统采用5步Agent流水线：

1. **Safety Monitor (Pre-Check)** - 安全预检查
2. **Recipient Agent** - EMR信息提取
3. **Assessor Agent** - 临床评估和分诊
4. **Inquirer Agent** - 护士问诊
5. **Safety Monitor (Post-Check)** - 安全后检查

---

## 文件结构详解

### 后端文件 (backend/)

#### 1. `config.py`
**作用**: 配置文件，存储API密钥和模型设置

**内容**:
- `DASHSCOPE_API_KEY`: 硅基流动API密钥
- `DASHSCOPE_BASE_URL`: API端点 (https://api.siliconflow.cn/v1)
- `MODEL`: 当前使用的模型名称（可动态切换）

#### 2. `agents.py`
**作用**: 核心Agent实现，包含所有智能体的逻辑

**关键组件**:

**a) EMR字段定义**
- `EMR_FIELDS`: 24个病历字段列表
- `CRITICAL_FIELDS`: 7个必填字段（主诉、时间、患眼等）
- `EMR_LABELS`: 中英文标签映射

**b) SafetyAgent**
- `check()`: 预检查患者输入（检测人工转接请求）
- `post_check()`: 后检查护士输出（防止提供治疗建议）

**c) RecipientAgent**
- `update_emr()`: 从对话中提取并更新EMR
- 自动填充依赖字段（如Surgery=No时Surgery_Details=None）
- 过滤打招呼等非医疗内容
- 总结归纳患者描述为专业术语

**d) AssessorAgent**
- `evaluate()`: 基于AAO指南评估分诊等级
- 输出: triage_level, gap_analysis, disposition_ready
- 只在EMR完整时激活

**e) InquirerAgent**
- `generate_response()`: 生成护士问诊回复
- 两种模式: Autonomous（收集基本信息）/ Clinical（深入问诊）
- 根据disposition_ready决定是继续提问还是给出分诊结论
- 自动匹配患者语言（中文/英文）

#### 3. `main.py`
**作用**: FastAPI应用主文件，定义API端点和流水线逻辑

**API端点**:
- `GET /health`: 健康检查，返回模型信息
- `POST /model`: 动态切换模型
- `GET /prompts/{agent_type}`: 获取Agent的prompt
- `POST /prompts/{agent_type}`: 保存Agent的prompt（内存）
- `POST /chat`: 主要对话端点，SSE流式返回

**流水线逻辑** (`stream_pipeline`):
1. Safety pre-check
2. Recipient更新EMR
3. Assessor评估（如果EMR完整）
4. Inquirer生成回复
5. Safety post-check
6. 返回最终结果

---

### 前端文件 (frontend/)

#### 4. `index.html`
**作用**: 主页面结构

**布局**:
- Header: Logo、模型选择器、清空按钮、状态指示
- 左侧: 聊天界面、语音输入按钮、最终分诊结果
- 右侧: EMR显示、分诊报告、流水线状态、Agent调试日志、Prompt编辑器

#### 5. `app.js`
**作用**: 前端交互逻辑

**核心功能**:
- `sendMessage()`: 发送消息并处理SSE流
- `addAgentDebug()`: 显示完整的Agent输入输出
- `showFinalResult()`: 显示最终分诊结果
- `speakText()`: 语音输出（Web Speech API）
- 语音识别: 使用浏览器原生API
- 模型切换: 调用后端API动态更改模型

#### 6. `style.css`
**作用**: 样式定义

**设计特点**:
- Google Material Design风格
- 响应式布局
- 分诊等级颜色编码（红/黄/绿）
- 流水线步骤动画效果

---

## 工作流程详解

### 1. 用户发送消息
前端通过POST /chat发送消息、历史记录、当前EMR

### 2. Safety Pre-Check
检查是否包含人工转接请求或非眼科紧急情况

### 3. Recipient提取信息
- 解析患者消息
- 更新EMR字段
- 自动填充依赖字段
- 检查EMR是否完整（CRITICAL_FIELDS）

### 4. Assessor评估
**如果EMR不完整**: 返回SLEEP状态
**如果EMR完整**:
- 映射症状到AAO分类
- 评估分诊等级
- 生成gap_analysis（需要问的问题）
- 判断是否Ready for Disposition

### 5. Inquirer生成回复
**如果disposition_ready=True**: 给出最终分诊结论
**如果disposition_ready=False**: 根据gap_analysis继续提问

### 6. Safety Post-Check
检查护士回复是否包含治疗建议

### 7. 返回结果
通过SSE流式返回每个步骤的状态和最终结果

---

## 部署指南

详见 `DEPLOYMENT.md`，推荐使用：
- **Vercel**: 免费，支持FastAPI和静态网站
- **Railway**: 最简单，自动检测
- **Render**: 稳定可靠

---

## 特色功能

1. **语音交互**: 支持语音输入和输出（浏览器原生API）
2. **实时调试**: 完整显示每个Agent的输入输出
3. **Prompt编辑**: 在线查看和编辑Agent的prompt
4. **模型切换**: 支持5种Qwen模型动态切换
5. **多语言**: 护士自动匹配患者语言
6. **完整EMR**: 自动填充依赖字段，确保无遗漏

---

## 开发者指南

### 添加新的EMR字段
1. 在`agents.py`的`EMR_FIELDS`中添加
2. 在`EMR_LABELS`中添加标签
3. 如果是依赖字段，在`update_emr()`中添加自动填充逻辑

### 修改分诊逻辑
编辑`agents.py`中的`ASSESSOR_PROMPT`，遵循AAO指南格式

### 自定义护士行为
编辑`INQUIRER_AUTONOMOUS_PROMPT`和`INQUIRER_CLINICAL_PROMPT`

---

## 测试

运行20轮对话测试:
```bash
python3 test_conversation.py
```

---

## 许可证

本项目仅供学习和研究使用。

