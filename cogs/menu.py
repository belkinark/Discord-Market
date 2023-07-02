import nextcord
from hashlib import md5

from nextcord.ext import commands, application_checks
from datetime import datetime
from configs.config_menager import config_get, message_get
from database.conection import db


class Modal(nextcord.ui.Modal):
    def __init__(self, messages: list, bot: commands.Bot, **kwargs: nextcord.ui.text_input.TextInput):
        self.bot = bot
        self.kwargs = kwargs
        super().__init__(messages["modal"])
        [self.add_item(val) for val in self.kwargs.values()]

    async def callback(self, interaction: nextcord.Interaction):
        color = config_get("color")
        command = [self.kwargs.get(key).custom_id for key in self.kwargs.keys()]
        values = [self.kwargs.get(key).value for key in self.kwargs.keys()]
        user, channel = interaction.user, interaction.channel

        if command[0][:5] == "price":
            suffix = int(command[0][6:])
            command = command[0][:5]

        if "name" in command:
            hash = f"{user.id}_{datetime.now()}"
            hash = md5(hash.encode()).hexdigest()
            await db["products"].insert_one({
                "_id": hash,
                "price": 0,
                "holder": user.id,
                "name": values[0],
                "privat": values[1],
                "thread": "",
            })

            messages = message_get("created")
            emb = nextcord.Embed(title=messages["title"],
                            description=messages["desc"],
                            color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            await interaction.send(embed=emb, ephemeral=True)
        
        if command == "price":
            try:
                price = int(values[0])
                messages = message_get("price")
            except ValueError:
                messages = message_get("error1")
                return await interaction.send(messages["text"], ephemeral=True)
            
            products = [i async for i in db["products"].find({"holder": user.id, "price": 0})][suffix]
            msg = await channel.fetch_message((await db["users"].find_one({"_id": user.id}))["message"])

            catalog_channel = interaction.guild.get_channel(config_get("catalog"))
            emb = nextcord.Embed(title=f"{products['name']} - {price}$",
                                description=f"id - {products['_id']}\nauthor - {user.name}",
                                color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            buttons = [
                ["buy", None, nextcord.ButtonStyle.success, "buy", 1, None, False],
                ["take off", None, nextcord.ButtonStyle.danger, "take_off", 1, None, False],
            ]
            thread = await catalog_channel.create_thread(name=f"{products['name']} - {price}$", embed=emb, view=ViewButton(self.bot, buttons))

            emb = nextcord.Embed(title=messages["title"],
                                description=messages["desc"],
                                color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            buttons = [
                [messages["btns"][0], None, nextcord.ButtonStyle.secondary, "menu", 1, None, False],
            ]
            await msg.edit(f"<@{user.id}>", embed=emb, view=ViewButton(self.bot, buttons))

            await db["products"].update_one({"_id": products['_id']}, {"$set": {"price": price, "thread": thread.id}})


class Button(nextcord.ui.Button["ViewButton"]):
    def __init__(self, bot: commands.Bot, *args):
        super().__init__(label=args[0], emoji=args[1], style=args[2], custom_id=args[3], row=args[4], url=args[5], disabled=args[6])
        self.bot = bot

    async def callback(self, interaction: nextcord.Interaction):
        command = self.custom_id

        if command[:11] == "show_hidden":
            suffix = int(command[12:])
            command = command[:11]
        elif command[:4] == "show":
            suffix = int(command[5:])
            command = command[:4]
        elif command[:4] == "sell":
            suffix = int(command[5:])
            command = command[:4]

        color, messages = config_get("color"), message_get(command)
        user, channel = interaction.user, interaction.channel

        if command == "open":
            if await db["users"].find_one({ "_id": user.id }) == None:
                await db["users"].insert_one({
                    "_id": user.id,
                    "balance": 10,
                    "message": 0,
                    "thread": 0,
                    "action": "menu"
                })
                balance = 10
                member = await interaction.guild.fetch_member(user.id)
                catalog = interaction.guild.get_channel(config_get("catalog"))
                await catalog.set_permissions(member, read_messages=True)
            else:
                user_db = await db["users"].find_one({ "_id": user.id })
                thread, balance = user_db["thread"], user_db["balance"]
                await channel.get_thread(thread).delete()
                await db["creations"].delete_one({"_id": user.id})

            thread = await channel.create_thread(name=f"menu ({user.name})",
                                                 auto_archive_duration=1440,
                                                 type=nextcord.ChannelType.private_thread,
                                                 reason=None)
            emb = nextcord.Embed(title=messages["title"]+user.name,
                             description=messages["desc"]+str(balance),
                             color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            buttons = [
                [messages["btns"][0], None, nextcord.ButtonStyle.success, "show_0", 1, None, False],
                [messages["btns"][1], None, nextcord.ButtonStyle.primary, "create", 1, None, False],
            ]
            msg = await thread.send(f"<@{user.id}>", embed=emb, view=ViewButton(self.bot, buttons))

            await db["users"].update_one({"_id": user.id}, {"$set": {"message": msg.id, "thread": thread.id, "action": "menu"}})

        elif command == "menu":
            messages = message_get("open")
            user_db = await db["users"].find_one({"_id": user.id})
            msg = await channel.fetch_message(user_db["message"])
            await db["creations"].delete_one({"_id": user.id})

            emb = nextcord.Embed(title=messages["title"]+user.name,
                             description=messages["desc"]+str(user_db["balance"]),
                             color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            buttons = [
                [messages["btns"][0], None, nextcord.ButtonStyle.success, "show_0", 1, None, False],
                [messages["btns"][1], None, nextcord.ButtonStyle.primary, "create", 1, None, False],
            ]
            await msg.edit(f"<@{user.id}>", embed=emb, view=ViewButton(self.bot, buttons))

            await db["users"].update_one({"_id": user.id}, {"$set": {"action": "menu"}})

        elif command == "show":
            msg = await channel.fetch_message((await db["users"].find_one({"_id": user.id}))["message"])
            products = [i async for i in db["products"].find({"holder": user.id, "price": 0})]
            if len(products) == 0:
                return await interaction.send(messages["text"], ephemeral=True)

            emb = nextcord.Embed(title=f"{suffix+1}/{len(products)}",
                             description=products[suffix]["name"],
                             color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
            buttons = [
                [messages["btns"][0], None, nextcord.ButtonStyle.secondary, f"show_{suffix-1}", 1, None, True if suffix == 0 else False],
                [messages["btns"][1], None, nextcord.ButtonStyle.success, f"show_hidden_{suffix}", 1, None, False],
                [messages["btns"][2], None, nextcord.ButtonStyle.primary, f"sell_{suffix}", 1, None, False],
                [messages["btns"][3], None, nextcord.ButtonStyle.secondary, f"show_{suffix+1}", 1, None, True if suffix+1 == len(products) else False],
                [messages["btns"][4], None, nextcord.ButtonStyle.danger, "menu", 2, None, False],
            ]
            await msg.edit(f"<@{user.id}>", embed=emb, view=ViewButton(self.bot, buttons))
        
        elif command == "create":
            emOne = nextcord.ui.TextInput(
                label=messages["labels"][0],
                min_length=4,
                max_length=32,
                required=True,
                custom_id="name",
                style=nextcord.TextInputStyle.short
            )
            emTwo = nextcord.ui.TextInput(
                label=messages["labels"][1],
                min_length=1,
                max_length=200,
                required=True,
                custom_id="privat",
                style=nextcord.TextInputStyle.short
            )
            await interaction.response.send_modal(Modal(messages, self.bot, emOne=emOne, emTwo=emTwo))
        
        elif command == "show_hidden":
            products = [i async for i in db["products"].find({"holder": user.id})]
            await interaction.send(products[suffix]["privat"], ephemeral=True)
        
        elif command == "sell":
            emOne = nextcord.ui.TextInput(
                label=messages["labels"][0],
                min_length=1,
                max_length=5,
                required=True,
                custom_id=f"price_{suffix}",
                style=nextcord.TextInputStyle.short
            )
            await interaction.response.send_modal(Modal(messages, self.bot, emOne=emOne))

        elif command == "buy":
            product = await db["products"].find_one({"thread": channel.id})
            user_db = await db["users"].find_one({"_id": user.id})
            holder_db = await db["users"].find_one({"_id": product["holder"]})

            if user_db["balance"] >= product["price"]:
                emb = nextcord.Embed(title=messages["title"],
                             description=product["privat"],
                             color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
                await interaction.send(embed=emb, ephemeral=True)

                catalog_channel = interaction.guild.get_channel(config_get("catalog"))
                thread = catalog_channel.get_thread(channel.id)
                await thread.edit(archived=True, locked=True)

                await db["products"].update_one({"_id": product['_id']}, {"$set": {"price": 0, "holder": user.id, "thread": ""}})
                await db["users"].update_one({"_id": holder_db["_id"]}, {"$set": {"balance": holder_db["balance"]+product["price"]}})
                await db["users"].update_one({"_id": user.id}, {"$set": {"balance": user_db["balance"]-product["price"]}})

            else:
                await interaction.send(messages["text"], ephemeral=True)

        elif command == "take_off":
            product = await db["products"].find_one({"thread": channel.id})
            if product["holder"] == user.id:
                catalog_channel = interaction.guild.get_channel(config_get("catalog"))
                thread = catalog_channel.get_thread(channel.id)
                await thread.edit(archived=True, locked=True)
                await db["products"].update_one({"_id": product['_id']}, {"$set": {"price": 0, "thread": ""}})

            else:
                await interaction.send(messages["text"], ephemeral=True)


class ViewButton(nextcord.ui.View):
    def __init__(self, bot: commands.Bot, elem: list):
        super().__init__(timeout = None)
        [self.add_item(Button(bot, elem[i][0], elem[i][1], elem[i][2], elem[i][3], elem[i][4], elem[i][5], elem[i][6])) for i in range(len(elem))]


class Menu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        custom_ids = ["open", "menu", "show_0", "create", "buy", "take_off"]
        [self.bot.add_view(ViewButton(bot=self.bot, elem=[[None, None, None, i, 1, None, None]])) for i in custom_ids]

    @nextcord.slash_command()
    @application_checks.is_owner()
    async def menu_setting(self, interaction: nextcord.Interaction):
        color, messages = config_get("color"), message_get("menu_channel")
        emb = nextcord.Embed(title=messages["title"],
                             description=messages["desc"],
                             color=nextcord.Color.from_rgb(r=color[0], g=color[1], b=color[2]))
        buttons = [
            [messages["btns"][0], None, nextcord.ButtonStyle.success, "open", 1, None, False],
        ]
        channel = interaction.guild.get_channel(config_get("menu"))
        await channel.send(embed=emb, view=ViewButton(self.bot, buttons))


def setup(bot):
    bot.add_cog(Menu(bot))