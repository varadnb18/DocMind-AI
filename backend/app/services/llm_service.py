import logging
from typing import Dict, Any, Tuple, List
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # Initialize LangChain Chat Models
        self.groq_chat = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=1024
        )
        self.gemini_chat = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
            max_tokens=1024
        )
        self.openai_chat = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.2,
            max_tokens=1024
        )

        # Create LangChain PromptTemplate
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful AI assistant answering questions based on context. Please provide a comprehensive answer based only on the provided context. If the context doesn't contain enough information to answer the question, please state that clearly."),
            ("user", "Context:\n{context}\n\nQuestion: {question}")
        ])

    def generate_answer(self, query: str, documents: List[Document]) -> Tuple[str, str]:
        """
        Attempts to generate an answer with fallback logic using LangChain.
        Priority: 1. Groq -> 2. Gemini -> 3. OpenAI
        Returns a tuple: (answer_text, provider_name)
        """
        # Format the context from the retrieved LangChain documents
        context_parts = [
            f"Source: {doc.metadata.get('filename', 'Unknown')}\nContent: {doc.page_content}\n"
            for doc in documents
        ]
        context = "\n---\n".join(context_parts)

        # Format the prompt
        messages = self.prompt_template.format_messages(context=context, question=query)

        # 1. Try Groq (Primary)
        try:
            logger.info("Attempting to use Groq API via LangChain...")
            response = self.groq_chat.invoke(messages)
            if response and response.content:
                logger.info("Successfully generated answer using Groq.")
                return response.content.strip(), "Groq (llama-3.3-70b)"
        except Exception as e:
            logger.warning(f"Groq API failed: {e}")

        # 2. Try Gemini (Secondary)
        try:
            logger.info("Attempting to use Gemini API via LangChain...")
            response = self.gemini_chat.invoke(messages)
            if response and response.content:
                logger.info("Successfully generated answer using Gemini.")
                return response.content.strip(), "Google Gemini"
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}")

        # 3. Try OpenAI (Fallback)
        try:
            logger.info("Attempting to use OpenAI API via LangChain...")
            response = self.openai_chat.invoke(messages)
            if response and response.content:
                logger.info("Successfully generated answer using OpenAI.")
                return response.content.strip(), "OpenAI (gpt-3.5-turbo)"
        except Exception as e:
            logger.error(f"OpenAI API failed: {e}")
            raise Exception("All LLM providers failed to generate an answer.")

llm_service = LLMService()
