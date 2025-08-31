@ECHO off

:: Windows 10

@SET "ENCODING=65001"
@SET "CURRENT_DIR=%~dp0"
@SET "SCRIPT_NAME=Run PKI Chain Builder"

:: Pre start
@CHCP %ENCODING% > nul

@TITLE %SCRIPT_NAME%
:: Start
::==============================================================================================================
@SET "ROOT_DIR=%CURRENT_DIR%../.."
@SET "SOURCE_DIR=%ROOT_DIR%/src"

@PUSHD "%SOURCE_DIR%"

@SET "PYTHON=%ROOT_DIR%/env/python-3.12.10-embed-amd64-win/python.exe"
@SET "ENTRYPOINT=main.py"

"%PYTHON%" %ENTRYPOINT% %*

@ECHO.

@PAUSE

@POPD
::==============================================================================================================
:: Stop

@EXIT /B 0
