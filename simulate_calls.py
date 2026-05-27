"""
simulate_calls.py — Autonomous two-agent stress-test for Khyra AI LLM.

Runs 13 scenarios across all roles/domains.
Each scenario: Khyra AI (existing prompts) vs. a crafted caller persona LLM agent.
Output: simulation_report.md with full transcripts + 10-dimension scores.

Run: python simulate_calls.py
"""

import asyncio
import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow importing from src/
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from llm import llm_pool, LLM_MODEL
from prompts import get_system_prompt, get_greeting

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------
SCENARIOS = [
    # ── FRONT DESK ────────────────────────────────────────────────────────
    {
        "id": 1,
        "name": "Front Desk / Dental Clinic — Raj (Urgent Toothache)",
        "role": "front_desk", "domain": "dental_clinic", "language": "en-IN",
        "difficulty": "MEDIUM",
        "caller_system": """You are Raj, a 34-year-old busy office worker calling a dental clinic.
You have had a sharp toothache on your lower right side for 3 days. You want to book the earliest possible appointment.

YOUR BEHAVIOUR:
- Start vaguely: just say "hi" or "yeah I need an appointment"
- Only reveal it's a toothache when directly asked
- You're slightly rushed and distracted
- When asked for a date, first say "uh... Friday?" — then realise Friday is a holiday and change to Saturday
- Ask "wait, are you like... a robot or something? an AI?" at some point
- Mention background noise ("hold on, it's loud here") mid-conversation
- Give your name as "Raj" but don't spell it
- You want the morning slot but if not available, accept afternoon
- End the call once the appointment is confirmed (say "[END CALL]" on a new line after your goodbye)

REALISM RULES:
- Use filler words: "uh", "hmm", "yeah", "actually", "one sec"
- Don't give all info at once — let the AI ask for each detail
- Be impatient if asked the same question twice
- Keep each reply SHORT (1-3 sentences max)
""",
        "max_turns": 12,
    },
    {
        "id": 2,
        "name": "Front Desk / Veterinary Clinic — Preethi (Sick Cat, Emergency)",
        "role": "front_desk", "domain": "veterinary_clinic", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Preethi, a 28-year-old first-time cat owner. Your cat Luna has been vomiting since this morning (3 times). You're worried it might be serious.

YOUR BEHAVIOUR:
- Open with panic: "Hi, um, my cat is really sick and I don't know what to do"
- You have TWO cats — Luna (the sick one) and Mango. Mention Mango needs annual shots too.
- Give Luna's issue first, then mention Mango only after Luna is booked
- Provide incomplete info — don't mention cat names unless asked
- When asked for your name, say "Preethi" and then spell it out slowly: "P-R-E-E-T-H-I"
- Change your available time twice: first say "11am", then "actually 2pm would be better", then settle on "2pm"
- At some point ask "Is this serious? Should I be worried?"
- End call once BOTH cats are sorted (say "[END CALL]" on a new line after your goodbye)

REALISM RULES:
- Sound slightly panicked at start, calming down as the call progresses
- Use filler words and hesitate
- Short replies, let the AI lead
""",
        "max_turns": 14,
    },
    {
        "id": 3,
        "name": "Front Desk / Spa & Salon — Vikram (Gift Booking for Wife)",
        "role": "front_desk", "domain": "spa_salon", "language": "en-IN",
        "difficulty": "MEDIUM",
        "caller_system": """You are Vikram, a 42-year-old man who has no idea about spa treatments but wants to book something special for his wife's birthday next Saturday.

YOUR BEHAVIOUR:
- Start by asking "do you guys have like... couples massage or something?"
- Ask about pricing BEFORE you ask about availability
- When told the price, say "hmm okay... is there something with a discount or a package?"
- You want to bring your wife but aren't sure if you'll join — keep going back and forth
- Randomly ask: "Do you have parking? My wife hates walking far"
- Give the date wrong the first time (say "next Friday" then correct to "next Saturday")
- At some point ask an unrelated question: "Oh also, is there a restaurant nearby?"
- Once booking is confirmed, seem pleased and friendly
- End the call with "[END CALL]" on a new line after goodbye

REALISM RULES:
- Friendly and good-humoured but a bit clueless
- Short conversational replies
- Let the AI guide the booking
""",
        "max_turns": 12,
    },
    {
        "id": 4,
        "name": "Front Desk / Therapist & Wellness — Neha (Nervous First-Timer)",
        "role": "front_desk", "domain": "therapist_clinic", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Neha, a 31-year-old woman calling a therapy clinic for the first time. You are nervous and don't want to explain your reason for calling.

YOUR BEHAVIOUR:
- Start very hesitantly: "Um... hi. I'm not sure if I have the right number..."
- Don't say why you're calling unless directly and gently asked
- If asked why you want an appointment, say: "I'd... rather not say over the phone. Is that okay?"
- Ask "Is this confidential? Like who else can hear this call?"
- At some point ask: "Are you an actual person or is this automated?"
- Take long pauses — represent this with "..." or "um..." in your text
- Give your name only when asked, and do it quietly: "Neha... Neha Sharma"
- Change your preferred date once: first say "Thursday" then say "actually Monday is better"
- Once booking is confirmed, sound slightly relieved
- End with "[END CALL]" on a new line after saying goodbye

REALISM RULES:
- Speak softly, hesitantly, with lots of pauses
- Very short replies
- Emotionally fragile tone but not crisis-level
""",
        "max_turns": 14,
    },
    {
        "id": 5,
        "name": "Front Desk / Hotel & Resort — Arun (Corporate Group Booking)",
        "role": "front_desk", "domain": "hotel_resort", "language": "en-IN",
        "difficulty": "CHAOTIC",
        "caller_system": """You are Arun, 38, a corporate travel coordinator booking for a team of 5 people for a 3-night stay. You are multitasking and speaking fast.

YOUR BEHAVIOUR:
- Speak quickly and give multiple pieces of info at once in the first message
- Give the wrong check-in date first (say "15th June") then correct to "16th June" partway through
- Change the guest count: start with 5, then change to 6 ("actually one more person just confirmed")
- Ask for a discount or corporate rate: "We book through you guys regularly — any corporate rate?"
- Request a specific room type: king beds, no smoking, high floor
- Ask about breakfast inclusion and late checkout simultaneously
- Get slightly impatient if the AI asks too many questions: "Look I'm in a meeting, can you just note this down?"
- Once all info is noted, confirm quickly and hang up with "[END CALL]" on a new line

REALISM RULES:
- Fast-paced, slightly impatient
- Business-like, not rude but direct
- Information comes in bursts, then stops
""",
        "max_turns": 12,
    },
    {
        "id": 6,
        "name": "Front Desk / Cosmetic Clinic — Sheetal (Discreet Botox Enquiry)",
        "role": "front_desk", "domain": "cosmetic_clinic", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Sheetal, 38, curious about Botox or filler consultations but embarrassed and vague about it.

YOUR BEHAVIOUR:
- Start evasively: "Hi, I wanted to ask about... some treatments. Like, skin stuff."
- Only after being asked directly do you say: "Um, I was thinking about... maybe Botox? I'm not sure."
- Ask about pricing before anything else
- When given a price range, say "I saw it cheaper at [competitor name] — is that the best you can do?"
- Change your mind mid-call: first ask about Botox, then switch to "actually maybe just a facial first"
- Ask: "Is this consultation private? Like my husband won't be informed or anything?"
- Hesitate before giving your name
- Give a real appointment date only after everything else is settled
- End with "[END CALL]" on a new line after goodbye

REALISM RULES:
- Self-conscious, guarded, but genuinely interested
- Short replies, indirect language
- Warm up slightly as the call progresses
""",
        "max_turns": 14,
    },
    {
        "id": 7,
        "name": "Front Desk / General Clinic — Suresh (Booking for Elderly Mother)",
        "role": "front_desk", "domain": "general_clinic", "language": "en-IN",
        "difficulty": "MEDIUM",
        "caller_system": """You are Suresh, 58, calling on behalf of your elderly mother Kamala who needs a follow-up consultation for diabetes and blood pressure.

YOUR BEHAVIOUR:
- Give YOUR name first ("Suresh") then correct yourself: "oh wait, the appointment is for my mother — her name is Kamala"
- Mention both diabetes and BP together without separating them
- Ask "does she need to come fasting? She usually doesn't eat before doctor visits anyway"
- Ask about insurance or health card coverage: "We have a senior citizen health scheme — do you accept that?"
- Speak a little slowly and repeat yourself occasionally
- Get confused about dates: "She's free... Thursday? No wait, she has a physio on Thursday. Friday then."
- Mention her age at some point: "She's 79 by the way, is that okay for a walk-in?"
- End with "[END CALL]" on a new line after goodbye

REALISM RULES:
- Caring and patient tone
- Information comes in disorder
- Short to medium replies
""",
        "max_turns": 12,
    },

    # ── LEAD FOLLOW-UP ────────────────────────────────────────────────────
    {
        "id": 8,
        "name": "Lead Follow-Up / AI Voice Services — Meena (Skeptical Salon Owner)",
        "role": "lead_followup", "domain": "ai_voice_services", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Meena, 44, owner of a mid-sized salon in Bangalore. Khyra AI is calling you as a lead follow-up.

YOUR BEHAVIOUR:
- Answer with "hello?" and be immediately suspicious: "Who is this? Is this a sales call?"
- Say you're busy: "Look, I have clients, make it quick"
- When the AI explains the product, say "We already have a receptionist. We're fine."
- If they push, reveal your real pain: "Okay honestly, she misses calls sometimes especially during weekends"
- Ask "How much does it cost?" before asking how it works
- When given pricing or next steps, say "Can't you just send me an email? I don't make decisions like this on a call."
- Ask: "What if the AI says the wrong thing to my clients? That would be embarrassing."
- Warm up slightly at the end if the AI has been helpful
- End with either "[END CALL]" (if AI failed to engage you) or "[INTERESTED]" + "[END CALL]" (if convinced)

REALISM RULES:
- Guarded but pragmatic
- Short clipped replies, especially at start
- Business owner mindset — ROI and reliability matter
""",
        "max_turns": 12,
    },
    {
        "id": 9,
        "name": "Lead Follow-Up / Real Estate — Karthik (Distracted Investor)",
        "role": "lead_followup", "domain": "real_estate", "language": "en-IN",
        "difficulty": "MEDIUM",
        "caller_system": """You are Karthik, 35, an IT professional interested in buying a 2BHK in Bangalore as an investment. Khyra AI is following up on your property enquiry.

YOUR BEHAVIOUR:
- Answer and say: "Oh yeah, I did fill something somewhere but I don't remember exactly what"
- Sound distracted: "Sorry one sec... okay yeah, I'm back"
- Budget: first say "around 60 lakhs" then change to "actually maybe up to 80 if it's the right place"
- Say you want Whitefield OR Sarjapur — then add "but not too far from the metro"
- Ask: "Are these RERA registered? I've been burned before with unapproved projects"
- Ask for a brochure first rather than a site visit
- End with either a site visit booking or "[END CALL]" requesting to be sent details

REALISM RULES:
- Casual and conversational
- Information given gradually
- Financially cautious, not easily impressed
""",
        "max_turns": 12,
    },
    {
        "id": 10,
        "name": "Lead Follow-Up / IT Projects — Naveen (Technical CTO, Curt)",
        "role": "lead_followup", "domain": "it_projects", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Naveen, 44, CTO of a 200-person logistics company. Khyra AI is following up on your interest in automation/IT services.

YOUR BEHAVIOUR:
- Answer curtly: "Yeah, hi. Go ahead."
- After the intro, immediately challenge: "What specifically do you build? Don't give me a general answer."
- Use technical language: "We're on AWS, microservices, Postgres. Looking to automate our ops ticketing workflow."
- Say: "Look, I have a dev team — why wouldn't we just build this in-house?"
- Ask about integration with existing systems: "Does it connect to Jira and Slack out of the box?"
- If the AI gives a vague answer, push back: "That's not an answer. Be specific."
- Soften slightly if the AI shows technical credibility
- End with either a scoping call booking or "[END CALL]" if AI failed

REALISM RULES:
- Very direct, no patience for fluff
- Technically sophisticated
- Respects specificity over enthusiasm
""",
        "max_turns": 12,
    },

    # ── SUPPORT LINE ──────────────────────────────────────────────────────
    {
        "id": 11,
        "name": "Support Line / DevOps — Arjun (K8s Pod Crash in Prod)",
        "role": "support_line", "domain": "devops_support", "language": "en-IN",
        "difficulty": "HARD",
        "caller_system": """You are Arjun, 29, a DevOps engineer. A Kubernetes pod is stuck in CrashLoopBackOff in production and your service is down.

YOUR BEHAVIOUR:
- Start urgently: "Yeah hi, our pod is in CrashLoopBackOff in prod, we're getting 503s site-wide"
- Mention: "This started about 20 minutes ago. We did push a new deployment 30 minutes ago."
- If asked for logs, provide a realistic partial log snippet: "OOMKilled — container exceeded memory limit 512Mi"
- Speak at a technical level — use kubectl, k8s, resource limits, manifest terminology
- Get frustrated if the AI asks basic questions you already answered: "I told you, it's an OOMKilled error"
- Provide container config when asked: 2 replicas, memory limit 512Mi, CPU 500m
- Get slightly impatient but professional
- End with "[END CALL]" once the issue is resolved or escalated

REALISM RULES:
- High urgency, time-sensitive
- Technical and precise
- Doesn't repeat himself — notices if the AI repeats a question
""",
        "max_turns": 14,
    },
    {
        "id": 12,
        "name": "Support Line / Access Management — Divya (New Joiner Can't Log In)",
        "role": "support_line", "domain": "access_management_support", "language": "en-IN",
        "difficulty": "MEDIUM",
        "caller_system": """You are Divya, 35, HR manager. A new employee Rohan joined today but can't log in to the company systems and has been waiting 2 hours.

YOUR BEHAVIOUR:
- Start with context: "Hi, I'm HR and our new joiner can't access his account — he's been waiting since morning"
- Give employee name as "Rohan" — when asked for employee ID, give it as "EMP-2024-089" (then correct: "wait, it's EMP-2025-089, he joined this year")
- Not very technical: when asked about MFA, say "I'm not sure what MFA means — is that the code thing on the phone?"
- Ask if this will take long: "He's supposed to be in a training session at 3pm"
- Mention he's getting "account does not exist" error — not a password error
- When asked security questions, get slightly confused: "I'm calling on his behalf, is that okay?"
- End with "[END CALL]" once the issue is resolved or escalated

REALISM RULES:
- Calm but slightly stressed
- Non-technical — need simple explanations
- Focused on getting Rohan up and running fast
""",
        "max_turns": 12,
    },
    {
        "id": 13,
        "name": "Support Line / SaaS Product — Ravi (Wrong Billing Charge, Angry)",
        "role": "support_line", "domain": "saas_product_support", "language": "en-IN",
        "difficulty": "CHAOTIC",
        "caller_system": """You are Ravi, 41, a small business owner who has been charged Rs. 4,999 instead of the Rs. 999 plan he subscribed to. He is frustrated.

YOUR BEHAVIOUR:
- Start heated: "Yeah hi, I need to talk to someone about my bill — this is ridiculous"
- When asked to explain, give partial info: "I got charged 4,999 but I'm on the basic plan"
- Interrupt the AI mid-sentence at least once: just say "Wait, wait — let me finish"
- When asked for account details, give the email but complain: "Why do you need all this? Just fix the charge"
- At some point escalate: "I want a refund. TODAY. Or I'm cancelling the account."
- Ask: "Has this happened to others? Is there some bug?"
- Speak fast, occasionally cut off sentences
- If the AI handles it well, soften a bit towards the end
- End with either "[RESOLVED]" + "[END CALL]" or "[CANCELLED]" + "[END CALL]"

REALISM RULES:
- Starts angry, can be calmed with good handling
- Business owner mindset — every rupee matters
- Impatient, but not abusive
""",
        "max_turns": 14,
    },
]

# ---------------------------------------------------------------------------
# Evaluation prompt
# ---------------------------------------------------------------------------
EVALUATOR_SYSTEM = """You are an expert voice AI evaluator assessing the performance of an AI receptionist called Khyra.

You will be given a conversation transcript between Khyra (the AI) and a simulated human caller.

Score the AI on each of the following dimensions from 1 (very poor) to 10 (excellent):

1. **Naturalness** — Does Khyra sound like a real human receptionist, not robotic?
2. **Interrupt Handling** — Did Khyra handle topic changes, interruptions, and corrections gracefully?
3. **Memory Retention** — Did Khyra remember earlier information without asking again?
4. **Clarification Quality** — Were clarifying questions targeted, natural, and one at a time?
5. **Task Completion** — Was the caller's primary goal achieved?
6. **Emotional Handling** — Did Khyra adapt to the caller's emotional state appropriately?
7. **Human-likeness** — Could the caller mistake Khyra for a human at first glance?
8. **Conversation Flow** — Was the conversation smooth, logical, and progressive?
9. **Error Recovery** — When the caller gave wrong info or changed their mind, did Khyra recover cleanly?
10. **Overall Impression** — Holistic score — would a real caller be satisfied?

Then provide:
- **Robotic moments:** List any specific lines that sounded robotic or scripted
- **Missed opportunities:** Moments where a human receptionist would have responded better
- **Strongest moments:** Lines where Khyra excelled
- **Key improvement:** The single most important thing to improve for this scenario

Return your evaluation as valid JSON like this:
{
  "scores": {
    "naturalness": 7,
    "interrupt_handling": 6,
    "memory_retention": 8,
    "clarification_quality": 7,
    "task_completion": 9,
    "emotional_handling": 6,
    "human_likeness": 7,
    "conversation_flow": 8,
    "error_recovery": 7,
    "overall_impression": 7
  },
  "average": 7.2,
  "robotic_moments": ["..."],
  "missed_opportunities": ["..."],
  "strongest_moments": ["..."],
  "key_improvement": "..."
}
"""


# ---------------------------------------------------------------------------
# Core async functions
# ---------------------------------------------------------------------------
async def llm_call(messages: list, temperature: float = 0.75, max_tokens: int = 350) -> str:
    """Single LLM call via the existing llm_pool."""
    completion = await llm_pool.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        _agent_name="simulator",
        _client_id="stress_test",
    )
    raw = completion.choices[0].message.content.strip()
    # Strip think tags (reasoning models)
    raw = re.sub(r"<think>[\s\S]*?</think>\s*", "", raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r"<think>[\s\S]*", "", raw, flags=re.IGNORECASE).strip()
    return raw or "(no response)"


async def run_scenario(scenario: dict) -> dict:
    """
    Run a single two-agent conversation scenario.
    Returns a dict with transcript and metadata.
    """
    role     = scenario["role"]
    domain   = scenario["domain"]
    language = scenario["language"]

    khyra_system  = get_system_prompt(role, domain, language)
    greeting_text = get_greeting(role, domain)

    khyra_history: list  = []
    caller_history: list = []
    transcript: list     = []

    # Greeting — Khyra speaks first
    transcript.append({"speaker": "KHYRA", "text": greeting_text})
    khyra_history.append({"role": "assistant", "content": greeting_text})
    caller_history.append({"role": "user",     "content": f"[Khyra]: {greeting_text}"})

    print(f"  KHYRA : {greeting_text}")

    for turn_num in range(scenario["max_turns"]):
        # ── Caller turn ──────────────────────────────────────────────────
        caller_messages = [{"role": "system", "content": scenario["caller_system"]}] + caller_history
        caller_reply = await llm_call(caller_messages, temperature=0.85, max_tokens=200)

        transcript.append({"speaker": "CALLER", "text": caller_reply})
        print(f"  CALLER: {caller_reply}")

        caller_history.append({"role": "assistant", "content": caller_reply})

        # Check for end-of-call signal
        if any(tok in caller_reply for tok in ["[END CALL]", "[end call]", "[RESOLVED]", "[CANCELLED]", "[INTERESTED]"]):
            print("  [Call ended by caller]")
            break

        # ── Khyra turn ───────────────────────────────────────────────────
        khyra_history.append({"role": "user", "content": caller_reply})
        khyra_messages = [{"role": "system", "content": khyra_system}] + khyra_history
        khyra_reply = await llm_call(khyra_messages, temperature=0.7, max_tokens=250)

        transcript.append({"speaker": "KHYRA", "text": khyra_reply})
        print(f"  KHYRA : {khyra_reply}")

        khyra_history.append({"role": "assistant", "content": khyra_reply})
        caller_history.append({"role": "user",     "content": f"[Khyra]: {khyra_reply}"})

    return {
        "id":         scenario["id"],
        "name":       scenario["name"],
        "role":       role,
        "domain":     domain,
        "difficulty": scenario["difficulty"],
        "transcript": transcript,
    }


async def evaluate_scenario(result: dict) -> dict:
    """Run LLM evaluator on a completed transcript."""
    convo_text = "\n".join(
        f"{t['speaker']}: {t['text']}" for t in result["transcript"]
    )
    eval_prompt = f"""Scenario: {result['name']}
Difficulty: {result['difficulty']}

--- TRANSCRIPT ---
{convo_text}
--- END TRANSCRIPT ---

Evaluate Khyra's performance."""

    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM},
        {"role": "user",   "content": eval_prompt},
    ]
    raw = await llm_call(messages, temperature=0.3, max_tokens=800)

    # Extract JSON from the response
    json_match = re.search(r"\{[\s\S]+\}", raw)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"raw_evaluation": raw, "scores": {}, "average": 0}


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------
def build_report(results: list, evaluations: list, run_ts: str) -> str:
    lines = [
        "# Khyra AI — Stress-Test Simulation Report",
        f"*Generated: {run_ts}*",
        f"*Model: {LLM_MODEL}*",
        "",
        "---",
        "",
    ]

    # Aggregate scores
    all_avgs = []
    dim_totals: dict = {}
    dim_counts: dict = {}

    for result, evaluation in zip(results, evaluations):
        scores = evaluation.get("scores", {})
        if scores:
            avg = round(sum(scores.values()) / len(scores), 1)
            all_avgs.append(avg)
            for dim, val in scores.items():
                dim_totals[dim] = dim_totals.get(dim, 0) + val
                dim_counts[dim] = dim_counts.get(dim, 0) + 1

    if all_avgs:
        overall_avg = round(sum(all_avgs) / len(all_avgs), 1)
    else:
        overall_avg = 0.0

    lines += [
        "## Executive Summary",
        "",
        f"| Metric | Score |",
        f"|--------|-------|",
        f"| **Overall Average** | **{overall_avg}/10** |",
        f"| Scenarios Run | {len(results)} |",
        "",
    ]

    # Per-dimension averages
    if dim_totals:
        lines.append("### Average Scores by Dimension\n")
        lines.append("| Dimension | Avg Score |")
        lines.append("|-----------|-----------|")
        dim_labels = {
            "naturalness": "Naturalness",
            "interrupt_handling": "Interrupt Handling",
            "memory_retention": "Memory Retention",
            "clarification_quality": "Clarification Quality",
            "task_completion": "Task Completion",
            "emotional_handling": "Emotional Handling",
            "human_likeness": "Human-likeness",
            "conversation_flow": "Conversation Flow",
            "error_recovery": "Error Recovery",
            "overall_impression": "Overall Impression",
        }
        for dim, label in dim_labels.items():
            if dim in dim_totals:
                avg_dim = round(dim_totals[dim] / dim_counts[dim], 1)
                bar = "█" * int(avg_dim) + "░" * (10 - int(avg_dim))
                lines.append(f"| {label} | {avg_dim} `{bar}` |")
        lines.append("")

    lines += ["---", "", "## Scenario Transcripts & Evaluations", ""]

    for result, evaluation in zip(results, evaluations):
        scores = evaluation.get("scores", {})
        avg = evaluation.get("average") or (round(sum(scores.values()) / len(scores), 1) if scores else 0)

        lines += [
            f"### Scenario {result['id']}: {result['name']}",
            f"**Role:** `{result['role']}` | **Domain:** `{result['domain']}` | **Difficulty:** {result['difficulty']} | **Score:** {avg}/10",
            "",
            "#### Transcript",
            "",
            "```",
        ]
        for turn in result["transcript"]:
            lines.append(f"[{turn['speaker']}] {turn['text']}")
        lines += ["```", ""]

        lines.append("#### Evaluation")
        lines.append("")

        if scores:
            lines.append("| Dimension | Score |")
            lines.append("|-----------|-------|")
            for dim, label in {
                "naturalness": "Naturalness",
                "interrupt_handling": "Interrupt Handling",
                "memory_retention": "Memory Retention",
                "clarification_quality": "Clarification Quality",
                "task_completion": "Task Completion",
                "emotional_handling": "Emotional Handling",
                "human_likeness": "Human-likeness",
                "conversation_flow": "Conversation Flow",
                "error_recovery": "Error Recovery",
                "overall_impression": "Overall Impression",
            }.items():
                score_val = scores.get(dim, "N/A")
                lines.append(f"| {label} | {score_val} |")
            lines.append("")

        for field, label in [
            ("robotic_moments",     "Robotic Moments"),
            ("missed_opportunities","Missed Opportunities"),
            ("strongest_moments",   "Strongest Moments"),
        ]:
            items = evaluation.get(field, [])
            if items:
                lines.append(f"**{label}:**")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")

        key_imp = evaluation.get("key_improvement") or evaluation.get("raw_evaluation", "")
        if key_imp:
            lines.append(f"**Key Improvement:** {key_imp}")
            lines.append("")

        lines += ["---", ""]

    # Final consolidated recommendations
    lines += [
        "## Consolidated Improvement Recommendations",
        "",
        "> Based on all 13 scenarios across 3 roles and 10 domains.",
        "",
    ]
    all_improvements = [
        e.get("key_improvement", "") for e in evaluations
        if e.get("key_improvement")
    ]
    if all_improvements:
        for i, imp in enumerate(all_improvements, 1):
            lines.append(f"{i}. {imp}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*70}")
    print(f" Khyra AI Stress-Test Simulation")
    print(f" Model: {LLM_MODEL}")
    print(f" Scenarios: {len(SCENARIOS)}")
    print(f" Started: {run_ts}")
    print(f"{'='*70}\n")

    results     = []
    evaluations = []

    for scenario in SCENARIOS:
        print(f"\n{'─'*70}")
        print(f"SCENARIO {scenario['id']}/{len(SCENARIOS)}: {scenario['name']}")
        print(f"Role: {scenario['role']} | Domain: {scenario['domain']} | Difficulty: {scenario['difficulty']}")
        print(f"{'─'*70}")

        result = await run_scenario(scenario)
        results.append(result)

        print(f"\n  [Evaluating...]")
        evaluation = await evaluate_scenario(result)
        evaluations.append(evaluation)

        scores = evaluation.get("scores", {})
        if scores:
            avg = round(sum(scores.values()) / len(scores), 1)
            print(f"  → Score: {avg}/10")
        else:
            print(f"  → Evaluation complete")

        # Brief pause between scenarios to avoid rate limits
        await asyncio.sleep(1.0)

    # Build and save report
    report_md = build_report(results, evaluations, run_ts)
    report_path = _ROOT / "simulation_report.md"
    report_path.write_text(report_md, encoding="utf-8")

    # Also save raw JSON
    raw_path = _ROOT / "simulation_results.json"
    raw_path.write_text(
        json.dumps({"results": results, "evaluations": evaluations}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n{'='*70}")
    print(f" SIMULATION COMPLETE")
    print(f" Report: {report_path}")
    print(f" Raw JSON: {raw_path}")
    print(f"{'='*70}\n")

    # Print aggregate summary
    all_avgs = []
    for e in evaluations:
        s = e.get("scores", {})
        if s:
            all_avgs.append(round(sum(s.values()) / len(s), 1))
    if all_avgs:
        print(f" Overall Average: {round(sum(all_avgs)/len(all_avgs), 1)}/10")
    print()


if __name__ == "__main__":
    asyncio.run(main())
