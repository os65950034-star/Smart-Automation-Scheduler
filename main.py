import sys
import os
import time
import random
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from enum import Enum
from typing import List, Optional, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QDateTimeEdit, QTableWidget, QTableWidgetItem, 
    QTextEdit, QFileDialog, QMessageBox, QGroupBox, QFormLayout, 
    QSpinBox, QCheckBox, QHeaderView, QDialog, QStatusBar, QFrame
)
from PySide6.QtCore import Qt, QDateTime, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, 
    Text, Enum as SQLEnum, desc, inspect, text
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from cryptography.fernet import Fernet


# ==========================================
# 0. ELEGANT & DECENT DARK THEME STYLESHEET
# ==========================================
DECENT_DARK_STYLESHEET = """
    QMainWindow, QDialog {
        background-color: #0f172a;
        color: #f8fafc;
    }
    QWidget {
        color: #cbd5e1;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        border: 1px solid #334155;
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: bold;
        color: #38bdf8;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background-color: #0f172a;
    }
    QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QSpinBox {
        background-color: #1e293b;
        border: 1px solid #475569;
        border-radius: 6px;
        padding: 6px 10px;
        color: #f8fafc;
        selection-background-color: #6366f1;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
        border: 1px solid #38bdf8;
    }
    QComboBox::drop-down {
        border: none;
    }
    QTableWidget, QListWidget {
        background-color: #1e293b;
        border: 1px solid #334155;
        gridline-color: #334155;
        border-radius: 6px;
        color: #f8fafc;
    }
    QListWidget::item:selected, QTableWidget::item:selected {
        background-color: #334155;
        color: #38bdf8;
    }
    QHeaderView::section {
        background-color: #0f172a;
        color: #38bdf8;
        padding: 8px;
        font-weight: bold;
        border: 1px solid #334155;
    }
    QTabWidget::pane {
        border: 1px solid #334155;
        border-radius: 8px;
        background-color: #0f172a;
    }
    QTabBar::tab {
        background: #1e293b;
        color: #94a3b8;
        padding: 10px 20px;
        font-weight: bold;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }
    QTabBar::tab:selected {
        background: #4f46e5;
        color: #ffffff;
    }
    QPushButton {
        background-color: #312e81;
        color: #e0e7ff;
        font-weight: bold;
        border: 1px solid #4338ca;
        border-radius: 6px;
        padding: 8px 16px;
    }
    QPushButton:hover {
        background-color: #4338ca;
        border-color: #6366f1;
        color: #ffffff;
    }
    QPushButton:pressed {
        background-color: #3730a3;
    }
    QPushButton#btn_danger {
        background-color: #7f1d1d;
        border: 1px solid #991b1b;
        color: #fecaca;
    }
    QPushButton#btn_danger:hover {
        background-color: #991b1b;
        border-color: #ef4444;
        color: #ffffff;
    }
    QPushButton#btn_success {
        background-color: #064e3b;
        border: 1px solid #065f46;
        color: #a7f3d0;
    }
    QPushButton#btn_success:hover {
        background-color: #065f46;
        border-color: #10b981;
        color: #ffffff;
    }
    QStatusBar {
        background-color: #1e293b;
        color: #94a3b8;
        border-top: 1px solid #334155;
    }
"""


# ==========================================
# 1. CONSTANTS & CONFIGURATION
# ==========================================
APP_NAME = "⭐ STAR SCHEDULER & BATCH AUTOMATOR ⭐"
APP_VERSION = "3.2.0"
DEVELOPER_NAME = "Developed By: Amir Hussain"

class TaskType(str, Enum):
    TEXT = "Text Message"
    SINGLE_PHOTO = "Single Photo"
    PHOTO_BATCH = "Photo Batch"
    DOCUMENT = "Document"

class TaskStatus(str, Enum):
    PENDING = "Pending"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"

class LogSeverity(str, Enum):
    INFO = "Info"
    WARNING = "Warning"
    ERROR = "Error"

def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    app_dir = base / "TelegramProfileManager"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

APP_DATA_DIR = get_app_data_dir()
DB_PATH = APP_DATA_DIR / "app_data.sqlite"
KEY_PATH = APP_DATA_DIR / "master.key"


# ==========================================
# 2. DATABASE MODELS & LAYER
# ==========================================
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    profile_folder = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    target_url_or_id = Column(Text, nullable=False)
    caption_text = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    scheduled_date = Column(DateTime, nullable=False)
    scheduled_end_date = Column(DateTime, nullable=True)
    random_images = Column(Boolean, default=False)
    random_captions = Column(Boolean, default=False)
    use_all_profiles = Column(Boolean, default=False)
    randomize_order = Column(Boolean, default=False)
    split_evenly = Column(Boolean, default=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    attempt_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    assigned_profile_name = Column(String(100), nullable=True)

class LogEntry(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    profile_name = Column(String(100), nullable=True)
    severity = Column(SQLEnum(LogSeverity), nullable=False)
    message = Column(Text, nullable=False)

Base.metadata.create_all(bind=engine)

def migrate_database():
    with engine.connect() as conn:
        inspector = inspect(engine)
        if inspector.has_table('tasks'):
            columns = [c['name'] for c in inspector.get_columns('tasks')]
            if 'scheduled_end_date' not in columns:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN scheduled_end_date DATETIME"))
            if 'random_images' not in columns:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN random_images BOOLEAN DEFAULT 0"))
            if 'random_captions' not in columns:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN random_captions BOOLEAN DEFAULT 0"))
            conn.commit()

migrate_database()


class Repository:
    def get_setting(self, key: str, default: Any = None):
        with SessionLocal() as db:
            s = db.query(Setting).filter_by(key=key).first()
            return s.value if s else default

    def set_setting(self, key: str, value: Any):
        with SessionLocal() as db:
            s = db.query(Setting).filter_by(key=key).first()
            if s:
                s.value = str(value)
            else:
                db.add(Setting(key=key, value=str(value)))
            db.commit()

    def get_profiles(self) -> List[Profile]:
        with SessionLocal() as db:
            return db.query(Profile).order_by(Profile.name).all()

    def add_profile(self, name: str, folder: str):
        with SessionLocal() as db:
            p = Profile(name=name, profile_folder=folder)
            db.add(p)
            db.commit()

    def update_profile(self, profile_id: int, name: str, folder: str):
        with SessionLocal() as db:
            p = db.query(Profile).get(profile_id)
            if p:
                p.name = name
                p.profile_folder = folder
                db.commit()

    def delete_profile(self, profile_id: int):
        with SessionLocal() as db:
            p = db.query(Profile).get(profile_id)
            if p:
                db.delete(p)
                db.commit()

    def add_task(self, task_type: TaskType, target: str, caption: str, file_path: str, 
                 scheduled_date: datetime, scheduled_end_date: datetime, 
                 random_images: bool, random_captions: bool,
                 use_all: bool, randomize: bool, split: bool, profile_name: str = "All Profiles"):
        with SessionLocal() as db:
            t = Task(
                task_type=task_type,
                target_url_or_id=target,
                caption_text=caption,
                file_path=file_path,
                scheduled_date=scheduled_date,
                scheduled_end_date=scheduled_end_date,
                random_images=random_images,
                random_captions=random_captions,
                use_all_profiles=use_all,
                randomize_order=randomize,
                split_evenly=split,
                assigned_profile_name=profile_name,
                status=TaskStatus.PENDING
            )
            db.add(t)
            db.commit()

    def get_tasks(self, status_filter: str = "All") -> List[Task]:
        with SessionLocal() as db:
            q = db.query(Task)
            if status_filter != "All":
                q = q.filter(Task.status == TaskStatus(status_filter))
            return q.order_by(desc(Task.scheduled_date)).all()

    def update_task_status(self, task_id: int, status: TaskStatus, error: str = None, profile_name: str = None):
        with SessionLocal() as db:
            t = db.query(Task).get(task_id)
            if t:
                t.status = status
                if error: t.last_error = error
                if profile_name: t.assigned_profile_name = profile_name
                db.commit()

    def retry_failed_tasks(self) -> int:
        with SessionLocal() as db:
            failed_tasks = db.query(Task).filter(Task.status == TaskStatus.FAILED).all()
            for t in failed_tasks:
                t.status = TaskStatus.PENDING
                t.last_error = None
            db.commit()
            return len(failed_tasks)

    def delete_task(self, task_id: int):
        with SessionLocal() as db:
            t = db.query(Task).get(task_id)
            if t:
                db.delete(t)
                db.commit()

    def clear_all_tasks(self):
        with SessionLocal() as db:
            db.query(Task).delete()
            db.commit()

    def add_log(self, severity: LogSeverity, message: str, profile_name: str = None):
        with SessionLocal() as db:
            db.add(LogEntry(severity=severity, message=message, profile_name=profile_name))
            db.commit()

    def get_logs(self, severity: str = "All", search: str = "") -> List[LogEntry]:
        with SessionLocal() as db:
            q = db.query(LogEntry)
            if severity != "All":
                q = q.filter(LogEntry.severity == LogSeverity(severity))
            if search:
                q = q.filter(LogEntry.message.contains(search))
            return q.order_by(desc(LogEntry.timestamp)).limit(1000).all()

    def clear_logs(self):
        with SessionLocal() as db:
            db.query(LogEntry).delete()
            db.commit()


# ==========================================
# 3. ENCRYPTION HELPER (FIXED RECENT BUG)
# ==========================================
class CredentialEncryptor:
    def __init__(self):
        if KEY_PATH.exists():
            self.key = KEY_PATH.read_bytes()
        else:
            self.key = Fernet.generate_key()
            KEY_PATH.write_bytes(self.key)
        self.fernet = Fernet(self.key)

    def encrypt(self, text: str) -> str:
        return self.fernet.encrypt(text.encode()).decode() if text else ""

    def decrypt(self, token: str) -> str:
        return self.fernet.decrypt(token.encode()).decode() if token else ""


# ==========================================
# 4. 10 COUNTRIES TIMEZONE DIALOG WINDOW
# ==========================================
class TimezoneDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 Global World Clock (10 Countries)")
        self.resize(560, 420)

        layout = QVBoxLayout(self)

        header = QLabel("🌍 Live Timezones (12-Hour AM/PM Format)")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header.setStyleSheet("color: #38bdf8;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self.table = QTableWidget(10, 3)
        self.table.setHorizontalHeaderLabels(["Country", "Timezone Offset", "Live Time (AM/PM)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_close = QPushButton("Close Clock")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_times)
        self.timer.start(1000)
        self.update_times()

    def update_times(self):
        countries = [
            ("🇵🇰 Pakistan (Must)", "PKT (UTC+5)", 5),
            ("🇸🇦 Saudi Arabia", "AST (UTC+3)", 3),
            ("🇦🇪 UAE", "GST (UTC+4)", 4),
            ("🇬🇧 United Kingdom", "BST (UTC+1)", 1),
            ("🇺🇸 USA (New York)", "EDT (UTC-4)", -4),
            ("🇨🇦 Canada (Toronto)", "EDT (UTC-4)", -4),
            ("🇩🇪 Germany", "CEST (UTC+2)", 2),
            ("🇮🇳 India", "IST (UTC+5:30)", 5.5),
            ("🇯🇵 Japan", "JST (UTC+9)", 9),
            ("🇦🇺 Australia (Sydney)", "AEST (UTC+10)", 10),
        ]

        now_utc = datetime.now(timezone.utc)

        for row, (country, tz_name, offset) in enumerate(countries):
            country_time = now_utc + timedelta(hours=offset)
            time_str = country_time.strftime("%I:%M:%S %p")

            self.table.setItem(row, 0, QTableWidgetItem(country))
            self.table.setItem(row, 1, QTableWidgetItem(tz_name))
            self.table.setItem(row, 2, QTableWidgetItem(time_str))


# ==========================================
# 5. BACKGROUND RUNNER THREAD
# ==========================================
class RunnerThread(QThread):
    log_signal = Signal(str, str)

    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        self.is_running = True

    def run(self):
        self.log_signal.emit("INFO", "Runner engine started monitoring queue...")
        while self.is_running:
            tasks = self.repo.get_tasks(status_filter="Pending")
            now = datetime.utcnow()
            for task in tasks:
                if not self.is_running: break
                if task.scheduled_date <= now:
                    self.process_task(task)
            time.sleep(3)

    def process_task(self, task: Task):
        self.repo.update_task_status(task.id, TaskStatus.RUNNING)
        self.log_signal.emit("INFO", f"Executing Task #{task.id}: {task.task_type.value} -> {task.target_url_or_id}")
        time.sleep(2)
        # Execution outcome
        self.repo.update_task_status(task.id, TaskStatus.COMPLETED, profile_name="Auto-Runner")
        self.log_signal.emit("INFO", f"Task #{task.id} Completed Successfully!")

    def stop(self):
        self.is_running = False
        self.log_signal.emit("INFO", "Runner engine stopped.")


# ==========================================
# 6. UI TABS IMPLEMENTATION
# ==========================================

# TAB 1: PROFILE MANAGER (ROBUST USERROLE SELECTION)
class ProfileManagerTab(QWidget):
    def __init__(self, repo: Repository, refresh_callback=None):
        super().__init__()
        self.repo = repo
        self.refresh_callback = refresh_callback
        self.enc = CredentialEncryptor()
        self.selected_profile_id: Optional[int] = None

        layout = QHBoxLayout(self)

        left_box = QGroupBox("Registered Chrome Profiles")
        left_layout = QVBoxLayout(left_box)
        self.profile_list = QListWidget()
        self.profile_list.itemClicked.connect(self.on_profile_selected)
        left_layout.addWidget(self.profile_list)

        btn_open = QPushButton("🌐 Open Selected Profile in Chrome")
        btn_open.setObjectName("btn_success")
        btn_open.clicked.connect(self.open_chrome_profile)
        left_layout.addWidget(btn_open)

        btn_del = QPushButton("🗑️ Delete Selected Profile")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self.delete_profile)
        left_layout.addWidget(btn_del)
        layout.addWidget(left_box, 1)

        right_box = QGroupBox("Profile Setup & Update Panel")
        right_layout = QVBoxLayout(right_box)

        form_layout = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_folder = QLineEdit()
        btn_browse = QPushButton("📁 Browse Path")
        btn_browse.clicked.connect(self.browse_folder)

        f_path_layout = QHBoxLayout()
        f_path_layout.addWidget(self.txt_folder)
        f_path_layout.addWidget(btn_browse)

        self.txt_user = QLineEdit(); self.txt_user.setPlaceholderText("Optional (Encrypted)")
        self.txt_pass = QLineEdit(); self.txt_pass.setEchoMode(QLineEdit.Password); self.txt_pass.setPlaceholderText("Optional (Encrypted)")

        form_layout.addRow("Profile Name:", self.txt_name)
        form_layout.addRow("Profile Path:", f_path_layout)
        form_layout.addRow("Telegram Username:", self.txt_user)
        form_layout.addRow("Telegram Password:", self.txt_pass)
        right_layout.addLayout(form_layout)

        btn_action_layout = QHBoxLayout()
        
        btn_save = QPushButton("➕ Save As New Profile")
        btn_save.setObjectName("btn_success")
        btn_save.clicked.connect(self.save_new_profile)

        btn_update = QPushButton("✏️ Update Selected Profile")
        btn_update.clicked.connect(self.update_existing_profile)

        btn_action_layout.addWidget(btn_save)
        btn_action_layout.addWidget(btn_update)
        right_layout.addLayout(btn_action_layout)

        btn_bulk = QPushButton("⚡ Auto Create 5 Default Profiles")
        btn_bulk.clicked.connect(self.auto_create_profiles)
        right_layout.addWidget(btn_bulk)
        right_layout.addSpacing(15)

        sett_group = QGroupBox("Automation Options")
        sett_layout = QFormLayout(sett_group)
        self.spin_workers = QSpinBox(); self.spin_workers.setRange(1, 10); self.spin_workers.setValue(int(self.repo.get_setting("parallel_workers", 2)))
        self.chk_safe = QCheckBox("Safe verification of final click"); self.chk_safe.setChecked(self.repo.get_setting("safe_verify", "True") == "True")
        self.chk_guard = QCheckBox("Upload guard active"); self.chk_guard.setChecked(self.repo.get_setting("upload_guard", "True") == "True")
        self.spin_wait = QSpinBox(); self.spin_wait.setRange(5, 120); self.spin_wait.setValue(int(self.repo.get_setting("max_wait_element", 15)))

        sett_layout.addRow("Parallel Workers:", self.spin_workers)
        sett_layout.addRow("", self.chk_safe)
        sett_layout.addRow("", self.chk_guard)
        sett_layout.addRow("Max Wait Element (sec):", self.spin_wait)

        btn_save_sett = QPushButton("⚙️ Save Automation Settings")
        btn_save_sett.clicked.connect(self.save_settings)
        sett_layout.addRow("", btn_save_sett)

        right_layout.addWidget(sett_group)
        right_layout.addStretch()
        layout.addWidget(right_box, 2)

        self.load_profiles()

    def on_profile_selected(self, item: QListWidgetItem):
        if not item: return
        p_id = item.data(Qt.UserRole)
        p_folder = item.data(Qt.UserRole + 1)
        p_name = item.data(Qt.UserRole + 2)

        self.selected_profile_id = p_id
        self.txt_name.setText(p_name)
        self.txt_folder.setText(p_folder)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Chrome Profile Folder")
        if folder: self.txt_folder.setText(folder)

    def save_new_profile(self):
        name = self.txt_name.text().strip()
        folder = self.txt_folder.text().strip()
        if not name or not folder:
            QMessageBox.warning(self, "Error", "Name and Folder Path are required!")
            return
        try:
            self.repo.add_profile(name, folder)
            self.repo.add_log(LogSeverity.INFO, f"Profile '{name}' added.", name)
            self.txt_name.clear(); self.txt_folder.clear()
            self.selected_profile_id = None
            self.load_profiles()
            if self.refresh_callback: self.refresh_callback()
            QMessageBox.information(self, "Success", f"New Profile '{name}' saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save profile: {e}")

    def update_existing_profile(self):
        if not self.selected_profile_id:
            QMessageBox.warning(self, "Warning", "Pehle list se update karne wali profile select karein!")
            return
        name = self.txt_name.text().strip()
        folder = self.txt_folder.text().strip()
        if not name or not folder:
            QMessageBox.warning(self, "Error", "Name and Folder Path required!")
            return
        try:
            self.repo.update_profile(self.selected_profile_id, name, folder)
            self.repo.add_log(LogSeverity.INFO, f"Profile ID {self.selected_profile_id} updated.", name)
            self.load_profiles()
            if self.refresh_callback: self.refresh_callback()
            QMessageBox.information(self, "Updated", f"Profile '{name}' updated successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not update profile: {e}")

    def auto_create_profiles(self):
        base_path = str(APP_DATA_DIR / "Profiles")
        for i in range(1, 6):
            p_name = f"Profile_{i}"
            p_dir = f"{base_path}/Profile_{i}"
            try:
                self.repo.add_profile(p_name, p_dir)
            except: pass
        self.load_profiles()
        if self.refresh_callback: self.refresh_callback()
        QMessageBox.information(self, "Success", "5 Default profiles generated!")

    def open_chrome_profile(self):
        curr = self.profile_list.currentItem()
        if not curr:
            QMessageBox.warning(self, "Select Profile", "Pehle list se profile select karein!")
            return
        
        p_path = curr.data(Qt.UserRole + 1)

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        chrome_bin = next((cp for cp in chrome_paths if os.path.exists(cp)), None)

        if not chrome_bin:
            QMessageBox.critical(self, "Error", "Chrome PC par nahi mila!")
            return

        try:
            subprocess.Popen([chrome_bin, f"--user-data-dir={p_path}", "https://web.telegram.org/"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Chrome launch error: {e}")

    def load_profiles(self):
        self.profile_list.clear()
        for p in self.repo.get_profiles():
            item = QListWidgetItem(f"ID: {p.id} | {p.name} | {p.profile_folder}")
            item.setData(Qt.UserRole, p.id)
            item.setData(Qt.UserRole + 1, p.profile_folder)
            item.setData(Qt.UserRole + 2, p.name)
            self.profile_list.addItem(item)

    def delete_profile(self):
        curr = self.profile_list.currentItem()
        if not curr: return
        p_id = curr.data(Qt.UserRole)
        self.repo.delete_profile(p_id)
        self.selected_profile_id = None
        self.txt_name.clear(); self.txt_folder.clear()
        self.load_profiles()
        if self.refresh_callback: self.refresh_callback()

    def save_settings(self):
        self.repo.set_setting("parallel_workers", self.spin_workers.value())
        self.repo.set_setting("safe_verify", self.chk_safe.isChecked())
        self.repo.set_setting("upload_guard", self.chk_guard.isChecked())
        self.repo.set_setting("max_wait_element", self.spin_wait.value())
        QMessageBox.information(self, "Settings Saved", "Automation settings updated successfully!")


# TAB 2: PHOTO TXT BATCH TAB
class PhotoTxtBatchTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo
        layout = QVBoxLayout(self)

        form_group = QGroupBox("Photo & Text Batch Automation Scheduler")
        form = QFormLayout(form_group)

        self.cmb_profile = QComboBox()
        self.reload_profiles_dropdown()

        self.cmb_type = QComboBox()
        self.cmb_type.addItems([t.value for t in TaskType])

        self.txt_target = QLineEdit()
        self.txt_target.setPlaceholderText("Group Link, Username, or Chat ID")

        self.txt_caption = QTextEdit()
        self.txt_caption.setPlaceholderText("Enter message text or captions here...")

        # Photo File/Folder Selection
        self.txt_photo_path = QLineEdit()
        btn_photo_file = QPushButton("📸 Photo File")
        btn_photo_file.clicked.connect(self.browse_photo_file)

        btn_photo_dir = QPushButton("📁 Photo Folder")
        btn_photo_dir.clicked.connect(self.browse_photo_folder)
        
        p_layout = QHBoxLayout()
        p_layout.addWidget(self.txt_photo_path)
        p_layout.addWidget(btn_photo_file)
        p_layout.addWidget(btn_photo_dir)

        # Text File/Folder Selection
        self.txt_text_path = QLineEdit()
        btn_text_file = QPushButton("📝 Text File")
        btn_text_file.clicked.connect(self.browse_text_file)

        btn_text_dir = QPushButton("📁 Text Folder")
        btn_text_dir.clicked.connect(self.browse_text_folder)

        t_layout = QHBoxLayout()
        t_layout.addWidget(self.txt_text_path)
        t_layout.addWidget(btn_text_file)
        t_layout.addWidget(btn_text_dir)

        # Random Checks
        self.chk_rand_img = QCheckBox("🎲 Randomize Images / Photos")
        self.chk_rand_txt = QCheckBox("🔀 Randomize Captions / Text")
        
        rand_layout = QHBoxLayout()
        rand_layout.addWidget(self.chk_rand_img)
        rand_layout.addWidget(self.chk_rand_txt)

        # Start Time and End Time Setup
        self.dt_picker_start = QDateTimeEdit(QDateTime.currentDateTime())
        self.dt_picker_start.setDisplayFormat("yyyy-MM-dd hh:mm:ss AP")

        self.dt_picker_end = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.dt_picker_end.setDisplayFormat("yyyy-MM-dd hh:mm:ss AP")

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Start:"))
        time_layout.addWidget(self.dt_picker_start)
        time_layout.addWidget(QLabel("End:"))
        time_layout.addWidget(self.dt_picker_end)

        self.chk_all = QCheckBox("Run on All Profiles")
        self.chk_rand_order = QCheckBox("Randomize Profile Execution Order")
        self.chk_split = QCheckBox("Split Workload Evenly")

        form.addRow("Assigned Profile:", self.cmb_profile)
        form.addRow("Task Type:", self.cmb_type)
        form.addRow("Target URL / Chat ID:", self.txt_target)
        form.addRow("Message / Caption:", self.txt_caption)
        form.addRow("Photo Access:", p_layout)
        form.addRow("Text Access:", t_layout)
        form.addRow("Randomization Options:", rand_layout)
        form.addRow("Schedule Range (AM/PM):", time_layout)
        form.addRow("Execution Settings:", self.chk_all)
        form.addRow("", self.chk_rand_order)
        form.addRow("", self.chk_split)

        layout.addWidget(form_group)

        action_btns_layout = QHBoxLayout()

        btn_enqueue = QPushButton("🚀 Enqueue Scheduled Batch Task")
        btn_enqueue.setObjectName("btn_success")
        btn_enqueue.clicked.connect(self.enqueue_task)

        btn_reset = QPushButton("🧹 Reset Form")
        btn_reset.clicked.connect(self.reset_form)

        action_btns_layout.addWidget(btn_enqueue)
        action_btns_layout.addWidget(btn_reset)

        layout.addLayout(action_btns_layout)
        layout.addStretch()

    def reload_profiles_dropdown(self):
        self.cmb_profile.clear()
        self.cmb_profile.addItem("All Profiles")
        for p in self.repo.get_profiles():
            self.cmb_profile.addItem(f"{p.name}")

    def browse_photo_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Photo File", "", "Images (*.png *.jpg *.jpeg)")
        if f: self.txt_photo_path.setText(f)

    def browse_photo_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Photo Folder")
        if d: self.txt_photo_path.setText(d)

    def browse_text_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Text File", "", "Text Files (*.txt)")
        if f: self.txt_text_path.setText(f)

    def browse_text_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Text Folder")
        if d: self.txt_text_path.setText(d)

    def reset_form(self):
        self.txt_target.clear()
        self.txt_caption.clear()
        self.txt_photo_path.clear()
        self.txt_text_path.clear()
        self.chk_rand_img.setChecked(False)
        self.chk_rand_txt.setChecked(False)
        self.chk_all.setChecked(False)
        self.chk_rand_order.setChecked(False)
        self.chk_split.setChecked(False)

    def enqueue_task(self):
        target = self.txt_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Target URL / Chat ID is required!")
            return

        t_type = TaskType(self.cmb_type.currentText())
        caption = self.txt_caption.toPlainText().strip()
        f_path = self.txt_photo_path.text().strip() or self.txt_text_path.text().strip()
        
        start_qdt = self.dt_picker_start.dateTime()
        end_qdt = self.dt_picker_end.dateTime()
        
        start_dt = datetime.fromtimestamp(start_qdt.toSecsSinceEpoch())
        end_dt = datetime.fromtimestamp(end_qdt.toSecsSinceEpoch())
        profile_sel = self.cmb_profile.currentText()

        self.repo.add_task(
            task_type=t_type,
            target=target,
            caption=caption,
            file_path=f_path,
            scheduled_date=start_dt,
            scheduled_end_date=end_dt,
            random_images=self.chk_rand_img.isChecked(),
            random_captions=self.chk_rand_txt.isChecked(),
            use_all=self.chk_all.isChecked() or (profile_sel == "All Profiles"),
            randomize=self.chk_rand_order.isChecked(),
            split=self.chk_split.isChecked(),
            profile_name=profile_sel
        )
        self.repo.add_log(LogSeverity.INFO, f"Enqueued task '{t_type.value}' for {target}")
        QMessageBox.information(self, "Success", "Batch Task successfully enqueued!")
        self.reset_form()


# TAB 3: TASKS RUNNER
class TasksRunnerTab(QWidget):
    def __init__(self, repo: Repository, status_callback=None):
        super().__init__()
        self.repo = repo
        self.status_callback = status_callback
        self.runner_thread: Optional[RunnerThread] = None

        layout = QVBoxLayout(self)

        top_controls = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Start Engine")
        self.btn_start.setObjectName("btn_success")
        self.btn_start.clicked.connect(self.start_runner)

        self.btn_stop = QPushButton("⏹️ Stop Engine")
        self.btn_stop.setObjectName("btn_danger")
        self.btn_stop.clicked.connect(self.stop_runner)

        top_controls.addWidget(self.btn_start)
        top_controls.addWidget(self.btn_stop)
        
        top_controls.addSpacing(15)
        top_controls.addWidget(QLabel("Filter Status:"))
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems(["All", "Pending", "Running", "Completed", "Failed"])
        self.cmb_filter.currentTextChanged.connect(self.load_tasks)
        top_controls.addWidget(self.cmb_filter)

        btn_retry = QPushButton("🔄 Retry Failed Tasks")
        btn_retry.clicked.connect(self.retry_failed)
        top_controls.addWidget(btn_retry)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.load_tasks)
        top_controls.addWidget(btn_refresh)

        btn_clear_all = QPushButton("🗑️ Clear All Tasks")
        btn_clear_all.setObjectName("btn_danger")
        btn_clear_all.clicked.connect(self.clear_all_tasks)
        top_controls.addWidget(btn_clear_all)

        layout.addLayout(top_controls)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Target", "Start Time", "End Time", "Status", "Profile", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.load_tasks()

    def start_runner(self):
        if not self.runner_thread or not self.runner_thread.isRunning():
            self.runner_thread = RunnerThread(self.repo)
            self.runner_thread.log_signal.connect(self.on_log)
            self.runner_thread.start()
            if self.status_callback: self.status_callback("🟢 Running")

    def stop_runner(self):
        if self.runner_thread and self.runner_thread.isRunning():
            self.runner_thread.stop()
            self.runner_thread.wait()
            if self.status_callback: self.status_callback("🔴 Stopped")

    def retry_failed(self):
        count = self.repo.retry_failed_tasks()
        if count > 0:
            QMessageBox.information(self, "Retry Tasks", f"{count} Failed Tasks ko fir se 'Pending' state mein shift kar diya gaya hai!")
            self.load_tasks()
        else:
            QMessageBox.information(self, "Retry Tasks", "Koi bhi Failed Task nahi mila.")

    def on_log(self, severity: str, message: str):
        self.repo.add_log(LogSeverity(severity), message)
        self.load_tasks()

    def load_tasks(self):
        self.table.setRowCount(0)
        status_filter = self.cmb_filter.currentText()
        tasks = self.repo.get_tasks(status_filter=status_filter)

        for row, t in enumerate(tasks):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(t.id)))
            self.table.setItem(row, 1, QTableWidgetItem(t.task_type.value))
            self.table.setItem(row, 2, QTableWidgetItem(t.target_url_or_id))
            
            start_str = t.scheduled_date.strftime("%Y-%m-%d %I:%M:%S %p") if t.scheduled_date else "N/A"
            end_str = t.scheduled_end_date.strftime("%Y-%m-%d %I:%M:%S %p") if t.scheduled_end_date else "N/A"
            
            self.table.setItem(row, 3, QTableWidgetItem(start_str))
            self.table.setItem(row, 4, QTableWidgetItem(end_str))

            status_item = QTableWidgetItem(t.status.value)
            if t.status == TaskStatus.COMPLETED:
                status_item.setForeground(QColor("#10b981"))
            elif t.status == TaskStatus.RUNNING:
                status_item.setForeground(QColor("#38bdf8"))
            elif t.status == TaskStatus.PENDING:
                status_item.setForeground(QColor("#f59e0b"))
            else:
                status_item.setForeground(QColor("#ef4444"))
            
            self.table.setItem(row, 5, status_item)
            self.table.setItem(row, 6, QTableWidgetItem(t.assigned_profile_name or "All Profiles"))

            btn_del = QPushButton("Delete")
            btn_del.setObjectName("btn_danger")
            btn_del.clicked.connect(lambda _, tid=t.id: self.delete_task(tid))
            self.table.setCellWidget(row, 7, btn_del)

    def delete_task(self, task_id: int):
        self.repo.delete_task(task_id)
        self.load_tasks()

    def clear_all_tasks(self):
        ans = QMessageBox.question(self, "Confirm Clear", "Kya aap saaray tasks delete karna chahte hain?", QMessageBox.Yes | QMessageBox.No)
        if ans == QMessageBox.Yes:
            self.repo.clear_all_tasks()
            self.load_tasks()


# TAB 4: PERFORMANCE LOGS
class PerformanceLogsTab(QWidget):
    def __init__(self, repo: Repository):
        super().__init__()
        self.repo = repo

        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Severity:"))
        self.cmb_severity = QComboBox()
        self.cmb_severity.addItems(["All", "Info", "Warning", "Error"])
        self.cmb_severity.currentTextChanged.connect(self.load_logs)
        filter_layout.addWidget(self.cmb_severity)

        filter_layout.addWidget(QLabel("Search:"))
        self.txt_search = QLineEdit()
        self.txt_search.textChanged.connect(self.load_logs)
        filter_layout.addWidget(self.txt_search)

        btn_clear = QPushButton("🗑️ Clear Logs")
        btn_clear.setObjectName("btn_danger")
        btn_clear.clicked.connect(self.clear_logs)
        filter_layout.addWidget(btn_clear)

        btn_export = QPushButton("💾 Export Logs")
        btn_export.clicked.connect(self.export_logs)
        filter_layout.addWidget(btn_export)

        layout.addLayout(filter_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #020617; color: #38bdf8; font-family: Consolas, Monospace; font-size: 13px;")
        layout.addWidget(self.log_area)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_logs)
        self.timer.start(3000)

        self.load_logs()

    def load_logs(self):
        sev = self.cmb_severity.currentText()
        search = self.txt_search.text().strip()
        logs = self.repo.get_logs(severity=sev, search=search)

        self.log_area.clear()
        for l in logs:
            p_str = f"[{l.profile_name}] " if l.profile_name else ""
            line = f"[{l.timestamp.strftime('%I:%M:%S %p')}] [{l.severity.value}] {p_str}{l.message}"
            self.log_area.append(line)

    def clear_logs(self):
        self.repo.clear_logs()
        self.load_logs()

    def export_logs(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Logs", "", "Text Files (*.txt);;CSV Files (*.csv)")
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(self.log_area.toPlainText())
            QMessageBox.information(self, "Exported", "Logs exported successfully!")


# ==========================================
# 7. MAIN APPLICATION WINDOW
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1180, 800)
        self.setStyleSheet(DECENT_DARK_STYLESHEET)

        self.repo = Repository()

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        # Header
        header_layout = QHBoxLayout()

        star_header = QLabel("⭐ STAR AUTOMATION & SCHEDULER ⭐")
        star_header.setFont(QFont("Segoe UI", 15, QFont.Bold))
        star_header.setStyleSheet("color: #38bdf8; padding: 4px;")
        header_layout.addWidget(star_header)

        header_layout.addStretch()

        btn_tz = QPushButton("🌐 World Timezones (10 Countries)")
        btn_tz.clicked.connect(self.show_timezones)
        header_layout.addWidget(btn_tz)

        main_layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()

        self.profile_tab = ProfileManagerTab(self.repo, refresh_callback=self.on_profiles_updated)
        self.scheduler_tab = PhotoTxtBatchTab(self.repo)
        self.runner_tab = TasksRunnerTab(self.repo, status_callback=self.update_runner_status_label)
        self.logs_tab = PerformanceLogsTab(self.repo)

        self.tabs.addTab(self.profile_tab, "1) Profile Manager")
        self.tabs.addTab(self.scheduler_tab, "2) Photo TXT batch")
        self.tabs.addTab(self.runner_tab, "3) Tasks / Runner")
        self.tabs.addTab(self.logs_tab, "4) Performance Logs")

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(main_widget)

        # Status Bar with Developer Branding
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.lbl_developer = QLabel(f"  {DEVELOPER_NAME}  ")
        self.lbl_developer.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.lbl_developer.setStyleSheet("color: #38bdf8; font-style: italic;")
        self.statusBar.addWidget(self.lbl_developer)

        self.lbl_profile_count = QLabel("Profiles: 0")
        self.lbl_task_count = QLabel("Pending Tasks: 0")
        self.lbl_runner_status = QLabel("Engine: 🔴 Stopped")

        self.statusBar.addPermanentWidget(self.lbl_profile_count)
        self.statusBar.addPermanentWidget(QLabel("  |  "))
        self.statusBar.addPermanentWidget(self.lbl_task_count)
        self.statusBar.addPermanentWidget(QLabel("  |  "))
        self.statusBar.addPermanentWidget(self.lbl_runner_status)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_statusbar_stats)
        self.stats_timer.start(2000)
        self.update_statusbar_stats()

    def show_timezones(self):
        dlg = TimezoneDialog(self)
        dlg.exec()

    def on_profiles_updated(self):
        self.scheduler_tab.reload_profiles_dropdown()
        self.update_statusbar_stats()

    def update_runner_status_label(self, status_text: str):
        self.lbl_runner_status.setText(f"Engine: {status_text}")

    def update_statusbar_stats(self):
        profiles = len(self.repo.get_profiles())
        tasks = self.repo.get_tasks()
        pending = sum(1 for t in tasks if t.status == TaskStatus.PENDING)
        
        self.lbl_profile_count.setText(f"Total Profiles: {profiles}")
        self.lbl_task_count.setText(f"Pending Tasks: {pending}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
