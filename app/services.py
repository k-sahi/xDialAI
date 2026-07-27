import os
from typing import List
from app.schemas import Message, ConversationRequest, NextQuestionResponse, StructuredLLMResponse

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
except ImportError:
    client = None

SYSTEM_PROMPT = """You are an AI assistant for a healthcare voice agent calling insurance companies to verify patient benefits.
Analyze the transcript between the agent and the insurance representative.
Determine what information has already been asked and answered (e.g., deductible status, remaining deductible, copay, out-of-pocket max, effective dates).
Generate the single next logical question the agent should ask to complete benefit verification. Keep it concise, natural, and professional.
"""

def generate_next_question_llm(request: ConversationRequest) -> NextQuestionResponse:
    """Extract next question using OpenAI Structured Outputs."""
    formatted = "\n".join([f"{m.speaker.upper()}: {m.text}" for m in request.conversation])

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{formatted}"},
        ],
        response_format=StructuredLLMResponse,
    )

    data: StructuredLLMResponse = completion.choices[0].message.parsed
    return NextQuestionResponse(next_question=data.next_question)

def generate_next_question_simulated(request: ConversationRequest) -> NextQuestionResponse:
    """Rule-based simulation fallback for insurance benefit verification."""
    full_text = " ".join([m.text.lower() for m in request.conversation])

    # Basic insurance verification state machine
    if "out-of-pocket" not in full_text and "oop" not in full_text:
        next_q = "What is the remaining out-of-pocket maximum for this plan?"
    elif "copay" not in full_text:
        next_q = "Is there a copay required for an office visit?"
    elif "effective date" not in full_text and "active" not in full_text:
        next_q = "Could you confirm the effective start date of the policy?"
    elif "prior authorization" not in full_text and "auth" not in full_text:
        next_q = "Is prior authorization required for specialist visits?"
    else:
        next_q = "Thank you, that covers all the benefit information I needed today."

    return NextQuestionResponse(next_question=next_q)