import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import asyncio
import time
from typing import Optional

load_dotenv()
TOKEN = os.getenv('TOKEN')

# Bot Configuration
BOT_INFO = {
    "name": "Artemis Ticket Bot",
    "creator": {
        "name": "at.9",
        "discord_id": "547451355179253760",
        "github": "https://github.com/AX9zz",
        "website": "https://guns.lol/AX9"
    },
    "support_server": "https://discord.gg/ubm9msKS",
    "invite_url": "https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot"
}

class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix='/', intents=intents)
        self.ticket_settings = {}
        self.start_time = time.time()

    async def setup_hook(self):
        await self.tree.sync()

class TicketModal(discord.ui.Modal):
    def __init__(self, title: str, action_type: str):
        super().__init__(title=title)
        self.action_type = action_type
        
        if action_type == "rename":
            self.name = discord.ui.TextInput(
                label="New Ticket Name",
                placeholder="Enter new name...",
                required=True,
                max_length=32
            )
            self.add_item(self.name)
        elif action_type == "reason":
            self.reason = discord.ui.TextInput(
                label="Reason",
                placeholder="Enter the reason...",
                required=True,
                style=discord.TextStyle.paragraph
            )
            self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if self.action_type == "rename":
            new_name = f"📩︱ticket・{self.name.value}"
            await interaction.channel.edit(name=new_name)
            await log_action(
                interaction.guild,
                "Ticket Renamed",
                f"Renamed by: {interaction.user.mention}\nNew name: {new_name}",
                discord.Color.blue(),
                interaction.user,
                interaction.channel
            )
            await interaction.response.send_message(f"Ticket renamed to {new_name}", ephemeral=True)
        
        elif self.action_type == "reason":
            await log_action(
                interaction.guild,
                "Ticket Closed",
                f"Closed by: {interaction.user.mention}\nReason: {self.reason.value}",
                discord.Color.red(),
                interaction.user,
                interaction.channel
            )
            await move_to_closed(interaction)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Create Ticket Button
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Create Ticket",
            emoji="📩",
            custom_id="create_ticket"
        ))
        
        # Add Bot Invite Button
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Add to Server",
            url=BOT_INFO["invite_url"]
        ))
        
        # Add Support Server Button
        self.add_item(discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Support Server",
            url=BOT_INFO["support_server"]
        ))

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Ticket Control Buttons
        self.add_item(discord.ui.Button(
            label="Close",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            custom_id="close_ticket"
        ))
        self.add_item(discord.ui.Button(
            label="Claim",
            style=discord.ButtonStyle.success,
            emoji="✋",
            custom_id="claim_ticket"
        ))
        self.add_item(discord.ui.Button(
            label="Rename",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            custom_id="rename_ticket"
        ))
        self.add_item(discord.ui.Button(
            label="Delete",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            custom_id="delete_ticket"
        ))

bot = TicketBot()

async def log_action(guild, title, description, color, user, channel):
    """Utility function to log ticket actions"""
    settings = bot.ticket_settings.get(str(guild.id))
    if not settings:
        return
    
    log_channel = guild.get_channel(settings['log_channel'])
    if not log_channel:
        return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(
        name="User Information",
        value=f"Name: {user.name}\nID: {user.id}\nMention: {user.mention}"
    )
    embed.add_field(
        name="Channel Information",
        value=f"Name: {channel.name}\nID: {channel.id}\nMention: {channel.mention}"
    )
    embed.set_footer(text=f"Ticket System • {guild.name}")
    
    await log_channel.send(embed=embed)

async def create_ticket(interaction: discord.Interaction):
    """Create a new ticket"""
    guild_id = str(interaction.guild.id)
    settings = bot.ticket_settings.get(guild_id)
    
    if not settings:
        return await interaction.response.send_message(
            "❌ Ticket system is not set up!",
            ephemeral=True
        )
    
    # Create ticket channel
    category = interaction.guild.get_channel(settings['open_category'])
    ticket_channel = await category.create_text_channel(
        f"📩︱ticket・{interaction.user.name}",
        overwrites={
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(settings['support_role']): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
    )
    
    # Send initial ticket message
    embed = discord.Embed(
        title="🎫 New Support Ticket",
        description=(
            f"Welcome {interaction.user.mention}!\n\n"
            "Please describe your issue and wait for a support team member to assist you.\n"
            "Use the buttons below to manage your ticket."
        ),
        color=discord.Color.blue()
    )
    
    await ticket_channel.send(
        content=f"{interaction.user.mention} | <@&{settings['support_role']}>",
        embed=embed,
        view=TicketControls()
    )
    
    # Log ticket creation
    await log_action(
        interaction.guild,
        "Ticket Created",
        f"Created by: {interaction.user.mention}",
        discord.Color.green(),
        interaction.user,
        ticket_channel
    )
    
    await interaction.response.send_message(
        f"✅ Your ticket has been created: {ticket_channel.mention}",
        ephemeral=True
    )

async def move_to_closed(interaction: discord.Interaction):
    """Move ticket to closed category"""
    guild_id = str(interaction.guild.id)
    settings = bot.ticket_settings.get(guild_id)
    
    if not settings:
        return
    
    closed_category = interaction.guild.get_channel(settings['close_category'])
    await interaction.channel.edit(category=closed_category)
    await interaction.channel.set_permissions(
        interaction.guild.default_role,
        read_messages=False
    )
    
    embed = discord.Embed(
        title="Ticket Closed",
        description=(
            "This ticket has been closed. Staff members can still view its contents.\n"
            "Use `/delete` to permanently delete this ticket."
        ),
        color=discord.Color.red()
    )
    await interaction.channel.send(embed=embed)

@bot.tree.command(name='setup', description='Set up the ticket system')
@app_commands.describe(
    support_role="Support team role",
    ticket_channel="Channel for ticket creation",
    open_category="Category for open tickets",
    close_category="Category for closed tickets",
    log_channel="Channel for ticket logs"
)
async def setup(
    interaction: discord.Interaction,
    support_role: discord.Role,
    ticket_channel: discord.TextChannel,
    open_category: discord.CategoryChannel,
    close_category: discord.CategoryChannel,
    log_channel: discord.TextChannel
):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "❌ You need Administrator permission to set up the ticket system!",
            ephemeral=True
        )
    
    # Save settings
    guild_id = str(interaction.guild.id)
    bot.ticket_settings[guild_id] = {
        'support_role': support_role.id,
        'ticket_channel': ticket_channel.id,
        'open_category': open_category.id,
        'close_category': close_category.id,
        'log_channel': log_channel.id
    }
    
    # Create ticket message
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=(
            "Need help? Click the button below to create a support ticket.\n"
            "Our team will assist you as soon as possible."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Bot by {BOT_INFO['creator']['name']}")
    
    await ticket_channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message(
        "✅ Ticket system has been set up successfully!",
        ephemeral=True
    )

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="tickets • /help"
    )
    await bot.change_presence(activity=activity)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    
    if interaction.custom_id == "create_ticket":
        await create_ticket(interaction)
    
    elif interaction.custom_id == "close_ticket":
        await interaction.response.send_modal(
            TicketModal("Close Ticket", "reason")
        )
    
    elif interaction.custom_id == "claim_ticket":
        await log_action(
            interaction.guild,
            "Ticket Claimed",
            f"Claimed by: {interaction.user.mention}",
            discord.Color.gold(),
            interaction.user,
            interaction.channel
        )
        await interaction.response.send_message(
            f"✅ Ticket claimed by {interaction.user.mention}"
        )
    
    elif interaction.custom_id == "rename_ticket":
        await interaction.response.send_modal(
            TicketModal("Rename Ticket", "rename")
        )
    
    elif interaction.custom_id == "delete_ticket":
        await log_action(
            interaction.guild,
            "Ticket Deleted",
            f"Deleted by: {interaction.user.mention}",
            discord.Color.dark_red(),
            interaction.user,
            interaction.channel
        )
        await interaction.response.send_message(
            "🗑️ Deleting ticket in 5 seconds..."
        )
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.tree.command(name='about', description='About the bot and its creator')
async def about(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"About {BOT_INFO['name']}",
        description="A powerful ticket management system for Discord servers",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.utcnow()
    )
    
    creator = BOT_INFO['creator']
    embed.add_field(
        name="👨‍💻 Creator",
        value=f"Name: {creator['name']}\nDiscord: <@{creator['discord_id']}>",
        inline=False
    )
    
    embed.add_field(
        name="🔗 Links",
        value=f"[GitHub]({creator['github']}) | [Website]({creator['website']})",
        inline=False
    )
    
    uptime = time.time() - bot.start_time
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed.add_field(
        name="⚙️ Bot Stats",
        value=f"Servers: {len(bot.guilds)}\nUptime: {hours}h {minutes}m {seconds}s",
        inline=False
    )
    
    embed.set_footer(text="Thanks for using our bot! ❤️")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: `{round(bot.latency * 1000)}ms`",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Run the bot
bot.run(TOKEN)
