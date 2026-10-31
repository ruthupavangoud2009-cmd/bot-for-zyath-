import discord
from discord.ext import commands
import random
import asyncio
import json
import os
from utils.embeds import standard_embed, success_embed, error_embed, info_embed

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def get_allowed_spam_users():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [str(u) for u in data.get("allowed_spam_users", [])]
        except Exception:
            pass
    return []

def save_allowed_spam_users(users: list):
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["allowed_spam_users"] = users
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

class Fun(commands.Cog):
    """Fun, utilities, $say, and restricted ghost spam commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="say", help="Make the bot say something and delete your command message. E.g. $say hi")
    async def say(self, ctx: commands.Context, *, message: str = None):
        # Delete author's trigger message immediately
        try:
            await ctx.message.delete()
        except Exception:
            pass

        if not message:
            return

        await ctx.send(message)

    @commands.command(name="sayembed", help="Make the bot speak in a clean embed. E.g. $sayembed Title | Description")
    async def say_embed(self, ctx: commands.Context, *, text: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        if "|" in text:
            parts = text.split("|", 1)
            title = parts[0].strip()
            desc = parts[1].strip()
        else:
            title = None
            desc = text.strip()

        embed = standard_embed(title=title, description=desc)
        await ctx.send(embed=embed)

    @commands.command(name="spam", help="Restricted fast ping spam that deletes trigger and all spam messages.")
    async def spam(self, ctx: commands.Context, count: int, member: discord.Member, *, extra_msg: str = ""):
        # Delete user trigger message immediately
        try:
            await ctx.message.delete()
        except Exception:
            pass

        allowed_users = get_allowed_spam_users()
        # Allow if author ID in allowed list or bot owner
        is_owner = await self.bot.is_owner(ctx.author)
        if str(ctx.author.id) not in allowed_users and not is_owner:
            err = await ctx.send(embed=error_embed("Restricted Command", "⛔ You are not authorized to use the `$spam` command."))
            await err.delete(delay=4)
            return

        if count < 1:
            return
        if count > 100:
            count = 100  # Cap at 100

        text = f"{member.mention} {extra_msg}".strip()

        for _ in range(count):
            try:
                msg = await ctx.send(text)
                await msg.delete()
                await asyncio.sleep(0.3)
            except discord.HTTPException:
                await asyncio.sleep(1.0)
            except Exception:
                break

    @commands.command(name="setspamusers", aliases=["addspamuser"], help="Set or add allowed user IDs for the $spam command.")
    @commands.has_permissions(administrator=True)
    async def set_spam_users(self, ctx: commands.Context, member: discord.Member):
        allowed = get_allowed_spam_users()
        user_id_str = str(member.id)
        if user_id_str not in allowed:
            allowed.append(user_id_str)
            save_allowed_spam_users(allowed)
            await ctx.send(embed=success_embed("Spam Whitelist Updated", f"Added {member.mention} (`{member.id}`) to allowed spam users."))
        else:
            await ctx.send(embed=info_embed("Already Whitelisted", f"{member.mention} is already in the spam allowed list."))

    @commands.command(name="removespamuser", help="Remove a user from the allowed spam users list.")
    @commands.has_permissions(administrator=True)
    async def remove_spam_user(self, ctx: commands.Context, member: discord.Member):
        allowed = get_allowed_spam_users()
        user_id_str = str(member.id)
        if user_id_str in allowed:
            allowed.remove(user_id_str)
            save_allowed_spam_users(allowed)
            await ctx.send(embed=success_embed("Spam Whitelist Updated", f"Removed {member.mention} from allowed spam users."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"{member.mention} was not in the allowed list."))

    @commands.command(name="8ball", help="Ask the magic 8ball a question.")
    async def eight_ball(self, ctx: commands.Context, *, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        choice = random.choice(responses)
        embed = standard_embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n**Answer:** {choice}",
            color=0x3498DB
        )
        await ctx.send(embed=embed)

    @commands.command(name="coinflip", aliases=["flip"], help="Flip a coin.")
    async def coin_flip(self, ctx: commands.Context):
        result = random.choice(["Heads 🪙", "Tails 🪙"])
        await ctx.send(embed=info_embed("Coin Flip", f"The coin landed on **{result}**!"))

    @commands.command(name="roll", help="Roll a dice. E.g. $roll 100")
    async def roll(self, ctx: commands.Context, max_val: int = 6):
        if max_val < 2:
            max_val = 6
        result = random.randint(1, max_val)
        await ctx.send(embed=info_embed("Dice Roll", f"🎲 You rolled a **{result}** (1-{max_val})!"))

    @commands.command(name="roast", help="Roast a member.")
    async def roast(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roasts = [
            "You bring everyone so much joy... when you leave the room.",
            "I'd agree with you, but then we'd both be wrong.",
            "I'm not saying I hate you, but I would unplug your life support to charge my phone.",
            "You have something on your chin... no, the 3rd one down.",
            "Light travels faster than sound, which is why you seemed bright until you spoke.",
            "If I had a face like yours, I'd sue my parents.",
            "You're like a cloud. When you disappear, it's a beautiful day.",
            "I'd give you a nasty look, but you've already got one."
        ]
        await ctx.send(f"{member.mention} {random.choice(roasts)}")

    @commands.command(name="avatar", aliases=["av"], help="Get a member's avatar.")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        embed = standard_embed(
            title=f"Avatar for {member.display_name}",
            image=member.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.command(name="userinfo", aliases=["whois"], help="Get information about a user.")
    async def user_info(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        roles_str = ", ".join(roles) if roles else "None"

        embed = standard_embed(
            title=f"User Info • {member}",
            thumbnail=member.display_avatar.url
        )
        embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
        embed.add_field(name="🏷️ Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="🤖 Bot?", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="📅 Created At", value=discord.utils.format_dt(member.created_at, style="f"), inline=True)
        embed.add_field(name="📥 Joined Server", value=discord.utils.format_dt(member.joined_at, style="f") if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="🔝 Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=roles_str[:1024] if len(roles_str) < 1024 else f"{len(roles)} roles", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo", help="Get information about the server.")
    async def server_info(self, ctx: commands.Context):
        g = ctx.guild
        embed = standard_embed(
            title=f"Server Info • {g.name}",
            thumbnail=g.icon.url if g.icon else None
        )
        embed.add_field(name="👑 Owner", value=f"<@{g.owner_id}>", inline=True)
        embed.add_field(name="🆔 Server ID", value=str(g.id), inline=True)
        embed.add_field(name="👥 Members", value=str(g.member_count), inline=True)
        embed.add_field(name="💬 Channels", value=f"{len(g.text_channels)} Text | {len(g.voice_channels)} Voice", inline=True)
        embed.add_field(name="🎭 Roles", value=str(len(g.roles)), inline=True)
        embed.add_field(name="✨ Boost Level", value=f"Level {g.premium_tier} ({g.premium_subscription_count} boosts)", inline=True)
        embed.add_field(name="📅 Created On", value=discord.utils.format_dt(g.created_at, style="f"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="poll", help="Create a reaction poll. E.g. $poll Should we do a giveaway?")
    async def poll(self, ctx: commands.Context, *, question: str):
        try:
            await ctx.message.delete()
        except Exception:
            pass

        embed = standard_embed(
            title="📊 Community Poll",
            description=f"**{question}**\n\nVote by reacting below!",
            author=ctx.author
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.command(name="ping", help="Check bot response latency.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(embed=info_embed("Pong! 🏓", f"Bot Latency: **{latency}ms**"))

async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
