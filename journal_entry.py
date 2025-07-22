import typer
import yaml
import subprocess
import tempfile
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.spinner import Spinner
import threading
import time
from config import load_config

class JournalEntry:
    def __init__(self, date: str = None):
        self.date = date
        if date is None:
            self.date = datetime.now().strftime("%Y-%m-%d")

    def file_path(self):
        config = load_config()
        entries_dir = Path(config.get("journal", {}).get("entries_dir", "journal_entries"))
        entries_dir.mkdir(exist_ok=True)
        
        filename = f"{self.date}.txt"
        entry_file = entries_dir / filename
        return entry_file
    
    def read(self):
        entry_file = self.file_path()
        if not entry_file.exists():
            typer.echo(f"No journal entry found for {self.date}", err=True)
            raise typer.Exit(1)
        
        with open(entry_file, 'r') as f:
            content = f.read()
        return content.strip()

    def write(self, content: str):
        with open(self.file_path(), "w") as f:
            f.write(content)
    
    def append(self, content: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry_text = f"[{timestamp}] {content}\n"
        
        with open(self.file_path(), "a") as f:
            f.write(entry_text)
    
    def open(self, editor: str = "open"):
        subprocess.run([editor, self.file_path()])
    
    def day(self):
        config = load_config()
        today = datetime.now()
        start_date_str = config["company"]["start_date"]
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today_date = today.date()
        return (today_date - start_date).days
    
    def title(self):
        days_elapsed = self.day()
        today = datetime.now()
        return f"Day {days_elapsed} - {today.strftime('%A, %B %d, %Y')}\n\n"
    
    def email_subject(self):
        days_elapsed = self.day()
        return f"Day {days_elapsed}"
    
    def __str__(self):
        return f"{self.date}: {self.read()}"
    
    def __repr__(self):
        return f"JournalEntry(date={self.date})"