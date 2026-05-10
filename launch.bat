@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::  Mine-Streaker — Interactive Launcher
:: ============================================================

title Mine-Streaker Launcher

:: Change to the directory this .bat lives in
cd /d "%~dp0"

:: Detect Python - prefer venv, fall back to system
set PYTHON=python
if exist "venv\Scripts\python.exe"     set PYTHON=venv\Scripts\python.exe
if exist ".venv\Scripts\python.exe"    set PYTHON=.venv\Scripts\python.exe
if exist "env\Scripts\python.exe"      set PYTHON=env\Scripts\python.exe

echo.
echo  ============================================================
echo   Mine-Streaker - Image Minesweeper
echo  ============================================================
echo.

:: --- MODE ---------------------------------------------------
echo  Select board mode:
echo    1) Random  - classic randomly generated board
echo    2) Easy    - 9x9,  10 mines  (preset)
echo    3) Medium  - 16x16, 40 mines (preset)
echo    4) Hard    - 30x16, 99 mines (preset)
echo    5) Load    - load a saved .npy board file
echo    6) Image   - image-reveal mode (MineStreaker pipeline)
echo.
set /p MODE_CHOICE=" Mode [1]: "
if "!MODE_CHOICE!"=="" set MODE_CHOICE=1

set MODE_ARG=
set DIFF_ARG=
set CUSTOM=0
set ASK_DIMS=0

if "!MODE_CHOICE!"=="1" (
    set MODE_ARG=--random
    set ASK_DIMS=1
)
if "!MODE_CHOICE!"=="2" set DIFF_ARG=--easy
if "!MODE_CHOICE!"=="3" set DIFF_ARG=--medium
if "!MODE_CHOICE!"=="4" set DIFF_ARG=--hard
if "!MODE_CHOICE!"=="5" goto :ask_load
if "!MODE_CHOICE!"=="6" goto :ask_image

if defined DIFF_ARG goto :ask_seed_tile

:: --- CUSTOM BOARD DIMENSIONS (random mode) ------------------
if "!ASK_DIMS!"=="1" (
    echo.
    set /p BOARD_W=" Board width  in tiles [300]: "
    if "!BOARD_W!"=="" set BOARD_W=300

    set /p BOARD_H=" Board height in tiles [370]: "
    if "!BOARD_H!"=="" set BOARD_H=370

    set /p MINES=" Mine count (0 = auto) [0]: "
    if "!MINES!"=="" set MINES=0
)
goto :ask_seed_tile

:: --- LOAD .NPY ----------------------------------------------
:ask_load
echo.
set /p NPY_PATH=" Path to .npy board file: "
if "!NPY_PATH!"=="" (
    echo  ERROR: No path provided. Exiting.
    pause
    exit /b 1
)
set MODE_ARG=--load "!NPY_PATH!"
set BOARD_W=
set BOARD_H=
set MINES=
goto :ask_seed_tile

:: --- IMAGE MODE ---------------------------------------------
:ask_image
echo.
set /p IMG_PATH=" Path to source image: "
if "!IMG_PATH!"=="" (
    echo  ERROR: No path provided. Exiting.
    pause
    exit /b 1
)
set MODE_ARG=--image "!IMG_PATH!"

echo.
set /p BOARD_W=" Board width  in tiles [300]: "
if "!BOARD_W!"=="" set BOARD_W=300

set /p BOARD_H=" Board height in tiles [370]: "
if "!BOARD_H!"=="" set BOARD_H=370

set /p MINES=" Mine count (0 = auto) [0]: "
if "!MINES!"=="" set MINES=0
goto :ask_seed_tile

:: --- SEED & TILE SIZE ---------------------------------------
:ask_seed_tile
echo.
set /p SEED=" Random seed [42]: "
if "!SEED!"=="" set SEED=42

set /p TILE=" Tile size in pixels [32]: "
if "!TILE!"=="" set TILE=32

:: --- BUILD COMMAND ------------------------------------------
:build_cmd
set CMD="%PYTHON%" gameworks\main.py

if defined DIFF_ARG (
    set CMD=!CMD! !DIFF_ARG!
) else (
    set CMD=!CMD! !MODE_ARG!
    if defined BOARD_W set CMD=!CMD! --board-w !BOARD_W!
    if defined BOARD_H set CMD=!CMD! --board-h !BOARD_H!
    if defined MINES   set CMD=!CMD! --mines !MINES!
)

set CMD=!CMD! --seed !SEED! --tile !TILE!

:: --- CONFIRM & LAUNCH ---------------------------------------
echo.
echo  --------------------------------------------------------
echo  Command: !CMD!
echo  --------------------------------------------------------
echo.
set /p CONFIRM=" Launch? [Y/n]: "
if /i "!CONFIRM!"=="n" (
    echo  Aborted.
    pause
    exit /b 0
)

echo.
echo  Starting Mine-Streaker...
echo.
!CMD!

if errorlevel 1 (
    echo.
    echo  ERROR: Game exited with an error.
    echo  Make sure dependencies are installed: pip install -r requirements.txt
)

echo.
pause
endlocal
