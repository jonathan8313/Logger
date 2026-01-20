import os
import time
import multiprocessing
from pathlib import Path
import pytest
from jvlogger import JVLogger

def run_instance(name, log_dir, message):
    """Fonction exécutée dans un processus séparé."""
    with JVLogger(name=name, log_dir=log_dir, single_instance=False) as logger:
        logger.info(message)
    # Le logger est fermé à la fin du bloc with, ce qui déclenche le merge

def test_multi_instance_merge(temp_log_dir):
    app_name = "multi_merge_test"
    msg1 = "Message from instance 1"
    msg2 = "Message from instance 2"
    
    # On lance deux processus
    p1 = multiprocessing.Process(target=run_instance, args=(app_name, temp_log_dir, msg1))
    p2 = multiprocessing.Process(target=run_instance, args=(app_name, temp_log_dir, msg2))
    
    p1.start()
    p2.start()
    
    p1.join()
    p2.join()
    
    # Vérification des fichiers
    log_file = Path(temp_log_dir) / f"{app_name}.log"
    json_file = Path(temp_log_dir) / f"{app_name}.json"
    
    assert log_file.exists()
    assert json_file.exists()
    
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert msg1 in content
        assert msg2 in content
        
    # Vérification qu'il ne reste pas de fichiers temporaires
    remaining_files = list(Path(temp_log_dir).glob(f"{app_name}_*.log"))
    assert len(remaining_files) == 0, f"Temporary files still exist: {remaining_files}"
