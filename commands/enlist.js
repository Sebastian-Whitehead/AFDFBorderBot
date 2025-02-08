import roles from './roles.json';
const channels = require('./channels.json');
const fs = require('fs').promises;

export const command = {
    name: 'enlist',
    description: 'Enlists a user to the military department, if the user is not yet a citizen they will be granted citizenship'
};

export const handler = async (interaction, user) => {
    const guild = interaction.guild;
    const member = guild.members.cache.get(user.id);

    if (member) {
        const conscript_roles = roles.conscript_roles; // Get conscript roles to add
        const immigrant_role = roles.immigrant_role; // Get immigrant role to remove
        const citizenRoles = roles.citizen_roles; // Get citizen roles

        // Check if the user is already a citizen if not approve citizen ship
        hasCitizenRole = citizenRoles.some(role => member.roles.cache.has(role));

        if (!hasCitizenRole) {
            console.log('User is not a citizen, approving citizenship...');
            // Call the handler function from approve.js
            await require('./approve.js').handler(interaction, user);
        }

        // Add conscript roles
        await member.roles.add(conscript_roles);
        await interaction.reply({content: `User ${user.username} has been enlisted and roles have been updated.`, ephemeral: true});


        // Send an enlistment embed message based on the content of a json file in ./embeds/enlist.json
        const embed = await fs.readFile('./embeds/enlist.json', 'utf8');
        let embedDict = JSON.parse(embed);

        // TODO: Replace placeholders with user data
        const compiled_embed = { embeds: [embedDict] };

        const channel = guild.channels.cache.get(channels.military_general);
        if (channel) {
            await channel.send({ content: user.toString(), ...citizenEmbed });            
        } else {
            console.error('Main channel not found.');
        }

        

    } else {
        await interaction.reply({content: 'User not found in the guild.', ephemeral: true});
    }
};