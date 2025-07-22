#!/usr/bin/env uv run python
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

# Load environment variables from .env file
load_dotenv()

app = typer.Typer()

def load_config():
    config_path = Path("config.yaml")
    if not config_path.exists():
        typer.echo("Error: config.yaml not found", err=True)
        raise typer.Exit(1)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@app.command()
def day():
    """Show what day it is since company start."""
    config = load_config()
    start_date_str = config["company"]["start_date"]
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    days_elapsed = (today - start_date).days
    typer.echo(f"Today is Day {days_elapsed}")

@app.command()
def journal(entry: str = typer.Argument(None, help="Journal entry text")):
    """Write a quick journal entry."""
    config = load_config()
    entries_dir = Path(config.get("journal", {}).get("entries_dir", "journal_entries"))
    entries_dir.mkdir(exist_ok=True)
    
    today = datetime.now()
    filename = f"{today.strftime('%Y-%m-%d')}.txt"
    entry_file = entries_dir / filename
    
    if entry is None:
        # Open vim with existing content or empty file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
            # Load existing content if file exists, otherwise create title
            if entry_file.exists():
                with open(entry_file, 'r') as f:
                    temp_file.write(f.read())
            else:
                # Create title with day number
                config = load_config()
                start_date_str = config["company"]["start_date"]
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                today_date = today.date()
                days_elapsed = (today_date - start_date).days
                
                title = f"Day {days_elapsed} - {today.strftime('%A, %B %d, %Y')}\n\n"
                temp_file.write(title)
            temp_file.flush()
            
            # Open vim
            subprocess.run(['vim', temp_file.name])
            
            # Read the content back
            temp_file.seek(0)
            with open(temp_file.name, 'r') as f:
                content = f.read().strip()
            
            if content:
                # Write back to the journal file
                with open(entry_file, 'w') as f:
                    f.write(content)
                typer.echo(f"Journal updated: {entry_file}")
            else:
                typer.echo("No content saved")
                
        # Clean up temp file
        Path(temp_file.name).unlink()
    else:
        # Original behavior for command line entries
        timestamp = today.strftime("%H:%M:%S")
        entry_text = f"[{timestamp}] {entry}\n"
        
        with open(entry_file, "a") as f:
            f.write(entry_text)
        
        typer.echo(f"Journal entry added to {entry_file}")

def send_email(subject: str, body: str, to_email: str):
    """Send email using Gmail SMTP."""
    config = load_config()
    email_config = config.get("email", {})
    
    from_email = email_config.get("from_address")
    smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
    smtp_port = email_config.get("smtp_port", 587)
    
    if not from_email:
        typer.echo("Error: from_address not configured in config.yaml", err=True)
        raise typer.Exit(1)
    
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not password:
        typer.echo("Error: GMAIL_APP_PASSWORD environment variable not set", err=True)
        typer.echo("Generate an app password at https://myaccount.google.com/apppasswords", err=True)
        raise typer.Exit(1)
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    console = Console()
    
    def send_email_task():
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(from_email, password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            return True
        except Exception as e:
            console.print(f"Error sending email: {e}", style="red")
            raise typer.Exit(1)
    
    # Show spinner while sending email
    with console.status("[bold green]Sending email...", spinner="dots"):
        success = send_email_task()
        if success:
            time.sleep(0.5)  # Brief pause to show completion
    
    console.print(f"✅ Email sent successfully to {to_email}", style="green")

@app.command()
def send_journal(date: str = typer.Option(None, help="Date in YYYY-MM-DD format, defaults to today")):
    """Send journal entry for a specific date via email."""
    config = load_config()
    entries_dir = Path(config.get("journal", {}).get("entries_dir", "journal_entries"))
    
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    entry_file = entries_dir / f"{date}.txt"
    
    if not entry_file.exists():
        typer.echo(f"No journal entry found for {date}", err=True)
        raise typer.Exit(1)
    
    with open(entry_file, 'r') as f:
        content = f.read()
    
    if not content.strip():
        typer.echo(f"Journal entry for {date} is empty", err=True)
        raise typer.Exit(1)
    
    # Get day number for subject
    start_date_str = config["company"]["start_date"]
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    entry_date = datetime.strptime(date, "%Y-%m-%d").date()
    days_elapsed = (entry_date - start_date).days
    
    subject = f"Day {days_elapsed}"
    to_email = config["company"]["email_list"]
    
    send_email(subject, content, to_email)

if __name__ == "__main__":
    app()
