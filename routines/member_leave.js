import { Events } from 'discord.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const memberLeaveEmbed = JSON.parse(fs.readFileSync(path.join(__dirname, '../embeds/member_leave.json'), 'utf8'));

export function setupMemberLeaveListener(client) {
    client.on(Events.GuildMemberRemove, async member => {
        const channel = member.guild.systemChannel; // You can change this to a specific channel if needed
        if (!channel) return;

        try {
            await channel.send({ embeds: [memberLeaveEmbed] });
            console.log(`Goodbye message sent for ${member.user.tag}`);
        } catch (error) {
            console.error(`Could not send goodbye message for ${member.user.tag}:`, error);
        }
    });
}