"""
Synapse Layer — Dynamic Plugin Loader

Loads the PRO plugin (``synapse_memory_pro``) at runtime if installed.
Respects ``SYNAPSE_MODE`` to enforce OSS/PRO separation.

Behavior:
    - SYNAPSE_MODE=oss  → Always returns None (ignore plugin)
    - SYNAPSE_MODE=pro  → Attempts import; warns if not installed

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .interfaces import SynapseProPlugin

logger = logging.getLogger("synapse.core.plugin_loader")


def load_pro_plugin(mode: Optional[str] = None) -> Optional[SynapseProPlugin]:
    """Attempt to load the PRO plugin bundle.

    Parameters
    ----------
    mode : str | None
        Override for SYNAPSE_MODE. Reads env var if None.

    Returns
    -------
    SynapseProPlugin | None
        The plugin instance if available and allowed, else None.
    """
    resolved_mode = (mode or os.getenv("SYNAPSE_MODE", "oss")).lower()

    # OSS mode: never load plugin, even if installed
    if resolved_mode != "pro":
        logger.debug("Plugin loader: mode=%s, skipping PRO plugin", resolved_mode)
        return None

    # PRO mode: attempt import
    try:
        import synapse_memory_pro  # type: ignore[import-not-found]
        plugin = synapse_memory_pro.get_plugin()

        # Validate plugin interface
        if not isinstance(plugin, SynapseProPlugin):
            logger.error(
                "PRO plugin does not conform to SynapseProPlugin protocol. "
                "Falling back to OSS defaults."
            )
            return None

        logger.info("PRO plugin loaded successfully")
        return plugin

    except ImportError:
        logger.warning(
            "SYNAPSE_MODE=pro but synapse-layer-pro is not installed. "
            "Install with: pip install synapse-layer-pro. "
            "Falling back to OSS defaults."
        )
        return None

    except Exception as exc:
        logger.error(
            "Failed to load PRO plugin: %s. Falling back to OSS defaults.",
            str(exc),
        )
        return None
