"""
Synapse Memory — Zero-Knowledge Memory Layer for AI Agents

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .sanitizer import SynapseSanitizer, SanitizationResult, SensitivityLevel

__version__ = "1.0.3"
__all__ = ["SynapseSanitizer", "SanitizationResult", "SensitivityLevel"]
