@echo off
REM Build C++ Execution Engine (Windows)
REM =====================================

setlocal enabledelayedexpansion

echo.
echo =========================================
echo Mini-Medallion C++ Execution Engine
echo Building for Windows
echo =========================================
echo.

REM Get the script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set CPP_DIR=%PROJECT_DIR%\src\execution\cpp
set BUILD_DIR=%CPP_DIR%\build

REM Check for CMake
where cmake >nul 2>nul
if errorlevel 1 (
    echo ERROR: cmake not found. 
    echo Install from: https://cmake.org/download/
    echo Or use: choco install cmake
    exit /b 1
)

REM Detect Visual Studio
set CMAKE_GENERATOR=

REM Try Visual Studio 2022
if exist "C:\Program Files\Microsoft Visual Studio\2022" (
    set CMAKE_GENERATOR=Visual Studio 17 2022
    set VS_VERSION=2022
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2019" (
    set CMAKE_GENERATOR=Visual Studio 16 2019
    set VS_VERSION=2019
) else (
    echo WARNING: Visual Studio not found. Attempting MinGW/Unix Makefiles.
    set CMAKE_GENERATOR=MinGW Makefiles
    set VS_VERSION=MinGW
)

echo Detected Generator: %CMAKE_GENERATOR%
echo.

REM Create build directory
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
cd /d "%BUILD_DIR%"

echo CMake Configuration...
REM Check for CUDA
nvcc --version >nul 2>nul
if errorlevel 0 (
    echo   CUDA found - enabling GPU support
    cmake -G "%CMAKE_GENERATOR%" -DCMAKE_BUILD_TYPE=Release -DENABLE_CUDA=ON ..
) else (
    echo   CUDA not found - building CPU-only
    cmake -G "%CMAKE_GENERATOR%" -DCMAKE_BUILD_TYPE=Release ..
)

if errorlevel 1 (
    echo ERROR: CMake configuration failed
    exit /b 1
)

echo.
echo Building...
if "%CMAKE_GENERATOR%"=="MinGW Makefiles" (
    mingw32-make -j
) else (
    cmake --build . --config Release --parallel
)

if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

echo.
echo =========================================
echo Build completed successfully!
echo Output: %BUILD_DIR%\Release\order_router_demo.exe
echo =========================================
echo.
echo To run the demo:
echo   %BUILD_DIR%\Release\order_router_demo.exe
echo.
pause
