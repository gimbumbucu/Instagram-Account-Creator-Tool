import discord
from discord import app_commands
from discord.ext import commands
import requests
import nest_asyncio
import asyncio
import random

nest_asyncio.apply()

# --- [ 필수 설정 ] ---
TOKEN = 'MTQ3NjgyMzYwODMxOTAyMTA4Ng.GLsS9N.JS6gYKQvdLgI5HK7omdsDsv_eTGkCIpPS6SuDA'
GROUP_ID = "17253423"
ROLE_NAME = "유저 | User"

verify_requests = {}

# --- [ 1. 인증 입력 모달 창 ] ---
class VerifyModal(discord.ui.Modal, title="로블록스 계정 인증"):
    nickname = discord.ui.TextInput(label="로블록스 닉네임", placeholder="닉네임을 입력하세요", min_length=2, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        code = str(random.randint(100000, 999999))
        verify_requests[interaction.user.id] = {"name": self.nickname.value, "code": code}

        embed = discord.Embed(title="🔐 인증 코드가 발급되었습니다", color=0x3498db)
        embed.description = f"**{self.nickname.value}**님의 소개글(About)에 아래 코드를 적고 `/확인`을 입력하세요."
        embed.add_field(name="인증 코드", value=f"**{code}**", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# --- [ 2. 인증 시작 버튼 뷰 ] ---
class VerifyStartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="인증 시작하기", style=discord.ButtonStyle.primary, custom_id="start_verify")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

# --- [ 3. 메인 봇 클래스 ] ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        self.add_view(VerifyStartView()) # 버튼 지속성 유지
        await self.tree.sync()
        print("--- 슬래시 명령어 및 버튼 시스템 준비 완료 ---")

bot = MyBot()

# --- [ 명령어: /인증설정 ] ---
@bot.tree.command(name="인증설정", description="인증 시작 임베드와 버튼을 생성합니다. (관리자용)")
@app_commands.checks.has_permissions(administrator=True)
async def 인증설정(interaction: discord.Interaction):
    embed = discord.Embed(
        title="레어점 유저 인증",
        description="아래 버튼을 눌러 인증을 시작하세요!",
        color=0x5865f2
    )
    await interaction.response.send_message(embed=embed, view=VerifyStartView())

# --- [ 명령어: /확인 ] ---
@bot.tree.command(name="확인", description="소개글을 확인하여 인증을 완료합니다.")
async def 확인(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id not in verify_requests:
        await interaction.response.send_message("❌ 인증을 먼저 시작해 주세요.", ephemeral=True)
        return

    req = verify_requests[user_id]
    await interaction.response.send_message(f"🔍 `{req['name']}`님의 프로필 확인 중...", ephemeral=True)

    try:
        user_res = requests.post('https://users.roblox.com/v1/usernames/users', json={"usernames": [req['name']]})
        rbx_id = user_res.json()['data'][0]['id']
        profile = requests.get(f'https://users.roblox.com/v1/users/{rbx_id}').json()

        if req['code'] in profile.get('description', ""):
            role = discord.utils.get(interaction.guild.roles, name=ROLE_NAME)
            if role:
                await interaction.user.add_roles(role)
                await interaction.edit_original_response(content=f"✅ 인증 성공! `{req['name']}`님 환영합니다.")
                del verify_requests[user_id]
            else:
                await interaction.edit_original_response(content="⚠️ 역할을 찾을 수 없습니다.")
        else:
            await interaction.edit_original_response(content="❌ 코드가 일치하지 않습니다.")
    except:
        await interaction.edit_original_response(content="⚠️ 인증 중 오류가 발생했습니다.")

async def main():
    async with bot:
        await bot.start(TOKEN)

try:
    asyncio.run(main())
except:
    pass
