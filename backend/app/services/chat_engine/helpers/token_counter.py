"""
Token counting utilities using tiktoken.
"""
import logging
from typing import List

from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class TokenCounter:
    """Utility class for counting tokens in text and messages."""
    
    _tokenizer = None
    
    @classmethod
    def _get_tokenizer(cls):
        """Lazy load tiktoken tokenizer."""
        if cls._tokenizer is None:
            try:
                import tiktoken
                cls._tokenizer = tiktoken.get_encoding("cl100k_base")
                logger.debug("Tokenizer (cl100k_base) loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken: {e}. Using fallback estimation.")
                cls._tokenizer = False  # Mark as failed
        return cls._tokenizer
    
    @classmethod
    def count_tokens(cls, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            int: Number of tokens (or estimated count if tiktoken unavailable)
        """
        if not text:
            return 0
        
        tokenizer = cls._get_tokenizer()
        if tokenizer and tokenizer is not False:
            return len(tokenizer.encode(text))
        else:
            # Fallback: rough estimation (4 chars = 1 token)
            return len(text) // 4
    
    @classmethod
    def count_message_tokens(cls, messages: List[BaseMessage]) -> int:
        """
        Count total tokens in a list of messages.
        
        Args:
            messages: List of LangChain messages
            
        Returns:
            int: Total token count
        """
        total = 0
        for msg in messages:
            if msg.content:
                total += cls.count_tokens(msg.content)
        return total
