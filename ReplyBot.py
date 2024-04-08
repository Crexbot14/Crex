import os
import discord
from discord.ext import commands
from discord_slash import SlashCommand
import asyncpg
import asyncio
from discord import Embed
from discord.ext import tasks
from discord import Intents
import datetime
from datetime import datetime
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
from aiohttp.client_exceptions import ClientOSError
from pymongo import MongoClient
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle
from discord_slash.context import ComponentContext
user_data_store = {}  # Add this line at the top of your file
intents = Intents.default()
intents.members = True
TOKEN = 'token'
client = MongoClient('mongodb+srv://AutoEconomy:0921229784653120@autoeconomy.uf1wywq.mongodb.net/')
db = client["AutoEconomy"]
collection = db["AutoChat"]

class MyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = client
        self.db = db
        self.collection = collection

from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.model import ButtonStyle

bot = MyBot(command_prefix="!")
slash = SlashCommand(bot, sync_commands=True)

@slash.slash(
    name="toggle_autoreply",
    description="Toggle the auto-reply feature on or off."
)
async def toggle_autoreply(ctx: SlashContext):
    user_id = str(ctx.author.id)
    user_data = bot.db['AutoData'].find_one({"_id": user_id})

    if not user_data:
        await ctx.send(content="No user data found.")
        return

    # Create a button for each account the user has
    account_count = len(user_data.get('configs', []))
    buttons = [create_button(style=ButtonStyle.green, label=f"Account {i+1}") for i in range(account_count)]

    # Split the buttons into groups of 5
    button_groups = [buttons[i:i + 5] for i in range(0, len(buttons), 5)]

    # Create an action row for each group of buttons
    action_rows = [create_actionrow(*group) for group in button_groups]

    embed = Embed(title="Auto-Reply Feature", description="Select an account to toggle auto-reply.")
    await ctx.send(embed=embed, components=action_rows)


@bot.event
async def on_component(ctx: ComponentContext):
    user_id = str(ctx.author.id)
    user_data = bot.db['AutoData'].find_one({"_id": user_id})

    if not user_data:
        await ctx.send(content="No user data found.")
        return

    if "Account" in ctx.component['label']:
        account_index = int(ctx.component['label'].split(" ")[1]) - 1
        user_data_store[user_id] = {'account_index': account_index}  # Store the account index

        buttons = [
            create_button(style=ButtonStyle.green, label="Run"),
            create_button(style=ButtonStyle.red, label="Stop"),
            create_button(style=ButtonStyle.grey, label="Cancel")
        ]
        action_row = create_actionrow(*buttons)

        embed = Embed(title=f"Auto-Reply Feature for Account {account_index+1}", description="Do you want to run or stop the auto-reply feature?")
        await ctx.send(embed=embed, components=[action_row])
    elif ctx.component['label'] == "Cancel":
        await ctx.send(content="Operation cancelled.")
        return
    else:
        new_status = True if ctx.component['label'] == "Run" else False

        user_id = str(ctx.author.id)
        account_index = user_data_store[user_id]['account_index']  # Get the stored account index

        if account_index is None:
            await ctx.send(content="No account selected.")
            return

        account = user_data['configs'][account_index]

        # Update the 'is_autoreply_running' field of the specific account
        user_data['configs'][account_index]['is_autoreply_running'] = new_status
        bot.db['AutoData'].update_one({"_id": user_id}, {"$set": {"configs": user_data['configs']}})

        await ctx.send(content=f"Auto reply has been {'started' if new_status else 'stopped'}.")

class AutoReplyBotClient(discord.Client):
    def __init__(self, user_id, db, account_index):
        super().__init__()
        self.user_id = user_id
        self.db = db
        self.account_index = account_index
        self.replied_users = {}

    async def start(self):
        print("Starting AutoBotClient...")
        user_data = self.db['AutoData'].find_one({"_id": self.user_id})
        if user_data and 'configs' in user_data:
            config = user_data['configs'][self.account_index]
            if config and config['is_autoreply_running']:
                try:
                    await asyncio.sleep(5)  # Wait for 1 second before starting the bot
                    await super().start(config['token'], bot=False)
                except asyncio.CancelledError:
                    print("Bot task was cancelled, ignoring...")
                except Exception as e:
                    print(f"Bot stopped with error: {e}")

    async def on_ready(self):
        print(f"Bot for user {self.user_id} is ready and working.")
        
    async def on_message(self, message):
        if not message.guild is None or message.author == self.user:
            return

        print(f"Received message from {message.author} with ID {message.author.id}")
        if str(message.author.id) != self.user_id:

            try:
                # rest of your code...
                user_data = self.db['AutoData'].find_one({"_id": self.user_id})

                if not user_data:
                    print("No user data found.")
                    return

                if not user_data['configs'][self.account_index]['is_autoreply_running']:
                    print("Auto reply is not running for this user.")
                    return

                self.db['AutoData'].update_one({"_id": self.user_id}, {"$inc": {"total_messages": 1}})
                print("Incremented total_messages for the user.")

                auto_reply_content = user_data['configs'][self.account_index]['auto_reply_content']
                if not auto_reply_content:
                    print("No auto reply content found.")
                    return

                submessage = user_data['configs'][self.account_index]['submessage']
                submessage_reply_limit = user_data['configs'][self.account_index].get('submessage_reply_limit', '0')
                if submessage_reply_limit == '':
                    submessage_reply_limit = '0'  # default value
                submessage_reply_limit = int(submessage_reply_limit)

                if message.author.id not in self.replied_users:
                    print("Sending auto reply content...")
                    await message.reply(auto_reply_content)
                    self.replied_users[message.author.id] = 0
                elif self.replied_users.get(message.author.id, 0) < submessage_reply_limit and submessage:
                    print("Sending submessage...")
                    await message.reply(submessage)
                    self.replied_users[message.author.id] = self.replied_users.get(message.author.id, 0) + 1

            except Exception as e:
                print(f"An error occurred in AutoReplyBotClient for user {self.user_id}: {e}")

auto_reply_clients = {}
auto_reply_tasks = {}

@tasks.loop(seconds=10)
async def auto_reply_task():
    global user_running_states
    for user_id, states in user_running_states.items():
        print(f"Checking auto reply task for user {user_id}...")
        if states.get('autoreply'):
            user_data = bot.db['AutoData'].find_one({"_id": user_id})
            if user_data and 'configs' in user_data:
                for account_index, config in enumerate(user_data['configs']):
                    if config['is_running']:
                        if (user_id, account_index) not in auto_reply_clients:
                            print("Starting new AutoReplyBotClient for user...")
                            auto_reply_client = AutoReplyBotClient(user_id, bot.db, account_index)
                            task = bot.loop.create_task(auto_reply_client.start())
                            auto_reply_clients[(user_id, account_index)] = auto_reply_client
                            auto_reply_tasks[(user_id, account_index)] = task
        elif user_id in auto_reply_clients:
            print("Closing AutoReplyBotClient for user...")
            for account_index in auto_reply_clients[user_id]:
                await auto_reply_clients[(user_id, account_index)].close()
                del auto_reply_clients[(user_id, account_index)]

            print("Cancelling task for AutoReplyBotClient...")
            for account_index in auto_reply_tasks[user_id]:
                auto_reply_tasks[(user_id, account_index)].cancel()
                del auto_reply_tasks[(user_id, account_index)]

@bot.event
async def on_ready():
    if bot.user is None:
        print("Bot is not connected to Discord.")
    else:
        print(f'We have logged in as {bot.user}')

    try:
        # Load the user_running_states dictionary from the MongoDB database
        MONGO = MongoClient('mongodb+srv://AutoEconomy:0921229784653120@autoeconomy.uf1wywq.mongodb.net/')
        db = MONGO['AutoEconomy']
        user_states = db['AutoData'].find()
        for state in user_states:
            user_id = str(state['_id'])
            if 'configs' in state:
                for account_index, config in enumerate(state['configs']):
                    if config['is_autoreply_running']:
                        print(f"Starting auto-reply bot for user {user_id} on account {account_index}")
                        if (user_id, account_index) not in auto_reply_clients:
                            print("Starting new AutoReplyBotClient for user...")
                            auto_reply_client = AutoReplyBotClient(user_id, db, account_index)
                            task = bot.loop.create_task(auto_reply_client.start())
                            auto_reply_clients[(user_id, account_index)] = auto_reply_client
                            auto_reply_tasks[(user_id, account_index)] = task
                        else:
                            print(f"AutoReplyBotClient already running for user {user_id} on account {account_index}")

    except Exception as e:
        print(f"Error fetching user states: {e}")
        return

    print("Finished processing all users.")

bot.run(TOKEN)
