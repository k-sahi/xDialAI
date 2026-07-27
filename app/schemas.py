from pydantic import BaseModel, Field
from typing import List

class Message(BaseModel):
    speaker: str = Field(..., description="Either 'agent' or 'insurance'")
    text: str = Field(..., description="Spoken transcript line")

class ConversationRequest(BaseModel):
    conversation: List[Message]

class StructuredLLMResponse(BaseModel):
    """Pydantic schema for structured output from LLM"""
    next_question: str = Field(..., description="The next logical verification question to ask the insurance representative")

class NextQuestionResponse(BaseModel):
    next_question: str