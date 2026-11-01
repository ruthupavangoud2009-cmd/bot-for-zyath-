import discord
from discord.ext import commands
import asyncio
from utils.embeds import standard_embed, success_embed, error_embed, info_embed, warning_embed
from utils.database import db
from utils.transcript import generate_html_transcript, generate_text_transcript
from utils.ticket_creator import create_safe_ticket_channel

# --- Modals ---
class CreateEmbedModal(discord.ui.Modal, title="Create Custom Embed"):
    embed_title = discord.ui.TextInput(
        label="Embed Title",
        placeholder="Enter embed title...",
        required=False
    )
    embed_description = discord.ui.TextInput(
        label="Embed Description",
        placeholder="Enter description (Markdown supported)...",
        style=discord.TextStyle.paragraph,
        required=True
    )
    embed_color = discord.ui.TextInput(
        label="Color (Hex e.g. #5865F2 or green/red)",
        placeholder="#5865F2",
        required=False
    )
    embed_image = discord.ui.TextInput(
        label="Image / Banner URL",
        placeholder="https://example.com/banner.png",
        required=False
    )
    embed_footer = discord.ui.TextInput(
        label="Footer Text",
        placeholder="Footer text...",
        required=False
    )

    def __init__(self, target_channel: discord.TextChannel = None):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        # Resolve color
        color_val = 0x5865F2
        raw_color = self.embed_color.value.strip().lower()
        color_map = {
            "green": 0x57F287, "red": 0xED4245, "yellow": 0xFEE75C,
            "blue": 0x3498DB, "gold": 0xF1C40F, "purple": 0x9B59B6
        }
        if raw_color in color_map:
            color_val = color_map[raw_color]
        elif raw_color.startswith("#"):
            try:
                color_val = int(raw_color.replace("#", ""), 16)
            except Exception:
                pass

        embed = discord.Embed(
            title=self.embed_title.value or None,
            description=self.embed_description.value,
            color=color_val,
            timestamp=discord.utils.utcnow()
        )
        if self.embed_image.value.strip().startswith("http"):
            embed.set_image(url=self.embed_image.value.strip())
        if self.embed_footer.value.strip():
            embed.set_footer(text=self.embed_footer.value.strip())
        else:
            embed.set_footer(text=f"Sent via Zyath Embed Creator • {interaction.guild.name}")

        channel = self.target_channel or interaction.channel
        await channel.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Embed Sent", f"Your custom embed was posted to {channel.mention}!"),
            ephemeral=True
        )

class CreateTicketModal(discord.ui.Modal):
    subject = discord.ui.TextInput(
        label="Subject / What do you need?",
        placeholder="e.g. Buying Nitro, Middleman Trade, Question",
        required=True
    )
    details = discord.ui.TextInput(
        label="Details & Budget",
        placeholder="Provide all details, payment method, or item description...",
        style=discord.TextStyle.paragraph,
        required=False
    )

    def __init__(self, category_name: str, guild_id: int = None, default_subject: str = None):
        super().__init__(title=f"Open {category_name[:35]} Ticket")
        self.category_name = category_name
        self.guild_id = guild_id
        if default_subject:
            self.subject.default = default_subject[:100]

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category_name = self.category_name

        # Look up modular category configurations
        cat_info = await db.get_ticket_category(guild.id, category_name)
        cat_emoji = cat_info.get("emoji", "🎫") if cat_info else "🎫"
        cat_channel_id = cat_info.get("category_channel_id") if cat_info else None
        cat_role_id = cat_info.get("staff_role_id") if cat_info else None

        settings = await db.get_guild_settings(guild.id)
        parent_cat_id = cat_channel_id or settings.get("ticket_category_id")
        parent_cat = guild.get_channel(parent_cat_id) if parent_cat_id else None

        staff_role_id = cat_role_id or settings.get("ticket_staff_role_id")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        clean_user_name = "".join(c for c in user.name.lower() if c.isalnum() or c in "-_")
        clean_cat = "".join(c for c in category_name.lower() if c.isalnum())[:6]
        channel_name = f"ticket-{clean_cat}-{clean_user_name}"[:32]

        try:
            ticket_channel = await create_safe_ticket_channel(
                guild=guild,
                user=user,
                channel_name=channel_name,
                category=parent_cat,
                staff_role=staff_role,
                topic=f"Ticket for {user.name} | Category: {category_name} | Subject: {self.subject.value}"
            )
        except Exception as e:
            return await interaction.response.send_message(embed=error_embed("Failed to Create Ticket", str(e)), ephemeral=True)

        await db.create_ticket_record(guild.id, ticket_channel.id, user.id, category_name)
        await interaction.response.send_message(embed=success_embed("Ticket Created", f"Your ticket has been created at {ticket_channel.mention}!"), ephemeral=True)

        mention_str = user.mention
        if staff_role:
            mention_str += f" | {staff_role.mention}"

        welcome_ticket_embed = standard_embed(
            title=f"{cat_emoji} {category_name} • #{ticket_channel.name}",
            description=(
                f"> Welcome {user.mention}! Support staff and the Zyath AI Assistant have been notified.\n\n"
                f"• **Ticket Creator:** {user.mention}\n"
                f"• **Assigned Staff:** {staff_role.mention if staff_role else '*All Support Staff*'}\n"
                f"• **Category:** `{category_name}`\n"
                f"• **AI Manager:** `Active (24/7 Monitoring)`\n\n"
                f"📌 **Subject:** `{self.subject.value}`\n"
                f"📝 **Details:**\n```{self.details.value or 'No additional details provided.'}```\n\n"
                "⚡ *Staff will assist you shortly. If staff is away, our AI Assistant is active!*"
            ),
            color=0x2B2D31,
            thumbnail=user.display_avatar.url
        )
        welcome_ticket_embed.set_footer(text=f"Zyath Support Desk • Ticket ID: {ticket_channel.id}")

        await ticket_channel.send(content=mention_str, embed=welcome_ticket_embed, view=TicketControlsView())

class AddUserModal(discord.ui.Modal, title="Add Member to Ticket"):
    user_id = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="Enter user ID (e.g. 1234567890)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.replace("<@", "").replace(">", "").replace("!", "").strip()
        try:
            member = interaction.guild.get_member(int(raw)) or await interaction.guild.fetch_member(int(raw))
            if not member:
                return await interaction.response.send_message(embed=error_embed("Member Not Found", "Could not find that member in this server."), ephemeral=True)
            
            await interaction.channel.set_permissions(member, view_channel=True, send_messages=True, attach_files=True, embed_links=True)
            await interaction.response.send_message(embed=success_embed("Member Added", f"{member.mention} has been added to this ticket."))
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Error", f"Failed to add member: {str(e)}"), ephemeral=True)

class RemoveUserModal(discord.ui.Modal, title="Remove Member from Ticket"):
    user_id = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="Enter user ID (e.g. 1234567890)",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.user_id.value.replace("<@", "").replace(">", "").replace("!", "").strip()
        try:
            member = interaction.guild.get_member(int(raw)) or await interaction.guild.fetch_member(int(raw))
            if not member:
                return await interaction.response.send_message(embed=error_embed("Member Not Found", "Could not find that member in this server."), ephemeral=True)
            
            await interaction.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(embed=success_embed("Member Removed", f"{member.mention} has been removed from this ticket."))
        except Exception as e:
            await interaction.response.send_message(embed=error_embed("Error", f"Failed to remove member: {str(e)}"), ephemeral=True)

class CreateInvoiceModal(discord.ui.Modal, title="Issue Order Invoice"):
    amount = discord.ui.TextInput(label="Amount Due", placeholder="e.g. $25.00 / 0.05 LTC", required=True)
    method = discord.ui.TextInput(label="Payment Method / Address", placeholder="e.g. LTC: ltc1q... / PayPal: user@email", required=True)
    product = discord.ui.TextInput(label="Product / Item", placeholder="e.g. Discord Nitro 1 Year", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = standard_embed(
            title=f"🧾 Official Invoice • {self.product.value}",
            description=(
                f"**Amount Due:** `{self.amount.value}`\n"
                f"**Payment Method / Address:**\n```{self.method.value}```\n\n"
                f"Please send the exact amount to complete your order.\n"
                f"Once paid, send a screenshot of the transaction here."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text=f"Issued by {interaction.user.display_name} • Zyath Store")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Invoice sent successfully!", ephemeral=True)

# --- Ticket Action Views ---
class TicketControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_btn")
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        record = await db.get_ticket_record(interaction.channel_id)
        if not record:
            return await interaction.response.send_message("This channel is not an active database ticket.", ephemeral=True)
        
        await interaction.response.defer()
        await db.close_ticket_record(interaction.channel_id)

        creator = interaction.guild.get_member(record['user_id'])
        if creator:
            await interaction.channel.set_permissions(creator, view_channel=True, send_messages=False)

        close_embed = warning_embed(
            "Ticket Closed",
            f"Ticket was closed by {interaction.user.mention}.\nUse the buttons below to re-open, save transcript, leave a vouch, or delete."
        )
        await interaction.channel.send(embed=close_embed, view=TicketClosedControlsView())

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="ticket_claim_btn")
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await db.get_guild_settings(interaction.guild_id)
        staff_role_id = settings.get("ticket_staff_role_id")
        
        is_staff = interaction.user.guild_permissions.administrator
        if staff_role_id:
            role = interaction.guild.get_role(staff_role_id)
            if role and role in interaction.user.roles:
                is_staff = True

        if not is_staff:
            return await interaction.response.send_message(embed=error_embed("Access Denied", "Only support staff can claim this ticket."), ephemeral=True)

        record = await db.get_ticket_record(interaction.channel_id)
        if record and record.get("claimed_by"):
            claimed_by = interaction.guild.get_member(record["claimed_by"])
            name = claimed_by.mention if claimed_by else f"ID: {record['claimed_by']}"
            return await interaction.response.send_message(embed=warning_embed("Already Claimed", f"This ticket has already been claimed by {name}."), ephemeral=True)

        await db.claim_ticket(interaction.channel_id, interaction.user.id)
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(embed=success_embed("Ticket Claimed", f"🌟 {interaction.user.mention} is now handling this ticket!"))

    @discord.ui.button(label="Invoice", style=discord.ButtonStyle.primary, emoji="🧾", custom_id="ticket_invoice_btn")
    async def invoice_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        settings = await db.get_guild_settings(interaction.guild_id)
        staff_role_id = settings.get("ticket_staff_role_id")
        is_staff = interaction.user.guild_permissions.manage_messages
        if staff_role_id:
            role = interaction.guild.get_role(staff_role_id)
            if role and role in interaction.user.roles:
                is_staff = True
        if not is_staff:
            return await interaction.response.send_message(embed=error_embed("Access Denied", "Only staff can issue invoices."), ephemeral=True)
        await interaction.response.send_modal(CreateInvoiceModal())

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="ticket_transcript_btn")
    async def transcript_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        file = await generate_html_transcript(interaction.channel)
        await interaction.followup.send(content="📄 **Here is your ticket transcript:**", file=file)

    @discord.ui.button(label="Add Member", style=discord.ButtonStyle.secondary, emoji="➕", custom_id="ticket_add_btn")
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="Remove Member", style=discord.ButtonStyle.secondary, emoji="➖", custom_id="ticket_rem_btn")
    async def rem_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveUserModal())

class TicketClosedControlsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Re-Open", style=discord.ButtonStyle.success, emoji="🔓", custom_id="ticket_reopen_btn")
    async def reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        record = await db.get_ticket_record(interaction.channel_id)
        if record:
            await db.reopen_ticket_record(interaction.channel_id)
            creator = interaction.guild.get_member(record['user_id'])
            if creator:
                await interaction.channel.set_permissions(creator, view_channel=True, send_messages=True)

        await interaction.response.send_message(embed=success_embed("Ticket Re-Opened", f"Ticket re-opened by {interaction.user.mention}."))

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="ticket_closed_trans_btn")
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        file = await generate_html_transcript(interaction.channel)
        await interaction.followup.send(content="📄 **Transcript generated:**", file=file)

    @discord.ui.button(label="⭐ Leave Vouch", style=discord.ButtonStyle.primary, emoji="⭐", custom_id="ticket_closed_vouch_btn")
    async def leave_vouch(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=info_embed("Leave a Vouch", "To submit your review, use:\n`$vouch @seller [1-5 stars] [Your review]`"),
            ephemeral=True
        )

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="ticket_delete_btn")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(embed=error_embed("Deleting Ticket", "Ticket will be deleted in 5 seconds..."))
        
        settings = await db.get_guild_settings(interaction.guild_id)
        logs_id = settings.get("ticket_logs_channel_id")
        if logs_id:
            log_chan = interaction.guild.get_channel(logs_id)
            if log_chan:
                try:
                    record = await db.get_ticket_record(interaction.channel_id)
                    creator_str = f"<@{record['user_id']}>" if record else "Unknown"
                    log_embed = standard_embed(
                        title="Ticket Log Archived",
                        description=f"**Ticket:** #{interaction.channel.name}\n**Creator:** {creator_str}\n**Deleted By:** {interaction.user.mention}"
                    )
                    trans_file = await generate_html_transcript(interaction.channel)
                    await log_chan.send(embed=log_embed, file=trans_file)
                except Exception:
                    pass

        await asyncio.sleep(5)
        await db.delete_ticket_record(interaction.channel_id)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

# --- Modular Ticket Panel Views ---
class ModularTicketCategorySelect(discord.ui.Select):
    def __init__(self, categories: list = None):
        options = []
        cats = categories or []
        for cat in cats[:25]:
            desc = cat.get("description") or "Open a ticket in this category"
            options.append(discord.SelectOption(
                label=cat["name"][:100],
                emoji=cat.get("emoji") or "🎫",
                description=desc[:100],
                value=cat["name"]
            ))
        if not options:
            options = [
                discord.SelectOption(label="Buy / Order", emoji="🛒", description="Purchase products, services, or custom orders", value="Buy / Order"),
                discord.SelectOption(label="Middleman", emoji="🤝", description="Request a trusted Middleman (MM) for safe trades", value="Middleman"),
                discord.SelectOption(label="General Support", emoji="🛠️", description="Need help, questions, or server support", value="General Support"),
                discord.SelectOption(label="Report / Dispute", emoji="⚠️", description="Report a user, scam, or submit an appeal", value="Report / Dispute")
            ]
        super().__init__(
            placeholder="🎟️ Select ticket category to open form...",
            min_values=1,
            max_values=1,
            custom_id="modular_ticket_select",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0]
        await interaction.response.send_modal(CreateTicketModal(category_name, interaction.guild_id))

class ModularTicketButton(discord.ui.Button):
    def __init__(self, category_name: str, emoji: str = "🎫", style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(
            label=category_name[:80],
            emoji=emoji,
            style=style,
            custom_id=f"modtkt:{category_name}"
        )
        self.category_name = category_name

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CreateTicketModal(self.category_name, interaction.guild_id))

class TicketPanelView(discord.ui.View):
    def __init__(self, categories: list = None, bot_user_id: int = None):
        super().__init__(timeout=None)
        cats = categories or [
            {"name": "Buy / Order", "emoji": "🛒", "description": "Purchase products, services, or custom orders"},
            {"name": "Middleman", "emoji": "🤝", "description": "Request a trusted Middleman (MM) for safe trades"},
            {"name": "General Support", "emoji": "🛠️", "description": "Need help, questions, or server support"},
            {"name": "Report / Dispute", "emoji": "⚠️", "description": "Report a user, scam, or submit an appeal"}
        ]
        self.add_item(ModularTicketCategorySelect(cats))
        styles = [
            discord.ButtonStyle.success,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.danger,
            discord.ButtonStyle.primary
        ]
        for idx, cat in enumerate(cats[:5]):
            style = styles[idx % len(styles)]
            self.add_item(ModularTicketButton(
                category_name=cat["name"],
                emoji=cat.get("emoji") or "🎫",
                style=style
            ))

        # Add link buttons matching Help module
        client_id = bot_user_id or 1521774957065928734
        invite_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
        self.add_item(discord.ui.Button(label="Invite Zyath", style=discord.ButtonStyle.link, url=invite_url, emoji="🚀"))
        from utils.config_manager import get_support_server
        self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.link, url=get_support_server(), emoji="💬"))

# --- Cog Class ---
class Tickets(commands.Cog):
    """Ultra-modular ticket system with customizable categories, modals, buttons, transcripts, and routing."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Register persistent views with timeout=None
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlsView())
        self.bot.add_view(TicketClosedControlsView())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Global persistent listener for modular category buttons and selects across bot reboots."""
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if cid.startswith("modtkt:"):
            cat_name = cid.split("modtkt:", 1)[1]
            await interaction.response.send_modal(CreateTicketModal(cat_name, interaction.guild_id))
        elif cid == "modular_ticket_select":
            vals = interaction.data.get("values", [])
            if vals:
                await interaction.response.send_modal(CreateTicketModal(vals[0], interaction.guild_id))
        elif cid == "restock_open_ticket_btn":
            await interaction.response.send_modal(CreateTicketModal("Buy / Order", interaction.guild_id, default_subject="Order: Restocked Item"))

    @commands.command(name="createembed", aliases=["embed"], help="Open the interactive custom embed creator modal.")
    @commands.has_permissions(manage_messages=True)
    async def create_embed_cmd(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        view = discord.ui.View()
        async def btn_cb(interaction: discord.Interaction):
            await interaction.response.send_modal(CreateEmbedModal(target))
        btn = discord.ui.Button(label="Open Embed Builder", style=discord.ButtonStyle.primary, emoji="🎨")
        btn.callback = btn_cb
        view.add_item(btn)
        await ctx.send(
            embed=info_embed("Embed Builder", f"Click below to build and send a custom embed to {target.mention}."),
            view=view
        )

    @commands.command(name="invoice", aliases=["bill"], help="Send a payment invoice inside a ticket. E.g. $invoice $25.00 LTC [Product]")
    @commands.has_permissions(manage_messages=True)
    async def send_invoice(self, ctx: commands.Context, amount: str, method: str, *, product: str = "Order Item"):
        embed = standard_embed(
            title=f"🧾 Official Invoice • {product}",
            description=(
                f"**Amount Due:** `{amount}`\n"
                f"**Payment Method:** `{method}`\n\n"
                f"Please send the exact amount to complete your order.\n"
                f"Once paid, send a screenshot of the transaction here."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text=f"Issued by {ctx.author.display_name} • Zyath Store")
        await ctx.send(embed=embed)

    @commands.command(name="ticketpanel", aliases=["ticketsetup"], help="Deploy the dynamic modular ticket creation panel.")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        target = channel or ctx.channel
        categories = await db.get_ticket_categories(ctx.guild.id)
        stats = await db.get_ticket_stats(ctx.guild.id)
        bot_name = self.bot.user.name if self.bot.user else "Zyath"

        cat_bullets = []
        for cat in categories:
            cat_bullets.append(f"• **{cat.get('emoji', '🎫')} {cat['name']}**\n  └ *{cat.get('description', 'Click to open ticket')}*")
        cat_desc = "\n".join(cat_bullets)

        embed = standard_embed(
            title=f"Hey, I'm {bot_name} • Support Desk",
            description=(
                "> Built for our community — keeping orders safe, tickets verified, and support instant.\n\n"
                f"• **Support Status:** `🟢 Active 24/7` | **AI Assistant:** `Online`\n"
                f"• **Available Hubs:** `{len(categories)} Modules` | **Resolved:** `{stats['total']}` Tickets\n"
                f"• **Prefix:** `$` | **Slash:** `/`\n\n"
                f"{cat_desc}\n\n"
                "⚡ *Select a category from the dropdown or click a quick button below to open a ticket.*"
            ),
            color=0x2B2D31
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text=f"Zyath Modular Desk • {ctx.guild.name}")

        bot_id = self.bot.user.id if self.bot.user else None
        await target.send(embed=embed, view=TicketPanelView(categories, bot_user_id=bot_id))
        if target.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Panel Deployed", f"Modular ticket panel deployed in {target.mention}."))

    @commands.command(name="addcategory", aliases=["addticketcategory"], help="Add or update a modular ticket category. E.g. $addcategory Nitro & Boosts | ⚡ | Cheap Discord Nitro")
    @commands.has_permissions(administrator=True)
    async def add_category(self, ctx: commands.Context, *, raw_input: str):
        parts = [p.strip() for p in raw_input.split("|")]
        name = parts[0]
        emoji = parts[1] if len(parts) > 1 else "🎫"
        description = parts[2] if len(parts) > 2 else "Open a support ticket"

        await db.add_ticket_category(ctx.guild.id, name, emoji, description)
        await ctx.send(embed=success_embed(
            "Category Configured",
            f"✅ Modular ticket category **{emoji} {name}** has been added/updated!\n\n"
            f"**Description:** `{description}`\n\n"
            f"💡 **Next Steps:**\n"
            f"• Route to specific Discord channel: `$setcategorychannel \"{name}\" #Category`\n"
            f"• Assign specific staff role: `$setcategoryrole \"{name}\" @Role`\n"
            f"• Refresh ticket panel: `$ticketpanel`"
        ))

    @commands.command(name="delcategory", aliases=["removeticketcategory", "deletecategory"], help="Delete a modular ticket category. E.g. $delcategory Nitro & Boosts")
    @commands.has_permissions(administrator=True)
    async def del_category(self, ctx: commands.Context, *, category_name: str):
        clean_name = category_name.strip().strip('"').strip("'")
        success = await db.remove_ticket_category(ctx.guild.id, clean_name)
        if success:
            await ctx.send(embed=success_embed("Category Removed", f"Deleted category **{clean_name}**.\nRun `$ticketpanel` to deploy an updated panel."))
        else:
            await ctx.send(embed=error_embed("Not Found", f"No category named `{clean_name}` found.\nCheck active categories with `$categories`."))

    @commands.command(name="categories", aliases=["ticketcategories", "listcategories"], help="List all modular ticket categories configured in this server.")
    async def list_categories(self, ctx: commands.Context):
        categories = await db.get_ticket_categories(ctx.guild.id)
        embed = standard_embed(
            title=f"🎫 {ctx.guild.name} Modular Categories",
            description="All active ticket modules in this server. Use `$ticketpanel` to deploy.",
            color=0x5865F2
        )
        for cat in categories:
            chan_str = f"<#{cat['category_channel_id']}>" if cat.get("category_channel_id") else "*Server Default*"
            role_str = f"<@&{cat['staff_role_id']}>" if cat.get("staff_role_id") else "*Server Default*"
            embed.add_field(
                name=f"{cat.get('emoji', '🎫')} {cat['name']}",
                value=(
                    f"**Description:** *{cat.get('description', 'N/A')}*\n"
                    f"**Channel:** {chan_str} | **Staff:** {role_str}"
                ),
                inline=False
            )
        embed.set_footer(text=f"Total: {len(categories)} categories • Manage: $addcategory / $delcategory")
        await ctx.send(embed=embed)

    @commands.command(name="setcategorychannel", help="Route a ticket category to a specific Discord category channel. E.g. $setcategorychannel \"Buy / Order\" #ORDERS")
    @commands.has_permissions(administrator=True)
    async def set_category_channel(self, ctx: commands.Context, category_name: str, channel: discord.CategoryChannel):
        clean_name = category_name.strip().strip('"').strip("'")
        success = await db.update_ticket_category(ctx.guild.id, clean_name, category_channel_id=channel.id)
        if success:
            await ctx.send(embed=success_embed("Routing Configured", f"Tickets opened for **{clean_name}** will now be created in **{channel.name}**!"))
        else:
            await ctx.send(embed=error_embed("Category Not Found", f"Category `{clean_name}` not found. Check `$categories`."))

    @commands.command(name="setcategoryrole", help="Assign a specific staff role to a ticket category. E.g. $setcategoryrole \"Buy / Order\" @Sales")
    @commands.has_permissions(administrator=True)
    async def set_category_role(self, ctx: commands.Context, category_name: str, role: discord.Role):
        clean_name = category_name.strip().strip('"').strip("'")
        success = await db.update_ticket_category(ctx.guild.id, clean_name, staff_role_id=role.id)
        if success:
            await ctx.send(embed=success_embed("Staff Role Configured", f"Tickets for **{clean_name}** will now alert {role.mention}!"))
        else:
            await ctx.send(embed=error_embed("Category Not Found", f"Category `{clean_name}` not found. Check `$categories`."))

    @commands.command(name="resetticketcategories", help="Reset server ticket categories back to standard 4 modular modules.")
    @commands.has_permissions(administrator=True)
    async def reset_categories(self, ctx: commands.Context):
        cats = await db.reset_ticket_categories(ctx.guild.id)
        await ctx.send(embed=success_embed("Categories Reset", f"Restored {len(cats)} default modular categories (Buy / Order, Middleman, General Support, Report)."))

    @commands.command(name="setticketcategory", aliases=["ticketcat"], help="Set the default Discord category where tickets are created.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_category(self, ctx: commands.Context, category: discord.CategoryChannel):
        await db.update_guild_setting(ctx.guild.id, "ticket_category_id", category.id)
        await ctx.send(embed=success_embed("Ticket Category Configured", f"New tickets will be created under **{category.name}**."))

    @commands.command(name="setticketrole", aliases=["ticketrole"], help="Set the default staff role that has access to tickets.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_role(self, ctx: commands.Context, role: discord.Role):
        await db.update_guild_setting(ctx.guild.id, "ticket_staff_role_id", role.id)
        await ctx.send(embed=success_embed("Ticket Role Configured", f"Support role set to {role.mention}."))

    @commands.command(name="setticketlogs", aliases=["ticketlogs"], help="Set the channel where ticket transcripts and close logs are sent.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_logs(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "ticket_logs_channel_id", channel.id)
        await ctx.send(embed=success_embed("Ticket Logs Configured", f"Ticket logs will be saved to {channel.mention}."))

    @commands.command(name="ticket", help="Ticket commands: close, add, remove, transcript")
    async def ticket_cmd(self, ctx: commands.Context, action: str = "help", *, target: str = None):
        action = action.lower()
        if action == "close":
            record = await db.get_ticket_record(ctx.channel.id)
            if not record:
                return await ctx.send(embed=error_embed("Not a Ticket", "This channel is not an active ticket."))
            await db.close_ticket_record(ctx.channel.id)
            close_embed = warning_embed("Ticket Closed", f"Ticket was closed by {ctx.author.mention}.")
            await ctx.send(embed=close_embed, view=TicketClosedControlsView())

        elif action == "transcript":
            file = await generate_html_transcript(ctx.channel)
            await ctx.send(content="📄 **Ticket Transcript:**", file=file)

        elif action == "add":
            if not target:
                return await ctx.send(embed=error_embed("Missing Argument", "Usage: `$ticket add @user`"))
            clean = target.replace("<@", "").replace(">", "").replace("!", "").strip()
            try:
                member = ctx.guild.get_member(int(clean))
                if member:
                    await ctx.channel.set_permissions(member, view_channel=True, send_messages=True)
                    await ctx.send(embed=success_embed("Member Added", f"{member.mention} was added to this ticket."))
            except Exception as e:
                await ctx.send(embed=error_embed("Error", str(e)))

        elif action in ["remove", "rem"]:
            if not target:
                return await ctx.send(embed=error_embed("Missing Argument", "Usage: `$ticket remove @user`"))
            clean = target.replace("<@", "").replace(">", "").replace("!", "").strip()
            try:
                member = ctx.guild.get_member(int(clean))
                if member:
                    await ctx.channel.set_permissions(member, overwrite=None)
                    await ctx.send(embed=success_embed("Member Removed", f"{member.mention} was removed from this ticket."))
            except Exception as e:
                await ctx.send(embed=error_embed("Error", str(e)))

        elif action in ["stats", "dashboard"]:
            stats = await db.get_ticket_stats(ctx.guild.id)
            embed = standard_embed(
                title=f"📊 {ctx.guild.name} • Ticket System Dashboard",
                description=(
                    "> Live real-time analytics for the automated server support portal.\n\n"
                    f"• **Total Tickets Created:** `{stats['total']}`\n"
                    f"• **Active Open Tickets:** `🟢 {stats['open']}`\n"
                    f"• **Resolved & Closed:** `🔒 {stats['closed']}`\n"
                ),
                color=0x2B2D31
            )
            if stats["categories"]:
                cat_lines = [f"• **{cat}**: `{cnt}` tickets" for cat, cnt in stats["categories"].items()]
                embed.add_field(name="📌 Top Modules", value="\n".join(cat_lines), inline=False)
            embed.set_footer(text=f"Zyath Ticket Analytics • Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)

        elif action == "rename":
            if not target:
                return await ctx.send(embed=error_embed("Missing Argument", "Usage: `$ticket rename <new_name>`"))
            clean_name = target.lower().replace(" ", "-")[:32]
            try:
                await ctx.channel.edit(name=clean_name)
                await ctx.send(embed=success_embed("Ticket Renamed", f"Channel renamed to `#{clean_name}`."))
            except Exception as e:
                await ctx.send(embed=error_embed("Rename Failed", str(e)))

        elif action == "priority":
            if not target:
                return await ctx.send(embed=error_embed("Missing Argument", "Usage: `$ticket priority <low|normal|high|urgent>`"))
            level = target.upper()
            badge_map = {"LOW": "🟢 LOW", "NORMAL": "🟡 NORMAL", "HIGH": "🟠 HIGH", "URGENT": "🔴 URGENT"}
            badge = badge_map.get(level, f"⚪ {level}")
            try:
                await ctx.channel.edit(topic=f"[{level} PRIORITY] {ctx.channel.topic or ''}"[:1024])
            except Exception:
                pass
            embed = standard_embed(
                title=f"Priority Updated • {badge}",
                description=f"Ticket priority was set to **{badge}** by {ctx.author.mention}.",
                color=0xED4245 if "URGENT" in level else 0xFEE75C
            )
            await ctx.send(embed=embed)

        elif action == "alert":
            settings = await db.get_guild_settings(ctx.guild.id)
            staff_role_id = settings.get("ticket_staff_role_id")
            role = ctx.guild.get_role(staff_role_id) if staff_role_id else None
            mention_str = role.mention if role else "@everyone"
            embed = standard_embed(
                title="🚨 Urgent Staff Attention Required!",
                description=f"{ctx.author.mention} has requested urgent staff assistance in {ctx.channel.mention}!",
                color=0xED4245
            )
            await ctx.send(content=mention_str, embed=embed)

        elif action == "claim":
            settings = await db.get_guild_settings(ctx.guild.id)
            staff_role_id = settings.get("ticket_staff_role_id")
            is_staff = ctx.author.guild_permissions.administrator
            if staff_role_id:
                role = ctx.guild.get_role(staff_role_id)
                if role and role in ctx.author.roles:
                    is_staff = True
            if not is_staff:
                return await ctx.send(embed=error_embed("Access Denied", "Only support staff can claim tickets."))
            await db.claim_ticket(ctx.channel.id, ctx.author.id)
            await ctx.send(embed=success_embed("Ticket Claimed", f"🌟 {ctx.author.mention} is now handling this ticket!"))
        else:
            await ctx.send(embed=info_embed(
                "Ticket Commands",
                "• `$ticket close` - Close current ticket\n"
                "• `$ticket transcript` - Generate HTML transcript\n"
                "• `$ticket add @user` - Add user to ticket\n"
                "• `$ticket remove @user` - Remove user from ticket\n"
                "• `$ticket stats` - View ticket analytics dashboard\n"
                "• `$ticket rename <name>` - Rename active ticket channel\n"
                "• `$ticket priority <low|high|urgent>` - Set ticket priority\n"
                "• `$ticket alert` - Request urgent staff intervention\n"
                "• `$ticket claim` - Claim ticket for support staff\n"
                "• `$createembed` - Build custom embed\n"
                "• `$invoice <amount> <method>` - Post payment invoice\n"
                "• `$ticketpanel` - Deploy modular ticket panel\n"
                "• `$addcategory <name> | [emoji] | [desc]` - Add category\n"
                "• `$delcategory <name>` - Remove category\n"
                "• `$categories` - List modular categories"
            ))

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
