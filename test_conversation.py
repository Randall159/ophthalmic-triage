#!/usr/bin/env python3
"""
20轮医患对话测试 - 模拟喋喋不休的病人
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

# 喋喋不休的病人对话脚本
PATIENT_MESSAGES = [
    "hi",
    "hello there",
    "我眼睛不太舒服",
    "就是有点模糊",
    "左眼",
    "今天早上开始的",
    "没做过手术啊",
    "没有受伤",
    "有点疼",
    "疼痛在加重",
    "有点恶心",
    "眼睛有点红",
    "你说的是什么意思？",
    "我需要马上去医院吗？",
    "会不会失明啊？",
    "我很担心",
    "还有其他症状吗？",
    "需要做什么检查？",
    "大概要多久能好？",
    "谢谢你"
]

def test_conversation():
    print("🏥 开始20轮医患对话测试\n")
    print("="*80)

    history = []
    emr = None
    issues = []

    for round_num, patient_msg in enumerate(PATIENT_MESSAGES, 1):
        print(f"\n{'='*80}")
        print(f"第 {round_num} 轮")
        print(f"{'='*80}")
        print(f"👤 患者: {patient_msg}")

        try:
            response = requests.post(
                f"{API_BASE}/chat",
                json={
                    "message": patient_msg,
                    "conversation_history": history,
                    "current_emr": emr
                },
                stream=True,
                timeout=30
            )

            nurse_reply = ""
            step_details = {}

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        event = json.loads(line[6:])

                        if event.get('type') == 'step_done':
                            step = event['step']
                            agent = event['agent']
                            detail = event.get('detail', '')
                            input_data = event.get('input', '')

                            step_details[step] = {
                                'agent': agent,
                                'input': input_data,
                                'output': detail
                            }

                        if event.get('type') == 'done':
                            nurse_reply = event['response']
                            emr = event['emr']

                            # 分析问题
                            issues.extend(analyze_round(
                                round_num, patient_msg, nurse_reply,
                                step_details, emr
                            ))

                    except:
                        pass

            print(f"🏥 护士: {nurse_reply}")

            # 显示关键Agent输出
            if 2 in step_details:
                print(f"\n📋 Recipient提取:")
                print(f"   {step_details[2]['output'][:200]}...")

            history.append({"role": "user", "content": patient_msg})
            history.append({"role": "assistant", "content": nurse_reply})

            time.sleep(0.5)

        except Exception as e:
            print(f"❌ 错误: {e}")
            issues.append(f"Round {round_num}: API调用失败 - {e}")

    # 输出问题总结
    print(f"\n\n{'='*80}")
    print("🔍 问题分析报告")
    print(f"{'='*80}\n")

    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}\n")
    else:
        print("✅ 未发现明显问题")

    return issues

def analyze_round(round_num, patient_msg, nurse_reply, step_details, emr):
    """分析单轮对话中的问题"""
    issues = []

    # 问题1: 打招呼被当作主诉
    if patient_msg.lower() in ['hi', 'hello', 'hello there', '你好']:
        if emr and emr.get('Problem_Description') not in ['[NOT STATED]', None]:
            if emr['Problem_Description'].lower() in ['hi', 'hello']:
                issues.append(
                    f"Round {round_num}: ❌ Recipient错误 - "
                    f"将打招呼'{patient_msg}'提取为主诉'{emr['Problem_Description']}'"
                )

    # 问题2: 患者没提到的症状被标记为Yes
    symptom_keywords = {
        'Vision_Changed': ['看不清', '模糊', '视力', 'blurry', 'vision'],
        'Vision_Loss': ['看不见', '失明', '黑', 'blind', 'loss'],
        'Eye_Pain': ['疼', '痛', 'pain', 'hurt'],
        'Eyes_Red': ['红', 'red'],
        'Nausea_Vomiting': ['恶心', '吐', 'nausea', 'vomit']
    }

    for field, keywords in symptom_keywords.items():
        if emr and emr.get(field) == 'Yes':
            # 检查患者是否真的提到过
            mentioned = any(kw in patient_msg.lower() for kw in keywords)
            if not mentioned:
                # 检查历史对话
                # 这里简化处理，实际应该检查整个历史
                issues.append(
                    f"Round {round_num}: ⚠️ Recipient可能推断 - "
                    f"{field}=Yes，但患者本轮未明确提及"
                )

    # 问题3: 护士没有先问主诉
    if round_num == 1 and '症状' not in nurse_reply and '不舒服' not in nurse_reply:
        if 'symptom' not in nurse_reply.lower() and 'concern' not in nurse_reply.lower():
            issues.append(
                f"Round {round_num}: ⚠️ Inquirer问题 - "
                f"首轮应该先问'您有什么症状？'而不是直接问细节"
            )

    # 问题4: 患者提问时护士没有回答
    if '?' in patient_msg or '吗' in patient_msg or '什么' in patient_msg:
        if '?' not in nurse_reply and len(nurse_reply) < 50:
            issues.append(
                f"Round {round_num}: ⚠️ Inquirer问题 - "
                f"患者提问但护士没有充分回答，只是继续追问"
            )

    return issues

if __name__ == "__main__":
    issues = test_conversation()
    print(f"\n共发现 {len(issues)} 个问题")
