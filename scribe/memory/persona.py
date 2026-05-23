"""
Persona loader for markdown-based persona configuration.

Ports scribe-memory/src/persona.rs to Python.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from scribe.types import PersonaConfig, ConsciousnessMode


class PersonaLoader:
    """
    Loads persona configuration from markdown template files.
    
    Expected directory structure:
        persona_dir/
            identity.md    (required)
            ishiki.md      (required)
            yuan.md        (optional - enables MOOD/REFLECT consciousness blocks)
    """

    @staticmethod
    def load(persona_dir: Path) -> PersonaConfig:
        """
        Load persona from a directory of markdown files.
        
        Args:
            persona_dir: Directory containing identity.md, ishiki.md, and optionally yuan.md
            
        Returns:
            PersonaConfig with loaded content and detected consciousness mode
            
        Raises:
            FileNotFoundError: If required files are missing
        """
        identity_path = persona_dir / "identity.md"
        ishiki_path = persona_dir / "ishiki.md"
        
        if not identity_path.exists():
            raise FileNotFoundError(f"Required file not found: {identity_path}")
        if not ishiki_path.exists():
            raise FileNotFoundError(f"Required file not found: {ishiki_path}")
        
        identity = identity_path.read_text(encoding="utf-8")
        ishiki = ishiki_path.read_text(encoding="utf-8")
        
        yuan_path = persona_dir / "yuan.md"
        yuan: Optional[str] = None
        consciousness_mode = ConsciousnessMode.NONE
        
        if yuan_path.exists():
            yuan = yuan_path.read_text(encoding="utf-8")
            consciousness_mode = _detect_consciousness_mode(yuan)
        
        return PersonaConfig(
            identity=identity,
            ishiki=ishiki,
            yuan=yuan,
            consciousness_mode=consciousness_mode,
        )

    @staticmethod
    def build_prompt(config: PersonaConfig, user_name: str) -> str:
        """
        Build the system prompt fragment from a persona config.
        
        Replaces {{user_name}} placeholder in identity.
        
        Args:
            config: The loaded persona configuration
            user_name: The name to substitute for {{user_name}}
            
        Returns:
            Combined prompt string
        """
        parts = []
        
        # Identity - replace {{user_name}} placeholder
        identity = config.identity.replace("{{user_name}}", user_name)
        parts.append(identity)
        
        # Ishiki (speaking style)
        parts.append(config.ishiki)
        
        # Yuan consciousness mode instructions
        if config.yuan:
            if config.consciousness_mode == ConsciousnessMode.MOOD:
                parts.append(config.yuan)
            elif config.consciousness_mode == ConsciousnessMode.REFLECT:
                parts.append(config.yuan)
            # ConsciousnessMode.NONE - don't add yuan content
        
        return "\n\n".join(parts)


def _detect_consciousness_mode(content: str) -> ConsciousnessMode:
    """
    Detect consciousness mode from yuan.md content.
    
    Looks for ## MOOD or ## REFLECT markers (case-insensitive).
    """
    upper = content.upper()
    
    if "## MOOD" in upper or "<MOOD>" in upper:
        return ConsciousnessMode.MOOD
    elif "## REFLECT" in upper or "<REFLECT>" in upper:
        return ConsciousnessMode.REFLECT
    else:
        return ConsciousnessMode.NONE
