import dotenv from 'dotenv';
dotenv.config();

import { 
    Client,
    Events,
    GatewayIntentBits,
    REST,
    Routes
} from 'discord.js';
import fs from 'fs';
import path from 'path';

const client = new Client({
    intents:[
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.DirectMessages
    ],
});

const commands = [];
const commandHandlers = new Map();

// Load command files
const commandFiles = fs.readdirSync(path.join(__dirname, 'commands')).filter(file => file.endsWith('.js'));

(async () => {
    for (const file of commandFiles) {
        const { command, handler } = await import(`./commands/${file}`);
        commands.push(command);
        commandHandlers.set(command.name, handler);
    }
})();

const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

(async () => {
    try {
        console.log('Started refreshing application (/) commands.');

        await rest.put(
            Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
            { body: commands }
        );

        console.log('Successfully reloaded application (/) commands.');
    } catch (error) {
        console.error(error);
    }
})();

client.on(Events.InteractionCreate, async interaction => {
    if (!interaction.isCommand()) return;

    const handler = commandHandlers.get(interaction.commandName);
    if (!handler) {
        await interaction.reply('Unknown command');
        return;
    }

    await handler(interaction);
});

(async () => {
    await client.login(process.env.DISCORD_TOKEN);
})();