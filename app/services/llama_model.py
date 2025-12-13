"""Wrapper around Ollama for deterministic prompts."""
from typing import Dict
import requests

from app.config import get_settings


class LLaMAModel:
    """Interact with an Ollama model using a consistent prompt template."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def build_prompt(self, knowledge_level: str, topic: str, user_message: str) -> str:
        """Create a structured prompt to maintain reliable tutoring responses."""

        return (
            "You are a patient finance tutor. "
            "Always stay concise, practical, and encouraging. "
            "Ask clarifying questions only when needed. "
            f"Learner level: {knowledge_level}. "
            "Topics allowed: investing basics; budgeting; UK taxes (PAYE, NI, ISA tax rules); "
            "retirement accounts (ISA, SIPP, pensions); risk management; debt management; "
            "business finance (profit, cashflow, forecasting, simple accounting). "
            "For every reply follow this exact format:\n"
            "1) Simplified explanation to the user's prompt.\n"
            "2) A realistic, safe step-by-step exercise the learner can do now.\n"
            "3) Add: 'This is educational only — not professional financial advice.'\n"
            f"User topic or question: {topic}.\n"
            f"User message: {user_message}"
        )

    def generate(self, knowledge_level: str, topic: str, user_message: str) -> Dict[str, str]:
        """Call Ollama to generate a tutor response."""

        prompt = self.build_prompt(knowledge_level, topic, user_message)
        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": False}
        response = requests.post(f"{self.settings.ollama_base_url}/api/generate", json=payload, timeout=60)
        response.raise_for_status()
        content = response.json().get("response", "")
        return {"response": content}


llama_model = LLaMAModel()
