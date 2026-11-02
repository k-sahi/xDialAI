import os
from fastapi import FastAPI, HTTPException
from app.schemas import ConversationRequest, NextQuestionResponse
from app.services import client, generate_next_question_llm, generate_next_question_simulated

app = FastAPI(
    title="xDial Benefits Verification Engine",
    description="Analyzes B2B insurance calls and returns the next question.",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "llm" if (client and os.getenv("OPENAI_API_KEY")) else "simulated"}

@app.post("/next-question", response_model=NextQuestionResponse)
async def get_next_question(request: ConversationRequest):
    if not request.conversation:
        raise HTTPException(status_code=400, detail="Conversation transcript cannot be empty.")

    try:
        if client and os.getenv("OPENAI_API_KEY"):
            return await generate_next_question_llm(request)
        else:
            return generate_next_question_simulated(request)
    except Exception as e:
        print(f"LLM Error, triggering rule-based fallback: {e}")
        return generate_next_question_simulated(request)