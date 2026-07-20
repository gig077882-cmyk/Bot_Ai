@echo off
chcp 65001 >nul
title GD AI - Control Panel
cd /d "%~dp0"

:MENU
cls
echo ========================================
echo     GEOMETRY DASH AI - CONTROL PANEL
echo ========================================
echo.
echo  ~~~ QUICK START (Launch + Level + AI) ~~~
echo  1. Launch GD + Level ^& Train AI
echo  2. Launch GD + Level ^& Play AI
echo  3. Launch GD + Practice ^& Train AI
echo.
echo  ~~~ GAME ONLY ~~~
echo  4. Launch GD (windowed 800x600) + Level
echo  5. Launch GD (windowed 800x600) + Practice
echo  6. Close GD
echo.
echo  ~~~ AI ONLY (GD must already be on a level) ~~~
echo  7. Train AI (with live visualizer)
echo  8. Play AI (with live visualizer)
echo.
echo  ~~~ TOOLS ~~~
echo  9. Monitor (Attempt counter overlay)
echo  P. Disable Effects (particles in .plist)
echo  R. Restore Effects (from backup)
echo  F. Find Memory Addresses
echo  V. Visualizer Standalone (see what AI sees)
echo.
echo  ~~~ SETUP ~~~
echo  A. Install Dependencies
echo  0. Exit
echo.
set /p choice="Select: "

if /i "%choice%"=="1" goto Q_TRAIN
if /i "%choice%"=="2" goto Q_PLAY
if /i "%choice%"=="3" goto Q_PRACTICE_TRAIN
if /i "%choice%"=="4" goto LAUNCH
if /i "%choice%"=="5" goto LAUNCH_PRACTICE
if /i "%choice%"=="6" goto CLOSE
if /i "%choice%"=="7" goto TRAIN
if /i "%choice%"=="8" goto PLAY
if /i "%choice%"=="9" goto MONITOR
if /i "%choice%"=="P" goto PATCH
if /i "%choice%"=="p" goto PATCH
if /i "%choice%"=="R" goto RESTORE
if /i "%choice%"=="r" goto RESTORE
if /i "%choice%"=="F" goto FINDADDR
if /i "%choice%"=="f" goto FINDADDR
if /i "%choice%"=="V" goto VISUALIZER
if /i "%choice%"=="v" goto VISUALIZER
if /i "%choice%"=="A" goto INSTALL
if /i "%choice%"=="a" goto INSTALL
if "%choice%"=="0" exit /b
goto MENU

:Q_TRAIN
cls
set /p level="Level number (1-22, default=1): "
if "%level%"=="" set level=1
echo.
echo [1/3] Launching GD in windowed 800x600...
echo [2/3] Starting Level %level%...
echo [3/3] Starting Training...
echo.
python launcher.py launch_train %level%
echo.
pause
goto MENU

:Q_PLAY
cls
set /p level="Level number (1-22, default=1): "
if "%level%"=="" set level=1
echo.
echo [1/3] Launching GD in windowed 800x600...
echo [2/3] Starting Level %level%...
echo [3/3] Starting AI Play...
echo.
python launcher.py launch_play %level%
echo.
pause
goto MENU

:Q_PRACTICE_TRAIN
cls
set /p level="Level number (1-22, default=1): "
if "%level%"=="" set level=1
echo.
echo [1/3] Launching GD in windowed 800x600...
echo [2/3] Starting Practice Level %level%...
echo [3/3] Starting Training...
echo.
python launcher.py practice %level%
echo.
pause
goto MENU

:LAUNCH
cls
set /p level="Level number (1-22, default=1): "
if "%level%"=="" set level=1
echo Launching GD in windowed 800x600 + Level %level%...
python launcher.py launch %level%
echo.
pause
goto MENU

:LAUNCH_PRACTICE
cls
set /p level="Level number (1-22, default=1): "
if "%level%"=="" set level=1
echo Launching GD + Practice Level %level%...
python launcher.py practice %level%
echo.
pause
goto MENU

:CLOSE
cls
python launcher.py close
echo.
pause
goto MENU

:TRAIN
cls
echo Starting Training...
echo GD must be running on a level already.
echo Visualizer opens. Press Q to stop.
echo.
python train.py
echo.
pause
goto MENU

:PLAY
cls
echo Starting AI Player...
echo GD must be running on a level already.
echo Visualizer opens. Press Q to stop.
echo.
python play.py
echo.
pause
goto MENU

:MONITOR
cls
echo Starting Monitor...
start /min python monitor.py
echo Monitor launched in background.
echo.
pause
goto MENU

:PATCH
cls
python patch_effects.py
echo.
pause
goto MENU

:RESTORE
cls
python -c "from patch_effects import restore_backups; restore_backups(r'C:\Users\GG\Desktop\Geometry Dash\Resources')"
echo.
pause
goto MENU

:FINDADDR
cls
python find_addrs.py
echo.
pause
goto MENU

:VISUALIZER
cls
echo Starting standalone visualizer...
echo GD must be running on a level.
echo.
python -c "
from gd_env import GeometryDashEnv
from visualizer import AIVisualizer
from utils import load_config
import numpy as np, time
cfg = load_config()
env = GeometryDashEnv(cfg)
vis = AIVisualizer('GD AI - Live View')
print('Press Q in visualizer to stop.')
try:
    while True:
        gray, raw = env._capture_screen()
        proc = env._preprocess(gray)
        if len(env.frames) < env.stack_size:
            env.frames.append(proc)
            env.raw_frames.append(raw)
            continue
        state = list(env.frames)
        if len(state) >= 4:
            s = np.array(state[-4:])
            key = vis.render(s, raw)
            if key == ord('q') or key == ord('Q'):
                break
        time.sleep(0.016)
except: pass
finally: vis.close(); env.close()
"
echo.
pause
goto MENU

:INSTALL
cls
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% equ 0 (
    echo Done!
) else (
    echo Error. Try manual: pip install torch torchvision numpy opencv-python mss pydirectinput pywin32 pyyaml pillow pymem
)
echo.
pause
goto MENU
