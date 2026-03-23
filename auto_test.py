#!/usr/bin/env python3
"""
眼科分诊系统自动化测试
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_case_1():
    """测试案例1: 急性视力丧失 - 应判定为EMERGENT"""
    print("\n" + "="*60)
    print("测试案例 1: 急性视力丧失（预期：EMERGENT）")
    print("="*60)

    messages = [
        "我的左眼突然看不清了",
        "今天早上开始的",
        "没有做过手术",
        "没有受伤",
        "有眼痛",
        "疼痛在加重",
        "有恶心想吐",
        "眼睛有点红"
    ]

    history = []
    emr = None

    for i, msg in enumerate(messages, 1):
        print(f"\n[第{i}轮] 患者: {msg}")

        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": msg,
                "conversation_history": history,
                "current_emr": emr
            },
            stream=True
        )

        nurse_reply = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    event = json.loads(line[6:])
                    if event.get('type') == 'done':
                        nurse_reply = event['response']
                        emr = event['emr']
                        triage_level = event.get('triage_level')
                        disposition_ready = event.get('disposition_ready')

                        print(f"[第{i}轮] 护士: {nurse_reply}")
                        print(f"[状态] 分诊等级: {triage_level}, 可判定: {disposition_ready}")

                        if disposition_ready:
                            print(f"\n{'='*60}")
                            print(f"✅ 最终分诊结果: {triage_level}")
                            print(f"{'='*60}")
                            print("\n完整EMR:")
                            print(event.get('emr_text', ''))
                            print("\n分诊报告:")
                            print(event.get('triage_report', ''))
                            return triage_level

                        history.append({"role": "user", "content": msg})
                        history.append({"role": "assistant", "content": nurse_reply})
                        break
                except:
                    pass

        time.sleep(0.5)

    return None

def test_case_2():
    """测试案例2: 轻度不适 - 应判定为ROUTINE"""
    print("\n" + "="*60)
    print("测试案例 2: 轻度眼部不适（预期：ROUTINE）")
    print("="*60)

    messages = [
        "我的眼睛有点干涩",
        "右眼",
        "昨天开始的",
        "没有手术",
        "没有受伤",
        "视力没有变化",
        "没有眼痛",
        "没有发红"
    ]

    history = []
    emr = None

    for i, msg in enumerate(messages, 1):
        print(f"\n[第{i}轮] 患者: {msg}")

        response = requests.post(
            f"{API_BASE}/chat",
            json={
                "message": msg,
                "conversation_history": history,
                "current_emr": emr
            },
            stream=True
        )

        nurse_reply = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    event = json.loads(line[6:])
                    if event.get('type') == 'done':
                        nurse_reply = event['response']
                        emr = event['emr']
                        triage_level = event.get('triage_level')
                        disposition_ready = event.get('disposition_ready')

                        print(f"[第{i}轮] 护士: {nurse_reply}")
                        print(f"[状态] 分诊等级: {triage_level}, 可判定: {disposition_ready}")

                        if disposition_ready:
                            print(f"\n{'='*60}")
                            print(f"✅ 最终分诊结果: {triage_level}")
                            print(f"{'='*60}")
                            return triage_level

                        history.append({"role": "user", "content": msg})
                        history.append({"role": "assistant", "content": nurse_reply})
                        break
                except:
                    pass

        time.sleep(0.5)

    return None

if __name__ == "__main__":
    print("\n🏥 眼科分诊系统自动化测试")
    print("="*60)

    # 检查后端
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3)
        print(f"✅ 后端连接成功: {health.json()}")
    except:
        print("❌ 后端未启动，请先运行: python3 backend/main.py")
        exit(1)

    # 测试案例1
    result1 = test_case_1()

    # 测试案例2
    result2 = test_case_2()

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"案例1 (急性视力丧失): {result1} {'✅ 正确' if result1 == 'EMERGENT' else '❌ 错误'}")
    print(f"案例2 (轻度不适): {result2} {'✅ 正确' if result2 == 'ROUTINE' else '❌ 错误'}")
    print("="*60)
