import roles from './roles.json';

export const command = {
    name: 'enlist',
    description: 'Enlists a user to the military department, if the user is not yet a citizen they will be granted citizenship'
};

export const handler = async (interaction, user) => {
    const guild = interaction.guild;
    const member = guild.members.cache.get(user.id);

    if (member) {
        const rolesToAdd = roles.conscript_roles; // Get conscript roles to add
        const roleToRemove = roles.immigrant_role; // Get immigrant role to remove
        const citizenRoles = roles.citizen_roles; // Get citizen roles

        // Add citizen roles if the member doesn't already have them
        for (const role of citizenRoles) {
            if (!member.roles.cache.has(role)) {
                await member.roles.add(role);
            }
        }

        // Add conscript roles
        await member.roles.add(rolesToAdd);
        // Remove immigrant role
        await member.roles.remove(roleToRemove);

        await interaction.reply(`User ${user.username} has been enlisted and roles have been updated.`);
    } else {
        await interaction.reply('User not found in the guild.');
    }
};