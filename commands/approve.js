import roles from './roles.json';

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

        await interaction.reply(`User ${user.username} has been approved and roles have been updated.`);
    } else {
        await interaction.reply('User not found in the guild.');
    }
};