"""
Assistant conversationnel NutriScope (TP 18).

- ``config`` : modèle et serveur lus dans les variables d'environnement (LLAMACPP_HOST, LLM_MODEL...) ;
- ``client`` : un appel mesuré à un point d'accès compatible OpenAI (llama.cpp, Ollama ou API) ;
- ``behavior`` : le rôle, lu dans ``assistant_behavior.txt`` ;
- ``guards`` : garde-fous écrits en code (refus médical, nombres justifiés par les faits) ;
- ``agent`` : la boucle d'appel d'outils, bornée.

Les outils sont les plugins de ``nutriscope.tools`` ; le catalogue est ``nutriscope.catalog`` (PostgreSQL).
"""

from .agent import Assistant, AssistantAnswer, ToolTrace
from .behavior import Behavior, load_behavior
from .client import ModelReply, chat, llamacpp_status, make_client, ollama_status
from .config import ConfigError, LLMConfig, load_config

__all__ = ["Assistant", "AssistantAnswer", "Behavior", "ConfigError", "LLMConfig", "ModelReply", "ToolTrace",
           "chat", "llamacpp_status", "load_behavior", "load_config", "make_client", "ollama_status"]
