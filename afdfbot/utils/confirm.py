"""Shared Approve/Decline confirmation prompt, shown as an embed from the embeds folder."""

import discord

from .embed_processor import load_embeds


class _Confirm(discord.ui.View):
    """Approve/Decline buttons, usable only by the officer who ran the command."""

    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.approved = None

    async def interaction_check(self, interaction):
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):
        self.approved = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Decline", emoji="❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction, button):
        self.approved = False
        await interaction.response.defer()
        self.stop()


async def confirm(interaction, embed_file, replacements=None, declined="↩️ Cancelled.", timed_out="⌛ Timed out, cancelled."):
    """Ask the command sender to approve. The interaction must already be deferred.
    Returns True on approve (the prompt stays up so the caller can edit it with the result);
    on decline or timeout it replaces the prompt with `declined`/`timed_out` and returns False."""
    view = _Confirm(interaction.user.id)
    await interaction.followup.send(embeds=load_embeds(embed_file, replacements or {}), view=view)
    await view.wait()
    if view.approved:
        return True
    await interaction.edit_original_response(
        content=declined if view.approved is False else timed_out, embeds=[], view=None)
    return False
