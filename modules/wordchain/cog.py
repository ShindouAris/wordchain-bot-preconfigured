from botbase import BotBase

import disnake
from disnake.ext import commands
import logging

from .dictionary import Dictionary, IllegalWordException, reform_word, check_input
from utils.cache import LRUCache
from utils.guild_data import GuildData
from utils.configuration import EPHEMERAL_AUDIT_ACTION, EPHEMERAL_ERROR_ACTION
from cambridge_dictionary import Cambridge_Dictionary
from oxford_dictionary import OxfordDictionary
from cambridge_dictionary.error import ApiError, NotFoundWord

logger: logging.Logger = logging.getLogger(__name__)

class ChainNotMatchException(Exception):
    def __init__(self, *args):
        super().__init__("Từ nhập vào không khớp với chuỗi từ hiện tại", *args)
    

class  CurrentIsLastPlayer(Exception):
    def __init__(self, *args):
        super().__init__("Người chơi hiện tại vừa chơi lượt trước đó", *args)


class DuplicateWordError(Exception):
    def __init__(self, *args, word: str, previous_message_url = None):
        self.previous_message_url = previous_message_url
        super().__init__(f"Từ {word} đã được sử dụng trước đó.", *args)

    
class GuildChain(LRUCache):
    __slots__ = "chain", "previous_last_character", "previous_player_id"
    
    def __init__(self):
        self.previous_last_character = ""
        self.previous_player_id = 0
        super().__init__(5000, -1)
        
    def add_word(self, word: str, message_url: str, player_id: int):
        if self.previous_player_id == player_id: raise CurrentIsLastPlayer()
        word = reform_word(word)
        if not word.startswith(self.previous_last_character): raise ChainNotMatchException()
        try: data = self.get(word)
        except KeyError: data = None
        if data is not None: raise DuplicateWordError(word=word, previous_message_url=data)
        self.put(word, message_url)
        self.previous_last_character = word[-1]
        self.previous_player_id = player_id
        
        
GAME_ACTIVATED_NOTIFICATION_EMBED = disnake.Embed(
    title="Trò chơi nối từ đã được kích hoạt tại kênh này",
    description="""
        __**Hướng dẫn chơi:** Hãy gửi một từ đơn đáp ứng các yêu cầu sau__
        
        ✨ *Là một từ đơn hợp lệ trong tiếng Anh*
        ✨ *Có ít nhất 3 chữ cái, không chứa các dấu, số hay kí tự đặc biệt*
        ✨ *Từ bắt đầu bằng chữ cái cuối cùng của người chơi có từ hợp lệ gần nhất*
        
        🌙 *Để trò chơi bỏ qua tin nhắn của bạn, hãy thêm dấu `.`(chấm) vào trước tin nhắn*
        📝 *Hãy thông báo cho người quản trị bot nếu gặp lỗi khi chơi nhé*
    """,
    color=0x00FFFF
)
        

class WordChain(commands.Cog):
    def __init__(self, bot: BotBase):
        self.bot: BotBase = bot
        self.dictionary: Dictionary = Dictionary()
        self.storage: dict[int, GuildChain] = {}
        self.guild_data: GuildData = bot.guild_data
        self.combo = 0
        self.cambridge_dictionary = Cambridge_Dictionary()
        self.oxford_dictionary = OxfordDictionary()

        
    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.guild is None: return
        if message.author.bot: return
        if message.is_system(): return
        if message.webhook_id is not None: return
        if not isinstance(message.channel, disnake.TextChannel): return
        guild_id = message.guild.id
        msg_content = message.content.strip()
        if not check_input(msg_content):
            return
        msg_split = msg_content.split()
        entity = await self.guild_data.get_guild(guild_id)
        if entity.wordchain_channel_id != message.channel.id: return
        if self.storage.get(message.guild.id) is None: self.storage[guild_id] = GuildChain()
        chain = self.storage[guild_id]
        try:
            if msg_split.__len__() != 1 or msg_split[0].__len__() < 3 or (not msg_split[0].isalpha()): raise IllegalWordException()
            if not self.dictionary.check(msg_split[0]):
                try:
                    check = await self.cambridge_dictionary.dictionary_check(msg_split[0])
                except NotFoundWord or ApiError:
                    check = await self.oxford_dictionary.check_word_async(msg_split[0])
                if not check:
                    raise IllegalWordException()
            chain.add_word(msg_split[0], message.jump_url, message.author.id)
            await message.add_reaction("✅")
            self.combo += 1
            if self.combo in (10, 50, 100, 1000, 2000, 6000, 9999):
                await message.reply("Tuyệt vời, combo của máy chủ hiện tại là: {}".format(self.combo), fail_if_not_exists=True, delete_after=10)
        except DuplicateWordError as err:
            await message.add_reaction("<:Hoshino_derp:1233102226197581874>")
            if self.combo:
                txt = f", bạn đã mất chuỗi {self.combo} từ liên tiếp đúng và không lặp lại"
            else:
                txt = ""
            await message.reply(f"⚠️ Từ này đã được sử dụng {err.previous_message_url}{txt}", fail_if_not_exists=False, delete_after=10)
            self.combo = 0
        except CurrentIsLastPlayer:
            await message.reply(f"🕒 Vui lòng đợi người chơi khác điền từ của họ trước khi điền từ của bạn vào nhé", fail_if_not_exists=True, delete_after=10)
        except ChainNotMatchException:
            if self.combo:
                txt = f", bạn đã mất chuỗi {self.combo} từ liên tiếp đúng và không lặp lại"
            else:
                txt = ""
            await message.reply(f"❌ Hãy chọn một từ khác bắt đầu bằng `{chain.previous_last_character}` nhé{txt}", fail_if_not_exists=False, delete_after=10)
            self.combo = 0
        except IllegalWordException:
            if self.combo:
                txt = f", bạn đã mất chuỗi {self.combo} từ liên tiếp đúng và không lặp lại"
            else:
                txt = ""
            try:
                await message.add_reaction("<:catto_depress:1233102216940884019>")
            except Exception:
                pass
            await message.reply(f"❌ Vui lòng nhập một từ tiếng Anh hợp lệ, tối thiểu 3 chữ cái và không chứa kí tự đặc biệt{txt}", fail_if_not_exists=False, delete_after=10)
            self.combo = 0
            
        
    @commands.slash_command(
        name="wordchain",
        dm_permission=False,
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def wordchain(self, inter: disnake.ApplicationCommandInteraction): pass
    
    
    @wordchain.sub_command(
        name="start",
        description="Kích hoạt trò chơi nối từ trên máy chủ ở kênh hiện tại"
    )
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(administrator=True)
    @commands.cooldown(1, 60)
    async def start(self, inter: disnake.ApplicationCommandInteraction):
        if not isinstance(inter.channel, disnake.TextChannel):
            await inter.response.send_message("❌ Trò chơi chỉ hoạt động trên kênh văn bản bình thường", ephemeral=EPHEMERAL_ERROR_ACTION)
            return
        await inter.response.defer(ephemeral=EPHEMERAL_AUDIT_ACTION)
        entity = await self.guild_data.get_guild(inter.guild_id)
        if entity.wordchain_channel_id != 0:
            await inter.edit_original_response(f"⚠️ Trò chơi đã được cấu hình trên máy chủ tại kênh https://discord.com/channels/{inter.guild_id}/{entity.wordchain_channel_id}\n"
                                                "        Hãy hủy trò chơi ở kênh cũ bằng lệnh `/wordchain stop` trước khi đặt trò chơi ở kênh mới")
            return
        entity.wordchain_channel_id = inter.channel_id
        await self.guild_data.update_guild(entity)
        await inter.channel.send(embed=GAME_ACTIVATED_NOTIFICATION_EMBED)
        await inter.edit_original_response("✅ Đã kích hoạt trò chơi nối từ trên máy chủ tại kênh này")

    
    @wordchain.sub_command(
        name="stop",
        description="Dừng trò chơi nối từ trên máy chủ"
    )
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.cooldown(1, 60)
    async def stop(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None: return
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message("❌ Bạn cần có quyền `Quản trị máy chủ` để sử dụng lệnh này", ephemeral=EPHEMERAL_ERROR_ACTION)
            return
        await inter.response.defer(ephemeral=EPHEMERAL_AUDIT_ACTION)
        entity = await self.guild_data.get_guild(inter.guild_id)
        channel_id = entity.wordchain_channel_id
        entity.wordchain_channel_id = 0
        await self.guild_data.update_guild(entity)
        self.storage.pop(channel_id, None)
        await inter.edit_original_response("✅ Đã dừng trò chơi nối từ trên máy chủ")
