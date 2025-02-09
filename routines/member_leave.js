import { Events } from 'discord.js';
const channels = require('./channels.json');

export const setupMemberLeaveListener = (client) => {
    client.on(Events.GuildMemberRemove, async member => {
        const channel = member.guild.channels.cache.get(channels.welcome);
        if (channel) {
            await channel.send(`User ${member.user.tag} has left the server.`);
        } else {
            console.error('Welcome channel not found.');
        }
    });
};