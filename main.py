import logging,json,os
from telegram import Update, ChatMember
from telegram.constants import ParseMode
from telegram import KeyboardButton, ReplyKeyboardMarkup,ReplyKeyboardRemove
from collections import defaultdict
from telegram.ext import (filters, ApplicationBuilder, ContextTypes, CommandHandler, ConversationHandler,
                          MessageHandler, ChatMemberHandler)
from UserStatus import UserStatus
from config import BOT_TOKEN, ADMIN_ID
from config import NOTIFY_CHANNEL as nf
from config import Loctaion_get as locat
import db_connection

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # Set the logging level to: (DEBUG, INFO, WARNING, ERROR, CRITICAL)
)

"""
####### List of commands #######
---> start - 🤖 starts the bot
---> chat - 💬 start searching for a partner
---> exit - 🔚 exit from the chat
---> newchat - ⏭ exit from the chat and open a new one
---> stats - 📊 show bot statistics (only for admin)
---> msg - use= /msg <user id> <message> bot will send that particular msg to that user (only for admin)
---> broad -  use= /broad <message> that particular msg sent to alll user ids avilable in json file (only for admin)
---> users - show all list of user ids avilable in list (only for admin)
"""




USER_IDS_FILE = 'user_ids.json'  # Path to the JSON file where user IDs will be stored

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Welcomes the user with their details, sends a message with an image caption,
    and sends user details to a specified channel. Additionally, saves user IDs to a JSON file.
    
    :param update: Update received from the user
    :param context: Context of the bot
    :return: Status USER_ACTION
    """
    # Extract user details
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Create a personalized welcome message with HTML formatting
    welcome_message = f"""
    <b>Hello</b>

    <b>User ID</b>: <code>{user_id}</code>

    <b>Username</b>: @{username if username else 'N/A'}

    <b>Welcome to the Meet-strangers! 🤖</b>
    <b>Here, you can chat with anyone randomly and anonymously. 💬</b>
    <b>➡️ To start searching for a partner, type <b>/chat</b>. 🔍</b>
    <b>➡️ Want to chat with someone nearby? Use <b>/fnear</b> to find partners close to you. 🌍</b>
    <b>For more information about how to use the bot, type</b> <b>/help</b>. 
    <b>Enjoy your experience! 😊</b>
    """

    # Send the welcome message along with the image (ensure the image link is valid)
    image_url = "https://drive.google.com/uc?id=1KBGv6683FnQC96oSfKCYOv3lt3WFopwI"  # Replace with actual image URL
    await context.bot.send_photo(chat_id=update.effective_chat.id,
                                 photo=image_url,
                                 caption=welcome_message,
                                 parse_mode=ParseMode.HTML)

    # Insert the user into the database if not already present
    db_connection.insert_user(user_id)  # Assuming `insert_user` is a function that inserts user into DB

    # Save the user ID to the JSON file
    save_user_id_to_json(user_id)

    # Send user info to a specific channel
    channel_id = nf # Replace with your actual channel ID
    channel_message = f"""
    New user started the bot! 🤖
    User: @{username if username else 'N/A'}
    User ID: <code>{user_id}</code>
    """

    # Send the user details to the channel
    await context.bot.send_message(chat_id=channel_id, text=channel_message,parse_mode=ParseMode.HTML)

    return USER_ACTION

# Define the help message with commands and descriptions
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


HELP_MESSAGE = """
<b>####### List of Commands #######</b>

➡️ <b>/start</b> - 🤖 Start the bot  

➡️ <b>/chat</b> - 💬 Start searching for a random partner 

➡️ <b>/end</b> - 💬 to end searching Chats 

➡️ <b>/exit</b> - 🔚 Exit from the current chat  

➡️ <b>/newchat</b> - ⏭ Exit from the current chat and start a new one 

➡️ <b>/fnear</b> - 💬 Start searching nearby persons.  

Use these commands to interact with the bot and manage your experience. 🤖
"""

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends the help message to the user when they request it using /help.
    """
    # Create a button that links to the developer's Telegram profile
    developer_button = InlineKeyboardButton(
        text="Developer 👨‍💻", 
        url="https://t.me/nerd_guy"  # Developer's username or link to their profile
    )

    # Create a keyboard with the button
    keyboard = InlineKeyboardMarkup([[developer_button]])

    # Send the help message with the developer button
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode="HTML",  # Ensure HTML is properly parsed
        reply_markup=keyboard  # Attach the keyboard with the button
    )




def save_user_id_to_json(user_id: int) -> None:
    """
    Saves the user ID to the JSON file.
    If the file does not exist, it creates it. If the file exists, appends the user ID.
    
    :param user_id: The user ID to save
    """
    # Check if the JSON file already exists
    if os.path.exists(USER_IDS_FILE):
        with open(USER_IDS_FILE, 'r') as file:
            data = json.load(file)
    else:
        data = []

    # Append the user ID to the list if not already in the file
    if user_id not in data:
        data.append(user_id)

    # Save the updated list back to the file
    with open(USER_IDS_FILE, 'w') as file:
        json.dump(data, file, indent=4)

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends a list of all user IDs along with usernames to the admin.
    :param update: Update object
    :param context: Context of the bot
    :return: None
    """
    # Check if the user who invoked the command is in the list of admins
    if update.effective_chat.id not in ADMIN_ID:
        await update.message.reply_text("🚫 You don't have permission to use this command.")
        return

    # Read the user IDs from the JSON file
    if os.path.exists(USER_IDS_FILE):
        with open(USER_IDS_FILE, 'r') as file:
            user_ids = json.load(file)
    else:
        user_ids = []

    # Check if there are any users in the file
    if user_ids:
        total_members = len(user_ids)
        message = f"👥 Total members: {total_members}\n\n"
        
        for idx, user_id in enumerate(user_ids, start=1):
            try:
                # Try to get the user info, including the username
                user_info = await context.bot.get_chat(user_id)
                username = user_info.username if user_info.username else "😕 No username"
                message += f"📝{idx}) <code>{user_id}</code> -  @{username}\n\n"
            except Exception as e:
                # In case of error (e.g., user info not available), provide a fallback message
                message += f"📝{idx}) {user_id} - 😕Username not found\n"
        
    else:
        message = "❌ No users found."

    # Send the list of user IDs and usernames to all admins
    for admin_id in ADMIN_ID:
        await context.bot.send_message(chat_id=admin_id, text=message, parse_mode=ParseMode.HTML)




# Temporary data storage (This should ideally be stored in a database)
user_location_data = {}


async def handle_location_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /fnear command by asking the user to share their location and removes the button after sharing.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id

    # Create a location-sharing button
    location_button = KeyboardButton("Share my location", request_location=True)
    custom_keyboard = [[location_button]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)

    # Send message asking for location with button
    await update.message.reply_text(
        "Please share your location to find nearby users. 🌍",
        reply_markup=reply_markup
    )

    # Now let's handle the location once it's received
    async def handle_shared_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Remove the keyboard after the location is shared
        await update.message.reply_text(
            "Thank you for sharing your location!",
            reply_markup=ReplyKeyboardRemove() 
        )

        # Further processing of the location can go here
        user_location = update.message.location

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Define the action to do based on the message received and the actual status of the user
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    # Check if the user is in chat
    if db_connection.get_user_status(user_id=user_id) == UserStatus.COUPLED:
        # User is in chat, retrieve the other user
        other_user_id = db_connection.get_partner_id(user_id)
        if other_user_id is None:
            return await handle_not_in_chat(update, context)
        else:
            return await in_chat(update, other_user_id)
    else:
        return await handle_not_in_chat(update, context)


async def handle_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /end command, which stops the user's search for a partner.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    # Get the current user ID
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    if current_user_status == UserStatus.IN_SEARCH:
        # Stop the search for a partner
        db_connection.set_user_status(user_id=current_user_id, new_status=UserStatus.IDLE)
        await context.bot.send_message(chat_id=current_user_id,
                                       text="🔴 Your search has been stopped.")
    elif current_user_status == UserStatus.COUPLED:
        # If the user is already paired with a partner, inform them that they need to exit the chat
        await context.bot.send_message(chat_id=current_user_id,
                                       text="🤖 You are currently in a chat. Please type /exit to end the chat first.")
    else:
        # If the user isn't in search or a chat, inform them they are idle
        await context.bot.send_message(chat_id=current_user_id,
                                       text="🔴 You are not in search or in a chat. Use /chat to start searching for a partner.")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /chat command, starting the search for a partner if the user is not already in search.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    if current_user_status == UserStatus.PARTNER_LEFT:
        # First, check if the user has been left by their partner
        db_connection.set_user_status(user_id=current_user_id, new_status=UserStatus.IDLE)
        return await start_search(update, context)
    elif current_user_status == UserStatus.IN_SEARCH:
        # Warn the user if they are already in search
        return await handle_already_in_search(update, context)
    elif current_user_status == UserStatus.COUPLED:
        # Double-check if the user is in chat
        other_user = db_connection.get_partner_id(current_user_id)
        if other_user is not None:
            # If the user has been paired, warn them to exit the chat
            await context.bot.send_message(chat_id=current_user_id,
                                           text="🤖 You are already in a chat, type /exit to exit from the chat.")
            return None
        else:
            return await start_search(update, context)
    elif current_user_status == UserStatus.IDLE:
        # The user is in IDLE status, so simply start the search
        return await start_search(update, context)


async def handle_not_in_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the case when the user is not in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user_id = update.effective_user.id
    current_user_status = db_connection.get_user_status(user_id=current_user_id)

    if current_user_status in [UserStatus.IDLE, UserStatus.PARTNER_LEFT]:
        await context.bot.send_message(chat_id=current_user_id,
                                       text="🤖 You are not in a chat, type /chat to start searching for a partner.")
        return
    elif current_user_status == UserStatus.IN_SEARCH:
        await context.bot.send_message(chat_id=current_user_id,
                                       text="🤖 Message not delivered, you are still in search!")
        return



async def handle_already_in_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the case when the user is already in search
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 You are already in search!")
    return



# Modify the start_search function to check for a nickname
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts the search for a partner, setting the user status to in_search and adding them to the list of users.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user_id = update.effective_chat.id

    # Set the user status to in_search
    db_connection.set_user_status(user_id=current_user_id, new_status=UserStatus.IN_SEARCH)
    await context.bot.send_message(chat_id=current_user_id, text="🤖 Searching for a partner...")

    # Search for a partner
    other_user_id = db_connection.couple(current_user_id=current_user_id)
    
    # If a partner is found, notify both the users
    if other_user_id is not None:
        # Send a generic message without nickname or first name
        await context.bot.send_message(chat_id=current_user_id, text="🤖 You've been paired with a new partner! 🎉\n\nPlease keep the conversation friendly and respectful! 😊 Let’s make this chat enjoyable for both of you! 💬\n\nUse /exit to end the chat"),
        await context.bot.send_message(chat_id=other_user_id, text="🤖 You've been paired with a new partner! 🎉\n\nPlease keep the conversation friendly and respectful! 😊 Let’s make this chat enjoyable for both of you! 💬\n\nUse /exit to end the chat")

        
    return 


async def handle_exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /exit command, exiting from the chat if the user is in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    await exit_chat(update, context)
    return


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /stats command, showing the bot statistics if the user is the admin
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    if user_id in ADMIN_ID:
        total_users_number, paired_users_number = db_connection.retrieve_users_number()
        
        # Prepare the summary message with emojis
        stats_message = (
            "👨‍💻 Welcome to the admin panel\n\n"
            f"🔗 Number of paired users: {paired_users_number}\n"
            f"👥 Number of active users: {total_users_number}\n"
        )
        
        # Send the summary message in one go
        await context.bot.send_message(chat_id=user_id, text=stats_message)
    else:
        logging.warning(f"User {user_id} tried to access the admin panel")
    return


async def exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Exits from the chat, sending a message to the other user and updating the status of both the users
    :param update: update received from the user
    :param context: context of the bot
    :return: a boolean value, True if the user was in chat (and so exited), False otherwise
    """
    current_user = update.effective_user.id
    if db_connection.get_user_status(user_id=current_user) != UserStatus.COUPLED:
        await context.bot.send_message(chat_id=current_user, text="🤖 You are not in a chat!")
        return

    other_user = db_connection.get_partner_id(current_user)
    if other_user is None:
        return

    # Perform the uncoupling
    db_connection.uncouple(user_id=current_user)

    await context.bot.send_message(chat_id=current_user, text="🤖 Ending chat...")
    await context.bot.send_message(chat_id=other_user,
                                   text="🤖 Your partner has left the chat, type /chat to start searching for a new "
                                        "partner.")
    await update.message.reply_text("🤖 You have left the chat.")

    return


async def exit_then_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /newchat command, exiting from the chat and starting a new search if the user is in chat
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    current_user = update.effective_user.id
    if db_connection.get_user_status(user_id=current_user) == UserStatus.IN_SEARCH:
        return await handle_already_in_search(update, context)
    # If exit_chat returns True, then the user was in chat and successfully exited
    await exit_chat(update, context)
    # Either the user was in chat or not, start the search
    return await start_search(update, context)


async def in_chat(update: Update, other_user_id) -> None:
    """
    Handles the case when the user is in chat
    :param update: update received from the user
    :param other_user_id: id of the other user in chat
    :return: None
    """
    # Check if the message is a reply to another message
    if update.message.reply_to_message is not None:
        # If the message is a reply to another message, check if the message is a reply to a message sent by the user
        # himself or by the other user
        if update.message.reply_to_message.from_user.id == update.effective_user.id:
            # The message is a reply to a message sent by the user himself, so send the message to the replyed+1
            # message (the one copyed by the bot has id+1)
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id,
                                                     protect_content=True,
                                                     reply_to_message_id=update.message.reply_to_message.message_id + 1)

        # Else, the replied message could be sent either by the other user, another previous user or the bot
        # Since the bot sends non-protected-content messages, use this as discriminator
        elif update.message.reply_to_message.has_protected_content is None:
            # Message is sent by the bot, forward message without replying
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id,
                                                     protect_content=True)

        else:
            # The message is a reply to a message sent by another user, forward the message replyed to the replyed -1
            # message. Other user will see the message as a reply to the message he/she sent, only if he was the sender
            await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id,
                                                     protect_content=True,
                                                     reply_to_message_id=update.message.reply_to_message.message_id - 1)
    else:
        # The message is not a reply to another message, so send the message without replying
        await update.effective_chat.copy_message(chat_id=other_user_id, message_id=update.message.message_id,
                                                 protect_content=True)

    return


def is_bot_blocked_by_user(update: Update) -> bool:
    new_member_status = update.my_chat_member.new_chat_member.status
    old_member_status = update.my_chat_member.old_chat_member.status
    if new_member_status == ChatMember.BANNED and old_member_status == ChatMember.MEMBER:
        return True
    else:
        return False


async def blocked_bot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_bot_blocked_by_user(update):
        # Check if user was in chat
        user_id = update.effective_user.id
        user_status = db_connection.get_user_status(user_id=user_id)
        if user_status == UserStatus.COUPLED:
            other_user = db_connection.get_partner_id(user_id)
            db_connection.uncouple(user_id=user_id)
            await context.bot.send_message(chat_id=other_user, text="🤖 Your partner has left the chat, type /chat to "
                                                                    "start searching for a new partner.")
        db_connection.remove_user(user_id=user_id)
        return ConversationHandler.END
    else:
        
        return USER_ACTION

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Allows the admin to send a message to any user by using the /msg command.
    Admin should provide a user_id and a message as arguments.
    """
    # Check if the sender is the admin
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Extract the command arguments
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("Usage: /msg <user_id> <message>\nPlease provide a user ID and a message.")
        return

    # Extract the user ID and message
    user_id = args[0]
    message = ' '.join(args[1:])

    try:
        # Check if the user ID is a valid integer
        user_id = int(user_id)

        # Send the message to the user with the provided user ID
        user = await context.bot.get_chat(user_id)
        await context.bot.send_message(chat_id=user_id, text=message)

        # Confirm to the admin that the message was sent
        await update.message.reply_text(f"Message sent to user ID {user_id}.")
    except ValueError:
        # If the user ID is not an integer
        await update.message.reply_text("Invalid user ID. Please provide a valid integer user ID.")
    except Exception as e:
        # Handle other exceptions, such as the user ID not being found
        await update.message.reply_text(f"Failed to send message. Error: {str(e)}")


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A general error handler to catch unexpected errors.
    """
    # Log the error to console
    print(f"Error occurred: {context.error}")

    # Send a friendly error message to the user
    await update.message.reply_text("An error occurred while processing your request. Please try again later.")

from telegram.error import BadRequest, TelegramError
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Allows the admin to send a broadcast message to all users with better error handling.
    """
    # Check if the sender is the admin
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Extract the message to broadcast
    args = context.args

    if len(args) < 1:
        await update.message.reply_text("Usage: /broad <message>\nPlease provide a message to broadcast.")
        return

    message = ' '.join(args)

    # Read the list of user IDs from the JSON file
    if os.path.exists(USER_IDS_FILE):
        with open(USER_IDS_FILE, 'r') as file:
            user_ids = json.load(file)
    else:
        user_ids = []

    # Initialize counters for success, failure, and skipped (e.g., blocked users)
    successful = 0
    failed = 0
    skipped = 0
    failed_user_ids = []  # List to track user IDs that failed (e.g., blocked)

    # Try to send the message to all users
    for user_id in user_ids:
        try:
            # Attempt to send the message
            await context.bot.send_message(chat_id=user_id, text=message)
            successful += 1  # Increment the success counter
        except BadRequest as e:
            # If the user has blocked the bot, we skip them
            if 'blocked' in str(e).lower():
                skipped += 1
                failed_user_ids.append(user_id)  # Track the user that has blocked the bot
            else:
                failed += 1  # For other types of errors, count as failed
            print(f"Error sending message to user {user_id}: {e}")
        except TelegramError as e:
            # General TelegramError, for things like rate limiting, etc.
            failed += 1
            print(f"Error sending message to user {user_id}: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            failed += 1
            print(f"Unexpected error with user {user_id}: {e}")

    # Notify the admin about the broadcast completion
    summary_message = (
        f"📢 **Broadcast completed!**\n\n"
        f"👥 **Total users:** {len(user_ids)}\n"
        f"✅ **Message sent successfully to:** {successful} users\n"
        f"❌ **Failed to send to:** {failed} users\n"
        f"⛔ **Skipped (blocked users):** {skipped} users\n\n"
        f"⚠️ **Failed user IDs (Blocked/Invalid):** {', '.join(map(str, failed_user_ids)) if failed_user_ids else 'None'}"
    )


    await update.message.reply_text(summary_message,parse_mode=ParseMode.MARKDOWN)


# Assuming user_location_data is a dictionary where user ID is the key and location is the value
user_location_data = defaultdict(dict)

# Define states for the ConversationHandler
USER_ACTION = range(1)

async def handle_location_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /fnear command by asking the user to share their location.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id

    # Create a location-sharing button
    location_button = KeyboardButton("Share my location", request_location=True)
    custom_keyboard = [[location_button]]
    reply_markup = ReplyKeyboardMarkup(custom_keyboard, one_time_keyboard=True)

    # Send message asking for location with button
    await update.message.reply_text(
        "Please share your location to find nearby users. 🌍",
        reply_markup=reply_markup
    )

# This handler will remove the keyboard once a location is shared and process the location
async def handle_shared_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the location shared by the user and sends it to the specified channel.
    :param update: update received from the user
    :param context: context of the bot
    :return: None
    """
    user_id = update.effective_user.id
    location = update.message.location  # This is the location shared by the user

    # Store the user's location (in this case, it's just a temporary storage)
    user_location_data[user_id] = location

    # Ensure the channel ID is correct
    channel_id = locat# Replace with your actual channel ID (e.g., -1001234567890)

    # Prepare the message caption with location information
    location_caption = f"New location shared! 🗺️\n" \
                       f"User ID: <code>{user_id}</code>\n" \
                       f"Username: @{update.effective_user.username if update.effective_user.username else 'N/A'}\n" \
                       f"Latitude: {location.latitude}\n" \
                       f"Longitude: {location.longitude}"

    try:
        # Send the location to the channel (without the caption)
        await context.bot.send_location(
            chat_id=channel_id, 
            latitude=location.latitude, 
            longitude=location.longitude
        )

        # Now send the location details (the caption) in a separate text message
        await context.bot.send_message(
            chat_id=channel_id, 
            text=location_caption,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        # Handle any errors, such as the bot not having permission to send messages
        await update.message.reply_text(
            "There was an issue sharing your location. Please try again later."
        )
        print(f"Error sharing location: {e}")

    # Remove the keyboard after the location is shared
    await update.message.reply_text(
        "Thanks for your location. You can now use /chat to find nearby users.",
        reply_markup=ReplyKeyboardRemove()  # This removes the keyboard
    )

# Define the ConversationHandler and add the new handler for shared locations
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],  # Assuming you have a start function defined
    states={
        USER_ACTION: [
            ChatMemberHandler(blocked_bot_handler),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,  # Handle non-command text messages
                handle_message
            ),
            CommandHandler("exit", handle_exit_chat),
            CommandHandler("chat", handle_chat),
            CommandHandler("newchat", exit_then_chat),
            CommandHandler("end", handle_end),
            CommandHandler("msg", handle_msg),
            CommandHandler("users", users),
            CommandHandler("help", help_command),
            CommandHandler("broad", handle_broadcast),
            CommandHandler("fnear", handle_location_request),
            CommandHandler("stats", handle_stats),
            MessageHandler(filters.LOCATION, handle_shared_location),  # Handle shared locations here
        ]
    },
    fallbacks=[MessageHandler(filters.TEXT, handle_not_in_chat)]
)

application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add the conversation handler to the application
application.add_handler(conv_handler)

# Start the bot
application.run_polling()
