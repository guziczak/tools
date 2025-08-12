#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kimi API configuration checker for Claude Code integration."""

import os
import sys
from pathlib import Path
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class KimiConfigChecker:
    """Check and manage Kimi API configuration."""
    
    ENV_FILE = ".env.kimi"
    
    @classmethod
    def check_kimi_config(cls, project_dir: Path) -> Optional[Dict[str, str]]:
        """Check if Kimi configuration exists and is valid."""
        # Use the directory where this script is located for config files
        script_dir = Path(__file__).parent
        env_file = script_dir / cls.ENV_FILE
        
        if not env_file.exists():
            return None
            
        config = {}
        required_keys = ["KIMI_API_BASE_URL", "KIMI_API_KEY"]
        
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            
            # Check if all required keys are present
            for key in required_keys:
                if key not in config:
                    logger.warning(f"Missing required key: {key}")
                    return None
                    
            # Check if API key is configured (not empty)
            if not config.get("KIMI_API_KEY"):
                logger.warning("KIMI_API_KEY is empty. Please add your API key to .env.kimi")
                return None
                
            logger.info("Valid Kimi configuration found")
            return config
            
        except Exception as e:
            logger.error(f"Error reading Kimi config: {e}")
            return None
    
    @classmethod
    def export_kimi_env(cls, config: Dict[str, str]) -> None:
        """Export Kimi configuration as environment variables."""
        # Map Kimi config to Claude Code expected variables
        env_mappings = {
            "KIMI_API_BASE_URL": "ANTHROPIC_BASE_URL",
            "KIMI_API_KEY": "ANTHROPIC_API_KEY",
            "KIMI_MODEL": "CLAUDE_DEFAULT_MODEL"
        }
        
        for kimi_key, claude_key in env_mappings.items():
            if kimi_key in config and config[kimi_key]:
                os.environ[claude_key] = config[kimi_key]
                logger.debug(f"Set {claude_key} from {kimi_key}")
        
        # Set additional flags to indicate Kimi mode
        os.environ["CLAUDE_PROVIDER"] = "kimi"
        os.environ["CLAUDE_MODE"] = "kimi"