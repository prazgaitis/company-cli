import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def load_config():
    config_path = Path("config.yaml")
    if not config_path.exists():
        typer.echo("Error: config.yaml not found", err=True)
        raise typer.Exit(1)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
