@ECHO off

:: Windows 10

@SET "ENCODING=65001"
@SET "CURRENT_DIR=%~dp0"
@SET "SCRIPT_NAME=Get repository"

:: Pre start
@CHCP %ENCODING% > nul

@TITLE %SCRIPT_NAME%
:: Start
::==============================================================================================================
@SET "REPO_URL=https://github.com/Bakminstof/pki-chain-builder"
@SET "REPO_NAME=pki-chain-builder"
@SET "BRANCH=release"


git clone --depth=1 --single-branch --branch "%BRANCH%" --no-checkout "%REPO_URL%" "%REPO_NAME%"

@CD "%REPO_NAME%"

git sparse-checkout set --no-cone "/.gitattributes" "/.gitignore" "!/env" "/env/python-3.12.10-embed-amd64-win" "/scripts" "/src" "/LICENSE" "/pyproject.toml"

git checkout "%BRANCH%"
git reset --hard "origin/%BRANCH%"
git pull -X theirs "origin" "%BRANCH%"
