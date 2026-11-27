"""Attendance workflow: build a list from the voice channel, edit it, then commit it to the DB."""

import datetime
import logging

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from database.attendance_functions import find_unaccounted, get_attendance_history, submit_attendance, load_session_attendance
from database.session_functions import get_open_session
from database.loa_functions import LOAManager
from ..utils.choices import to_choices
from ..utils.confirm import confirm
from ..config import CIVIL_SERVANT_ROLE_ID

logger = logging.getLogger(__name__)

STATUSES = ["present", "absent", "on_leave", "excused"]


def _loa_text(loa):
    return f"LOA until {loa['end_date']}" + (f": {loa['reason']}" if loa["reason"] else "")


def _render(active):
    lines = []
    for uid, e in active["entries"].items():
        line = f"- <@{uid}> — {e['status']}" + (" (in VC)" if e["in_vc"] else "")
        if e["loa"]:
            line += f" · {_loa_text(e['loa'])}"
        elif e["note"]:
            line += f" · {e['note']}"
        lines.append(line)
    # shortcut: cut at Discord's 2000 char limit, page it if lists ever get that long
    sess = active["session"]
    title = f"**Attendance list** for **{sess['session_name']}** (id {sess['id']})" if sess else "**Attendance list**"
    return (f"{title} ({len(lines)})\n" + ("\n".join(lines) or "_empty_"))[:1900]


class Attendance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # In memory only: lost on restart. One list for the whole bot.
        self.active = None

    def _entry(self, status, in_vc, loa, note=None):
        return {"status": status, "in_vc": in_vc, "loa": loa, "note": note}

    @app_commands.command(name="start_attendance", description="Start an attendance list from your voice channel")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    async def start_attendance(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.active:
            await interaction.followup.send("❌ An attendance list is already active. Use /submit_attendance or /discard_attendance first.")
            return
        if not await get_open_session():
            await interaction.followup.send("❌ No open session (or database unavailable). Use /create_session first.")
            return
        voice = getattr(interaction.user, "voice", None)
        if not voice or not voice.channel:
            await interaction.followup.send("❌ Join a voice channel first.")
            return

        today = datetime.datetime.now(datetime.timezone.utc).date()
        loas = {}
        for loa in await LOAManager.get_all_active_loas():
            if loa["start_date"] <= today <= datetime.date.fromisoformat(loa["end_date"]):
                loas[loa["discord_id"]] = loa

        entries = {str(m.id): self._entry("present", True, loas.get(str(m.id)))
                   for m in voice.channel.members if not m.bot}
        # Members on LOA who are not in VC are on leave, not absent.
        for uid, loa in loas.items():
            entries.setdefault(uid, self._entry("on_leave", False, loa))
        self.active = {"entries": entries, "loas": loas, "session": None}
        await interaction.followup.send(_render(self.active))

    @app_commands.command(name="modify_attendance", description="Edit the attendance of an existing session")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(session_id="Session ID (see /session_list)")
    async def modify_attendance(
        self,
        interaction: Interaction,
        session_id: app_commands.Range[int, 1, None],
    ):
        """Load a session's saved attendance as the active list. Edit it, then /submit_attendance saves it back."""
        await interaction.response.defer(ephemeral=True)
        if self.active:
            await interaction.followup.send("❌ An attendance list is already active. Use /submit_attendance or /discard_attendance first.")
            return
        loaded = await load_session_attendance(session_id)
        if loaded is None:
            await interaction.followup.send("❌ Database error.")
            return
        session, saved = loaded
        if session is None:
            await interaction.followup.send(f"❌ No session with id {session_id}.")
            return
        entries = {r["discord_id"]: self._entry(r["status"], False, None, r["notes"]) for r in saved}
        self.active = {"entries": entries, "loas": {}, "session": session}
        await interaction.followup.send(_render(self.active))

    @app_commands.command(name="view_attendance", description="Show the current attendance list")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    async def view_attendance(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(_render(self.active) if self.active else "ℹ️ No active attendance list.")

    @app_commands.command(name="add_attendance", description="Add or change a person on the attendance list")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(user="Member to add", attendance_status="Status (default present)")
    @app_commands.choices(attendance_status=to_choices(STATUSES))
    async def add_attendance(
        self,
        interaction: Interaction,
        user: discord.User,
        attendance_status: str = "present",
    ):
        await interaction.response.defer(ephemeral=True)
        if not self.active:
            await interaction.followup.send("❌ No active attendance list. Use /start_attendance first.")
            return
        uid = str(user.id)
        old = self.active["entries"].get(uid)
        self.active["entries"][uid] = self._entry(attendance_status, bool(old and old["in_vc"]), self.active["loas"].get(uid), old and old["note"])
        await interaction.followup.send(_render(self.active))

    @app_commands.command(name="log_attendance", description="Add everyone currently in your voice channel to the attendance list")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    async def log_attendance(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if not self.active:
            await interaction.followup.send("❌ No active attendance list. Use /start_attendance first.")
            return
        voice = getattr(interaction.user, "voice", None)
        if not voice or not voice.channel:
            await interaction.followup.send("❌ Join a voice channel first.")
            return
        entries = self.active["entries"]
        for m in voice.channel.members:
            if m.bot:
                continue
            uid = str(m.id)
            old = entries.get(uid)
            if old is None:
                entries[uid] = self._entry("present", True, self.active["loas"].get(uid))
            else:
                old["in_vc"] = True
                if old["status"] == "absent":  # showed up late
                    old["status"] = "present"
        await interaction.followup.send(_render(self.active))

    @app_commands.command(name="remove_attendance", description="Remove a person from the attendance list")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(user="Member to remove")
    async def remove_attendance(self, interaction: Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        if not self.active:
            await interaction.followup.send("❌ No active attendance list. Use /start_attendance first.")
            return
        if self.active["entries"].pop(str(user.id), None) is None:
            await interaction.followup.send(f"❌ {user.mention} is not on the list.")
            return
        await interaction.followup.send(_render(self.active))

    @app_commands.command(name="discard_attendance", description="Throw away the active attendance list (nothing is saved)")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    async def discard_attendance(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        had = self.active is not None
        self.active = None
        await interaction.followup.send("🗑️ Attendance list discarded." if had else "ℹ️ There was no active attendance list.")

    @app_commands.command(name="submit_attendance", description="Save the attendance list to the database")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    async def submit_attendance(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        active = self.active
        if not active:
            await interaction.followup.send("❌ No active attendance list. Use /start_attendance first.")
            return
        session = active["session"] or await get_open_session()
        if not session:
            await interaction.followup.send("❌ No open session (or database unavailable). Use /create_session first.")
            return
        missing = await find_unaccounted(list(active["entries"]))
        if missing is None:
            await interaction.followup.send("❌ Database error, nothing saved.")
            return

        if missing:
            if not await confirm(
                    interaction, "attendance_absent_warning.json",
                    {"{absent_list}": "\n".join(f"- <@{m}>" for m in missing)[:3500]},
                    declined="↩️ Not submitted, back to the list.", timed_out="⌛ Timed out, not submitted. The list is kept."):
                return
            if self.active is not active:
                await interaction.edit_original_response(content="❌ The list changed while waiting. Run /submit_attendance again.", embeds=[], view=None)
                return
        else:
            await interaction.followup.send("⏳ Submitting…")

        rows = [{"discord_id": uid, "status": e["status"], "notes": _loa_text(e["loa"]) if e["loa"] else e["note"]}
                for uid, e in active["entries"].items()]
        rows += [{"discord_id": m, "status": "absent", "notes": None} for m in missing]
        result = await submit_attendance(session["id"], rows, str(interaction.user.id))
        if result is None:
            await interaction.edit_original_response(content="❌ Database error, nothing saved. The list is kept.", embeds=[], view=None)
            return
        self.active = None
        msg = f"✅ Attendance saved to **{session['session_name']}** (id {session['id']}): {len(result['saved'])} recorded."
        if result["skipped"]:
            msg += "\nNo service record, not saved:\n" + "\n".join(f"- <@{m}>" for m in result["skipped"])
        await interaction.edit_original_response(content=msg, embeds=[], view=None)

    @app_commands.command(name="attendance_history", description="Show a member's attendance history")
    @app_commands.checks.has_role(CIVIL_SERVANT_ROLE_ID)
    @app_commands.describe(user="Member", rows="Recent sessions to list (default 10)")
    async def attendance_history(
        self,
        interaction: Interaction,
        user: discord.User,
        rows: app_commands.Range[int, 1, 25] = 10,
    ):
        await interaction.response.defer(ephemeral=True)
        hist = await get_attendance_history(str(user.id), rows)
        if hist is None:
            await interaction.followup.send("❌ Database error.")
            return
        if not hist["has_record"]:
            await interaction.followup.send(f"❌ {user.mention} has no service record.")
            return
        counts = hist["counts"]
        total = sum(counts.values())
        if not total:
            await interaction.followup.send(f"ℹ️ No attendance recorded for {user.mention}.")
            return
        summary = " · ".join(f"{s} {counts[s]}" for s in STATUSES if s in counts)
        lines = [f"**{r['session_name'][:60]}** · {r['start_at'].astimezone(datetime.timezone.utc):%Y-%m-%d} · {r['status']}"
                 + (f" · {r['notes'][:50]}" if r["notes"] else "") for r in hist["recent"]]
        embed = discord.Embed(
            title=f"Attendance: {user.display_name}",
            description=f"{summary}\nAttendance rate: {counts.get('present', 0) / total:.0%} ({total} sessions)\n\n" + "\n".join(lines))
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Attendance(bot))
