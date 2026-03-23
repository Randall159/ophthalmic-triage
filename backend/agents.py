"""
Ophthalmic Triage — New Workflow (新工作流)
Architecture:
  - Safety Monitor: out-of-band, intercepts pre & post
  - Recipient: updates EMR incrementally (only missing fields)
  - Assessor: sleeps until EMR complete, then outputs Gap Analysis
  - Inquirer: autonomous mode (asks missing basics) or clinical mode (uses Gap Analysis)
"""
import json
from openai import OpenAI
try:
    from backend.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    from backend import config
except ModuleNotFoundError:
    from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
    import config

client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)

EMR_FIELDS = [
    "Problem_Description", "Problem_Begin_Time", "Problem_Suddenness", "Problem_Progression",
    "Affects_Eye", "Recent_Surgery", "Surgery_Details", "Vision_Changed", "Vision_Loss",
    "Flashes", "Floaters", "Peripheral_Shadows", "Vision_Change_Type",
    "Eye_Pain", "Pain_Details", "Pain_Progression", "Nausea_Vomiting", "Other_Pain",
    "Eyes_Red", "Discharge", "Eyelids_Stick", "Burn_Injury", "Injury_Details",
    "Wear_Contact_Lens", "Other_Symptoms",
]
CRITICAL_FIELDS = ["Problem_Description", "Affects_Eye", "Problem_Begin_Time", "Recent_Surgery", "Burn_Injury"]

EMR_LABELS = {
    "Problem_Description": "主诉 / Chief Complaint",
    "Problem_Begin_Time": "发病时间 / Onset When",
    "Problem_Suddenness": "起病方式 / How Sudden",
    "Problem_Progression": "病情变化 / Progression",
    "Affects_Eye": "患眼 / Laterality",
    "Recent_Surgery": "近期手术 / Recent Surgery",
    "Surgery_Details": "手术详情 / Surgery Details",
    "Vision_Changed": "视力变化 / Vision Changed",
    "Vision_Loss": "视力丧失 / Vision Loss",
    "Flashes": "闪光感 / Flashes",
    "Floaters": "飞蚊症 / Floaters",
    "Peripheral_Shadows": "周边阴影 / Peripheral Shadows",
    "Vision_Change_Type": "视觉类型变化 / Vision Type Change",
    "Eye_Pain": "眼痛 / Eye Pain",
    "Pain_Details": "疼痛详情 / Pain Details",
    "Pain_Progression": "疼痛变化 / Pain Progression",
    "Nausea_Vomiting": "恶心呕吐 / Nausea/Vomiting",
    "Other_Pain": "其他疼痛 / Other Pain",
    "Eyes_Red": "眼红 / Redness",
    "Discharge": "分泌物 / Discharge",
    "Eyelids_Stick": "眼睑粘连 / Eyelids Stick",
    "Burn_Injury": "烧伤/外伤 / Burn/Injury",
    "Injury_Details": "外伤详情 / Injury Details",
    "Wear_Contact_Lens": "隐形眼镜 / Contact Lens",
    "Other_Symptoms": "其他症状 / Other Symptoms",
}


def empty_emr() -> dict:
    return {f: "[NOT STATED]" for f in EMR_FIELDS}


def _call(system: str, user: str, max_tokens: int = 1200) -> str:
    resp = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        extra_body={"enable_thinking": False},
    )
    return (resp.choices[0].message.content or "").strip()


# ── Safety Monitor ────────────────────────────────────────────────────────────

SAFETY_PRE_PROMPT = """# Role
You are the "Safety Monitor Agent", an out-of-band watchdog. You evaluate the User's Input.

# Trigger Conditions & Overrides
1. USER INPUT CHECK (Human Handoff): If the patient explicitly demands to speak to a human, threatens self-harm, or describes a life-threatening NON-eye emergency (e.g., heart attack, stroke).
   -> Output: "[OVERRIDE_USER] I understand your concern. Please hold while I transfer you to a human nurse immediately. (Or dial 911 for non-eye emergencies)."

# Default Action
If NO triggers are met, output exactly: "[PASS]"

Note: Nausea/vomiting in context of eye symptoms is SAFE - it's critical for glaucoma diagnosis."""

SAFETY_POST_PROMPT = """# Role
You are the "Safety Monitor Agent", an out-of-band watchdog. You evaluate the Inquirer Agent's Drafted Output.

# Trigger Conditions & Overrides
2. AI OUTPUT CHECK (Treatment Violation): If the Inquirer Agent's drafted response prescribes specific medicine (e.g., "Take ibuprofen 200mg", "Use antibiotic drops"), suggests medical treatments (e.g., "You need laser surgery", "Apply steroid cream"), or advises surgical action.

   ALLOWED behaviors (do NOT block these):
   - Asking questions about symptoms (e.g., "How long has the pain lasted?", "Which eye is affected?")
   - Validating patient concerns (e.g., "I understand your worry")
   - Mentioning potential diagnoses for context (e.g., "This could be related to...")
   - Recommending over-the-counter artificial tears
   - Explaining what symptoms mean

   -> Output: "[OVERRIDE_AI] BLOCK. System instruction to Inquirer: You provided a treatment plan. Please regenerate without providing medical treatment advice."

# Default Action
If NO triggers are met, output exactly: "[PASS]"
"""


class SafetyAgent:
    def check(self, patient_input: str) -> dict:
        raw = _call(SAFETY_PRE_PROMPT, f"Patient input: {patient_input}", max_tokens=200)
        is_safe = "[PASS]" in raw
        override, trigger_handoff = "", False
        if not is_safe:
            if "[OVERRIDE_USER]" in raw:
                parts = raw.split("[OVERRIDE_USER]", 1)
                override = parts[1].strip() if len(parts) > 1 else raw
                trigger_handoff = True
        return {"is_safe": is_safe, "raw": raw, "override_message": override, "trigger_handoff": trigger_handoff}

    def post_check(self, nurse_reply: str) -> dict:
        raw = _call(SAFETY_POST_PROMPT, f"Nurse reply: {nurse_reply}", max_tokens=200)
        is_safe = "[PASS]" in raw
        override = ""
        if not is_safe:
            if "[OVERRIDE_AI]" in raw:
                parts = raw.split("->", 1)
                override = "I need to gather more information before I can advise further."
        return {"is_safe": is_safe, "raw": raw, "override_message": override}


# ── Recipient Agent ───────────────────────────────────────────────────────────

RECIPIENT_PROMPT = """# Role
You are the "Recipient Agent" in an asynchronous Ophthalmic Triage system. Your sole job is to rapidly extract new medical facts from the patient's latest message and output a JSON object containing ONLY the updated fields to modify the "Patient Telephone Screening Form" state file.

# Rules
1. DO NOT converse, diagnose, or output markdown text.
2. ONLY output a raw JSON object.
3. CRITICAL: Extract and SUMMARIZE patient information professionally. Do NOT copy patient's exact words.
4. CRITICAL: Ignore greetings like "hi", "hello", "你好" - these are NOT medical complaints.
5. For Problem_Description: Summarize the chief complaint in medical terms (e.g., "Blurred vision" not "my eye is blur")
6. For Problem_Begin_Time: Standardize time expressions (e.g., "10 days ago" not "10 days")
7. For Problem_Suddenness: Use "Sudden" or "Gradual" based on patient description
8. If patient says "no" to a question, map it correctly based on conversation context.

# Allowed JSON Keys (Based on the Screening Form):
- "Problem_Description" (String)
- "Problem_Begin_Time" (String)
- "Problem_Suddenness" (String)
- "Problem_Progression" ("Worsened" / "Improved" / "Unchanged")
- "Affects_Eye" ("Right" / "Left" / "Both")
- "Recent_Surgery" ("Yes" / "No")
- "Surgery_Details" (String)
- "Vision_Changed" ("Yes" / "No")
- "Vision_Loss" ("Yes" / "No", "Constant", "Intermittent")
- "Flashes" ("Yes" / "No")
- "Floaters" ("Yes" / "No")
- "Peripheral_Shadows" ("Yes" / "No")
- "Vision_Change_Type" ("Double" / "Distorted" / "Fading" / "Other")
- "Eye_Pain" ("Yes" / "No")
- "Pain_Details" (String: Location, description, intensity)
- "Pain_Progression" ("Worsened" / "Improved" / "Unchanged")
- "Nausea_Vomiting" ("Yes" / "No")
- "Other_Pain" ("Headache" / "Facial pain" / "Jaw pain" / "Other")
- "Eyes_Red" ("Yes" / "No")
- "Discharge" ("Yes" / "No", "Description")
- "Eyelids_Stick" ("Yes" / "No")
- "Burn_Injury" ("Yes" / "No")
- "Injury_Details" (String)
- "Wear_Contact_Lens" ("Yes" / "No")

# Example Output:
{"Affects_Eye": "Right", "Eye_Pain": "Yes", "Problem_Begin_Time": "This morning"}"""


class RecipientAgent:
    def update_emr(self, history: list, new_message: str, current_emr: dict) -> dict:
        missing = [f for f in EMR_FIELDS if current_emr.get(f) == "[NOT STATED]"]
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)

        # Check if message is just a greeting
        greeting_check = new_message.strip().lower()
        if greeting_check in ['hi', 'hello', 'hello there', '你好', 'hey']:
            return current_emr  # Don't update EMR for greetings

        user_prompt = (
            f"Current EMR:\n{json.dumps(current_emr, ensure_ascii=False, indent=2)}\n\n"
            f"Recent conversation:\n{history_text}\n\n"
            f"New patient message: {new_message}\n\n"
            "CRITICAL: Only extract what the patient EXPLICITLY said. Do NOT infer or fill in missing fields.\n"
            "Examples:\n"
            "- Patient: 'my eye is pain' → {\"Eye_Pain\": \"Yes\"}\n"
            "- Patient: 'no' (when asked about contact lens) → {\"Wear_Contact_Lens\": \"No\"}\n"
            "- Patient: 'no' (when asked about surgery) → {\"Recent_Surgery\": \"No\"}\n"
            "- Patient: 'no' (when asked about injury) → {\"Burn_Injury\": \"No\"}\n"
            "- Patient: '左眼模糊' → {\"Affects_Eye\": \"Left\", \"Vision_Changed\": \"Yes\"}\n"
            "- Patient: '今天早上开始的' → {\"Problem_Begin_Time\": \"今天早上\"}\n"
            "Look at the conversation history to understand what question was asked, then map the answer correctly.\n"
            "Output ONLY the JSON with fields mentioned by patient."
        )
        raw = _call(RECIPIENT_PROMPT, user_prompt, max_tokens=1000)
        try:
            start, end = raw.find("{"), raw.rfind("}") + 1
            updated = json.loads(raw[start:end])
            merged = dict(current_emr)
            for k, v in updated.items():
                if k in EMR_FIELDS and v and v != "[NOT STATED]":
                    # Filter out greetings from Problem_Description
                    if k == "Problem_Description":
                        v_lower = str(v).strip().lower()
                        if v_lower in ['hi', 'hello', 'hello there', '你好', 'hey']:
                            print(f"[DEBUG] Filtering greeting: {v}")
                            continue
                    merged[k] = v

            # Auto-fill dependent fields when parent is "No"
            if merged.get("Recent_Surgery") == "No":
                merged["Surgery_Details"] = "None"
            if merged.get("Eye_Pain") == "No":
                merged["Pain_Details"] = "None"
                merged["Pain_Progression"] = "None"
            if merged.get("Burn_Injury") == "No":
                merged["Injury_Details"] = "None"
            if merged.get("Vision_Changed") == "No":
                merged["Vision_Change_Type"] = "None"

            return merged
        except Exception as e:
            print(f"[DEBUG] Exception in update_emr: {e}")
            return current_emr

    def emr_complete(self, emr: dict) -> bool:
        return all(emr.get(f, "[NOT STATED]") != "[NOT STATED]" for f in CRITICAL_FIELDS)

    def emr_to_text(self, emr: dict) -> str:
        lines = ["=== Patient Telephone Screening Form ===", ""]
        for f in EMR_FIELDS:
            label = EMR_LABELS.get(f, f)
            value = emr.get(f, "[NOT STATED]")
            lines.append(f"{label}: {value}")
        complete = self.emr_complete(emr)
        lines.append("")
        lines.append(f"EMR Status: {'✅ COMPLETE' if complete else '⏳ INCOMPLETE'}")
        return "\n".join(lines)


# ── Assessor Agent ────────────────────────────────────────────────────────────

ASSESSOR_PROMPT = """# Role
You are the "Assessor Agent". You receive the current full JSON state of the "Patient Telephone Screening Form". Your job is to strictly evaluate the EMR against the AAO Symptom Guidelines.

# AAO Symptom Guidelines
### AAO Symptom Guidelines:

【Symptom guideline】
vision_loss_change
•	Emergent: symptom after eye injury or chemical burn within last few days
•	Emergent: Sudden, painless, severe loss of vision.
•	Emergent: Loss of vision after surgery or procedure within the last 6 weeks.
•	Emergent: Total darkness or part of vision missing for new onset
•	Urgent: Subacute loss of vision that has evolved gradually over a period of a few days to a week. Ask if vision loss is persistent (constant) or intermittent (off and on).
•	Emergent: Vision changes after surgery or procedure.
•	Emergent: Acute Eye Pain with Nausea and Foggy Vision.
•	Urgent: Sudden onset of diplopia (double vision) or other distorted vision. Double vision that has persisted for less than a week.
•	Urgent: Double vision with one eye closed or covered
•	Urgent：A decrease in vision accompanies photophobia that cannot be relieved by artificial tears.
•	Routine: Difficulty with near or distance work, fine or print.
###Pain:###
•	Emergent: symptom after eye injury or chemical burn within last few days
•	Emergent: Acute, rapid onset of eye pain or discomfort.
•	Emergent: Progressively worsening ocular pain.
•	Emergent: Worsening pain after surgery or procedure within the last 6 weeks.
•	Emergent: Acute Eye Pain with Nausea and Foggy Vision.
•	Emergent: Mild ocular pain if accompanied by redness in a contact lens wearer.
•	Urgent: Mild ocular pain if accompanied by redness
•	Urgent: Mild ocular pain if accompanied by a decrease in vision.
•	Urgent: Pain accompanied with bumps or lumps on the eyelid
•	Routine: Discomfort after prolonged use of the eyes.
•	Routine: Pain as only symptom that can be relieved by artificial tears.

###Flashes/Floaters:###
•	Emergent: symptom after eye injury or chemical burn within last few days
•	Emergent: Recent onset of light flashes and floaters in patient with myopia (nearsightedness) or with a history of LASIK or refractive surgery].
•	Emergent: Recent onset of light flashes and floaters in patient with After surgery or procedure within the last 6 weeks
•	Emergent: Recent onset of light flashes and floaters in patient with Accompanied by shadows in the peripheral vision.
•	Urgent: Recent onset of light flashes and floaters without situation of emergent category. Many ophthalmologists prefer to see these patients the same day. If in doubt, consult with the ophthalmologist.
•	Routine: Persistent and unchanged floaters whose cause has been previously determined.

###REDNESS/DISCHARGE:###
•	Emergent: symptom after eye injury or chemical burn within last few days
•	Emergent: Worsening redness or discharge after surgery or procedure within the last 6 weeks.
•	Emergent: Redness or discharge in a contact lens wearer.
•	Emergent: Acute Redness with Nausea and Foggy Vision.
•	Emergent: Acute red eye with progressively worsening pain
•	Emergent: Discharge with progressively worsening pain and vision loss
•	Urgent: Acute red eye with pain
•	Urgent: Acute red eye, with or without discharge.
•	Urgent: Discharge or tearing that causes the eyelids to stick together.
•	Urgent: Discharge accompanied by pain and vision loss
•	Routine: Mucous discharge from the eye that does not cause the eyelids to stick together. Mild redness of the eye not accompanied by other symptoms.

# Execution Logic
1. Check the `EMR_BASIC_STATUS` flag provided in the prompt.
2. IF `EMR_BASIC_STATUS` == "INCOMPLETE":
   - You must sleep to save compute.
   - Output ONLY: "[STATUS: SLEEP]"
3. IF `EMR_BASIC_STATUS` == "COMPLETE":
   - Map the EMR fields to the AAO categories.
   - Perform a deep evaluation to rule out EVERY Emergent criteria associated with EACH active symptom currently marked "Yes" in the EMR.
   - Output the "Triage Logic Report".

# Output Format (If Active)
**1. Highest Potential Triage Level**: [ROUTINE / URGENT / EMERGENT]
**2. Gap Analysis**: [Instruct the Inquirer what specific clinical symptom to ask about next to rule out emergent risks based on the AAO rules. E.g., "Patient has eye pain. Need to ask if there is nausea to rule out acute glaucoma."]
**3. Ready for Disposition**: [Yes / No]

CRITICAL: Only set "Ready for Disposition: Yes" when:
1. ALL EMR fields have been filled (no [NOT STATED] remaining)
2. All AAO guideline questions have been answered
3. Nurse has asked "Do you have any other symptoms?"
"""


class AssessorAgent:
    def evaluate(self, history: list, emr: dict, emr_text: str, emr_complete: bool) -> dict:
        if not emr_complete:
            return {
                "skipped": True,
                "raw": "[STATUS: SLEEP]",
                "triage_level": "INCOMPLETE",
                "gap_analysis": "",
                "disposition_ready": False,
            }

        # Check if ALL fields are filled (no [NOT STATED])
        all_filled = all(emr.get(f, "[NOT STATED]") != "[NOT STATED]" for f in EMR_FIELDS)

        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
        user_prompt = f"EMR_BASIC_STATUS: COMPLETE\nAll fields filled: {all_filled}\n\nComplete conversation history:\n{history_text}\n\nEMR Summary:\n{emr_text}"
        raw = _call(ASSESSOR_PROMPT, user_prompt, max_tokens=1000)

        triage_level = "INCOMPLETE"
        for line in raw.splitlines():
            if "Highest Potential Triage Level" in line:
                if "EMERGENT" in line:   triage_level = "EMERGENT"
                elif "URGENT" in line:   triage_level = "URGENT"
                elif "ROUTINE" in line:  triage_level = "ROUTINE"
                break

        gap = ""
        if "Gap Analysis" in raw:
            parts = raw.split("Gap Analysis", 1)
            if len(parts) > 1:
                gap_section = parts[1].split("**3.", 1)[0] if "**3." in parts[1] else parts[1]
                gap = gap_section.strip(" :\n*-[]")

        # Parse disposition_ready more carefully
        disposition_ready = False
        for line in raw.splitlines():
            if "Ready for Disposition" in line:
                if ": Yes" in line or "**Yes" in line:
                    disposition_ready = True
                elif ": No" in line or "**No" in line:
                    disposition_ready = False
                break

        return {
            "skipped": False,
            "raw": raw,
            "triage_level": triage_level,
            "gap_analysis": gap,
            "disposition_ready": disposition_ready,
        }


# ── Inquirer Agent ────────────────────────────────────────────────────────────

INQUIRER_AUTONOMOUS_PROMPT = """# Role
You are the "Inquirer Agent" (Triage Nurse). You interact directly with the patient. You operate dynamically based on the system state.

# System Input Modes (Provided by the system wrapper):
- [MODE: AUTONOMOUS]: The system will provide a "Missing Basic Field" (e.g., "Need to know which eye is affected").

# Conversational Rules (CRITICAL):
1. LANGUAGE: Always respond in the SAME language the patient is using. If patient speaks English, respond in English. If patient speaks Chinese, respond in Chinese.
2. PATIENT QUESTIONS FIRST: If the patient asks a question (contains "?" or "吗" or "什么"), you MUST answer it warmly and professionally BEFORE asking your next triage question. Never ignore patient questions.
3. FIRST INTERACTION: If this is the first real interaction (patient just greeted), ask "What symptoms are you experiencing today?" or "您有什么症状？" based on patient's language.
4. ONE QUESTION ONLY: Never ask more than one question per response.
5. EMPATHY: If patient expresses fear, comfort them first.
6. NEVER DIAGNOSE.
7. NATURAL FLOW: Integrate the required missing field into a natural, conversational question. Do not sound like a robot reading a checklist.

# Output
Output strictly what the nurse will say to the patient in the conversation.

Current missing critical fields: {missing_fields}"""

INQUIRER_CLINICAL_PROMPT = """# Role
You are the "Inquirer Agent" (Triage Nurse). You interact directly with the patient. You operate dynamically based on the system state.

# System Input Modes (Provided by the system wrapper):
- [MODE: CLINICAL DRILL-DOWN]: The system will provide a "Gap Analysis" from the Assessor based on AAO Guidelines.

# Conversational Rules (CRITICAL):
1. LANGUAGE: Always respond in the SAME language the patient is using. If patient speaks English, respond in English. If patient speaks Chinese, respond in Chinese.
2. PATIENT QUESTIONS FIRST: If the patient asks a question (contains "?" or "吗" or "什么"), you MUST answer it warmly and professionally BEFORE asking your next triage question. Never ignore patient questions.
3. ONE QUESTION ONLY: Never ask more than one question per response.
4. EMPATHY: If patient expresses fear, comfort them first.
5. NEVER DIAGNOSE.
6. NATURAL FLOW: Integrate the gap analysis into a natural, conversational question. Do not sound like a robot reading a checklist.

# Output
Output strictly what the nurse will say to the patient in the conversation.

Gap Analysis (questions to ask): {gap_analysis}"""


class InquirerAgent:
    def generate_response(self, history: list, new_message: str,
                          emr: dict, emr_text: str,
                          emr_complete: bool, gap_analysis: str,
                          disposition_ready: bool, triage_level: str) -> str:
        history_text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)

        # Detect if patient is asking a question
        is_question = any(marker in new_message for marker in ['?', '吗', '什么', '为什么', '怎么', '多久'])

        # If disposition ready, give final triage conclusion
        if disposition_ready and triage_level and triage_level != "INCOMPLETE":
            conclusions = {
                "EMERGENT": "Based on what you've described, you need to be seen immediately. Please go to the nearest emergency room or come to our clinic right now.",
                "URGENT": "Based on your symptoms, you need to be evaluated soon. I am scheduling you to come into the clinic within the next 24 hours.",
                "ROUTINE": "Your symptoms do not require immediate attention, but we should still have the doctor take a look. Let's get you scheduled for a standard appointment."
            }
            return conclusions.get(triage_level, "Please contact the clinic for further evaluation.")

        if not emr_complete:
            missing = [EMR_LABELS.get(f, f) for f in CRITICAL_FIELDS
                       if emr.get(f, "[NOT STATED]") == "[NOT STATED]"]
            system = INQUIRER_AUTONOMOUS_PROMPT.format(missing_fields=", ".join(missing))
        else:
            system = INQUIRER_CLINICAL_PROMPT.format(gap_analysis=gap_analysis or "Ask about symptom details.")

        user_prompt = (
            f"Conversation so far:\n{history_text}\n\n"
            f"Patient just said: {new_message}\n\n"
        )

        if is_question:
            user_prompt += "⚠️ IMPORTANT: The patient is asking a question. Answer it warmly first, then ask your triage question.\n\n"

        user_prompt += (
            f"Current EMR summary:\n{emr_text}\n\n"
            "Generate your nurse response (ONE question only)."
        )
        return _call(system, user_prompt, max_tokens=400)
