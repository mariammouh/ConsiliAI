"""
ConsiliAI Security Package
==========================
Provides multi-tiered security defenses and prompt injection detection
for the ConsiliAI agentic platform.

Key Modules:
- prompt_injection_guard: Inspects, sanitizes, and scores untrusted inputs
  (chat messages, uploaded PDF content, student experiment submissions) to prevent
  jailbreak attempts, system instruction overrides, and delimiter breakouts.
"""
