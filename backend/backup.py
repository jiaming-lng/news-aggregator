"""
资讯聚合网站 - 数据库自动备份模块
使用 SQLite 在线备份 API（conn.backup），WAL 模式下也能生成一致性快照。
每日定时备份 + 自动清理过期备份（默认保留 7 天）。
"""

import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

from database import DB_PATH

# ============================================================
# 配置
# ============================================================

BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), 'backups')
BACKUP_RETENTION_DAYS = 7      # 备份保留天数
BACKUP_HOUR = 3                # 每日备份时间（小时，24 小时制）
BACKUP_MINUTE = 0              # 每日备份时间（分钟）

_backup_lock = threading.Lock()


# ============================================================
# 备份核心
# ============================================================

def backup_now():
    """立即执行一次数据库备份（在线一致性快照）

    返回: (success: bool, path_or_error: str)
    """
    with _backup_lock:
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
        except OSError as e:
            print(f"[Backup] 创建备份目录失败: {e}")
            return False, str(e)

        dest_path = None
        try:
            src = sqlite3.connect(DB_PATH)
            try:
                stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest_path = os.path.join(BACKUP_DIR, f'news_backup_{stamp}.db')
                dest = sqlite3.connect(dest_path)
                try:
                    src.backup(dest)
                finally:
                    dest.close()
            finally:
                src.close()

            # 验证备份可打开且行数一致
            ok = _verify_backup(dest_path)
            if not ok:
                os.remove(dest_path)
                print(f"[Backup] 备份校验失败，已删除异常文件: {os.path.basename(dest_path)}")
                return False, '备份校验失败'

            _cleanup_old_backups()
            size_kb = os.path.getsize(dest_path) // 1024
            print(f"[Backup] 备份完成: {os.path.basename(dest_path)} ({size_kb} KB)")
            return True, dest_path
        except Exception as e:
            print(f"[Backup] 备份失败: {e}")
            if dest_path and os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass
            return False, str(e)


def _verify_backup(backup_path):
    """校验备份文件可正常打开，且文章数与源库一致"""
    try:
        src_conn = sqlite3.connect(DB_PATH)
        bak_conn = sqlite3.connect(backup_path)
        try:
            src_count = src_conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            bak_count = bak_conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            return src_count == bak_count
        finally:
            src_conn.close()
            bak_conn.close()
    except Exception:
        return False


def _cleanup_old_backups():
    """清理超过保留期的备份文件"""
    try:
        cutoff = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
        for f in os.listdir(BACKUP_DIR):
            if not (f.startswith('news_backup_') and f.endswith('.db')):
                continue
            fp = os.path.join(BACKUP_DIR, f)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if mtime < cutoff:
                    os.remove(fp)
                    print(f"[Backup] 清理过期备份: {f}")
            except OSError:
                pass
    except Exception as e:
        print(f"[Backup] 清理备份出错: {e}")


# ============================================================
# 每日定时备份线程
# ============================================================

def start_daily_backup():
    """启动每日备份线程（每天 BACKUP_HOUR:BACKUP_MINUTE 执行一次）"""
    def loop():
        print(f"[Backup] 每日备份已启动（每天 {BACKUP_HOUR:02d}:{BACKUP_MINUTE:02d}，保留 {BACKUP_RETENTION_DAYS} 天）")
        while True:
            now = datetime.now()
            target = now.replace(hour=BACKUP_HOUR, minute=BACKUP_MINUTE, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            time.sleep(wait_seconds)
            try:
                backup_now()
            except Exception as e:
                print(f"[Backup] 每日备份异常: {e}")

    threading.Thread(target=loop, daemon=True).start()


if __name__ == '__main__':
    # 手动执行一次备份（测试用）
    ok, result = backup_now()
    print(f"手动备份结果: {'成功' if ok else '失败'} -> {result}")
