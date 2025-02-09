import { Client } from 'discord.js';
import fs from 'fs';
import path from 'path';
import roles from './roles.json';
import channels from './channels.json';

const immigrationStaff_role = roles.immigrationStaff_role;
const CHECK_INTERVAL = 120000; // 2 minutes

class BorderOfficerMonitor {
    /**
     * A Discord bot class that monitors the online status of members with a specific role
     * and sends a message to a designated channel if no members are online.
     * @param {Client} bot - The bot instance.
     */
    constructor(bot) {
        this.bot = bot;
        this.lastOnlineStatus = false; // Track the last known online status
        this.msg = null; // Store the message sent to the channel

        // Get the guild (server) by ID
        this.guild = this.bot.guilds.cache.get(process.env.AEGEAN_FED);
        this.role = this.guild.roles.cache.get(immigrationStaff_role);
        this.channel = this.guild.channels.cache.get(channels.checkpoint);

        if (!this.guild) {
            console.error(`Guild with ID ${process.env.AEGEAN_FED} not found!`);
            return;
        }
        if (!this.role) {
            console.error(`Role with ID ${immigrationStaff_role} not found!`);
            return;
        }
        if (!this.channel) {
            console.error("Channel not found!");
            return;
        }

        this.startMonitoring(); // Start the monitoring process
    }

    // Start the monitoring process by checking the online status at regular intervals
    startMonitoring() {
        this.checkOnlineStatus(); // Initial check
        setInterval(this.checkOnlineStatus.bind(this), CHECK_INTERVAL); // Schedule subsequent checks
    }

    // Check the online status of members with the specified role
    async checkOnlineStatus() {
        console.log(`${new Date().toISOString()} Checking online status...`);

        // Ensure all members are loaded
        await this.guild.members.fetch();

        let onlineMembers = this.role.members.filter(member => 
            member.presence && !['offline', 'invisible', 'dnd'].includes(member.presence.status)
        ); // Get all online members with the specified role

        const staffOnline = onlineMembers.size > 0; // Determine if any members are online
        if (this.lastOnlineStatus === staffOnline) {
            console.log(`No change in status`);
            return; // Exit if there is no change in status
        }

        console.log(`Status changed! to ${staffOnline}`);
        this.lastOnlineStatus = staffOnline; // Update the last known status

        if (!staffOnline) {
            // If no members are online, send a message to the channel
            if (!this.msg) {
                this.msg = await this.checkpoint.send(":roundel2: The Aegean Federation immigration department is closing shop for the night, apologies for any inconveniences. :roundel2:");
            }
        } else {
            // If members are online, delete the previously sent message
            if (this.msg) {
                await this.msg.delete();
                this.msg = null;
            }
        }
        console.log(`Check complete. ${onlineMembers.size} Online border agents`);
    }
}

// Function to set up the BorderOfficerMonitor
export function setupBorderOfficerMonitor(bot) {
    new BorderOfficerMonitor(bot);
}
