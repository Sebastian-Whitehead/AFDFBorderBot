import { Events } from 'discord.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const memberJoinEmbed = JSON.parse(fs.readFileSync(path.join(__dirname, '../embeds/member_join.json'), 'utf8'));

export function setupMemberJoinListener(client) {
    client.on(Events.GuildMemberAdd, async member => {
        const channel = member.guild.systemChannel; // You can change this to a specific channel if needed
        if (!channel) return;

        try {
            await channel.send({ embeds: [memberJoinEmbed] });
            console.log(`Welcome message sent to ${member.user.tag}`);
        } catch (error) {
            console.error(`Could not send welcome message to ${member.user.tag}:`, error);
        }
    });
}