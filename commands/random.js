export const command = {
    name: 'random',
    description: 'Generates a random number between x and y',
    options: [
        {
            name: 'x',
            type: 'INTEGER',
            description: 'The lower bound',
            required: true
        },
        {
            name: 'y',
            type: 'INTEGER',
            description: 'The upper bound',
            required: true
        }
    ]
};

export const handler = async (interaction) => {
    const x = interaction.options.getInteger('x');
    const y = interaction.options.getInteger('y');
    const randomNumber = Math.floor(Math.random() * (y - x + 1)) + x;
    await interaction.reply(`Random number between ${x} and ${y}: ${randomNumber}`);
};