@ECHO off

:: Windows 10

@SET "ENCODING=65001"
@SET "CURRENT_DIR=%~dp0"
@SET "SCRIPT_NAME=Update python packages"

:: Pre start
@CHCP %ENCODING% > nul

@TITLE %SCRIPT_NAME%
:: Start
::==============================================================================================================
@SET "ROOT_DIR=%CURRENT_DIR%../.."

@PUSHD "%ROOT_DIR%"

@SET "POETRY_VIRTUALENVS_CREATE=false"

@SET "PYTHON=%ROOT_DIR%/env/python-3.12.10-embed-amd64-win/python.exe"
@SET "UPDATE_ARGS=-m poetry install --no-root"

"%PYTHON%" %UPDATE_ARGS%

@ECHO.

@PAUSE

@POPD
::==============================================================================================================
:: Stop

@EXIT /B 0
