@echo off
cd /d "%~dp0"

:: ── Pick latest results CSV ──
for /f "delims=" %%f in ('dir /b /od "..\scanner\results_*.csv" 2^>nul') do set LATEST=%%f

if "%LATEST%"=="" (
    echo No results CSV found in swing-screener. Run the screener first.
    pause
    exit /b 1
)

echo =============================================
echo  Swing Visualizer
echo =============================================
echo  Results file : %LATEST%
echo  Charts saved : charts\%date:~-4%-%date:~3,2%-%date:~0,2%\^<timeframe^>
echo.
echo  Select timeframe:
echo    1. Daily
echo    2. Weekly
echo.
set /p TF_CHOICE="Enter choice (1 or 2): "

if "%TF_CHOICE%"=="1" (
    set TIMEFRAME=daily
) else if "%TF_CHOICE%"=="2" (
    set TIMEFRAME=weekly
) else (
    echo Invalid choice. Defaulting to Daily.
    set TIMEFRAME=daily
)

echo.
echo Running %TIMEFRAME% charts...
echo.

python visualize.py --csv "..\scanner\%LATEST%" --timeframe %TIMEFRAME%

echo.
echo =============================================
echo  Charts saved to:
echo  %~dp0charts\%date:~-4%-%date:~3,2%-%date:~0,2%\%TIMEFRAME%\
echo =============================================
pause
