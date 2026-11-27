"""
Utility for processing embed data with placeholder replacements.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

import nextcord

from ..config import BORDER_OFFICER_ROLE_ID

logger = logging.getLogger(__name__)

# Placeholders any embed can use without code: {channel:loa_txt} {role:leadership} {setting:modpack-url}
_GENERIC = re.compile(r'\{(channel|role|setting):([\w\-]+)\}')


def _resolve_generic(match):
    from ..config import CHANNELS, ROLES, get_setting  # lazy: config pulls in the database package
    kind, key = match.groups()
    if kind == 'setting':
        value = get_setting(key)
    else:
        value = (CHANNELS if kind == 'channel' else ROLES).get(key)
        if isinstance(value, int):  # list-valued roles (citizen, enlisted, ranks) can't be mentioned
            value = f"<#{value}>" if kind == 'channel' else f"<@&{value}>"
        else:
            value = None
    return match.group(0) if value is None else str(value)  # unknown stays literal; tests/test_embeds.py catches it


def member_replacements(member) -> Dict[str, str]:
    """Per-member placeholders shared by the join/leave/approve/enlist embeds (and /test-msg)."""
    return {
        '{user}': member.mention,
        '{username}': member.display_name,
        '{User}': member.mention,
        '{Username}': member.display_name,
        '{userid}': str(member.id),
        '{usertag}': str(member),
        '{border_officer}': f'<@&{BORDER_OFFICER_ROLE_ID}>' if BORDER_OFFICER_ROLE_ID else 'Border Officers',
    }


class EmbedProcessor:
    @staticmethod
    def replace_placeholders(text: str, replacements: Dict[str, str]) -> str:
        if not isinstance(text, str):
            return text
        
        for placeholder, replacement in replacements.items():
            text = text.replace(placeholder, replacement)

        return _GENERIC.sub(_resolve_generic, text)
    
    @staticmethod
    def process_embed_data(embed_data: Dict[str, Any], replacements: Dict[str, str]) -> Optional[Dict[str, Any]]:
        if not embed_data:
            return None
        
        # Create a deep copy to avoid modifying the original
        processed_data = json.loads(json.dumps(embed_data))
        
        # Replace placeholders in content
        if 'content' in processed_data:
            processed_data['content'] = EmbedProcessor.replace_placeholders(
                processed_data['content'], replacements
            )
        
        # Replace placeholders in embeds
        if 'embeds' in processed_data:
            for embed in processed_data['embeds']:
                # Process title, description
                for field in ['title', 'description']:
                    if field in embed:
                        embed[field] = EmbedProcessor.replace_placeholders(embed[field], replacements)
                
                # Process footer text
                if 'footer' in embed and 'text' in embed['footer']:
                    embed['footer']['text'] = EmbedProcessor.replace_placeholders(
                        embed['footer']['text'], replacements
                    )
                
                # Process author name
                if 'author' in embed and 'name' in embed['author']:
                    embed['author']['name'] = EmbedProcessor.replace_placeholders(
                        embed['author']['name'], replacements
                    )
                
                # Process image urls (e.g. {avatar_url})
                for key in ('thumbnail', 'image'):
                    if 'url' in embed.get(key, {}):
                        embed[key]['url'] = EmbedProcessor.replace_placeholders(embed[key]['url'], replacements)

                # Process fields
                if 'fields' in embed:
                    for field in embed['fields']:
                        if 'name' in field:
                            field['name'] = EmbedProcessor.replace_placeholders(field['name'], replacements)
                        if 'value' in field:
                            field['value'] = EmbedProcessor.replace_placeholders(field['value'], replacements)
        
        return processed_data
    
    @staticmethod
    def load_embed_data(filename: str, embeds_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        # embeds_dir defaults to the project embeds folder
        if embeds_dir is None:
            # Default to project embeds directory
            embeds_dir = Path(__file__).parent.parent.parent / "embeds"
        
        embed_path = embeds_dir / filename
        try:
            with open(embed_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading embed file {filename}: {e}")
            return None
    
    @staticmethod
    async def send_embed(channel, embed_data):
        """Send processed embed data to a channel; returns the sent message (truthy), or None."""
        if not embed_data or not channel:
            return None
        try:
            # "flags": 4096 in the JSON sends the message silently (no notifications)
            silent = bool(embed_data.get('flags', 0) & 4096)
            return await channel.send(content=embed_data.get('content', ''), embeds=_to_embeds(embed_data),
                                      flags=nextcord.MessageFlags(suppress_notifications=silent))
        except Exception as e:
            logger.exception(f"Error sending embed: {e}")
            return None


def _to_embeds(data) -> list:
    # "id"/"type" come from Discord-exported JSON and make Embed.from_dict choke
    return [nextcord.Embed.from_dict({k: v for k, v in e.items() if k not in ("id", "type")})
            for e in (data or {}).get("embeds", [])]


def load_embeds(filename: str, replacements: Dict[str, str]) -> list:
    """Load an embed file, apply placeholders and return nextcord Embeds (for interaction replies)."""
    return _to_embeds(EmbedProcessor.process_embed_data(EmbedProcessor.load_embed_data(filename), replacements))


async def send_processed_embed(channel, filename: str, replacements: Dict[str, str]):
    """Load, process and send an embed file in one call; returns the sent message (truthy), or None."""
    embed_data = EmbedProcessor.load_embed_data(filename)
    if not embed_data:
        return None
    processed_data = EmbedProcessor.process_embed_data(embed_data, replacements)
    if not processed_data:
        return None
    return await EmbedProcessor.send_embed(channel, processed_data)
