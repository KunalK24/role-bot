import os
import discord
import re
import pymongo
import bot_config
import smtplib
import logging
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pymongo import MongoClient
from discord.ext import commands
from discord.utils import get


cluster = MongoClient(bot_config.auth)
db = cluster[bot_config.database_name]
collection = db[bot_config.collection_name]

bot = commands.Bot(command_prefix='!')
logging.basicConfig(filename='{0}-BackersBot-Discord.out'.format(bot_config.log_folder),
                    level=logging.INFO,
                    format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%Y/%m/%d-%H:%M:%S')
msg = "\rHello, I just need a bit of information to give you the rewards you pledged for!\r" \
      "What's the email address linked to your KickStarter account?"


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    logging.info(f'{bot.user.name} has connected to Discord at {datetime.datetime.now()}')
    channel = bot.get_channel(bot_config.channel_id)
    emoji = bot.get_emoji(bot_config.emoji_id)

    text = "Hi there, I'm the KickStarter Assistant for {0}! I'll be assigning roles to the backers in the discord.\r" \
           "All you need to do it react to this message with a  {1}  emoji and I'll send you a message with instructions!".format(bot_config.server, emoji)
    await channel.send(text)

    
@bot.event
async def on_raw_reaction_add(raw_reaction):
    channel = bot.get_channel(bot_config.channel_id)
    try:
        message = await channel.fetch_message(raw_reaction.message_id)
    except:
        return
    if message.channel.id != bot_config.channel_id:
        return
    if message.author != bot.user:
        return
    emoji = bot.get_emoji(bot_config.emoji_id)
    if raw_reaction.emoji == emoji and raw_reaction.message_id == bot_config.message_id:
        user = bot.get_user(raw_reaction.user_id)
        try:
            await user.send(msg)
        except discord.errors.Forbidden:
            logging.info('f{user} has disabled direct messages from this server')
            await channel.send("{0} you have disabled direct messages from this server member.\r" \
                                                "Please send me the command again."
                           .format(user.mention))


@bot.event
async def on_message(message):
    
    if message.author == bot.user:
        return
    
    if message.channel.type is not discord.ChannelType.private:
        return
    
    string = (message.content).split()
    valid = False
    for word in string:
        if valid_email(word):
            valid = True
            result = collection.find_one({'email': word})
            token = ''
            if result == None:
                await message.author.send("Hmm, I can't find that email in the backer list. Please check the email and try again!")
                logging.info(f'{word} was not found in the database. The type of this word is {type(word)}')
                return
            elif result['verification_code'] == '':
                token = '#' + str(result['_id'])
                collection.update_one({'email': word}, {'$set': {'verification_code': token}})
            elif result['verification_code'] != '':
               token = result['verification_code']

            if token != '':
                    user = bot_config.email_user
                    password = bot_config.email_password
                    
                    try:
                        mail = MIMEMultipart()
                        mail['From'] = user
                        mail['To'] = word
                        mail['Subject'] = bot_config.email_subject
                        mail.attach(MIMEText(bot_config.email_body, 'plain'))
                        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                        server.ehlo()
                        server.login(user, password)
                        email_text = mail.as_string()
                        server.sendmail(user, word, email_text)
                        server.close()
                        await message.author.send('Awesome, a verification email has been sent to that address.\rAll I need is that verification code starting with # and I can assign your roles!')
                    except:
                        await message.author.send('Email has failed! Reach out to the devs because I am shutting do-')

                    
        elif word[0] == '#':
            valid = True
            result = collection.find_one({'verification_code': word})
            if result != None:
                if result['discord_tag'] != '':
                    await message.author.send("Looks like another user claimed the rewards for that email. Reach out to one of the devs and they'll help sort this out!")
                else:
                    await message.author.send("I found that code in database. Let me check what roles you qualify for.")
                    pledge = result['pledge']
                    server = await bot.fetch_guild(bot_config.server_id)
                    server_member = await server.fetch_member(message.author.id)
                    if server_member == None:
                        #User is not a member of the server
                        await message.author.send("This is awakward, you haven't joined the Discord yet! Join it first and run the command again. Server Link: {}".format(bot_config.server_link))
                    else:
                        role = get(server.roles, name=bot_config.discord_role_name)
                            
                        if role in server_member.roles:
                            #Member has the role
                            await message.author.send("Looks like you already have the {} role.".format(role))
                        else:
                            #Member does not have the role
                            await server_member.add_roles(role)
                            await message.author.send("You've been added to the {} role in the discord. Thank you again for your support!".format(role))

                        collection.update_one({"verification_code": message.content}, {"$set": {"discord_tag": str(message.author.id)}})

    if valid == False:
        await message.author.send("Sorry, I don't recognize that input. Make sure you send me just your email or verification code if I've already sent you an email!")
        
    return

        
def valid_email(email: str):
    return re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email)


bot.run(bot_config.token)
