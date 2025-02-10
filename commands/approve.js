import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const channels = JSON.parse(fs.readFileSync(path.join(__dirname, '../channels.json'), 'utf8'));
const roles = JSON.parse(fs.readFileSync(path.join(__dirname, '../roles.json'), 'utf8'));

export const command = {
    name: 'approve',
    description: 'approves a user though the border control'
};

export const handler = async (interaction, user) => {
    const guild = interaction.guild;
    const member = guild.members.cache.get(user.id);

    if (member) {
        const rolesToAdd = roles.citizen_roles;
        const roleToRemove = roles.immigrant_role;

        await member.roles.add(rolesToAdd);
        await member.roles.remove(roleToRemove);

        await interaction.reply({ content: `User ${user.username} has been approved and roles have been updated.`, ephemeral: true });

        // Send an enlistment embed message based on the content of a json file in ./embeds/enlist.json
        try {
            // Load and parse the embed json file
            const embed = await fs.readFile('./embeds/border_approve.json', 'utf8');
            let embedDict = JSON.parse(embed);

            // Replace placeholders with user data
            embedDict.title = embedDict.title.replace('{username}', user.global_name || 'A NEW CITIZEN HAS ARRIVED!');
            embedDict.description = embedDict.description.replace('{username}', user.toString());
            embedDict.thumbnail.url = embedDict.thumbnail.url.replace('{profile_picture}', user.avatarURL());
            const compiled_embed = { embeds: [embedDict] };

            // Send the embed to the main channel
            const channel = guild.channels.cache.get(channels.main);
            if (channel) {
                await channel.send({ content: user.toString(), ...compiled_embed });
            } else {
                console.error('Main channel not found.');
            }

        } catch (error) {
            console.error('Error reading or parsing embed file:', error);
        }
    } else {
        await interaction.reply({content: 'User not found in the guild.', ephemeral: true});
    }
};