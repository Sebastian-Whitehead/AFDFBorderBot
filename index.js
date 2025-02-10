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
import { fileURLToPath } from 'url';

import { setupMemberLeaveListener } from './routines/member_leave.js';
import { setupBorderOfficerMonitor } from './routines/immigrationStaff.js';
import { setupMemberJoinListener } from './routines/member_join.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const client = new Client({
    intents:[
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildPresences,
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
            Routes.applicationGuildCommands(process.env.DISCORD_CLIENT_ID, process.env.AEGEAN_FED),
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

client.once('ready', () => {
    console.log(`Logged in as ${client.user.tag}!`);
    setupMemberLeaveListener(client);
    setupMemberJoinListener(client);
    setupBorderOfficerMonitor(client);
});

(async () => {
    await client.login(process.env.DISCORD_TOKEN);
})();