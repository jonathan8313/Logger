"""
mylogger.py
Logger complet, réutilisable et personnalisable :
- Couleurs en console
- Logs JSON en fichier (rotation quotidienne)
- Un fichier par module
- Capture automatique des exceptions (traceback)
- Gestion globale des hooks (sys, threading, asyncio) + last_crash.log
"""

import logging
import logging.handlers
import sys
import traceback
import json
import os
import threading  # NOUVEAU
import asyncio  # NOUVEAU
from datetime import datetime
from pathlib import Path
from typing import Optional
from colorama import init as colorama_init, Fore, Style


# Initialisation colorama (Windows friendly)
colorama_init(autoreset=True)

# =============================
# VARIABLES ET CONSTANTES GLOBALES
# =============================

# Le chemin pour le fichier de crash dédié
LAST_CRASH_FILE = Path(__file__).resolve().parent / "last_crash.log"


# ---------- Couleurs console (Inchagé) ----------
COLOR_LEVELS = {
    "DEBUG": Fore.BLUE + Style.DIM,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}


class ColoredFormatter(logging.Formatter):
    """Formatter pour la console avec couleurs selon le niveau."""
    def format(self, record: logging.LogRecord) -> str:
        # ... (Inchangé) ...
        levelname = record.levelname
        color = COLOR_LEVELS.get(levelname, "")
        reset = Style.RESET_ALL
        record_copy = logging.makeLogRecord(record.__dict__.copy())
        record_copy.levelname = f"{color}{levelname}{reset}"
        return super().format(record_copy)


class JsonFormatter(logging.Formatter):
    """Formateur qui écrit chaque log en JSON (fichier)."""

    def format(self, record: logging.LogRecord) -> str:
        # ... (Inchangé) ...
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "filename": record.filename,
            "lineno": record.lineno,
            "funcName": record.funcName,
        }
        if record.exc_info:
            log_record["traceback"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


# =============================
# TRACEBACK → last_crash.log
# =============================

def dump_last_crash(exc_type, exc_value, exc_traceback):
    """Écrit un fichier last_crash.log contenant le traceback complet."""
    try:
        with open(LAST_CRASH_FILE, "w", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass


# =============================
# HOOK PRINCIPAL : sys (Processus principal)
# =============================

def excepthook_logger(exc_type, exc_value, exc_traceback):
    """Gère les exceptions non gérées du thread principal."""
    logger = logging.getLogger()

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(
        "Exception non gérée :",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

    dump_last_crash(exc_type, exc_value, exc_traceback)


# =============================
# HOOK THREADS
# =============================

def thread_excepthook(args):
    """Gère les exceptions non gérées dans les threads secondaires."""
    logger = logging.getLogger()

    if issubclass(args.exc_type, KeyboardInterrupt):
        return

    logger.critical(
        f"Exception dans un thread '{args.thread.name}' :",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )

    dump_last_crash(args.exc_type, args.exc_value, args.exc_traceback)


# =============================
# HOOK ASYNCIO
# =============================

def asyncio_exception_handler(loop, context):
    """Gère les exceptions non gérées dans les tâches asyncio."""
    logger = logging.getLogger()
    msg = context.get("message", "Erreur asyncio inconnue")
    exception = context.get("exception")

    if exception:
        logger.error(f"Exception asyncio : {msg}", exc_info=exception)
        dump_last_crash(type(exception), exception, exception.__traceback__)
    else:
        logger.error(f"Exception asyncio : {msg}")


# =============================
# INSTALLATION DES HOOKS GLOBALE
# =============================

def install_global_exception_handlers():
    """Installe tous les hooks d'exception globaux."""
    
    # Hook du processus principal
    sys.excepthook = excepthook_logger
    
    # Hook des threads secondaires (nécessite Python 3.8+)
    if sys.version_info >= (3, 8):
        threading.excepthook = thread_excepthook

    # Hook asyncio (gestionnaire du loop par défaut)
    try:
        # Tente de récupérer le loop par défaut si disponible
        loop = asyncio.get_event_loop()
        # Vérifie si le loop est déjà en cours d'exécution
        if not loop.is_running():
            # Si non démarré, on peut définir le gestionnaire
             loop.set_exception_handler(asyncio_exception_handler)
        else:
             # Si le loop est déjà en cours, définir le handler pourrait échouer ou être ignoré
             pass 
    except RuntimeError:
        # Aucune loop d'événements n'est définie. (OK si pas d'asyncio utilisé)
        pass


# ---------- Logger Class (Mise à jour) ----------
class Logger:
    
    def __init__(
        self,
        name: Optional[str] = None,
        level: int = logging.INFO,
        install_excepthook: bool = True,
    ):
        """Initialise le logger."""
        self.module_name = name if name and name != "__main__" else Path(sys.argv[0]).name
        
        # Chemins des fichiers (log normal et json)
        self.log_path = self._log_path_for_module()
        self.api_log_path = self._log_path_Jsonfor_module()

        self.logger = logging.getLogger(self.module_name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        if not self.logger.handlers:
            self._setup_console_handler(level)
            self._setup_file_handler() # Log standard
            self._setup_api_app()      # Log JSON
            
        logging.captureWarnings(True)

        # 🚨 MISE À JOUR ICI 🚨
        if install_excepthook:
            install_global_exception_handlers()
            
        self.logger.debug(f"Logger initialisé. Log: {self.log_path}, JSON: {self.api_log_path}")

    # ... (les méthodes _log_path_for_module, _log_path_Jsonfor_module, 
    # _setup_console_handler, _setup_file_handler, _setup_api_app restent inchangées) ...

    def _log_path_for_module(self) -> Path:
        """
        Crée un fichier de log unique dans le dossier "logs" avec
        le nom du script courant (sans extension) et extension .log
        """
        base = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "application"
        log_dir = Path(sys.argv[0]).resolve().parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        # Utilisation de get("COMPUTERNAME", "unknown") pour la robustesse
        log_file = log_dir / f"{base}_{os.environ.get('COMPUTERNAME', 'unknown')}.log" 
        return log_file
    
    def _log_path_Jsonfor_module(self) -> Path:
        """
        Crée un fichier de log unique dans le dossier "logs" avec
        le nom du script courant (sans extension) et extension .json
        """
        base = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else "application"
        log_dir = Path(sys.argv[0]).resolve().parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{base}_{os.environ.get('COMPUTERNAME', 'unknown')}.json"
        return log_file

    def _setup_console_handler(self, level: int):
        """Configure le handler console avec couleurs."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_fmt = ColoredFormatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_fmt)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self):
        """Configure le handler fichier avec rotation et log standard (.log)."""
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(self.log_path),
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # tout logger dans le fichier
        file_formatter = logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _setup_api_app(self):
        """Configure le handler fichier avec rotation et JSON (.json)."""
        api_file_handler = logging.handlers.RotatingFileHandler(
            filename=str(self.api_log_path),
            maxBytes=10485760,
            backupCount=7,
            encoding="utf-8",
        )
        api_file_handler.setLevel(logging.DEBUG)  # tout logger dans le fichier
        api_file_formatter = JsonFormatter()
        api_file_handler.setFormatter(api_file_formatter)
        self.logger.addHandler(api_file_handler)
        
    def get_logger(self) -> logging.Logger:
        return self.logger

# Suppression de la méthode statique Logger.excepthook_logger 
# car elle est remplacée par la fonction globale excepthook_logger


# ---------- Exemple d’utilisation ----------
if __name__ == "__main__":
    # Assurez-vous que le niveau est DEBUG pour voir tous les messages de setup
    my_logger = Logger(level=logging.DEBUG, install_excepthook=True)
    log = my_logger.get_logger()

    log.info("Logger initialisé avec tous les hooks.")
    
    # 1. Test d'exception gérée (écrit dans les logs + JSON avec traceback)
    try:
        1 / 0
    except Exception:
        log.exception("Erreur interceptée (division par zéro).")
    
    # 2. Test d'exception non gérée (écrit dans les logs + JSON + last_crash.log)
    # Décommentez ceci pour tester le hook global :
    # raise RuntimeError("Erreur non capturée pour test global.") 

    log.debug("Fin du script principal.")