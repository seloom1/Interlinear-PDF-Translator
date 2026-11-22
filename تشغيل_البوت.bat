@echo off
cd /d "%~dp0"
echo ====================================================
echo  Interlinear PDF Translator - Telegram Bot Launcher
echo ====================================================
set /p BOT_TOKEN="Enter your Telegram Bot Token from @BotFather: "
python bot.py %BOT_TOKEN%
pause
