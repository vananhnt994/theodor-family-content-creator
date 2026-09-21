import os
import json
import logging

logger = logging.getLogger(__name__)

def load_channel_config():
    """
    Loads the channel configuration defined by the THEODOR_CHANNEL_CONFIG environment variable.
    Defaults to channels/betheo.json if present, otherwise falls back to channels/channel.example.json.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_config = os.environ.get("THEODOR_CHANNEL_CONFIG")
    
    if env_config:
        full_path = os.path.join(base_dir, env_config)
    else:
        # Check betheo.json first, then fall back to channel.example.json
        betheo_path = os.path.join(base_dir, "channels", "betheo.json")
        example_path = os.path.join(base_dir, "channels", "channel.example.json")
        if os.path.exists(betheo_path):
            full_path = betheo_path
        elif os.path.exists(example_path):
            logger.info(f"ℹ️ channels/betheo.json nicht gefunden. Verwende Vorlage: {example_path}")
            full_path = example_path
        else:
            full_path = betheo_path

    if not os.path.exists(full_path):
        logger.error(f"❌ Kann Channel-Config nicht finden: {full_path}")
        raise FileNotFoundError(f"Missing channel config: {full_path}. Bitte channels/channel.example.json kopieren!")

    with open(full_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    return config
