import logging
from typing import Dict, Any, Tuple
from groq import Groq
import google.generativeai as genai
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Initialize clients
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_answer(self, prompt: str, context: str) -> Tuple[str, str]:
        """
        Attempts to generate an answer with fallback logic.
        Priority: 1. Groq -> 2. Gemini -> 3. OpenAI
        Returns a tuple: (answer_text, provider_name)
        """
        full_prompt = f"""Based on the following context, please answer the question accurately and concisely.

Context:
{context}

Question: {prompt}

Please provide a comprehensive answer based only on the provided context. If the context doesn't contain enough information to answer the question, please state that clearly."""

        # 1. Try Groq (Primary)
        try:
            logger.info("Attempting to use Groq API...")
            completion = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant answering questions based on context."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            answer = completion.choices[0].message.content
            if answer and answer.strip():
                logger.info("Successfully generated answer using Groq.")
                return answer.strip(), "Groq (llama-3.3-70b)"
        except Exception as e:
            logger.warning(f"Groq API failed: {e}")

        # 2. Try Gemini (Secondary)
        try:
            logger.info("Attempting to use Gemini API...")
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(full_prompt)
            if response and response.text:
                logger.info("Successfully generated answer using Gemini.")
                return response.text.strip(), "Google Gemini"
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}")

        # 3. Try OpenAI (Fallback)
        try:
            logger.info("Attempting to use OpenAI API...")
            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant answering questions based on context."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            answer = completion.choices[0].message.content
            if answer and answer.strip():
                logger.info("Successfully generated answer using OpenAI.")
                return answer.strip(), "OpenAI (gpt-3.5-turbo)"
        except Exception as e:
            logger.error(f"OpenAI API failed: {e}")
            raise Exception("All LLM providers failed to generate an answer.")

llm_service = LLMService()
