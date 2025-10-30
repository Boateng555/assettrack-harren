@echo off
echo 🤖 Setting up Ollama (Free AI) for AssetTrack on Windows
echo ==============================================================

REM Check if Ollama is already installed
ollama --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama is already installed
    goto :start_ollama
)

echo 📦 Installing Ollama...
echo Please download Ollama from: https://ollama.com/download
echo After installation, run this script again.
pause
exit /b 1

:start_ollama
echo 🚀 Starting Ollama service...
start /B ollama serve

REM Wait for Ollama to start
echo ⏳ Waiting for Ollama to start...
timeout /t 10 /nobreak >nul

REM Check if Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Ollama is running
) else (
    echo ❌ Ollama failed to start
    echo Please check if Ollama is installed correctly
    pause
    exit /b 1
)

echo 📥 Downloading AI models...
echo Downloading Llama 3.2 3B (3GB)...
ollama pull llama3.2:3b

if %errorlevel% equ 0 (
    echo ✅ Llama 3.2 3B downloaded successfully
) else (
    echo ❌ Failed to download Llama 3.2 3B
    pause
    exit /b 1
)

echo Downloading TinyLlama (1GB) as backup...
ollama pull tinyllama

if %errorlevel% equ 0 (
    echo ✅ TinyLlama downloaded successfully
) else (
    echo ⚠️ TinyLlama download failed (optional)
)

echo 🧪 Testing AI model...
ollama run llama3.2:3b "Hello, are you working?" >nul 2>&1

if %errorlevel% equ 0 (
    echo ✅ AI model is working correctly
) else (
    echo ❌ AI model test failed
    pause
    exit /b 1
)

echo 📝 Creating environment configuration...
echo # Ollama AI Configuration > .env.ollama
echo OLLAMA_URL=http://localhost:11434 >> .env.ollama
echo OLLAMA_MODEL=llama3.2:3b >> .env.ollama
echo. >> .env.ollama
echo # Alternative models (uncomment to use): >> .env.ollama
echo # OLLAMA_MODEL=tinyllama >> .env.ollama
echo # OLLAMA_MODEL=phi3:mini >> .env.ollama

echo ✅ Environment file created: .env.ollama

echo.
echo 🎉 Ollama setup completed successfully!
echo.
echo 📋 Next steps:
echo 1. Copy the environment variables to your .env file:
echo    type .env.ollama >> .env
echo.
echo 2. Restart your Django application:
echo    python manage.py runserver
echo.
echo 3. Test the AI Assistant:
echo    - Click the blue circle button in the app
echo    - Or go to: http://127.0.0.1:8000/ai-chat/
echo.
echo 🔧 Configuration:
echo    - Ollama URL: http://localhost:11434
echo    - Default Model: llama3.2:3b
echo.
echo 💡 Available models:
echo    - llama3.2:3b (recommended, 3GB)
echo    - tinyllama (lightweight, 1GB)
echo.
echo 🆓 This is completely FREE and runs on your server!
echo    No API costs, no external dependencies, full privacy!
echo.
pause
