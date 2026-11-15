"""
Utility for processing embed data with placeholder replacements.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

import nextcord


class EmbedProcessor:
    """Utility class for processing embed data with placeholder replacements."""
    
    @staticmethod
    def replace_placeholders(text: str, replacements: Dict[str, str]) -> str:
        """
        Replace placeholders in text with provided replacements.
        
        Args:
            text: The text to process
            replacements: Dictionary of placeholder -> replacement mappings
            
        Returns:
            Text with placeholders replaced
        """
        if not isinstance(text, str):
            return text
        
        for placeholder, replacement in replacements.items():
            text = text.replace(placeholder, replacement)
        
        return text
    
    @staticmethod
    def process_embed_data(embed_data: Dict[str, Any], replacements: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Process embed data by replacing placeholders throughout the structure.
        
        Args:
            embed_data: The embed data dictionary to process
            replacements: Dictionary of placeholder -> replacement mappings
            
        Returns:
            Processed embed data with placeholders replaced, or None if invalid input
        """
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
        """
        Load and parse embed data from JSON file.
        
        Args:
            filename: Name of the embed file to load
            embeds_dir: Directory containing embed files (defaults to project embeds folder)
            
        Returns:
            Loaded embed data or None if failed
        """
        if embeds_dir is None:
            # Default to project embeds directory
            embeds_dir = Path(__file__).parent.parent.parent / "embeds"
        
        embed_path = embeds_dir / filename
        try:
            with open(embed_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading embed file {filename}: {e}")
            return None
    
    @staticmethod
    async def send_embed(channel, embed_data):
        """
        Send processed embed data to a Discord channel.
        
        Args:
            channel: Discord channel object to send to
            embed_data: Processed embed data dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not embed_data or not channel:
            return False
        
        try:
            # Extract content
            content = embed_data.get('content', '')
            
            # Create embeds using from_dict
            embeds = []
            if 'embeds' in embed_data:
                for embed_dict in embed_data['embeds']:
                    # Remove any non-embed fields that might cause issues
                    clean_embed_dict = {k: v for k, v in embed_dict.items() 
                                      if k not in ['id', 'type']}
                    embed = nextcord.Embed.from_dict(clean_embed_dict)
                    embeds.append(embed)
            
            # Send the message
            await channel.send(content=content, embeds=embeds)
            return True
            
        except Exception as e:
            print(f"Error sending embed: {e}")
            return False


def load_embeds(filename: str, replacements: Dict[str, str]) -> list:
    """Load an embed file, apply placeholders and return nextcord Embeds (for interaction replies)."""
    data = EmbedProcessor.process_embed_data(EmbedProcessor.load_embed_data(filename), replacements)
    return [nextcord.Embed.from_dict({k: v for k, v in e.items() if k not in ("id", "type")})
            for e in (data or {}).get("embeds", [])]


# Simple convenience function
async def send_processed_embed(channel, filename: str, replacements: Dict[str, str]) -> bool:
    """
    Load, process, and send an embed in one call.
    
    Args:
        channel: Discord channel to send to
        filename: Embed JSON filename to load
        replacements: Dictionary of placeholder -> replacement mappings
        
    Returns:
        True if sent successfully, False otherwise
    """
    embed_data = EmbedProcessor.load_embed_data(filename)
    if not embed_data:
        return False
    
    processed_data = EmbedProcessor.process_embed_data(embed_data, replacements)
    if not processed_data:
        return False
    
    return await EmbedProcessor.send_embed(channel, processed_data)
