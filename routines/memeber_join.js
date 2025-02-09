import { Events } from 'discord.js';
const channels = require('./channels.json'); // Adjust the path to channels.json if necessary

export const setupMemberJoinListener = (client) => {
    client.on(Events.GuildMemberAdd, async member => {
        const channel = member.guild.channels.cache.get(channels.welcome);
        if (channel) {
            await channel.send(`User ${member.user.tag} has joined the server.`);
        } else {
            console.error('Welcome channel not found.');
        }
    });
};