"""
Automated Backup System
Handles database, model weights, and configuration backups
"""
import os
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import tarfile
import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups of critical system data"""
    
    def __init__(self, 
                 backup_dir: str = "./backups",
                 retention_days: int = 30,
                 interval_hours: int = 24):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.interval_seconds = interval_hours * 3600
        
        logger.info(f"Backup system initialized: {self.backup_dir}")
        logger.info(f"Retention: {retention_days} days, Interval: {interval_hours} hours")
    
    def create_backup(self, backup_type: str = "full") -> Optional[Path]:
        """
        Create system backup
        
        Args:
            backup_type: 'full', 'database', 'models', 'configs'
        
        Returns:
            Path to backup file or None if failed
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        try:
            logger.info(f"Creating {backup_type} backup: {backup_name}")
            
            with tarfile.open(backup_path, "w:gz") as tar:
                if backup_type in ["full", "database"]:
                    self._backup_database(tar)
                
                if backup_type in ["full", "models"]:
                    self._backup_models(tar)
                
                if backup_type in ["full", "configs"]:
                    self._backup_configs(tar)
                
                if backup_type == "full":
                    self._backup_logs(tar)
            
            # Verify backup
            if backup_path.exists() and backup_path.stat().st_size > 0:
                logger.info(f"✓ Backup created: {backup_path} ({self._format_size(backup_path.stat().st_size)})")
                return backup_path
            else:
                logger.error(f"❌ Backup failed: {backup_path}")
                return None
                
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None
    
    def _backup_database(self, tar: tarfile.TarFile):
        """Backup SQLite database"""
        db_path = Path("labeled_data.db")
        
        if not db_path.exists():
            logger.warning("Database not found, skipping")
            return
        
        # Create consistent snapshot
        snapshot_path = Path("labeled_data_snapshot.db")
        
        try:
            # Use SQLite backup API for consistency
            source_conn = sqlite3.connect(db_path)
            dest_conn = sqlite3.connect(snapshot_path)
            
            source_conn.backup(dest_conn)
            
            source_conn.close()
            dest_conn.close()
            
            # Add to archive
            tar.add(snapshot_path, arcname="database/labeled_data.db")
            logger.info("  ✓ Database backed up")
            
        finally:
            if snapshot_path.exists():
                snapshot_path.unlink()
    
    def _backup_models(self, tar: tarfile.TarFile):
        """Backup model weights"""
        models_dir = Path("models/weights")
        
        if not models_dir.exists():
            logger.warning("Models directory not found, skipping")
            return
        
        # Backup .pth, .pt, .safetensors files
        model_files = list(models_dir.glob("**/*.pth")) + \
                     list(models_dir.glob("**/*.pt")) + \
                     list(models_dir.glob("**/*.safetensors"))
        
        if not model_files:
            logger.warning("No model files found")
            return
        
        for model_file in model_files:
            arcname = f"models/{model_file.relative_to(models_dir.parent)}"
            tar.add(model_file, arcname=arcname)
        
        logger.info(f"  ✓ {len(model_files)} model files backed up")
    
    def _backup_configs(self, tar: tarfile.TarFile):
        """Backup configuration files"""
        config_files = [
            ".env",
            "config.py",
            "config_production.py",
            "model_accuracies.json"
        ]
        
        backed_up = 0
        for config_file in config_files:
            path = Path(config_file)
            if path.exists():
                tar.add(path, arcname=f"configs/{path.name}")
                backed_up += 1
        
        if backed_up > 0:
            logger.info(f"  ✓ {backed_up} config files backed up")
    
    def _backup_logs(self, tar: tarfile.TarFile):
        """Backup recent logs"""
        logs_dir = Path("logs")
        
        if not logs_dir.exists():
            return
        
        # Only backup logs from last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_logs = []
        
        for log_file in logs_dir.glob("*.log"):
            if datetime.fromtimestamp(log_file.stat().st_mtime) > cutoff_date:
                recent_logs.append(log_file)
        
        for log_file in recent_logs:
            tar.add(log_file, arcname=f"logs/{log_file.name}")
        
        if recent_logs:
            logger.info(f"  ✓ {len(recent_logs)} log files backed up")
    
    def clean_old_backups(self):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        deleted_count = 0
        total_size = 0
        
        for backup_file in self.backup_dir.glob("backup_*.tar.gz"):
            # Parse timestamp from filename
            try:
                timestamp_str = backup_file.stem.split("_")[-2] + "_" + backup_file.stem.split("_")[-1]
                backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                if backup_date < cutoff_date:
                    file_size = backup_file.stat().st_size
                    backup_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                    logger.info(f"  Deleted old backup: {backup_file.name}")
            
            except (ValueError, IndexError):
                # Skip files with unexpected names
                continue
        
        if deleted_count > 0:
            logger.info(f"✓ Cleaned {deleted_count} old backups ({self._format_size(total_size)} freed)")
    
    def list_backups(self) -> list:
        """List all available backups"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("backup_*.tar.gz")):
            try:
                timestamp_str = backup_file.stem.split("_")[-2] + "_" + backup_file.stem.split("_")[-1]
                backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'date': backup_date,
                    'size': backup_file.stat().st_size,
                    'size_formatted': self._format_size(backup_file.stat().st_size),
                    'type': backup_file.stem.split("_")[1]  # full, database, etc.
                })
            except (ValueError, IndexError):
                continue
        
        return sorted(backups, key=lambda x: x['date'], reverse=True)
    
    def restore_backup(self, backup_path: str, restore_type: str = "full") -> bool:
        """
        Restore from backup
        
        Args:
            backup_path: Path to backup file
            restore_type: 'full', 'database', 'models', 'configs'
        
        Returns:
            True if successful
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            logger.info(f"Restoring {restore_type} from: {backup_file.name}")
            
            with tarfile.open(backup_file, "r:gz") as tar:
                members_to_extract = []
                
                if restore_type in ["full", "database"]:
                    members_to_extract.extend([m for m in tar.getmembers() if m.name.startswith("database/")])
                
                if restore_type in ["full", "models"]:
                    members_to_extract.extend([m for m in tar.getmembers() if m.name.startswith("models/")])
                
                if restore_type in ["full", "configs"]:
                    members_to_extract.extend([m for m in tar.getmembers() if m.name.startswith("configs/")])
                
                # Extract to temporary directory first
                temp_dir = Path("restore_temp")
                temp_dir.mkdir(exist_ok=True)
                
                try:
                    for member in members_to_extract:
                        tar.extract(member, path=temp_dir)
                    
                    # Move files to correct locations
                    for member in members_to_extract:
                        src = temp_dir / member.name
                        
                        # Determine destination
                        if member.name.startswith("database/"):
                            dest = Path(member.name.replace("database/", ""))
                        elif member.name.startswith("models/"):
                            dest = Path(member.name.replace("models/", ""))
                        elif member.name.startswith("configs/"):
                            dest = Path(member.name.replace("configs/", ""))
                        else:
                            continue
                        
                        # Create parent directories
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Move file
                        if src.exists():
                            shutil.move(str(src), str(dest))
                    
                    logger.info(f"✓ Restore complete: {len(members_to_extract)} items restored")
                    return True
                    
                finally:
                    # Cleanup temp directory
                    if temp_dir.exists():
                        shutil.rmtree(temp_dir)
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    async def run_scheduled_backups(self):
        """Background task for automated backups"""
        logger.info("[Backup] Scheduled backup task started")
        
        while True:
            try:
                # Wait for next backup interval
                await asyncio.sleep(self.interval_seconds)
                
                logger.info("[Backup] Starting scheduled backup...")
                
                # Create full backup
                backup_path = self.create_backup(backup_type="full")
                
                if backup_path:
                    logger.info(f"[Backup] ✓ Scheduled backup complete: {backup_path.name}")
                    
                    # Clean old backups
                    self.clean_old_backups()
                else:
                    logger.error("[Backup] ❌ Scheduled backup failed")
                
            except Exception as e:
                logger.error(f"[Backup] Error in scheduled backup: {e}")
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retry

# Singleton instance
_backup_manager = None

def get_backup_manager(backup_dir: str = "./backups", 
                      retention_days: int = 30,
                      interval_hours: int = 24) -> BackupManager:
    """Get singleton backup manager instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(backup_dir, retention_days, interval_hours)
    return _backup_manager
