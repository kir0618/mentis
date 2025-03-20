from typing import Any, Dict, List, Optional, Union, Callable, TypedDict, Type

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore
from core.agents.react_agent import ReactAgent, AgentState
import re
import json
from datetime import datetime


class CodeSnippet(TypedDict):
    """Structured code snippet type"""
    language: str  # Programming language
    code: str  # Code content
    description: str  # Description of what the code does
    timestamp: str  # Creation timestamp


class CoderAgent(ReactAgent):
    """Coder agent implementation for code generation and problem-solving tasks.

    Responsibilities:
    - Generate code based on requirements
    - Debug and fix issues in existing code
    - Optimize code for performance and readability
    - Explain code functionality and implementation details
    - Provide code reviews and suggestions for improvement

    Design Principles:
    - Maintain separation of prompt template from initialization logic
    - Enable flexible prompt customization through inheritance
    - Follow PEP8 style guidelines for multi-line strings
    - Store code snippets in structured format for better organization
    """

    _PROMPT_TEMPLATE = """You are a professional Software Engineer specialized in writing clean, efficient, and well-documented code.

## REACT Methodology for Coding

### Problem Understanding
- Analyze requirements thoroughly before writing code
- Break down complex problems into smaller, manageable parts
- Identify edge cases and potential issues

### Solution Design
- Plan your approach before implementation
- Consider different algorithms and data structures
- Design for maintainability, scalability, and performance

### Implementation
- Write clean, readable, and well-documented code
- Follow language-specific best practices and conventions
- Use meaningful variable and function names
- Include comments for complex logic

### Testing and Debugging
- Test your code with various inputs, including edge cases
- Debug issues methodically
- Validate that your solution meets all requirements

### Optimization
- Improve code efficiency where necessary
- Refactor for better readability and maintainability
- Consider time and space complexity

## Important Guidelines
- Prioritize code readability and maintainability
- Include docstrings and comments where appropriate
- Handle errors and edge cases gracefully
- Follow language-specific conventions and best practices
- Provide explanations of your implementation choices

Available tools:
{tools}
"""

    def __init__(
        self,
        name: str,
        model: LanguageModelLike,
        tools: Optional[List[BaseTool]] = None,
        prompt: Optional[Union[str, SystemMessage, Callable, Runnable]] = None,
        max_iterations: int = 5,
        cache_enabled: bool = True,
        response_format: Optional[Union[dict, Type[Any]]] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        store: Optional[BaseStore] = None,
        interrupt_before: Optional[List[str]] = None,
        interrupt_after: Optional[List[str]] = None,
        debug: bool = False,
        version: str = "v1",
    ):
        """Initialize a coder agent with customizable components.

        Args:
            name: Unique identifier for the agent instance.
            model: Language model for code generation and problem-solving.
            tools: Available toolset for coding tasks (default: None).
            prompt: Custom instruction template (default: use class template).
            max_iterations: Maximum number of iterations (default: 5).
            cache_enabled: Whether to cache code snippets (default: True).
            response_format: Optional response format for structured output.
            checkpointer: Optional checkpoint saver for persisting agent state.
            store: Optional storage object for cross-thread data sharing.
            interrupt_before: Optional list of node names to interrupt before execution.
            interrupt_after: Optional list of node names to interrupt after execution.
            debug: Whether to enable debug mode.
            version: LangGraph version ("v1" or "v2").
        """
        # Format prompt template with tools information
        formatted_prompt = self._PROMPT_TEMPLATE
        if tools:
            tools_str = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
            formatted_prompt = formatted_prompt.format(tools=tools_str)
        
        super().__init__(
            name=name,
            model=model,
            tools=tools or [],
            prompt=prompt or formatted_prompt,
            response_format=response_format,
            checkpointer=checkpointer,
            store=store,
            interrupt_before=interrupt_before,
            interrupt_after=interrupt_after,
            debug=debug,
            version=version,
        )
        self.max_iterations = max_iterations
        self.cache_enabled = cache_enabled
        self._code_snippets = []  # Initialize code snippets list
        self._iteration_count = 0  # Current iteration count

    def add_tools(self, tools: List[BaseTool]) -> None:
        """Add tools to the agent and update the prompt.

        Args:
            tools: A list of tools to add.
        """
        self.tools.extend(tools)
        # Update tools list in prompt
        tools_str = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        if isinstance(self.prompt, str):
            self.prompt = self._PROMPT_TEMPLATE.format(tools=tools_str)

    def save_code_snippet(self, language: str, code: str, description: str) -> None:
        """Save a code snippet.

        Args:
            language: The programming language of the code.
            code: The code content.
            description: Description of what the code does.

        Returns:
            None
        """
        timestamp = datetime.now().isoformat()
        snippet = CodeSnippet(
            language=language,
            code=code,
            description=description,
            timestamp=timestamp
        )
        self._code_snippets.append(snippet)
        
        # Increment iteration count
        self._iteration_count += 1

    def get_code_snippets(self, language: Optional[str] = None) -> List[CodeSnippet]:
        """Get code snippets, optionally filtered by language.

        Args:
            language: Optional language filter.

        Returns:
            List of code snippets.
        """
        if language:
            return [snippet for snippet in self._code_snippets if snippet["language"] == language]
        return self._code_snippets

    def get_latest_snippet(self) -> Optional[CodeSnippet]:
        """Get the most recently created code snippet.

        Returns:
            The latest code snippet or None if no snippets exist.
        """
        if not self._code_snippets:
            return None
        return self._code_snippets[-1]

    def clear_snippets(self) -> None:
        """Clear all stored code snippets.

        Returns:
            None
        """
        self._code_snippets = []
        self._iteration_count = 0