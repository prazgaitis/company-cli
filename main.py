#!/usr/bin/env uv run python
import typer
import subprocess
import tempfile
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from rich.console import Console
import time
from journal_entry import JournalEntry
from config import load_config

app = typer.Typer()

@app.command()
def day():
    """Show what day it is since company start."""
    entry = JournalEntry()
    typer.echo(f"Today is Day {entry.day()}")

@app.command()
def read(date: str = typer.Option(None, help="Date in YYYY-MM-DD format, defaults to today")):
    """Read today's journal entry."""
    entry = JournalEntry(date)
    typer.echo(entry.read())

@app.command()
def edit(date: str = typer.Option(None, help="Date in YYYY-MM-DD format, defaults to today"), editor: str = "vim"):
    """Edit today's journal entry."""
    entry = JournalEntry(date)
    entry.open(editor)

@app.command()
def open_entry(date: str = typer.Option(None, help="Date in YYYY-MM-DD format, defaults to today")):
    """Open today's journal entry."""
    entry = JournalEntry(date)
    entry.open()

@app.command()
def open_dir():
    """Open the journal directory."""
    config = load_config()
    journal_dir = Path(config.get("journal", {}).get("entries_dir", "journal_entries"))
    subprocess.run(["open", journal_dir])

@app.command()
def journal(entry: str = typer.Argument(None, help="Journal entry text")):
    """Write a quick journal entry."""
    journal_entry = JournalEntry()
    
    if entry is None:
        # Open vim with existing content or empty file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
            # Load existing content if file exists, otherwise create title
            entry_file = journal_entry.file_path()
            if entry_file.exists():
                with open(entry_file, 'r') as f:
                    temp_file.write(f.read())
            else:
                # Create title with day number
                title = journal_entry.title()
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
                journal_entry.write(content)
                typer.echo(f"Journal updated: {journal_entry.file_path()}")
            else:
                typer.echo("No content saved")
                
        # Clean up temp file
        Path(temp_file.name).unlink()
    else:
        # Original behavior for command line entries
        journal_entry.append(entry)
        
        typer.echo(f"Journal entry added to {journal_entry.file_path()}")

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
    entry = JournalEntry(date)
    
    content = entry.read()
    
    if not content.strip():
        typer.echo(f"Journal entry for {date} is empty", err=True)
        raise typer.Exit(1)
    
    subject = entry.email_subject()
    to_email = config["company"]["email_list"]
    
    send_email(subject, content, to_email)

if __name__ == "__main__":
    app()
