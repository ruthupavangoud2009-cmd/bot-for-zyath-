import discord
from discord.ext import commands
from typing import Optional
from utils.embeds import standard_embed, success_embed, error_embed, info_embed
from utils.database import db

class AutoResponder(commands.Cog):
    """Custom Auto-Responder and Triggers for Community & Lal Servers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Do not trigger on prefix commands
        content = message.content.strip()
        if content.startswith(("$", "/", "!", "?", ".")):
            return

        resp = await db.find_auto_response(message.guild.id, content)
        if resp:
            # Format custom template variables
            formatted = (
                resp
                .replace("{user}", message.author.name)
                .replace("{user.mention}", message.author.mention)
                .replace("{user.id}", str(message.author.id))
                .replace("{server}", message.guild.name)
                .replace("{channel}", message.channel.mention)
            )
            try:
                await message.channel.send(formatted)
            except Exception:
                pass

    # ==========================================
    # AUTO-RESPONDER COMMANDS ($ar)
    # ==========================================
    @commands.group(name="autoresponder", aliases=["ar", "tag", "customcmd"], invoke_without_command=True, help="Manage server automated trigger responses. E.g. $ar")
    async def ar_group(self, ctx: commands.Context):
        embed = info_embed(
            "🤖 Server Auto-Responder Suite",
            "Automatically respond when members type custom trigger phrases.\n\n"
            "• `$ar add <trigger> | <response>` - Create a new auto-response.\n"
            "• `$ar remove <trigger>` - Delete an auto-response trigger.\n"
            "• `$ar list` - View all active auto-responders.\n\n"
            "**Supported Variables:**\n"
            "`{user}` — Author username\n"
            "`{user.mention}` — Author ping\n"
            "`{server}` — Server name\n"
            "`{channel}` — Channel mention"
        )
        await ctx.send(embed=embed)

    @ar_group.command(name="add", aliases=["create", "new"], help="Add an auto-response. E.g. $ar add pricing | Check our store catalog in #shop!")
    @commands.has_permissions(manage_guild=True)
    async def ar_add(self, ctx: commands.Context, *, raw_input: str):
        if "|" not in raw_input:
            return await ctx.send(embed=error_embed(
                "Invalid Format",
                "**Usage:** `$ar add <trigger> | <response>`\n\n"
                "**Example:**\n"
                "• `$ar add ltc | Send payment to our LTC address in $payment!`\n"
                "• `$ar add rules | Hey {user.mention}, check our server guidelines in #rules!`"
            ))

        parts = raw_input.split("|", 1)
        trigger = parts[0].strip()
        response = parts[1].strip()

        if not trigger or not response:
            return await ctx.send(embed=error_embed("Missing Parameters", "Both trigger phrase and response are required."))

        await db.add_auto_responder(ctx.guild.id, trigger, response, ctx.author.id)

        embed = success_embed(
            "Auto-Response Created",
            f"✅ Trigger phrase **\"{trigger}\"** has been registered!\n\n"
            f"**Response Preview:**\n```{response[:300]}```\n"
            f"*Whenever someone types `{trigger}`, the bot will auto-reply!*"
        )
        await ctx.send(embed=embed)

    @ar_group.command(name="remove", aliases=["del", "delete"], help="Delete an auto-responder trigger. E.g. $ar remove pricing")
    @commands.has_permissions(manage_guild=True)
    async def ar_remove(self, ctx: commands.Context, *, trigger: str):
        removed = await db.remove_auto_responder(ctx.guild.id, trigger)
        if removed:
            await ctx.send(embed=success_embed("Auto-Response Deleted", f"Successfully deleted trigger **\"{trigger}\"**."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No auto-responder found for trigger **\"{trigger}\"**."))

    @ar_group.command(name="list", help="List all configured auto-responders in this server.")
    async def ar_list(self, ctx: commands.Context):
        responders = await db.get_auto_responders(ctx.guild.id)
        if not responders:
            return await ctx.send(embed=info_embed("Auto-Responders", "No custom auto-responders registered in this server yet.\n*Create one with `$ar add <trigger> | <response>`.*"))

        lines = []
        for r in responders[:25]:
            snippet = r['response_text'][:50] + ("..." if len(r['response_text']) > 50 else "")
            lines.append(f"• **`{r['trigger_text']}`** ➔ *\"{snippet}\"*")

        embed = standard_embed(
            title=f"🤖 {ctx.guild.name} • Active Auto-Responders",
            description="\n".join(lines),
            color=0x2ECC71
        )
        embed.set_footer(text=f"Total: {len(responders)} triggers • Case-insensitive matching")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoResponder(bot))
