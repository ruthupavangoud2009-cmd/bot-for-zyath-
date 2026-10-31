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

    def __init__(self, category_name: str):
        super().__init__(title=f"Open {category_name} Ticket")
        self.category_name = category_name

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category_name = self.category_name

        settings = await db.get_guild_settings(guild.id)
        parent_cat_id = settings.get("ticket_category_id")
        parent_cat = guild.get_channel(parent_cat_id) if parent_cat_id else None

        staff_role_id = settings.get("ticket_staff_role_id")
        staff_role = guild.get_role(staff_role_id) if staff_role_id else None

        clean_user_name = user.name.lower().replace(" ", "-")
        channel_name = f"ticket-{category_name.lower()[:4]}-{clean_user_name}"

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
            title=f"🎫 {category_name} Ticket",
            description=(
                f"Welcome {user.mention}! Support staff has been notified.\n\n"
                f"**📌 Subject:** `{self.subject.value}`\n"
                f"**📝 Details:**\n```{self.details.value or 'No additional details provided.'}```\n"
                f"Use the buttons below to manage this ticket."
            ),
            thumbnail=user.display_avatar.url
        )

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

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="ticket_transcript_btn")
    async def transcript_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        file = await generate_html_transcript(interaction.channel)
        await interaction.followup.send(content="📄 **Here is your ticket transcript:**", file=file)

    @discord.ui.button(label="Add Member", style=discord.ButtonStyle.primary, emoji="➕", custom_id="ticket_add_btn")
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

# --- Ticket Panel Views ---
class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Support", description="Need help, questions, or server support", emoji="🛠️", value="General Support"),
            discord.SelectOption(label="Buy / Order", description="Purchase products, services, or custom orders", emoji="🛒", value="Buy / Order"),
            discord.SelectOption(label="Middleman Service", description="Request a safe Middleman (MM) for trade", emoji="🤝", value="Middleman"),
            discord.SelectOption(label="Report / Appeal", description="Report a user, scam, or submit an appeal", emoji="⚠️", value="Report"),
        ]
        super().__init__(
            placeholder="🎟️ Select ticket category to open ticket form...",
            min_values=1,
            max_values=1,
            custom_id="ticket_category_select",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category_name = self.values[0]
        # Open Modal so user can enter subject and details
        await interaction.response.send_modal(CreateTicketModal(category_name))

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

    @discord.ui.button(label="🛒 Order", style=discord.ButtonStyle.success, emoji="🛒", custom_id="btn_panel_order")
    async def btn_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTicketModal("Buy / Order"))

    @discord.ui.button(label="🤝 Middleman", style=discord.ButtonStyle.primary, emoji="🤝", custom_id="btn_panel_mm")
    async def btn_mm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTicketModal("Middleman"))

    @discord.ui.button(label="🛠️ Support", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="btn_panel_support")
    async def btn_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTicketModal("General Support"))

# --- Cog Class ---
class Tickets(commands.Cog):
    """Advanced customizable ticket system with drop-down menus, modals, transcripts, claim & roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketControlsView())
        self.bot.add_view(TicketClosedControlsView())

    @commands.command(name="createembed", aliases=["embed", "ce", "emb"], help="Open the interactive custom embed creator modal.")
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
            embed=info_embed(
                "Embed Builder",
                f"Click below to build and send a custom embed to {target.mention}."
            ),
            view=view
        )

    @commands.command(name="invoice", aliases=["inv", "bill"], help="Send a payment invoice inside a ticket. E.g. $invoice $25.00 LTC [Product]")
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

    @commands.command(name="ticketpanel", aliases=["ticketsetup", "tp"], help="Send the ticket creation panel with categories and buttons.")
    @commands.has_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        embed = standard_embed(
            title="🎫 Support & Service Tickets",
            description=(
                "Need assistance, want to buy something, or require a Middleman?\n"
                "Use the menu or buttons below to open your private ticket!\n\n"
                "🔹 **General Support**: Inquiries, questions, help\n"
                "🔹 **Buy / Order**: Order products or services\n"
                "🔹 **Middleman Service**: Secure trade mediation\n"
                "🔹 **Report / Appeal**: User reports and disputes\n\n"
                "⚡ *A staff member will assist you immediately.*"
            )
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await channel.send(embed=embed, view=TicketPanelView())
        if channel.id != ctx.channel.id:
            await ctx.send(embed=success_embed("Panel Created", f"Ticket panel deployed in {channel.mention}."))

    @commands.command(name="setticketcategory", aliases=["stcat", "ticketcat"], help="Set the Discord category where tickets are created.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_category(self, ctx: commands.Context, category: discord.CategoryChannel):
        await db.update_guild_setting(ctx.guild.id, "ticket_category_id", category.id)
        await ctx.send(embed=success_embed("Ticket Category Configured", f"New tickets will be created under **{category.name}**."))

    @commands.command(name="setticketrole", aliases=["strole", "ticketrole"], help="Set the staff role that has access to tickets.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_role(self, ctx: commands.Context, role: discord.Role):
        await db.update_guild_setting(ctx.guild.id, "ticket_staff_role_id", role.id)
        await ctx.send(embed=success_embed("Ticket Role Configured", f"Support role set to {role.mention}."))

    @commands.command(name="setticketlogs", aliases=["stlogs", "ticketlogs"], help="Set the channel where ticket transcripts and close logs are sent.")
    @commands.has_permissions(administrator=True)
    async def set_ticket_logs(self, ctx: commands.Context, channel: discord.TextChannel):
        await db.update_guild_setting(ctx.guild.id, "ticket_logs_channel_id", channel.id)
        await ctx.send(embed=success_embed("Ticket Logs Configured", f"Ticket logs will be saved to {channel.mention}."))

    @commands.command(name="ticket", aliases=["t"], help="Ticket commands: close, add, remove, transcript")
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
        else:
            await ctx.send(embed=info_embed(
                "Ticket Commands",
                "• `$ticket close` - Close current ticket\n"
                "• `$ticket transcript` - Generate HTML transcript\n"
                "• `$ticket add @user` - Add user to ticket\n"
                "• `$ticket remove @user` - Remove user from ticket\n"
                "• `$createembed` - Build custom embed\n"
                "• `$invoice <amount> <method>` - Post payment invoice\n"
                "• `$ticketpanel` - Deploy ticket panel"
            ))

async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
