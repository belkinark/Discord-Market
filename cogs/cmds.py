import nextcord

from nextcord.ext import commands, application_checks
from configs.config_menager import config_get, message_get
from database.conection import db


class Cmds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(name="money_add", description="Replenishment of the user's balance")
    @application_checks.has_role(config_get("manager_role"))
    async def money_add(self, interaction: nextcord.Interaction, user: nextcord.User, amount: int):
        balance = (await db["users"].find_one({"_id": user.id}))["balance"]
        await db["users"].update_one({"_id": user.id}, {"$set": {"balance": balance+amount}})
        await interaction.send(f"The balance of the user {user.name} has been replenished by ${amount}. The current balance is ${balance+amount}.", ephemeral=True)

    @nextcord.slash_command(name="money_remove", description="Takes money from the user's balance")
    @application_checks.has_role(config_get("manager_role"))
    async def money_remove(self, interaction: nextcord.Interaction, user: nextcord.User, amount: int):
        balance = (await db["users"].find_one({"_id": user.id}))["balance"]
        await db["users"].update_one({"_id": user.id}, {"$set": {"balance": balance-amount}})
        await interaction.send(f"The user {user.name} has ${amount} debited. The user's current balance is ${balance-amount}.", ephemeral=True)

    @nextcord.slash_command(name="delete_lot", description="Deletes a lot in the catalog")
    @application_checks.has_role(config_get("manager_role"))
    async def delete_lot(self, interaction: nextcord.Interaction, id: str):
        lot = await db["products"].find_one({"_id": id})
        channel = interaction.guild.get_channel(config_get("catalog"))
        await channel.get_thread(lot["thread"]).delete()
        await db["products"].delete_one({"_id": id})
        await interaction.send(f"The lot with the id {id} has been successfully deleted.", ephemeral=True)

    @nextcord.slash_command(name="block_user", description="Block access to the menu and directory from the user")
    @application_checks.has_role(config_get("manager_role"))
    async def block_user(self, interaction: nextcord.Interaction, member: nextcord.Member):
        catalog = interaction.guild.get_channel(config_get("catalog"))
        menu = interaction.guild.get_channel(config_get("menu"))
        await catalog.set_permissions(member, read_messages=False)
        await menu.set_permissions(member, read_messages=False)
        await interaction.send(f"User {member.name} has been successfully blocked.", ephemeral=True)


def setup(bot):
    bot.add_cog(Cmds(bot))