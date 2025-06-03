# core/config.py
import configparser
import os
from pathlib import Path

class Settings:
    """
    A class to handle application settings loaded from a configuration file.

    How to use example:
    
        ```python
        from app.core.config import settings

        # Access settings like this:
        print(settings.DB_HOST)
        print(settings.DB_PORT)
        ```
    """
    def __init__(self, ini_path: str):
        parser = configparser.ConfigParser()
        parser.read(ini_path)

        if 'security' not in parser:
            raise ValueError("Seção [security] não encontrada em config.ini")

        for key, val in parser['security'].items():
            # transforma em atributo MAIÚSCULO
            name = key.upper()
            # se existir VARIÁVEL_DE_AMBIENTE com mesmo nome, usa ela
            env = os.getenv(name)
            setattr(self, name, env if env is not None else val)

    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k,v in self.__dict__.items())
        return f"<security {attrs}>"

# instancia única, importável por todo o app
print(f"config base path: {Path(__file__).parent / "config.ini"}")
config_path = os.getenv("OPEN_SHEET_APP_CONFIG", Path(__file__).parent / "config.ini")
_base = config_path
settings = Settings(str(_base))
