import io
import discord
from discord.ext import commands
from typing import Optional

from utils.database import db
from utils.embeds import standard_embed, success_embed, error_embed, info_embed


DEFAULT_COLOR = 0x5846A8


class Branding(commands.Cog):
    """Guild-scoped bot profile settings. Each guild has its own persisted row."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get(self, guild_id: int) -> dict:
        if db.is_postgres and db.pool:
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM guild_branding WHERE guild_id=$1", guild_id)
                return dict(row) if row else {}
        import aiosqlite
        async with aiosqlite.connect(db.sqlite_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute("SELECT * FROM guild_branding WHERE guild_id=?", (guild_id,))
            row = await cur.fetchone()
            return dict(row) if row else {}

    async def _save(self, guild_id: int, **fields) -> None:
        allowed = {"display_name", "avatar_url", "banner_url", "bio", "color"}
        fields = {k: v for k, v in fields.items() if k in allowed}
        if not fields:
            return
        if db.is_postgres and db.pool:
            cols = ", ".join(["guild_id", *fields.keys()])
            vals = ", ".join(f"${i}" for i in range(1, len(fields) + 2))
            updates = ", ".join(f"{k}=EXCLUDED.{k}" for k in fields)
            async with db.pool.acquire() as conn:
                await conn.execute(
                    f"INSERT INTO guild_branding ({cols}) VALUES ({vals}) "
                    f"ON CONFLICT(guild_id) DO UPDATE SET {updates}",
                    guild_id, *fields.values()
                )
        else:
            import aiosqlite
            cols = ", ".join(["guild_id", *fields.keys()])
            marks = ", ".join("?" for _ in range(len(fields) + 1))
            updates = ", ".join(f"{k}=excluded.{k}" for k in fields)
            async with aiosqlite.connect(db.sqlite_path) as conn:
                await conn.execute(
                    f"INSERT INTO guild_branding ({cols}) VALUES ({marks}) "
                    f"ON CONFLICT(guild_id) DO UPDATE SET {updates}",
                    (guild_id, *fields.values())
                )
                await conn.commit()

    async def _reset(self, guild_id: int, field: Optional[str] = None) -> None:
        allowed = {"display_name", "avatar_url", "banner_url", "bio", "color"}
        if field and field not in allowed:
            return
        if db.is_postgres and db.pool:
            async with db.pool.acquire() as conn:
                if field:
                    await conn.execute(f"UPDATE guild_branding SET {field}=NULL WHERE guild_id=$1", guild_id)
                else:
                    await conn.execute("DELETE FROM guild_branding WHERE guild_id=$1", guild_id)
        else:
            import aiosqlite
            async with aiosqlite.connect(db.sqlite_path) as conn:
                if field:
                    await conn.execute(f"UPDATE guild_branding SET {field}=NULL WHERE guild_id=?", (guild_id,))
                else:
                    await conn.execute("DELETE FROM guild_branding WHERE guild_id=?", (guild_id,))
                await conn.commit()

    def _allowed(self, ctx: commands.Context) -> bool:
        return bool(ctx.guild and (
            ctx.author.id == ctx.guild.owner_id
            or ctx.author.guild_permissions.administrator
            or ctx.author.guild_permissions.manage_guild
            or ctx.author.id in (getattr(self.bot, "owner_ids", None) or set())
        ))

    @commands.group(name="botedit", aliases=["setbot", "botbrand"], invoke_without_command=True)
    @commands.guild_only()
    async def botedit(self, ctx: commands.Context):
        prefix = "$"
        row = await self._get(ctx.guild.id)
        e = discord.Embed(
            title=f"Server Bot Branding • {ctx.guild.name}",
            description=(
                f"`$botedit name <name>` — server nickname\n"
                f"`$botedit avatar` — attach an image\n"
                f"`$botedit banner` — attach an image\n"
                f"`$botedit bio <text>` — server profile bio\n"
                f"`$botedit color #HEX` — embed accent color\n"
                f"`$botedit view` — view saved settings\n"
                f"`$botedit reset [name|avatar|banner|bio|color]` — reset settings\n\n"
                "Settings are stored separately for this server. Requires Manage Server."
            ),
            color=int(row.get("color") or DEFAULT_COLOR)
        )
        await ctx.send(embed=e)

    @botedit.command(name="name", aliases=["nick"])
    @commands.guild_only()
    async def name(self, ctx: commands.Context, *, value: str):
        if not self._allowed(ctx):
            return await ctx.send(embed=error_embed("Permission denied", "Manage Server is required."))
        value = value.strip()
        if not value or len(value) > 32:
            return await ctx.send(embed=error_embed("Invalid name", "Use 1–32 characters."))
        try:
            await ctx.guild.me.edit(nick=value, reason=f"Server branding set by {ctx.author}")
            await self._save(ctx.guild.id, display_name=value)
            await ctx.send(embed=success_embed("Branding updated", f"Bot nickname set to **{value}** in this server."))
        except discord.HTTPException as exc:
            await ctx.send(embed=error_embed("Discord rejected the change", str(exc)[:500]))

    async def _image(self, ctx: commands.Context, kind: str, attachment: Optional[discord.Attachment]):
        if not self._allowed(ctx):
            return await ctx.send(embed=error_embed("Permission denied", "Manage Server is required."))
        attachment = attachment or (ctx.message.attachments[0] if ctx.message.attachments else None)
        if not attachment:
            return await ctx.send(embed=info_embed(f"Set {kind}", f"Attach a PNG, JPG, WEBP or GIF image with `$botedit {kind}`."))
        if attachment.content_type and not attachment.content_type.startswith("image/"):
            return await ctx.send(embed=error_embed("Invalid file", "Please attach an image."))
        if attachment.size > 10 * 1024 * 1024:
            return await ctx.send(embed=error_embed("Image too large", "Maximum image size is 10 MB."))
        data = await attachment.read()
        try:
            if kind == "avatar":
                await ctx.guild.me.edit(avatar=data, reason=f"Server avatar set by {ctx.author}")
            else:
                await ctx.guild.me.edit(banner=data, reason=f"Server banner set by {ctx.author}")
            await self._save(ctx.guild.id, **{f"{kind}_url": attachment.url})
            await ctx.send(embed=success_embed("Branding updated", f"Server-specific bot {kind} updated and saved."))
        except (discord.HTTPException, ValueError) as exc:
            await ctx.send(embed=error_embed("Discord could not apply this image", f"{str(exc)[:350]}\nYour server's saved branding was not changed."))

    @botedit.command(name="avatar")
    @commands.guild_only()
    async def avatar(self, ctx: commands.Context, attachment: Optional[discord.Attachment] = None):
        await self._image(ctx, "avatar", attachment)

    @botedit.command(name="banner")
    @commands.guild_only()
    async def banner(self, ctx: commands.Context, attachment: Optional[discord.Attachment] = None):
        await self._image(ctx, "banner", attachment)

    @botedit.command(name="bio")
    @commands.guild_only()
    async def bio(self, ctx: commands.Context, *, value: str):
        if not self._allowed(ctx):
            return await ctx.send(embed=error_embed("Permission denied", "Manage Server is required."))
        value = value.strip()
        if len(value) > 190:
            return await ctx.send(embed=error_embed("Too long", "Bio must be 190 characters or fewer."))
        try:
            await ctx.guild.me.edit(bio=value, reason=f"Server bio set by {ctx.author}")
            await self._save(ctx.guild.id, bio=value)
            await ctx.send(embed=success_embed("Branding updated", "Server-specific bot bio saved."))
        except (discord.HTTPException, ValueError) as exc:
            await ctx.send(embed=error_embed("Discord rejected the bio", str(exc)[:400]))

    @botedit.command(name="color")
    @commands.guild_only()
    async def color(self, ctx: commands.Context, value: str):
        if not self._allowed(ctx):
            return await ctx.send(embed=error_embed("Permission denied", "Manage Server is required."))
        try:
            color = int(value.strip().lstrip("#"), 16)
            if not 0 <= color <= 0xFFFFFF:
                raise ValueError
        except ValueError:
            return await ctx.send(embed=error_embed("Invalid color", "Use a hex color, for example #D4AF37."))
        await self._save(ctx.guild.id, color=color)
        await ctx.send(embed=success_embed("Accent color saved", f"Saved `#{color:06X}` for this server."))

    @botedit.command(name="view")
    @commands.guild_only()
    async def view(self, ctx: commands.Context):
        row = await self._get(ctx.guild.id)
        e = discord.Embed(title=f"Branding • {ctx.guild.name}", color=int(row.get("color") or DEFAULT_COLOR))
        e.add_field(name="Display name", value=row.get("display_name") or ctx.me.display_name, inline=True)
        e.add_field(name="Bio", value=row.get("bio") or "Default", inline=False)
        e.add_field(name="Avatar", value="Custom saved" if row.get("avatar_url") else "Default", inline=True)
        e.add_field(name="Banner", value="Custom saved" if row.get("banner_url") else "Default", inline=True)
        if row.get("avatar_url"):
            e.set_thumbnail(url=row["avatar_url"])
        if row.get("banner_url"):
            e.set_image(url=row["banner_url"])
        await ctx.send(embed=e)

    @botedit.command(name="reset")
    @commands.guild_only()
    async def reset(self, ctx: commands.Context, field: Optional[str] = None):
        if not self._allowed(ctx):
            return await ctx.send(embed=error_embed("Permission denied", "Manage Server is required."))
        aliases = {"name": "display_name", "nick": "display_name"}
        field = aliases.get(field, field) if field else None
        if field and field not in {"display_name", "avatar", "banner", "bio", "color"}:
            return await ctx.send(embed=error_embed("Invalid field", "Use name, avatar, banner, bio, or color."))
        try:
            if field == "display_name":
                await ctx.guild.me.edit(nick=None, reason=f"Server branding reset by {ctx.author}")
            elif field == "avatar":
                await ctx.guild.me.edit(avatar=None, reason=f"Server branding reset by {ctx.author}")
            elif field == "banner":
                await ctx.guild.me.edit(banner=None, reason=f"Server branding reset by {ctx.author}")
            elif field == "bio":
                await ctx.guild.me.edit(bio="", reason=f"Server branding reset by {ctx.author}")
            elif field is None:
                await ctx.guild.me.edit(
                    nick=None, avatar=None, banner=None, bio="",
                    reason=f"All server branding reset by {ctx.author}"
                )
            await self._reset(ctx.guild.id, {"avatar": "avatar_url", "banner": "banner_url"}.get(field, field) if field else None)
            await ctx.send(embed=success_embed("Branding reset", f"Reset **{field or 'all branding'}** for this server."))
        except (discord.HTTPException, ValueError) as exc:
            await ctx.send(embed=error_embed("Reset failed", str(exc)[:400]))


async def setup(bot: commands.Bot):
    await bot.add_cog(Branding(bot))
