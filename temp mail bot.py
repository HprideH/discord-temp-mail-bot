import discord
from discord import app_commands
from discord.ext import commands
import requests
import random
import string
import json
import os

DISCORD_BOT_TOKEN = "" #discord bot token you can get one from https://discord.com/developers/applications

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Path to the user storage file
USERS_FILE = "users.json"

# Load user data
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as file:
        user_data = json.load(file)
else:
    user_data = {}

# Save user data
def save_user_data():
    with open(USERS_FILE, "w") as file:
        json.dump(user_data, file, indent=4)

# Generate a random email
def generate_email():
    words = ["alpha", "mango", "storm", "light", "pixel", "void", "zen", "echo"]
    name = random.choice(words) + "-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return name + "@vwh.sh"

# Get all emails of a user
def get_user_emails(user_id):
    return user_data.get(str(user_id), [])

# Add new email to user
def add_new_email(user_id):
    email = generate_email()
    user_id_str = str(user_id)
    if user_id_str not in user_data:
        user_data[user_id_str] = []
    user_data[user_id_str].append(email)
    save_user_data()
    return email

# Get the most recent email of a user
def get_latest_email(user_id):
    emails = get_user_emails(user_id)
    return emails[-1] if emails else None

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user}")

# /newemail
@tree.command(name="newemail", description="Generate a new temporary email.")
async def new_email(interaction: discord.Interaction):
    email = add_new_email(interaction.user.id)
    await interaction.response.send_message(f"📧 New email created: `{email}`")

# /myemail
@tree.command(name="myemail", description="List all your generated emails.")
async def my_email(interaction: discord.Interaction):
    emails = get_user_emails(interaction.user.id)
    if not emails:
        await interaction.response.send_message("📭 You haven't generated any emails yet. Use `/newemail` to get started.")
        return

    msg = "**📧 Your emails:**\n" + "\n".join([f"- `{e}`" for e in emails])
    await interaction.response.send_message(msg)

# /inbox
@tree.command(name="inbox", description="Check inbox for your latest email.")
async def inbox(interaction: discord.Interaction):
    email = get_latest_email(interaction.user.id)
    if not email:
        await interaction.response.send_message("⚠️ You have no email address. Use `/newemail` first.")
        return

    url = f"https://email.vwh.sh/api/email/{email}"
    response = requests.get(url)
    data = response.json()

    if not data:
        await interaction.response.send_message(f"📭 No emails found for `{email}`.")
        return

    message = f"**📬 Inbox for `{email}`:**\n"
    for email_data in data[:5]:
        message += (
            f"**ID:** `{email_data['id']}`\n"
            f"**From:** {email_data['fromAddress']}\n"
            f"**Subject:** {email_data['subject']}\n"
            f"---\n"
        )

    await interaction.response.send_message(message)

# /view
@tree.command(name="view", description="View a message by its ID.")
@app_commands.describe(message_id="The ID of the message you want to view.")
async def view(interaction: discord.Interaction, message_id: str = None):
    if not message_id:
        await interaction.response.send_message("❌ You must provide a message ID to view.")
        return

    url = f"https://email.vwh.sh/api/inbox/{message_id}"
    response = requests.get(url)

    if response.status_code != 200:
        await interaction.response.send_message("❌ Message not found.")
        return

    data = response.json()
    user_emails = get_user_emails(interaction.user.id)

    if data["toAddress"].lower() not in [e.lower() for e in user_emails]:
        await interaction.response.send_message("🚫 This message doesn't belong to any of your emails.")
        return

    message = (
        f"**📄 Message Details:**\n"
        f"**From:** {data['fromAddress']}\n"
        f"**To:** {data['toAddress']}\n"
        f"**Subject:** {data['subject']}\n"
        f"**Content:**\n{data['textContent'] or 'No text content.'}"
    )

    await interaction.response.send_message(message)

# /delete
@tree.command(name="delete", description="Delete a message by its ID.")
@app_commands.describe(message_id="The ID of the message to delete.")
async def delete(interaction: discord.Interaction, message_id: str):
    check_url = f"https://email.vwh.sh/api/inbox/{message_id}"
    check_response = requests.get(check_url)

    if check_response.status_code != 200:
        await interaction.response.send_message("❌ Message not found.")
        return

    data = check_response.json()
    user_emails = get_user_emails(interaction.user.id)

    if data["toAddress"].lower() not in [e.lower() for e in user_emails]:
        await interaction.response.send_message("🚫 You can't delete this message. It doesn't belong to your email.")
        return

    delete_url = f"https://email.vwh.sh/api/delete/{message_id}"
    delete_response = requests.get(delete_url)

    if delete_response.status_code == 200 and delete_response.text == "true":
        await interaction.response.send_message("🗑️ Message deleted successfully.")
    else:
        await interaction.response.send_message("❌ Failed to delete the message.")

bot.run(DISCORD_BOT_TOKEN)
