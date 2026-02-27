import discord
from discord import app_commands
from discord.ext import commands
import requests
import nest_asyncio
import asyncio
import random
from flask import Flask
from threading import Thread

# 1. 환경 설정
nest_asyncio.apply()

# 2. 24시간 호스팅용 웹 서버 (Flask)
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- [ 설정 데이터 ] ---
# 주의: 아래 토큰이 정확한지 다시 한번 확인하세요!
TOKEN = "MTQ3NjgyMzYwODMxOTAyMTA4Ng.GLsS9N.JS6gYKQvdLgI5HK7omdsDsv_eTGkCIpPS6SuDA" 
GROUP_ID = "17253423"
ROLE_NAME = "유저 | User"
verify_requests = {}

# --- [ 티켓 닫기 뷰 ] ---
class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="🔒 티켓 닫기", style=discord.ButtonStyle.red, custom_id="close_t")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("티켓을 삭제합니다.")
        await asyncio.sleep(3)
        await interaction.channel.delete()

# --- [ 인증 닉네임 입력창 ] ---
class VerifyModal(discord.ui.Modal, title="로블록스 계정 인증"):
    nick = discord.ui.TextInput(label="로블록스 닉네임", placeholder="닉네임을 입력하세요")
    async def on_submit(self, interaction: discord.Interaction):
        code = str(random.randint(100000, 999999))
        verify_requests[interaction.user.id] = {"name": self.nick.value, "code": code}
        embed = discord.Embed(title="🔐 인증 코드 발급", color=0x3498db)
        embed.description = f"로블록스 `{self.nick.value}` 프로필 소개글에 **{code}**를 적고 `/확인`을 입력하세요."
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- [ 메인 버튼 뷰 (인증 & 티켓) ] ---
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="인증 시작하기", style=discord.ButtonStyle.primary, custom_id="v_start")
    async def v_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

    @discord.ui.button(label="📩 문의하기", style=discord.ButtonStyle.secondary, custom_id="t_start")
    async def t_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ch = await guild.create_text_channel(name=f"티켓-{interaction.user.name}", overwrites=overwrites)
        await interaction.response.send_message(f"티켓이 생성되었습니다: {ch.mention}", ephemeral=True)
        await ch.send(f"{interaction.user.mention}님, 문의 내용을 남겨주세요.", view=TicketControl())

# --- [ 봇 클래스 ] ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())
    async def setup_hook(self):
        self.add_view(MainView())
        self.add_view(TicketControl())
        await self.tree.sync() # 슬래시 명령어 동기화

bot = MyBot()

@bot.tree.command(name="초기설정", description="인증 및 티켓 버튼 임베드를 생성합니다.")
@app_commands.checks.has_permissions(administrator=True)
async def 초기설정(interaction: discord.Interaction):
    embed = discord.Embed(title="수영구 시민 인증", description="아래 버튼을 눌러 인증을 시작하세요!\n솜솔 | 수영구청", color=0x5865f2)
    await interaction.response.send_message(embed=embed, view=MainView())

@bot.tree.command(name="확인", description="로블록스 프로필 코드를 확인하여 인증을 완료합니다.")
async def 확인(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in verify_requests:
        await interaction.response.send_message("❌ 먼저 '인증 시작하기' 버튼을 눌러주세요.", ephemeral=True)
        return
    
    req = verify_requests[user_id]
    await interaction.response.send_message("🔍 확인 중...", ephemeral=True)
    
    try:
        u_res = requests.post('https://users.roblox.com/v1/usernames/users', json={"usernames": [req['name']]})
        rbx_id = u_res.json()['data'][0]['id']
        profile = requests.get(f'https://users.roblox.com/v1/users/{rbx_id}').json()
        
        if req['code'] in profile.get('description', ""):
            role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
            if role:
                await interaction.user.add_roles(role)
                await interaction.edit_original_response(content=f"✅ 인증 성공! `{req['name']}`님 환영합니다.")
                del verify_requests[user_id]
            else:
                await interaction.edit_original_response(content=f"⚠️ `{ROLE_NAME}` 역할을 서버에서 찾을 수 없습니다.")
        else:
            await interaction.edit_original_response(content=f"❌ 코드가 일치하지 않습니다. (코드: {req['code']})")
    except:
        await interaction.edit_original_response(content="⚠️ 오류가 발생했습니다. 닉네임을 확인하세요.")

# --- [ 메인 실행 ] ---
async def main():
    keep_alive() # 웹 서버 시작
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error occurred: {e}")
