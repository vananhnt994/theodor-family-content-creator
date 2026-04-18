import os
import json
import logging

logger = logging.getLogger(__name__)

def load_channel_config():
    """
    Loads the channel configuration defined by the THEODOR_CHANNEL_CONFIG environment variable.
    Defaults to channels/betheo.json if not set.
    """
    config_path = os.environ.get("THEODOR_CHANNEL_CONFIG", os.path.join("channels", "betheo.json"))
    
    # Pfad absichern, falls von woanders aufgerufen
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, config_path)
    
    if not os.path.exists(full_path):
        logger.error(f"❌ Kann Channel-Config nicht finden: {full_path}")
        raise FileNotFoundError(f"Missing channel config: {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    return config
