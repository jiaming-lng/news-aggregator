@echo off
chcp 65001 >nul
echo === TechNews Agnes AI 部署脚本 ===
echo.
echo 正在连接 VPS 并执行部署...
echo.

ssh -o StrictHostKeyChecking=no user@106.53.58.166 "bash -s" < deploy_remote.sh

echo.
echo === 部署完成 ===
pause
