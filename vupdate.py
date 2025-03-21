
# -*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons
import configparser
import datetime, time
from datetime import datetime
from collections import deque, defaultdict
import xbmc
import xbmcvfs
import shutil
import os
import traceback
import json
import io
import requests
import re
import builtins
import keyword
import ast
import socket
import textwrap
import difflib
from difflib import get_close_matches, SequenceMatcher
import random
import string
from string import Template
import sys
from typing import List, Optional, Dict, Set, Deque, Tuple, Union
import glob
import concurrent.futures
import threading
import tokenize
import symtable
import xml.etree.ElementTree as ET

from requests.exceptions import RequestException, SSLError
from resources.lib import logger
from resources.lib.logger import VSlog, VSPath

from io import StringIO, BytesIO
from functools import lru_cache

from resources.lib.unparser import Unparser

def insert_update_service_addon():
    """
    Opens the file at
    special://home/addons/plugin.video.vstream/resources/lib/update.py
    and makes the following changes:
      1. If the required_imports list contains the tokens "VSlog" and/or "VSPath" (uncommented),
         ensures that an import from resources.lib.comaddon includes addon and the required tokens.
      2. Ensures required imports (os, requests, zipfile, shutil, datetime) are present.
      3. Inserts the update_service_addon method into class cUpdate (if missing).
      4. Inserts a call to self.update_service_addon() at the end of getUpdateSetting().

    All logging uses VSlog("message") calls.
    """
    # Path to the file to modify
    file_path = VSPath("special://home/addons/plugin.video.vstream/resources/lib/update.py")
    
    # Read the file lines
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # ---------------------------------------------------------------------------
    # Define the required imports.
    # For controlling the conditional import from resources.lib.comaddon,
    # include the tokens "VSlog" and/or "VSPath" (as plain strings) in the list.
    # Uncomment the token if you want it imported.
    # ---------------------------------------------------------------------------
    required_imports = [
        "import os",
        "import requests",
        "import zipfile",
        "import shutil",
        "import datetime",
        "VSlog",      # Uncomment to require VSlog from comaddon
        "VSPath"   # Uncomment to require VSPath from comaddon
    ]
    
    # ---------------------------------------------------------------------------
    # STEP 1: Conditionally ensure that the import from resources.lib.comaddon
    # includes the tokens for VSlog and/or VSPath if they are uncommented.
    # ---------------------------------------------------------------------------
    comaddon_required = []
    for token in ["VSlog", "VSPath"]:
        # If token is present and not commented out, add it.
        if any(imp.strip() == token for imp in required_imports if not imp.strip().startswith("#")):
            comaddon_required.append(token)
    
    if comaddon_required:
        found_comaddon_import = False
        for i, line in enumerate(lines):
            if line.strip().startswith("from resources.lib.comaddon import"):
                found_comaddon_import = True
                # Split the line into the "from ... import" parts.
                parts = line.split("import", 1)
                if len(parts) < 2:
                    continue
                # Get current imported tokens.
                tokens = [t.strip() for t in parts[1].split(",") if t.strip()]
                changed = False
                # Ensure each required token is present.
                for token in comaddon_required:
                    if token not in tokens:
                        tokens.append(token)
                        changed = True
                # Optionally, ensure "addon" is included.
                if "addon" not in tokens:
                    tokens.insert(0, "addon")
                    changed = True
                if changed:
                    new_line = "from resources.lib.comaddon import " + ", ".join(tokens) + "\n"
                    lines[i] = new_line
                break
        # If no import from resources.lib.comaddon was found, insert one.
        if not found_comaddon_import:
            new_import_line = "from resources.lib.comaddon import " + ", ".join(["addon"] + comaddon_required) + "\n"
            # Insert after any initial comment or import block.
            insert_index = 0
            for i, line in enumerate(lines):
                if not (line.strip() == "" or
                        line.lstrip().startswith("#") or
                        line.lstrip().startswith("import") or
                        line.lstrip().startswith("from")):
                    insert_index = i
                    break
            lines.insert(insert_index, new_import_line)
    
    # ---------------------------------------------------------------------------
    # STEP 2: Ensure other required imports are present.
    # Only check lines starting with "import" (skip tokens like "VSlog" or "VSPath").
    # ---------------------------------------------------------------------------
    for req in required_imports:
        if not req.startswith("import"):
            continue
        token = req.split()[1]  # e.g., 'os' for "import os"
        if not any(line.strip().startswith(req.split()[0]) and token in line 
                   for line in lines if line.strip().startswith(("import", "from"))):
            lines.insert(0, req + "\n")
    
    # ---------------------------------------------------------------------------
    # STEP 3: Insert update_service_addon method into class cUpdate if missing.
    # ---------------------------------------------------------------------------
    class_start_index = None
    class_indent = ""
    for i, line in enumerate(lines):
        if re.search(r'^\s*class\s+cUpdate\s*:', line):
            class_start_index = i
            class_indent = line[:len(line) - len(line.lstrip())]
            break
    if class_start_index is None:
        VSlog("Error: Could not find 'class cUpdate:' in the file.")
        return
    
    # Check if update_service_addon is already defined in cUpdate.
    method_defined = any(re.search(r'^\s*def\s+update_service_addon\s*\(', line)
                         for line in lines[class_start_index:])
    if method_defined:
        VSlog("def update_service_addon() method is already defined in cUpdate")
    else:
        # Find where the class block ends (first line with indent less than or equal to class_indent).
        insert_class_index = None
        for i in range(class_start_index + 1, len(lines)):
            if lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip())) <= len(class_indent):
                insert_class_index = i
                break
        if insert_class_index is None:
            insert_class_index = len(lines)
        
        method_indent = class_indent + "    "  # one level deeper than the class
        new_method = [
            "\n",
            f"{method_indent}def update_service_addon(self):\n",
            f"{method_indent}    # URL du fichier zip\n",
            f"{method_indent}    sUrl = \"https://raw.githubusercontent.com/Ayuzerak/vupdate/refs/heads/main/service.vstreamupdate.zip\"\n",
            "\n",
            f"{method_indent}    # Résolution du répertoire des add-ons via le chemin spécial Kodi\n",
            f"{method_indent}    addons_dir = VSPath('special://home/addons/')\n",
            f"{method_indent}    if not os.path.exists(addons_dir):\n",
            f"{method_indent}        VSlog(\"Le répertoire des add-ons n'existe pas : \" + str(addons_dir))\n",
            f"{method_indent}        return\n",
            "\n",
            f"{method_indent}    # Définition des chemins pour l'addon et sa sauvegarde\n",
            f"{method_indent}    addon_name = \"service.vstreamupdate\"\n",
            f"{method_indent}    backup_name = \"_service.vstreamupdate\"\n",
            f"{method_indent}    addon_path = os.path.join(addons_dir, addon_name)\n",
            f"{method_indent}    backup_path = os.path.join(addons_dir, backup_name)\n",
            "\n",
            f"{method_indent}    # Vérification si la mise à jour a déjà été effectuée en cherchant le fichier 'updated'\n",
            f"{method_indent}    updated_flag_path = os.path.join(addon_path, \"updated\")\n",
            f"{method_indent}    if os.path.exists(updated_flag_path):\n",
            f"{method_indent}        VSlog(\"La mise à jour a déjà été effectuée. Aucune action supplémentaire n'est nécessaire.\")\n",
            f"{method_indent}        return\n",
            "\n",
            f"{method_indent}    zip_file_path = os.path.join(addons_dir, addon_name + \".zip\")\n",
            "\n",
            f"{method_indent}    # Étape 1. Téléchargement du fichier zip dans le dossier des add-ons.\n",
            f"{method_indent}    VSlog(\"Téléchargement du fichier zip depuis : \" + str(sUrl))\n",
            f"{method_indent}    try:\n",
            f"{method_indent}        response = requests.get(sUrl, stream=True)\n",
            f"{method_indent}        response.raise_for_status()  # Lève une erreur pour les codes d'état incorrects\n",
            f"{method_indent}        with open(zip_file_path, 'wb') as f:\n",
            f"{method_indent}            for chunk in response.iter_content(chunk_size=8192):\n",
            f"{method_indent}                if chunk:\n",
            f"{method_indent}                    f.write(chunk)\n",
            f"{method_indent}        VSlog(\"Téléchargement terminé : \" + str(zip_file_path))\n",
            f"{method_indent}    except Exception as e:\n",
            f"{method_indent}        VSlog(\"Erreur lors du téléchargement du fichier : \" + str(e))\n",
            f"{method_indent}        return\n",
            "\n",
            f"{method_indent}    # Vérification que le fichier téléchargé est une archive zip valide.\n",
            f"{method_indent}    if not zipfile.is_zipfile(zip_file_path):\n",
            f"{method_indent}        VSlog(\"Le fichier téléchargé n'est pas une archive zip valide.\")\n",
            f"{method_indent}        os.remove(zip_file_path)\n",
            f"{method_indent}        return\n",
            "\n",
            f"{method_indent}    # Étape 2. Sauvegarde du dossier addon existant, s'il existe.\n",
            f"{method_indent}    if os.path.exists(addon_path):\n",
            f"{method_indent}        # Suppression d'un éventuel dossier de sauvegarde précédent\n",
            f"{method_indent}        if os.path.exists(backup_path):\n",
            f"{method_indent}            try:\n",
            f"{method_indent}                shutil.rmtree(backup_path)\n",
            f"{method_indent}                VSlog(\"Ancien backup supprimé : \" + str(backup_path))\n",
            f"{method_indent}            except Exception as e:\n",
            f"{method_indent}                VSlog(\"Impossible de supprimer l'ancien backup : \" + str(e))\n",
            f"{method_indent}                return\n",
            f"{method_indent}        try:\n",
            f"{method_indent}            # Déplacement du dossier addon existant vers le dossier de backup\n",
            f"{method_indent}            shutil.move(addon_path, backup_path)\n",
            f"{method_indent}            VSlog(\"Backup créé : \" + str(backup_path))\n",
            f"{method_indent}        except Exception as e:\n",
            f"{method_indent}            VSlog(\"Erreur lors de la création du backup : \" + str(e))\n",
            f"{method_indent}            return\n",
            f"{method_indent}    else:\n",
            f"{method_indent}        VSlog(\"Aucun addon existant à sauvegarder.\")\n",
            "\n",
            f"{method_indent}    # (Optionnel) S'assurer qu'aucun dossier résiduel ne subsiste.\n",
            f"{method_indent}    if os.path.exists(addon_path):\n",
            f"{method_indent}        try:\n",
            f"{method_indent}            shutil.rmtree(addon_path)\n",
            f"{method_indent}            VSlog(\"Dossier addon résiduel supprimé : \" + str(addon_path))\n",
            f"{method_indent}        except Exception as e:\n",
            f"{method_indent}            VSlog(\"Erreur lors de la suppression du dossier addon résiduel : \" + str(e))\n",
            f"{method_indent}            return\n",
            "\n",
            f"{method_indent}    # Étape 3. Extraction du fichier zip téléchargé dans le dossier des add-ons.\n",
            f"{method_indent}    try:\n",
            f"{method_indent}        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:\n",
            f"{method_indent}            zip_ref.extractall(addons_dir)\n",
            f"{method_indent}        VSlog(\"Extraction terminée vers : \" + str(addons_dir))\n",
            f"{method_indent}    except Exception as e:\n",
            f"{method_indent}        VSlog(\"Erreur lors de l'extraction : \" + str(e))\n",
            f"{method_indent}        # Restauration du backup en cas d'échec de l'extraction.\n",
            f"{method_indent}        if os.path.exists(backup_path):\n",
            f"{method_indent}            shutil.move(backup_path, addon_path)\n",
            f"{method_indent}            VSlog(\"Backup restauré depuis : \" + str(backup_path))\n",
            f"{method_indent}        os.remove(zip_file_path)\n",
            f"{method_indent}        return\n",
            "\n",
            f"{method_indent}    # Suppression du fichier zip téléchargé après extraction.\n",
            f"{method_indent}    os.remove(zip_file_path)\n",
            "\n",
            f"{method_indent}    # Étape 4. Vérification que le dossier extrait contient addon.xml.\n",
            f"{method_indent}    addon_xml = os.path.join(addon_path, \"addon.xml\")\n",
            f"{method_indent}    if os.path.exists(addon_xml):\n",
            f"{method_indent}        VSlog(\"Mise à jour réussie. addon.xml trouvé dans : \" + str(addon_path))\n",
            "\n",
            f"{method_indent}        # Création du fichier 'updated' pour indiquer que la mise à jour a été effectuée.\n",
            f"{method_indent}        try:\n",
            f"{method_indent}            with open(updated_flag_path, 'w') as f:\n",
            f"{method_indent}                f.write(\"Mise à jour effectuée le \" + datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\"))\n",
            f"{method_indent}            VSlog(\"Fichier 'updated' créé dans : \" + str(addon_path))\n",
            f"{method_indent}        except Exception as e:\n",
            f"{method_indent}            VSlog(\"Erreur lors de la création du fichier 'updated' : \" + str(e))\n",
            "\n",
            f"{method_indent}        # Optionnel : suppression du backup maintenant que la mise à jour est confirmée.\n",
            f"{method_indent}        if os.path.exists(backup_path):\n",
            f"{method_indent}            try:\n",
            f"{method_indent}                shutil.rmtree(backup_path)\n",
            f"{method_indent}                VSlog(\"Dossier backup supprimé : \" + str(backup_path))\n",
            f"{method_indent}            except Exception as e:\n",
            f"{method_indent}                VSlog(\"Erreur lors de la suppression du dossier backup : \" + str(e))\n",
            f"{method_indent}    else:\n",
            f"{method_indent}        VSlog(\"addon.xml introuvable dans le dossier extrait. Annulation de la mise à jour...\")\n",
            f"{method_indent}        # Suppression du nouveau dossier défectueux\n",
            f"{method_indent}        if os.path.exists(addon_path):\n",
            f"{method_indent}            shutil.rmtree(addon_path)\n",
            f"{method_indent}        # Restauration du backup\n",
            f"{method_indent}        if os.path.exists(backup_path):\n",
            f"{method_indent}            shutil.move(backup_path, addon_path)\n",
            f"{method_indent}            VSlog(\"Backup restauré dans : \" + str(addon_path))\n",
            f"{method_indent}        else:\n",
            f"{method_indent}            VSlog(\"Aucun backup disponible pour restauration!\")\n",
            f"{method_indent}        return\n"
        ]
        lines = lines[:insert_class_index] + new_method + lines[insert_class_index:]
    
    # ---------------------------------------------------------------------------
    # STEP 4: Insert call to self.update_service_addon() at the end of getUpdateSetting()
    # ---------------------------------------------------------------------------
    new_lines = []
    in_get_update = False
    get_update_body_indent = ""
    call_inserted = False
    call_already_present = False
    for line in lines:
        # Detect the start of getUpdateSetting
        if re.search(r'^\s*def\s+getUpdateSetting\s*\(self\)\s*:', line):
            in_get_update = True
            get_update_body_indent = ""
            new_lines.append(line)
            continue
        
        if in_get_update:
            # Determine the method body indent on the first non-empty line.
            if get_update_body_indent == "" and line.strip():
                get_update_body_indent = line[:len(line) - len(line.lstrip())]

            if "self.update_service_addon()" in line:
                call_already_present = True
                VSlog("self.update_service_addon() call already present to " + file_path)

            # If a line appears with less indent than the method body, assume the method ended.
            if line.strip() and (len(line) - len(line.lstrip())) < len(get_update_body_indent):
                if not call_inserted and not call_already_present:
                    new_lines.append(get_update_body_indent + "self.update_service_addon()\n")
                    call_inserted = True
                in_get_update = False
                new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # In case getUpdateSetting is the last method and its block never ended:
    if in_get_update and not call_inserted and not call_already_present:
        new_lines.append(get_update_body_indent + "self.update_service_addon()\n")
    
    # Write the modified lines back to the file.
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    # Assuming VSlog is now available from the import, log completion.
    VSlog("Insertion complete. The update_service_addon method and its call have been added to " + file_path)
    
def add_vstreammonitor_import():
    # Resolve the Kodi special path to a file system path
    update_file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/update.py').replace('\\', '/')
    import_line = 'from resources.lib.monitor import VStreamMonitor\n'
    
    try:
        with open(update_file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
    except Exception as e:
        logger.error("Error reading file '{}': {}".format(update_file_path, e))
        return

    # Check if the import is already in the file
    if any('from resources.lib.monitor import VStreamMonitor' in line for line in content):
        logger.info("Import already present in the file.")
        return

    # Decide where to insert the import:
    # If there is a shebang (#!/usr/bin/env python) or a coding declaration, preserve them at the top.
    insertion_index = 0
    for i, line in enumerate(content):
        if line.startswith('#!') or ('coding' in line and line.startswith('#')):
            insertion_index = i + 1
        else:
            break

    # Insert the import line at the chosen location
    content.insert(insertion_index, import_line)

    try:
        with open(update_file_path, 'w', encoding='utf-8') as file:
            file.writelines(content)
    except Exception as e:
        logger.error("Error writing to file '{}': {}".format(update_file_path, e))
        return

    logger.info("Successfully added import to '{}'.".format(update_file_path))

def create_monitor_file():

    """Add the monitor and create monitor.py if not present."""
    VSlog("Starting the process to add monitor.")
    
    monitor_py = VSPath('special://home/addons/plugin.video.vstream/resources/lib/monitor.py').replace('\\', '/')

    VSlog(f"Path resolved - monitor.py: {monitor_py}")

    try:

        # Check if monitor.py exists
        VSlog("Checking if monitor.py exists...")
        if not os.path.exists(monitor_py):
            VSlog("monitor.py not found. Creating file...")
            with open(monitor_py, 'w', encoding='utf-8') as fichier:
                script_content = """# -*- coding: utf-8 -*- 
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from xbmc import Monitor
import xbmc
import json
from resources.lib.comaddon import VSPath, VSlog

class VStreamMonitor(Monitor):
    \"\"\"Service monitor for Kodi\"\"\"

    def __init__(self):
        \"\"\"Constructor for Monitor\"\"\"
        Monitor.__init__(self)

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        \"\"\"Notification event handler for accepting data from add-ons\"\"\"
        VSlog(f"onNotification: Received data from {sender} message({method}): {data}")
        if not method.endswith('vstream_data'):  # Method looks like Other.vstream_data
            return

        try:
            decoded_data = json.loads(data)
        except json.JSONDecodeError:
            VSlog(f'Received data from sender {sender} message({method}) is not JSON: {data}')
            return

        VSlog(f"onNotification: Received data from {sender} message({method}) is JSON: {decoded_data}")

        if "service.vstreamupdate" in sender:
            from resources.lib.update import cUpdate
            update_instance = cUpdate()
            update_instance.getUpdateSetting()
        elif "plugin.video.kodiconnect" in sender:
            # Call the function to launch a search in VStream
            from resources.lib.search import cSearch
            # Create an instance of the cSearch class
            search_instance = cSearch()
            # Assuming decoded_data[0] is a list of titles
            titles = decoded_data[0]

            # Iterate over the titles and call searchGlobalPlay for each title
            for title in titles:
                search_instance.playVideo()
                break

# Create an instance of the monitor
monitor = VStreamMonitor()

while not monitor.abortRequested():
    if monitor.waitForAbort(10):
        break

del monitor
"""
                fichier.write(script_content)
                VSlog(f"Created monitor.py with the required content at: {monitor_py}.")
        else:
            VSlog(f"monitor.py already exists at: {monitor_py}. Skipping file creation.")
    except Exception as e:
        VSlog(f"An error occurred: {str(e)}")

def get_setting_value_from_file(file_path: str, setting_id: str) -> str:
    """
    Retrieves the value of a setting from an XML file based on the setting ID.

    :param file_path: The path to the XML file.
    :param setting_id: The ID of the setting to retrieve.
    :return: The value of the setting or None if not found.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        for setting in root.findall("setting"):
            if setting.get("id") == setting_id:
                return setting.text if setting.text is not None else ""
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    return None


def add_netflix_like_recommendations():
    because_num, recommendations_num = add_translations_to_file_for_netflix_like_recommendations()
    add_is_recommendations_for_netflix_like_recommendations()
    modify_get_catWatched_for_netflix_like_recommendations()
    add_recommendations_for_netflix_like_recommendations(recommendations_num)
    create_recommendations_file_for_netflix_like_recommendations(because_num)
    add_get_recommendations_method_for_netflix_like_recommendations()

def add_is_recommendations_for_netflix_like_recommendations():
    def extract_indent(line):
        """Extract leading spaces or tabs for indentation."""
        return line[:len(line) - len(line.lstrip())]

    file_path = VSPath('special://home/addons/plugin.video.vstream/default.py').replace('\\', '/')
    
    # Define the new function to insert
    new_function = """def isRecommendations(sSiteName, sFunction):
    if sSiteName == 'cRecommendations':
        plugins = __import__('resources.lib.recommendations', fromlist=['cRecommendations']).cRecommendations()
        function = getattr(plugins, sFunction)
        function()
        return True
    return False\n\n"""  # Two newlines for separation

    insert_before_if = "if sSiteName == 'globalRun':"
    insert_before_def = "def _pluginSearch(plugin, sSearchText):"

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()

    # Check if modifications are already present
    is_recommendations_exists = any("def isRecommendations(" in line for line in content)
    is_if_check_exists = any("if isRecommendations(sSiteName, sFunction):" in line for line in content)

    if is_recommendations_exists and is_if_check_exists:
        VSlog("No modifications needed: isRecommendations function and check already exist")
        return False  # No changes needed

    modified_content = []
    inserted_if_check = False
    inserted_function = False

    for line in content:
        stripped_line = line.lstrip()

        # Insert the isRecommendations function before `def _pluginSearch(...)`
        if not inserted_function and not is_recommendations_exists and stripped_line.startswith(insert_before_def):
            modified_content.append(new_function)
            inserted_function = True

        # Insert the isRecommendations() check before `if sSiteName == 'globalRun':`
        if not inserted_if_check and not is_if_check_exists and stripped_line.startswith(insert_before_if):
            indent = extract_indent(line)
            modified_content.append(f"{indent}if isRecommendations(sSiteName, sFunction):\n")
            modified_content.append(f"{indent}    return\n\n")
            inserted_if_check = True

        modified_content.append(line)

    # Write only if changes were made
    if inserted_if_check or inserted_function:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_content)
        VSlog("File successfully modified")
        return True  # Successfully modified

    VSlog("No modifications made")
    return False  # No modifications made

def add_translations_to_file_for_netflix_like_recommendations():
    # Example usage
    file_path = VSPath('special://home/userdata/guisettings.xml').replace("\\", "/")
    language_setting = get_setting_value_from_file(file_path, "locale.language")
    (because_num_fr_fr, recommendations_num_fr_fr) = add_translations_to_fr_fr_po_file_for_netflix_like_recommendations()
    (because_num_fr_ca, recommendations_num_fr_ca) = add_translations_to_fr_ca_po_file_for_netflix_like_recommendations()
    (because_num_en_gb, recommendations_num_en_gb) = add_translations_to_en_gb_po_file_for_netflix_like_recommendations()
    recommendations_num = 0
    if language_setting == "resource.language.fr_fr":
        recommendations_num = recommendations_num_fr_fr
        because_num = because_num_fr_fr
    elif language_setting == "resource.language.fr_ca":
        recommendations_num = recommendations_num_fr_ca
        because_num = because_num_fr_ca
    elif language_setting == "resource.language.en_gb":
        recommendations_num = recommendations_num_en_gb
        because_num = because_num_en_gb

    return (because_num, recommendations_num)

def add_translations_to_fr_fr_po_file_for_netflix_like_recommendations():
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/language/resource.language.fr_fr/strings.po').replace('\\', '/')

    my_recommendations_num = None
    because_num = None

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        existing_translations = {
            "Because you watched": {"translated": "Parce que vous avez regardé", "msgctxt_num": None},
            "My Recommendations": {"translated": "Mes recommandations", "msgctxt_num": None}
        }

        # Recherche des traductions existantes et de leurs numéros
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith('msgctxt'):
                msgctxt_line = line.strip()
                msgctxt_num = msgctxt_line.split('#')[1].split('"')[0].strip()
                try:
                    current_num = int(msgctxt_num)
                except ValueError:
                    continue
                if i + 1 < len(lines) and lines[i+1].startswith('msgid'):
                    msgid_line = lines[i+1].strip()
                    msgid = msgid_line.split('"')[1]
                    if msgid in existing_translations:
                        existing_translations[msgid]["msgctxt_num"] = current_num
                        if i + 2 < len(lines) and lines[i+2].startswith('msgstr'):
                            msgstr_line = lines[i+2].strip()
                            msgstr = msgstr_line.split('"')[1]
                            if msgstr == existing_translations[msgid]["translated"]:
                                existing_translations[msgid]["found"] = True

        new_entries = []
        current_num = 0
        # Détermine le dernier numéro utilisé
        last_msgctxt_num = 0
        for line in lines:
            if line.startswith('msgctxt'):
                parts = line.split('#')
                if len(parts) > 1:
                    num_part = parts[1].split('"')[0].strip()
                    try:
                        num = int(num_part)
                        if num > last_msgctxt_num:
                            last_msgctxt_num = num
                    except ValueError:
                        pass

        current_num = last_msgctxt_num + 1

        # Gère l'ajout de 'Because you watched'
        if not existing_translations["Because you watched"].get("found", False):
            new_entries.append((current_num, "Because you watched", "Parce que vous avez regardé"))
            current_num += 1

        # Gère l'ajout de 'My Recommendations'
        if not existing_translations["My Recommendations"].get("found", False):
            new_entries.append((current_num, "My Recommendations", "Mes recommandations"))
            my_recommendations_num = current_num
            current_num += 1

        # Ajoute les nouvelles entrées si nécessaire
        if new_entries:
            with open(file_path, 'a', encoding='utf-8') as file:
                for entry in new_entries:
                    file.write(f'msgctxt "#{entry[0]}"\n')
                    file.write(f'msgid "{entry[1]}"\n')
                    file.write(f'msgstr "{entry[2]}"\n\n')

        # Récupère le numéro de 'Because you watched' existant ou nouvellement ajouté
        if existing_translations["Because you watched"]["msgctxt_num"] is not None:
            because_num = existing_translations["Because you watched"]["msgctxt_num"]
        elif because_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "Because you watched"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            because_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        # Récupère le numéro de 'My Recommendations' existant ou nouvellement ajouté
        if existing_translations["My Recommendations"]["msgctxt_num"] is not None:
            my_recommendations_num = existing_translations["My Recommendations"]["msgctxt_num"]
        elif my_recommendations_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "My Recommendations"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            my_recommendations_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        because_num = because_num if because_num is not None else 0
        my_recommendations_num = my_recommendations_num if my_recommendations_num is not None else 0

        return (because_num, my_recommendations_num)

    except Exception as e:
        VSlog(f"Erreur dans fr_fr: {str(e)}")
        return 0

def add_translations_to_fr_ca_po_file_for_netflix_like_recommendations():
    """
    Ajoute les traductions 'msgctxt', 'msgid' et 'msgstr' dans le fichier strings.po
    pour la langue `fr_ca` avec des numéros de # pour msgctxt en séquence, si elles ne sont pas déjà présentes.
    """
    # Chemin vers le fichier .po pour fr_ca
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/language/resource.language.fr_ca/strings.po').replace('\\', '/')
    
    my_recommendations_num = None
    because_num = None

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        existing_translations = {
            "Because you watched": {"translated": "Parce que vous avez regardé", "msgctxt_num": None},
            "My Recommendations": {"translated": "Mes recommandations", "msgctxt_num": None}
        }

        # Recherche des traductions existantes et de leurs numéros
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith('msgctxt'):
                msgctxt_line = line.strip()
                msgctxt_num = msgctxt_line.split('#')[1].split('"')[0].strip()
                try:
                    current_num = int(msgctxt_num)
                except ValueError:
                    continue
                if i + 1 < len(lines) and lines[i+1].startswith('msgid'):
                    msgid_line = lines[i+1].strip()
                    msgid = msgid_line.split('"')[1]
                    if msgid in existing_translations:
                        existing_translations[msgid]["msgctxt_num"] = current_num
                        if i + 2 < len(lines) and lines[i+2].startswith('msgstr'):
                            msgstr_line = lines[i+2].strip()
                            msgstr = msgstr_line.split('"')[1]
                            if msgstr == existing_translations[msgid]["translated"]:
                                existing_translations[msgid]["found"] = True

        new_entries = []
        current_num = 0
        # Détermine le dernier numéro utilisé
        last_msgctxt_num = 0
        for line in lines:
            if line.startswith('msgctxt'):
                parts = line.split('#')
                if len(parts) > 1:
                    num_part = parts[1].split('"')[0].strip()
                    try:
                        num = int(num_part)
                        if num > last_msgctxt_num:
                            last_msgctxt_num = num
                    except ValueError:
                        pass

        current_num = last_msgctxt_num + 1

        # Gère l'ajout de 'Because you watched'
        if not existing_translations["Because you watched"].get("found", False):
            new_entries.append((current_num, "Because you watched", "Parce que vous avez regardé"))
            current_num += 1

        # Gère l'ajout de 'My Recommendations'
        if not existing_translations["My Recommendations"].get("found", False):
            new_entries.append((current_num, "My Recommendations", "Mes Recommandations"))
            my_recommendations_num = current_num
            current_num += 1

        # Ajoute les nouvelles entrées si nécessaire
        if new_entries:
            with open(file_path, 'a', encoding='utf-8') as file:
                for entry in new_entries:
                    file.write(f'msgctxt "#{entry[0]}"\n')
                    file.write(f'msgid "{entry[1]}"\n')
                    file.write(f'msgstr "{entry[2]}"\n\n')

        # Récupère le numéro de 'Because you watched' existant ou nouvellement ajouté
        if existing_translations["Because you watched"]["msgctxt_num"] is not None:
            because_num = existing_translations["Because you watched"]["msgctxt_num"]
        elif because_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "Because you watched"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            because_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        # Récupère le numéro de 'My Recommendations' existant ou nouvellement ajouté
        if existing_translations["My Recommendations"]["msgctxt_num"] is not None:
            my_recommendations_num = existing_translations["My Recommendations"]["msgctxt_num"]
        elif my_recommendations_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "My Recommendations"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            my_recommendations_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        because_num = because_num if because_num is not None else 0
        my_recommendations_num = my_recommendations_num if my_recommendations_num is not None else 0

        return (because_num, my_recommendations_num)

    except Exception as e:
        VSlog(f"Erreur dans fr_ca: {str(e)}")
        return 0

def add_translations_to_en_gb_po_file_for_netflix_like_recommendations():
    """
    Ajoute les traductions 'msgctxt', 'msgid' et 'msgstr' dans le fichier strings.po
    pour la langue `en_gb` avec des numéros de # pour msgctxt en séquence, si elles ne sont pas déjà présentes.
    """
    # Chemin vers le fichier .po pour en_gb
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/language/resource.language.en_gb/strings.po').replace('\\', '/')
    
    my_recommendations_num = None
    because_num = None

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        existing_translations = {
            "Because you watched": {"translated": "Because you watched", "msgctxt_num": None},
            "My Recommendations": {"translated": "My Recommendations", "msgctxt_num": None}
        }

        # Recherche des traductions existantes et de leurs numéros
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith('msgctxt'):
                msgctxt_line = line.strip()
                msgctxt_num = msgctxt_line.split('#')[1].split('"')[0].strip()
                try:
                    current_num = int(msgctxt_num)
                except ValueError:
                    continue
                if i + 1 < len(lines) and lines[i+1].startswith('msgid'):
                    msgid_line = lines[i+1].strip()
                    msgid = msgid_line.split('"')[1]
                    if msgid in existing_translations:
                        existing_translations[msgid]["msgctxt_num"] = current_num
                        if i + 2 < len(lines) and lines[i+2].startswith('msgstr'):
                            msgstr_line = lines[i+2].strip()
                            msgstr = msgstr_line.split('"')[1]
                            if msgstr == existing_translations[msgid]["translated"]:
                                existing_translations[msgid]["found"] = True

        new_entries = []
        current_num = 0
        # Détermine le dernier numéro utilisé
        last_msgctxt_num = 0
        for line in lines:
            if line.startswith('msgctxt'):
                parts = line.split('#')
                if len(parts) > 1:
                    num_part = parts[1].split('"')[0].strip()
                    try:
                        num = int(num_part)
                        if num > last_msgctxt_num:
                            last_msgctxt_num = num
                    except ValueError:
                        pass

        current_num = last_msgctxt_num + 1

        # Gère l'ajout de 'Because you watched'
        if not existing_translations["Because you watched"].get("found", False):
            new_entries.append((current_num, "Because you watched", "Parce que vous avez regardé"))
            current_num += 1

        # Gère l'ajout de 'My Recommendations'
        if not existing_translations["My Recommendations"].get("found", False):
            new_entries.append((current_num, "My Recommendations", "Mes recommandations"))
            my_recommendations_num = current_num
            current_num += 1

        # Ajoute les nouvelles entrées si nécessaire
        if new_entries:
            with open(file_path, 'a', encoding='utf-8') as file:
                for entry in new_entries:
                    file.write(f'msgctxt "#{entry[0]}"\n')
                    file.write(f'msgid "{entry[1]}"\n')
                    file.write(f'msgstr "{entry[2]}"\n\n')

        # Récupère le numéro de 'Because you watched' existant ou nouvellement ajouté
        if existing_translations["Because you watched"]["msgctxt_num"] is not None:
            because_num = existing_translations["Because you watched"]["msgctxt_num"]
        elif because_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "Because you watched"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            because_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        # Récupère le numéro de 'My Recommendations' existant ou nouvellement ajouté
        if existing_translations["My Recommendations"]["msgctxt_num"] is not None:
            my_recommendations_num = existing_translations["My Recommendations"]["msgctxt_num"]
        elif my_recommendations_num is None:
            # Recherche dans les lignes existantes si la traduction existait déjà
            for i in range(len(lines)):
                if lines[i].startswith('msgid "My Recommendations"'):
                    if i > 0 and lines[i-1].startswith('msgctxt'):
                        msgctxt_num = lines[i-1].split('#')[1].split('"')[0].strip()
                        try:
                            my_recommendations_num = int(msgctxt_num)
                        except ValueError:
                            pass
                    break

        because_num = because_num if because_num is not None else 0
        my_recommendations_num = my_recommendations_num if my_recommendations_num is not None else 0

        return (because_num, my_recommendations_num)

    except Exception as e:
        VSlog(f"Erreur dans en_gb: {str(e)}")
        return 0

def modify_get_catWatched_for_netflix_like_recommendations():
    """
    Modifie la fonction `get_catWatched` dans le fichier db.py pour ajouter le paramètre `limit`
    et la logique de limitation de la requête SQL, si ces modifications ne sont pas déjà présentes.
    """
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/db.py').replace('\\', '/')
    
    try:
        # Lire le contenu actuel du fichier
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False
        inside_function = False
        function_start_line = None
        indent_level = None

        # Recherche de la fonction get_catWatched pour ajouter `limit` et modifier le code
        for i, line in enumerate(lines):
            if line.strip().startswith("def get_catWatched"):
                inside_function = True
                function_start_line = i
                # Trouver l'indentation de la fonction
                indent_level = len(line) - len(line.lstrip())
                
                # Vérifier si le paramètre limit est déjà présent dans la signature de la fonction
                if "limit" not in line:
                    VSlog(f"Adding parameter 'limit' to function signature in line: {line.strip()}")
                    lines[i] = line.replace(')', ', limit=None)')  # Modification de la signature
                    modified = True

            elif inside_function:
                # Chercher l'endroit pour ajouter la logique du `if limit:`
                if 'order by addon_id DESC' in line:
                    # Vérifier si la condition `if limit:` est déjà présente
                    if "if limit:" not in lines[i+1]:
                        # Ajouter l'instruction `if limit:` avec une indentation correcte
                        lines.insert(i + 1, " " * indent_level + "    if limit:\n")
                        lines.insert(i + 2, " " * indent_level + "        sql_select += \" limit %s\" % limit\n")
                        modified = True
                    inside_function = False
                    break  # Sortie après avoir modifié la fonction

        # Si des modifications ont été apportées, réécrire le fichier
        if modified:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.writelines(lines)
            VSlog(f"Modifications successfully applied to the function get_catWatched in {file_path}")
        else:
            VSlog(f"No modifications were necessary for the function get_catWatched in {file_path}")

    except FileNotFoundError:
        VSlog(f"Error: File not found - {file_path}")
    except Exception as e:
        VSlog(f"Error while modifying file '{file_path}': {str(e)}")

def add_recommendations_for_netflix_like_recommendations(recommendations_num):
    """
    Adds recommendation blocks for Netflix-like recommendations in the methods `showMovies` and `showSeries`
    in `home.py` after `# Nouveautés` or before `# Populaires`, scoped to each method.
    """
    
    # Chemin du fichier à éditer
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/home.py').replace('\\', '/')

    if not os.path.isfile(file_path):
        VSlog(f"Fichier non trouvé : {file_path}")
        exit(1)

    # Lecture du contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    modifications_effectuees = False

    # ============================================================================
    # 1. Ajout de la méthode addDir dans la classe cHome
    # ============================================================================
    if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' in content:
        VSlog("La méthode addDir existe déjà dans la classe cHome.")
    else:
        # Recherche de la déclaration de la classe cHome
        class_pattern = r'(class\s+cHome\s*:\s*\n)'
        match = re.search(class_pattern, content)
        if match:
            # Définition du code de la méthode addDir avec indentation sur 4 espaces
            adddir_method = (
                "    def addDir(self, categorie, oGui, oOutputParameterHandler):\n"
                "        categorie2 = \"\"\n"
                "        if categorie == \"tv\":\n"
                "            categorie2 = \"Shows\"\n"
                "        else:\n"
                "            categorie2 = \"Movies\"\n"
                "        oOutputParameterHandler.addParameter('siteUrl', f'{categorie}/recommendations')\n"
                "        oGui.addDir('cRecommendations', f'show{categorie2}Recommendations'," + f" self.addons.VSlang({recommendations_num})" + ", 'listes.png', oOutputParameterHandler)\n"
            )
            # Insertion de la méthode juste après la déclaration de la classe
            content = re.sub(class_pattern, r'\1' + adddir_method + "\n", content, count=1)
            # Vérification après insertion
            if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' in content:
                modifications_effectuees = True
                VSlog("La méthode addDir a été ajoutée avec succès dans cHome.")
            else:
                VSlog("Erreur: L'ajout de la méthode addDir a échoué.")
        else:
            VSlog("La classe cHome n'a pas été trouvée dans le fichier.")
            exit(1)

def add_recommendations_for_netflix_like_recommendations(recommendations_num):
    """
    Adds recommendation blocks for Netflix-like recommendations in the methods `showMovies` and `showSeries`
    in `home.py` after `# Nouveautés` or before `# Populaires`, scoped to each method.
    """
    
    # Chemin du fichier à éditer
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/home.py').replace('\\', '/')

    if not os.path.isfile(file_path):
        VSlog(f"Fichier non trouvé : {file_path}")
        exit(1)

    # Lecture du contenu du fichier
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    modifications_effectuees = False

    # ============================================================================
    # 1. Ajout de la méthode addDir dans la classe cHome
    # ============================================================================
    if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' in content:
        VSlog("La méthode addDir existe déjà dans la classe cHome.")
    else:
        # Recherche de la déclaration de la classe cHome
        class_pattern = r'(class\s+cHome\s*:\s*\n)'
        match = re.search(class_pattern, content)
        if match:
            # Définition du code de la méthode addDir avec indentation sur 4 espaces
            adddir_method = (
                "    def addDir(self, categorie, oGui, oOutputParameterHandler):\n"
                "        categorie2 = \"\"\n"
                "        if categorie == \"tv\":\n"
                "            categorie2 = \"Shows\"\n"
                "        else:\n"
                "            categorie2 = \"Movies\"\n"
                "        oOutputParameterHandler.addParameter('siteUrl', f'{categorie}/recommendations')\n"
                "        oGui.addDir('cRecommendations', f'show{categorie2}Recommendations'," + f" self.addons.VSlang({recommendations_num})" + ", 'listes.png', oOutputParameterHandler)\n"
            )
            # Insertion de la méthode juste après la déclaration de la classe
            content = re.sub(class_pattern, r'\1' + adddir_method + "\n", content, count=1)
            # Vérification après insertion
            if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' in content:
                modifications_effectuees = True
                VSlog("La méthode addDir a été ajoutée avec succès dans cHome.")
            else:
                VSlog("Erreur: L'ajout de la méthode addDir a échoué.")
        else:
            VSlog("La classe cHome n'a pas été trouvée dans le fichier.")
            exit(1)

    # ============================================================================ 
    # 2. Modification de showMovies pour y appeler self.addDir("movies", oGui, oOutputParameterHandler)
    #    avant oGui.setEndOfDirectory()
    # ============================================================================ 
    if re.search(r'def\s+showMovies\s*\(self\):', content):
        if re.search(r'self\.addDir\("movies",\s*oGui,\s*oOutputParameterHandler\)', content):
            VSlog("La fonction showMovies contient déjà l'appel à self.addDir pour 'movies'.")
        else:
            # Capture de l'intégralité de la fonction showMovies (header + corps)
            pattern_showMovies = r'(def\s+showMovies\s*\(self\):(?:\n[ \t]+.*)+)'
            def modify_showMovies(match):
                func_block = match.group(0)
                # Recherche de la ligne oGui.setEndOfDirectory() dans le corps
                pattern_setend = r'([ \t]*)oGui\.setEndOfDirectory\(\)'
                def insert_line(m):
                    indent = m.group(1)
                    # Insertion de l'appel à self.addDir juste avant oGui.setEndOfDirectory()
                    return f'{indent}self.addDir("movies", oGui, oOutputParameterHandler)\n{indent}oGui.setEndOfDirectory()'
                new_func_block, count_body = re.subn(pattern_setend, insert_line, func_block, count=1)
                if count_body == 0:
                    VSlog("Erreur: oGui.setEndOfDirectory() introuvable dans showMovies.")
                    return func_block
                return new_func_block
            new_content, count_movies = re.subn(pattern_showMovies, modify_showMovies, content, flags=re.DOTALL)
            if count_movies > 0 and 'self.addDir("movies", oGui, oOutputParameterHandler)' in new_content:
                content = new_content
                modifications_effectuees = True
                VSlog("La fonction showMovies a été modifiée avec succès.")
            else:
                VSlog("Erreur: La modification de la fonction showMovies a échoué.")
    else:
        VSlog("La fonction showMovies n'a pas été trouvée dans le fichier.")

    # ============================================================================ 
    # 3. Modification de showSeries pour y appeler self.addDir("tv", oGui, oOutputParameterHandler)
    #    avant oGui.setEndOfDirectory()
    # ============================================================================ 
    if re.search(r'def\s+showSeries\s*\(self\):', content):
        if re.search(r'self\.addDir\("tv",\s*oGui,\s*oOutputParameterHandler\)', content):
            VSlog("La fonction showSeries contient déjà l'appel à self.addDir pour 'tv'.")
        else:
            # Capture de l'intégralité de la fonction showSeries (header + corps)
            pattern_showSeries = r'(def\s+showSeries\s*\(self\):(?:\n[ \t]+.*)+)'
            def modify_showSeries(match):
                func_block = match.group(0)
                pattern_setend = r'([ \t]*)oGui\.setEndOfDirectory\(\)'
                def insert_line(m):
                    indent = m.group(1)
                    return f'{indent}self.addDir("tv", oGui, oOutputParameterHandler)\n{indent}oGui.setEndOfDirectory()'
                new_func_block, count_body = re.subn(pattern_setend, insert_line, func_block, count=1)
                if count_body == 0:
                    VSlog("Erreur: oGui.setEndOfDirectory() introuvable dans showSeries.")
                    return func_block
                return new_func_block
            new_content, count_series = re.subn(pattern_showSeries, modify_showSeries, content, flags=re.DOTALL)
            if count_series > 0 and 'self.addDir("tv", oGui, oOutputParameterHandler)' in new_content:
                content = new_content
                modifications_effectuees = True
                VSlog("La fonction showSeries a été modifiée avec succès.")
            else:
                VSlog("Erreur: La modification de la fonction showSeries a échoué.")
    else:
        VSlog("La fonction showSeries n'a pas été trouvée dans le fichier.")

        # ============================================================================
        # Sauvegarde des modifications et vérification finale
        # ============================================================================
        if modifications_effectuees:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            VSlog("Modifications sauvegardées. Vérification du fichier final en cours...")

            # Relecture du fichier pour vérification finale
            with open(file_path, 'r', encoding='utf-8') as f:
                final_content = f.read()
            verification = True

            if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' not in final_content:
                VSlog("Vérification échouée : La méthode addDir n'est pas présente dans le fichier final.")
                verification = False
            if not re.search(r'self\.addDir\("movies",\s*oGui,\s*oOutputParameterHandler\)', final_content):
                VSlog("Vérification échouée : L'appel self.addDir pour 'movies' est absent dans showMovies.")
                verification = False
            if not re.search(r'self\.addDir\("tv",\s*oGui,\s*oOutputParameterHandler\)', final_content):
                VSlog("Vérification échouée : L'appel self.addDir pour 'tv' est absent dans showSeries.")
                verification = False

            if verification:
                VSlog("Toutes les modifications ont été vérifiées avec succès dans le fichier final.")
            else:
                VSlog("Des erreurs ont été détectées lors de la vérification finale des modifications.")
        else:
            VSlog("Aucune modification n'a été apportée au fichier.")

    # ============================================================================
    # Sauvegarde des modifications et vérification finale
    # ============================================================================
    if modifications_effectuees:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        VSlog("Modifications sauvegardées. Vérification du fichier final en cours...")

        # Relecture du fichier pour vérification finale
        with open(file_path, 'r', encoding='utf-8') as f:
            final_content = f.read()
        verification = True

        if 'def addDir(self, categorie, oGui, oOutputParameterHandler):' not in final_content:
            VSlog("Vérification échouée : La méthode addDir n'est pas présente dans le fichier final.")
            verification = False
        if not re.search(r'self\.addDir\("movies",\s*oGui,\s*oOutputParameterHandler\)', final_content):
            VSlog("Vérification échouée : L'appel self.addDir pour 'movies' est absent dans showMovies.")
            verification = False
        if not re.search(r'self\.addDir\("tv",\s*oGui,\s*oOutputParameterHandler\)', final_content):
            VSlog("Vérification échouée : L'appel self.addDir pour 'tv' est absent dans showSeries.")
            verification = False

        if verification:
            VSlog("Toutes les modifications ont été vérifiées avec succès dans le fichier final.")
        else:
            VSlog("Des erreurs ont été détectées lors de la vérification finale des modifications.")
    else:
        VSlog("Aucune modification n'a été apportée au fichier.")

def create_recommendations_file_for_netflix_like_recommendations(because_num):
    """
    Vérifie si le fichier recommendations.py existe dans le chemin cible.
    S'il n'existe pas, le fichier est créé avec le contenu prédéfini.
    """
    VSlog("create_recommendations_file_for_netflix_like_recommendations()")

    # Chemin vers le répertoire cible
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/recommendations.py').replace('\\', '/')

    try:
        # Vérification de l'existence du fichier
        if not os.path.exists(file_path):
            VSlog(f"Fichier {file_path} non trouvé. Création en cours.")

            # Template du contenu prédéfini pour recommendations.py.
            # Utilisation de triple quotes avec des quotes simples pour éviter d'échapper les docstrings.
            file_content_template = Template(r'''from resources.lib.comaddon import dialog, addon, VSlog
from resources.lib.gui.gui import cGui
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.db import cDb
from resources.sites.themoviedb_org import SITE_IDENTIFIER as SITE_TMDB

import requests
import re
import traceback
import unicodedata

SITE_IDENTIFIER = 'cRecommendations'
SITE_NAME = 'Recommendations'


def get_tmdb_id(title, media_type="movie"):
    search_url = f"https://www.themoviedb.org/search?query={title}&language=fr-FR"
    response = requests.get(search_url)
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        if media_type == "movie":
            pattern = r'href="/movie/(\d+)-'
        else:
            pattern = r'href="/tv/(\d+)-'
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
        else:
            return None
    else:
        print(f"Erreur: {response.status_code}")
        return None

def remove_accents(input_str):
    """Remove accents from a given string."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def remove_normalise_doublon(lst):
    """
    Remove duplicates from a list of tuples (title, parameter_handler) based on title,
    ignoring accents and case, while preserving order.
    """
    unique = []
    seen = set()
    for item in lst:
        title = item[0]
        normalized_title = remove_accents(title).lower()
        if normalized_title not in seen:
            unique.append(item)
            seen.add(normalized_title)
    return unique


class cRecommendations:
    DIALOG = dialog()
    ADDON = addon()

    def showRecommendations(self, category, content_type, icon):
        """
        Generic method to fetch and display recommendations.

        :param category: The category ID for the type of content ('1' for movies, '4' for shows).
        :param content_type: The type of content ('showMovies' or 'showSeries').
        :param icon: The icon file to use ('films.png' or 'series.png').
        """
        oGui = cGui()
        recommendations = []  # List to store tuples of (title, outputParameterHandler)
        try:
            VSlog(f"Fetching recommendations for category {category}")
            
            with cDb() as DB:
                rows = DB.get_catWatched(category, 5)  # Fetch the last 5 watched items
                if not rows:
                    VSlog("No watched items found in this category.")
                    oGui.setEndOfDirectory()
                    return

                for data in rows:
                    # Log all keys in data
                    keys_list = list(data.keys())
                    VSlog("Clés de data: " + ", ".join(keys_list))
                    tmdb_id = data['tmdb_id']

                    oOutputParameterHandler = cOutputParameterHandler()
                    title = self.ADDON.VSlang(0) + ' ' + data['title']
                    sTitle = re.sub(r'(Saison\s*\d+|\s*S\d+\s*|[Ee]pisode\s*\d+|\s*E\d+\s*)', '', title, flags=re.IGNORECASE).strip()

                    if not isinstance(tmdb_id, int) or tmdb_id == 0:
                        tmdb_id = get_tmdb_id(sTitle, 'movie' if category == '1' else 'tv')

                    oOutputParameterHandler.addParameter('siteUrl', f"{'movie' if category == '1' else 'tv'}/{tmdb_id}/recommendations")
                    oOutputParameterHandler.addParameter('sTmdbId', tmdb_id)

                    recommendations.append((sTitle, oOutputParameterHandler))

                    VSlog(f"Title {sTitle} to make recommendations")
                    VSlog(f"tmdb_id: {tmdb_id} recommended from views.")

                recommendations = remove_normalise_doublon(recommendations)

                for sTitle, param_handler in recommendations:
                    oGui.addMovie(SITE_TMDB, content_type, sTitle, icon, '', '', param_handler)

        except Exception as e:
            VSlog(f"Error fetching recommendations: {e}\n{traceback.format_exc()}")
        finally:
            # Force the 'files' view for better clarity
            cGui.CONTENT = 'files'
            oGui.setEndOfDirectory()

    def showMoviesRecommendations(self):
        """Fetch and display movie recommendations."""
        self.showRecommendations('1', 'showMovies', 'films.png')

    def showShowsRecommendations(self):
        """Fetch and display TV show recommendations."""
        self.showRecommendations('4', 'showSeries', 'series.png')
''')

            # Substituer la variable dynamique dans le template
            file_content = file_content_template.substitute(because_num=because_num)

            # Création du fichier avec le contenu prédéfini
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(file_content)

            VSlog(f"Fichier {file_path} créé avec succès.")
        else:
            VSlog(f"Fichier {file_path} déjà existant. Aucune action requise.")

    except Exception as e:
        VSlog(f"Erreur lors de la création du fichier recommendations.py : {e}\n{traceback.format_exc()}")

def add_get_recommendations_method_for_netflix_like_recommendations():
    """
    Ajoute la méthode get_recommendations_by_id_movie à tmdb.py si elle est absente 
    et vérifie son ajout.
    """
    
    # Chemin vers le fichier tmdb.py
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/tmdb.py').replace('\\', '/')

    # Contenu brut de la méthode à ajouter
    raw_method_content = """
    def get_recommendations_by_id_movie(self, tmdbid):
        meta = self._call('movie/' + tmdbid + '/recommendations')
        if 'errors' not in meta and 'status_code' not in meta:
            return meta
        else:
            return {}

    def get_recommendations_by_id_tv(self, tmdbid):
        meta = self._call('tv/' + tmdbid + '/recommendations')
        if 'errors' not in meta and 'status_code' not in meta:
            return meta
        else:
            return {}
    """
    # Nettoyer le contenu et le ré-indenter pour respecter l'indentation d'une classe (4 espaces)
    dedented = textwrap.dedent(raw_method_content).strip('\n')
    indented_method = "\n    " + dedented.replace("\n", "\n    ") + "\n"

    # Vérifier si le fichier existe
    if not os.path.exists(file_path):
        VSlog(f"Fichier introuvable : {file_path}")
        return

    # Lire le contenu actuel du fichier
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        VSlog(f"Erreur lors de la lecture du fichier : {e}")
        return

    # Vérifier si la méthode est déjà présente
    if re.search(r"def\s+get_recommendations_by_id_movie\s*\(.*\):", content):
        VSlog("La méthode get_recommendations_by_id_movie est déjà présente.")
        return

    # Rechercher la première déclaration de classe
    # Cette regex accepte les classes avec ou sans parenthèses (pour les bases)
    class_regex = r'(class\s+\w+(?:\s*\([^)]*\))?\s*:)'
    match = re.search(class_regex, content, flags=re.MULTILINE)
    if match:
        new_content = re.sub(
            class_regex,
            r"\1" + indented_method,
            content,
            count=1,
            flags=re.MULTILINE
        )
    else:
        # Si aucune classe n'est définie, on ajoute la méthode à la fin du fichier
        new_content = content + "\n" + indented_method

    # Écrire les modifications dans le fichier
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
    except Exception as e:
        VSlog(f"Erreur lors de l'écriture dans le fichier : {e}")
        return

    # Vérification post-écriture pour confirmer l'ajout de la méthode
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            updated_content = file.read()
    except Exception as e:
        VSlog(f"Erreur lors de la relecture du fichier : {e}")
        return

    if re.search(r"def\s+get_recommendations_by_id_movie\s*\(.*\):", updated_content):
        VSlog(f"La méthode get_recommendations_by_id_movie a été ajoutée avec succès dans {file_path}.")
    else:
        VSlog("Erreur : La méthode get_recommendations_by_id_movie n'a pas été trouvée après modification.")

def addVstreamVoiceControl():
    # Recherche de tous les fichiers .py dans le répertoire
    file_paths = glob.glob(os.path.join(VSPath('special://home/addons/plugin.video.vstream/resources/sites/').replace('\\', '/'), "*.py"))

    for path in file_paths:
        file_path = VSPath(path).replace('\\', '/')
        VSlog(f"Processing file: {file_path}")
        add_parameter_to_function(file_path, 'showHosters', 'oInputParameterHandler=False')
        add_parameter_to_function_call(file_path, 'cHosterGui().showHoster', 'oInputParameterHandler=oInputParameterHandler')
        add_condition_to_statement(file_path, 'if not oInputParameterHandler:', 'oInputParameterHandler = cInputParameterHandler()')

    # Recherche de tous les fichiers .py dans le répertoire
    file_paths = glob.glob(os.path.join(VSPath('special://home/addons/plugin.video.vstream/resources/hosters/').replace('\\', '/'), "*.py"))

    for path in file_paths:
        file_path = VSPath(path).replace('\\', '/')
        VSlog(f"Processing file: {file_path}")
        add_parameter_to_function(file_path, 'getMediaLink', 'autoPlay=False')
        add_parameter_to_function(file_path, '_getMediaLinkForGuest', 'autoPlay=False')
        add_parameter_to_function_call(file_path, '_getMediaLinkForGuest', 'autoPlay')
        add_condition_to_statement(file_path, 'if not autoPlay:', 'oDialog = dialog().VSok', ["def getMediaLink:"])

    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/gui/gui.py').replace('\\', '/')
    codeblock = """
def emptySearchResult(self, siteName):
    cGui.searchResultsSemaphore.acquire()
    cGui.searchResults[siteName] = []  # vider le tableau de résultats
    cGui.searchResultsSemaphore.release()
    """

    codeblock2 = """
# On n'affiche pas si on fait une recherche
if window(10101).getProperty('playVideo') == 'true':
    return
    """

    add_parameter_to_function(file_path, 'addLink', 'oInputParameterHandler = False')
    add_condition_to_statement(file_path, 'if not oInputParameterHandler:', 'oInputParameterHandler = cInputParameterHandler()')
    add_codeblock_after_block(file_path, 'class cGui:', codeblock, 'searchResultsSemaphore = threading.Semaphore()')
    add_codeblock_after_block(file_path, 'def setEndOfDirectory(self, forceViewMode=False):', codeblock2)

    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/gui/hoster.py').replace('\\', '/')

    add_parameter_to_function(file_path, 'showHoster', 'oInputParameterHandler=False')
    add_parameter_to_function(file_path, 'play', 'oInputParameterHandler=False')
    add_parameter_to_function(file_path, 'play', 'autoPlay = False')
    add_parameter_to_function_call(file_path, 'oHoster.getMediaLink', 'autoPlay')
    add_parameter_to_function_call(file_path, 'cPlayer', 'oInputParameterHandler')
    add_condition_to_statement(file_path, 'if not oInputParameterHandler:', 'oInputParameterHandler = cInputParameterHandler()')
    add_condition_to_statement(file_path, 'if not autoPlay:', 'oDialog.VSinfo')
    add_condition_to_statement(file_path, 'if not autoPlay:', 'oDialog.VSerror')
    add_condition_to_statement(file_path, 'if not autoPlay:', 'oGui.setEndOfDirectory()')

    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/player.py').replace('\\', '/')
    add_parameter_to_function(file_path, '__init__', 'oInputParameterHandler=False', 'self')
    add_condition_to_statement(file_path, 'if not oInputParameterHandler:', 'oInputParameterHandler = cInputParameterHandler()')

    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/search.py').replace('\\', '/')

    new_content = '''
# -*- coding: utf-8 -*-
# vStream https://github.com/Kodi-vStream/venom-xbmc-addons
import re
import traceback
import threading
import xbmc
import json
import random

from resources.lib.gui.gui import cGui
from resources.lib.handler.rechercheHandler import cRechercheHandler
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.comaddon import progress, VSlog, addon, window, VSPath
from resources.lib.util import Quote

SITE_IDENTIFIER = 'cSearch'
SITE_NAME = 'Search'

# Chemins vers les fichiers JSON des films et séries les plus récents
FILMS_JSON = VSPath('special://home/addons/plugin.video.vstream/20filmslesplusrecents.json')
SERIES_JSON = VSPath('special://home/addons/plugin.video.vstream/20serieslesplusrecents.json')

class cSearch:

    MAX_NUMBER_CRITERIA = 5

    def __init__(self):
        self.addons = addon()
        self.autoPlayVideo = False
        self.findAndPlay = False
        self.allVideoLink = {}

    def load(self):
        """
        Sets the end of the directory for the GUI.
        """
        VSlog("Setting end of directory for GUI.")
        cGui().setEndOfDirectory()
        VSlog("End of directory set.")

    def searchGlobal(self, sSearchText='', sCat=''):
        try:
            if not sSearchText:
                oInputParameterHandler = cInputParameterHandler()
                sSearchText = oInputParameterHandler.getValue('searchtext')
                sCat = oInputParameterHandler.getValue('sCat')

            sSearchText = sSearchText.replace(':', ' ').strip()
            # vire doubles espaces
            sSearchText = re.sub(' +', ' ', sSearchText)

            listPlugins = self._initSearch(sSearchText, sCat)

            if len(listPlugins) == 0:
                return True

            # une seule source de sélectionée, on allege l'interface de résultat
            multiSource = len(listPlugins) != 1

            listThread = self._launchSearch(listPlugins, self._pluginSearch, [Quote(sSearchText), multiSource])
            self._finishSearch(listThread)

            oGui = cGui()
            if multiSource:
                oGui.addText('globalSearch', self.addons.VSlang(30081) % sSearchText, 'search.png')

            total = count = 0
            searchResults = oGui.getSearchResult()
            values = searchResults.values()
            for result in values:
                total += len(result)
            self._progressClose()


            if total:
                if multiSource:
                    xbmc.sleep(500)    # Nécessaire pour enchainer deux progressBar
                # Progress de chargement des metadata
                progressMeta = progress().VScreate(self.addons.VSlang(30076) + ' - ' + sSearchText, large=total > 50)
                for plugin in listPlugins:
                    pluginId = plugin['identifier']
                    if pluginId not in searchResults.keys():
                        continue
                    results = searchResults[pluginId]
                    if len(results) == 0:
                        continue
                    if multiSource:
                        # nom du site
                        count += 1
                        oGui.addText(pluginId, '%s. [COLOR olive]%s[/COLOR]' % (count, plugin['name']),
                                 'sites/%s.png' % pluginId)

                    # résultats du site
                    for result in results:
                        progressMeta.VSupdate(progressMeta, total)
                        oGui.addFolder(result['guiElement'], result['params'])
                        if progressMeta.iscanceled():
                            break

                progressMeta.VSclose(progressMeta)

            else:  # aucune source ne retourne de résultat
                oGui.addText('globalSearch')  # "Aucune information"

            cGui.CONTENT = 'files'

            oGui.setEndOfDirectory()

        except Exception as error:
            VSlog('Error with searchGlobal: ' + str(error))
            traceback.print_exc()
            self._progressForceClose()

        return True

    def playVideo(self, title='', sCat='movie'):
        """
        Initiates video playback by performing a quick search.

        :param title: Title of the video to play.
        :param sCat: Category of the video (default is 'movie').
        :return: Result of the quick search.
        """
        VSlog('Playing video')
        xbmc.executebuiltin("Notification(VStream,Recherche VStream en cours)")
        return self.quickSearch(True, title, sCat)


    def quickSearch(self, autoPlayVideo=False, title='', sCat='movie'):
        """
        Performs a quick search for videos and attempts to auto-play if enabled.

        :param autoPlayVideo: Flag to enable auto-play.
        :param title: Title of the video to search for.
        :param sCat: Category of the video (default is 'movie').
        :return: True if the search completes successfully.
        """
        try:
            VSlog("Starting quick search.")
            self.autoPlayVideo = autoPlayVideo

            searchInfo = self._getSearchInfo(title, sCat)
            VSlog(f"Search info: {searchInfo}")
            listPlugins = self._initSearch(searchInfo['title'], searchInfo['cat'])
            VSlog(f"List of plugins: {listPlugins}")

            if len(listPlugins) == 0:
                VSlog("No plugins available for search.")
                return True

            self.findAndPlay = False
            self.allVideoLink = {}
            self.eventFindOneLink = threading.Event()

            window(10101).setProperty('playVideo', 'true')
            VSlog("Set property 'playVideo' to 'true'.")

            listThread = self._launchSearch(listPlugins, self._quickSearchForPlugin, [searchInfo])
            VSlog("Launched search threads.")

            if autoPlayVideo:
                while len(self.listRemainingPlugins) > 0 and self._continueToSearch():
                    self.eventFindOneLink.wait()
                    self.eventFindOneLink.clear()
                    self._tryToAutoPlaySpecificCriteria(cSearch.MAX_NUMBER_CRITERIA)

                if self._continueToSearch():
                    self._tryToAutoPlay()

            self._finishSearch(listThread)
            window(10101).setProperty('playVideo', 'false')
            VSlog("Set property 'playVideo' to 'false'.")

            self._progressClose()

            if not self.findAndPlay:
                self._displayAllResult(searchInfo)

        except Exception as error:
            VSlog(f"Error with quickSearch: {error}")
            traceback.print_exc()
            self._progressForceClose()

        return True


    def _progressIsCancel(self):
        """
        Checks if the progress bar has been canceled.
        """
        if not self.autoPlayVideo:
            isCanceled = self.progress_.iscanceled()
            VSlog(f"Progress bar canceled: {isCanceled}")
            return isCanceled
        else:
            VSlog("AutoPlayVideo is enabled, progress bar not checked for cancellation.")
            return False

    def _progressInit(self, large=True):
        self.progress_ = progress().VScreate(large=large)

    def _progressUpdate(self):
        searchResults = cGui().getSearchResult()
        numberResult = 0
        values = searchResults.values()
        for result in values:
            numberResult += len(result)
        message = "\\n"
        message += (self.addons.VSlang(31209) % numberResult)
        message += "\\n"
        message += (self.addons.VSlang(31208) % (", ".join(self.listRemainingPlugins[0:7])))
        if len(self.listRemainingPlugins) > 7:
            message += ", ..."
        self.progress_.VSupdate(self.progress_, self.progressTotal, message, True)

    def _progressClose(self):
        self.progress_.VSclose(self.progress_)

    def _progressForceClose(self):
        self.progress_.VSclose()

    def _monitorAbortRequest(self):
        """
        Checks if an abort request has been made.
        """
        abortRequested = xbmc.Monitor().abortRequested()
        VSlog(f"Abort requested: {abortRequested}")
        return abortRequested

    def _continueToSearch(self):
        """
        Checks if the search process should continue based on various conditions.

        :return: True if the search should continue, False otherwise.
        """
        VSlog("Checking if search should continue")
        
        # Determine if the search should continue
        shouldContinue = not (self.findAndPlay or self._monitorAbortRequest() or self._progressIsCancel())
        
        VSlog(f"Search should {'continue' if shouldContinue else 'stop'}")
        return shouldContinue

    def _getAvailablePlugins(self, searchText, categorie):
        oHandler = cRechercheHandler()
        oHandler.setText(searchText)
        oHandler.setCat(categorie)
        return oHandler.getAvailablePlugins()



    def _initSearch(self, searchText, searchCat):
        try:
            listPlugins = self._getAvailablePlugins(searchText, searchCat)
            if not listPlugins:
                return []

            self.progressTotal = len(listPlugins)
            self._progressInit(self.progressTotal > 1)

            self.listRemainingPlugins = [plugin['name'] for plugin in listPlugins]
            cGui().resetSearchResult()
            return listPlugins
        except Exception as error:
            VSlog('Error when search is initiate: ' + str(error))
            traceback.print_exc()
            self._progressForceClose()
            return []

    def _tryToAutoPlay(self):
        """
        Attempts to auto-play video links, prioritizing those with the highest criteria scores.
        """
        VSlog("Attempting to auto-play video links.")
        
        if len(self.allVideoLink) > 0:  # Check if there are any video links to process
            numberMaxCriteria = max(self.allVideoLink.keys())  # Get the highest criteria score
            VSlog(f"Highest criteria score found: {numberMaxCriteria}")

            # Iterate from the highest score to the lowest score
            for iNumberCriteria in range(numberMaxCriteria, 0, -1):
                VSlog(f"Attempting to auto-play videos with criteria score: {iNumberCriteria}")
                self._tryToAutoPlaySpecificCriteria(iNumberCriteria)  # Attempt to play videos for the current score
        else:
            VSlog("No video links found to auto-play.")

    def _tryToAutoPlaySpecificCriteria(self, numberCriteria):
        """
        Attempts to auto-play video links with a specific criteria score.

        :param numberCriteria: The criteria score of the video links to attempt to play.
        """
        VSlog(f"Attempting to auto-play video links with criteria score: {numberCriteria}")

        if numberCriteria in self.allVideoLink:  # Check if there are links with the given criteria score
            VSlog(f"Found video links with criteria score: {numberCriteria}")

            for searchResult in self.allVideoLink[numberCriteria]:
                VSlog(f"Processing search result: {searchResult}")

                # Check if search should continue and the result hasn't been tested yet
                if self._continueToSearch() and searchResult['params'].getValue('playTest') == 'false':
                    VSlog("Search should continue and result has not been tested yet")

                    # Mark the result as tested
                    searchResult['params'].addParameter('playTest', 'true')
                    VSlog("Marked result as tested")

                    # Attempt to play the video
                    find = self._playHosterGui(
                        'play', 
                        [searchResult['params'], True]
                    )
                    VSlog(f"Attempted to play video, result: {find}")

                    if find:  # If playback is successful
                        self.findAndPlay = True  # Indicate that a video was successfully found and played
                        VSlog("Playback successful, video found and played")
                        return
        else:
            VSlog(f"No video links found with criteria score: {numberCriteria}")

    def _deepSearchLoop(self, searchResult, searchInfo):
        """
        Recursively navigates plugin menus to locate video links based on search criteria.

        :param searchResult: Dictionary representing the current search result.
        :param searchInfo: Dictionary containing search parameters like title, year, etc.
        """
        VSlog(f"Starting deep search loop for search result: {searchResult} with search info: {searchInfo}")

        if self._continueToSearch() or searchResult['guiElement'].getSiteName() != 'cHosterGui':  # Check if the search process should continue
            numberOfCriteria = self._getScoreOfThisResult(searchResult, searchInfo)
            VSlog(f"Number of criteria met: {numberOfCriteria}")

            if numberOfCriteria > 0:  # If the result meets minimum criteria
                videoParams = searchResult['params']  # OutputParameter object
                siteId = searchResult['guiElement'].getSiteName()
                functionName = searchResult['guiElement'].getFunction()
                gui_element = searchResult['guiElement']

                VSlog(f"Processing result from site: {siteId} with function: {functionName}")

                # If the result is from cHosterGui, process as a video link

                sHosterIdentifier = videoParams.getValue('sHosterIdentifier')
                VSlog('_deepSearchLoop: OutputParameter: sHosterIdentifier: {}'.format(sHosterIdentifier))

                sMediaUrl = videoParams.getValue('sMediaUrl')
                VSlog('_deepSearchLoop: OutputParameter: sMediaUrl: {}'.format(sMediaUrl))

                bGetRedirectUrl = videoParams.getValue('bGetRedirectUrl')
                VSlog('_deepSearchLoop: OutputParameter: bGetRedirectUrl: {}'.format(bGetRedirectUrl))

                sFileName = videoParams.getValue('sFileName')
                VSlog('_deepSearchLoop: OutputParameter: sFileName: {}'.format(sFileName))

                sTitle = videoParams.getValue('sTitle')
                VSlog('_deepSearchLoop: OutputParameter: sTitle: {}'.format(sTitle))

                siteUrl = videoParams.getValue('siteUrl')
                VSlog('_deepSearchLoop: OutputParameter: siteUrl: {}'.format(siteUrl))

                sCat = videoParams.getValue('sCat')
                VSlog('_deepSearchLoop: OutputParameter: sCat: {}'.format(sCat))

                sMeta = videoParams.getValue('sMeta')
                VSlog('_deepSearchLoop: OutputParameter: sMeta: {}'.format(sMeta))

                VSlog(f"_deepSearchLoop: gui_element : Type: {gui_element.getType()}")
                VSlog(f"_deepSearchLoop: gui_element : Catégorie: {gui_element.getCat()}")
                VSlog(f"_deepSearchLoop: gui_element : Meta Addon: {gui_element.getMetaAddon()}")
                VSlog(f"_deepSearchLoop: gui_element : Trailer: {gui_element.getTrailer()}")
                VSlog(f"_deepSearchLoop: gui_element : TMDb ID: {gui_element.getTmdbId()}")
                VSlog(f"_deepSearchLoop: gui_element : IMDb ID: {gui_element.getImdbId()}")
                VSlog(f"_deepSearchLoop: gui_element : Année: {gui_element.getYear()}")
                VSlog(f"_deepSearchLoop: gui_element : Résolution: {gui_element.getRes()}")
                VSlog(f"_deepSearchLoop: gui_element : Genre: {gui_element.getGenre()}")
                VSlog(f"_deepSearchLoop: gui_element : Saison: {gui_element.getSeason()}")
                VSlog(f"_deepSearchLoop: gui_element : Épisode: {gui_element.getEpisode()}")
                VSlog(f"_deepSearchLoop: gui_element : Temps total: {gui_element.getTotalTime()}")
                VSlog(f"_deepSearchLoop: gui_element : Temps de reprise: {gui_element.getResumeTime()}")
                VSlog(f"_deepSearchLoop: gui_element : Meta: {gui_element.getMeta()}")
                VSlog(f"_deepSearchLoop: gui_element : URL Média: {gui_element.getMediaUrl()}")
                VSlog(f"_deepSearchLoop: gui_element : URL Site: {gui_element.getSiteUrl()}")
                VSlog(f"_deepSearchLoop: gui_element : Nom du site: {gui_element.getSiteName()}")
                VSlog(f"_deepSearchLoop: gui_element : Nom du fichier: {gui_element.getFileName()}")
                VSlog(f"_deepSearchLoop: gui_element : Fonction: {gui_element.getFunction()}")


                if siteId == 'cHosterGui':
                    if numberOfCriteria not in self.allVideoLink:
                        self.allVideoLink[numberOfCriteria] = []

                    # Mark this result as not yet tested for playback
                    searchResult['params'].addParameter('playTest', 'false')
                    self.allVideoLink[numberOfCriteria].append(searchResult)
                    VSlog(f"Added result to allVideoLink with criteria: {numberOfCriteria}")

                    # Auto-play video if it matches the maximum number of criteria
                    if self.autoPlayVideo and numberOfCriteria == cSearch.MAX_NUMBER_CRITERIA:
                        VSlog("Auto-play video as it matches the maximum number of criteria")
                        self.eventFindOneLink.set()  # Signal to launch the video

                else:  # Otherwise, it's a plugin menu, navigate deeper
                    videoParams.addParameter('searchSiteId', siteId)  # Retain the original site
                    cGui().emptySearchResult(siteId)  # Clear previous results from this site
                    VSlog(f"Executing plugin search for site: {siteId} with function: {functionName}")
                    self._executePluginForSearch(siteId, functionName, videoParams)  # Execute the search

                    # Retrieve the new search results from the executed function
                    pluginResult = cGui().getSearchResult()
                    VSlog(f"New search results from site: {siteId}: {pluginResult}")

                    for newSearchResult in pluginResult[siteId]:
                        if self._continueToSearch() and siteId != 'cHosterGui':  # Continue only if allowed
                            # Merge additional parameters into the new result
                            for nSearchResult in pluginResult['cHosterGui']:
                                gui_element = nSearchResult['guiElement']
                                VSlog(f"_deepSearchLoop2: gui_element : Type: {gui_element.getType()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Catégorie: {gui_element.getCat()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Meta Addon: {gui_element.getMetaAddon()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Trailer: {gui_element.getTrailer()}")
                                VSlog(f"_deepSearchLoop2: gui_element : TMDb ID: {gui_element.getTmdbId()}")
                                VSlog(f"_deepSearchLoop2: gui_element : IMDb ID: {gui_element.getImdbId()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Année: {gui_element.getYear()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Résolution: {gui_element.getRes()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Genre: {gui_element.getGenre()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Saison: {gui_element.getSeason()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Épisode: {gui_element.getEpisode()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Temps total: {gui_element.getTotalTime()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Temps de reprise: {gui_element.getResumeTime()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Meta: {gui_element.getMeta()}")
                                VSlog(f"_deepSearchLoop2: gui_element : URL Média: {gui_element.getMediaUrl()}")
                                VSlog(f"_deepSearchLoop2: gui_element : URL Site: {gui_element.getSiteUrl()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Nom du site: {gui_element.getSiteName()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Nom du fichier: {gui_element.getFileName()}")
                                VSlog(f"_deepSearchLoop2: gui_element : Fonction: {gui_element.getFunction()}")

                            newSearchResult['params'].mergeUnexistingInfos(videoParams)
                            newSearchResult['params'].addParameter('searchSiteId', siteId)
                            VSlog(f"Merged parameters into new search result: {newSearchResult}")

                            # Avoid infinite recursion on the same function
                            if newSearchResult['guiElement'].getSiteName() == siteId and newSearchResult['guiElement'].getFunction() == functionName:
                                VSlog(f"Will not loop on the same function: {siteId}.{functionName}")
                            else:
                                # Recursively navigate deeper
                                self._deepSearchLoop(newSearchResult, searchInfo)
                        else:
                            VSlog("Search process stopped")
                            break

    def _quickSearchForPlugin(self, plugin, searchInfo):
        """
        Perform a quick search for a given plugin and process its results.

        :param plugin: Dictionary containing plugin information ('identifier', 'name', etc.).
        :param searchInfo: Dictionary containing search information ('title', 'year', etc.).
        """
        VSlog(f"Starting quick search for plugin: {plugin['name']} (ID: {plugin['identifier']})")
        VSlog(f"Search information: {searchInfo}")

        pluginId = plugin['identifier']
        pluginName = plugin['name']

        if self._continueToSearch():  # Check if the search should proceed
            VSlog(f"Initiating plugin search with title: {searchInfo['title']}")
            # Initiate plugin search with the quoted search title
            self._pluginSearch(plugin, Quote(searchInfo['title']))
            searchResults = cGui().getSearchResult()  # Retrieve results from GUI search

            VSlog(f"Search results for plugin {pluginName} (ID: {pluginId}): {searchResults}")

            if pluginId in searchResults and len(searchResults[pluginId]) > 0:  # If there are results for this plugin
                pluginResult = searchResults[pluginId][:]  # Copy results to avoid modifying the original
                VSlog(f"Results found for plugin {pluginName}: {pluginResult}")

                for searchResult in pluginResult:
                    # Add plugin name as a parameter to the result
                    searchResult['params'].addParameter('searchSiteName', pluginName)
                    VSlog(f"Added plugin name to search result parameters: {searchResult['params']}")

                    # Perform deep search loop on the result
                    self._deepSearchLoop(searchResult, searchInfo)

                    # Break if search should stop
                    if not self._continueToSearch():
                        VSlog("Search stopped by user or system.")
                        break
            else:
                VSlog(f"No result for plugin: {pluginId}")  # Log if no results are found for this plugin

        # Remove the plugin from the list of remaining plugins to search
        self.listRemainingPlugins.remove(pluginName)
        VSlog(f"Removed plugin {pluginName} from remaining plugins list.")

        # Update the progress bar or any other progress indicators
        self._progressUpdate(sum(map(len, self.allVideoLink.values())))
        VSlog("Updated progress bar with current search results.")

        # If all plugins have been processed and autoplay is enabled, signal the event
        if len(self.listRemainingPlugins) == 0 and self.autoPlayVideo:
            VSlog("All plugins processed and autoplay is enabled. Signaling event to find one link.")
            self.eventFindOneLink.set()

    def _removeNonLetterCaracter(self, word):
        """
        Removes non-alphanumeric characters from a string and normalizes accented characters.

        :param word: The input string to process.
        :return: A cleaned string with non-alphanumeric characters replaced by spaces 
                 and accented characters normalized.
        """
        VSlog(f"Original word: {word}")

        # Replace non-alphanumeric characters with spaces
        result = re.sub(r'[^a-zA-Z0-9]', ' ', word, flags=re.I)
        VSlog(f"After replacing non-alphanumeric characters: {result}")

        # Normalize accented characters
        result = re.sub(r'[éèêë]', 'e', result, flags=re.I)
        VSlog(f"After normalizing 'éèêë' to 'e': {result}")
        result = re.sub(r'à', 'a', result, flags=re.I)
        VSlog(f"After normalizing 'à' to 'a': {result}")
        result = re.sub(r'ô', 'o', result, flags=re.I)
        VSlog(f"After normalizing 'ô' to 'o': {result}")
        result = re.sub(r'ù', 'u', result, flags=re.I)
        VSlog(f"After normalizing 'ù' to 'u': {result}")
        result = re.sub(r'œ', 'oe', result, flags=re.I)
        VSlog(f"After normalizing 'œ' to 'oe': {result}")

        # Remove extra spaces introduced by replacements
        result = re.sub(r'\s+', ' ', result).strip()
        VSlog(f"After removing extra spaces: {result}")

        return result

    def _convert_category(self, sCat):
        """
        Converts a string category to its corresponding integer value.

        :param sCat: String representation of the category (e.g., "movie", "series").
        :return: Integer value representing the category, or 0 if not found.
        """
        category_mapping = {
            "movie": 1,
            "series": random.choice([2, 4]),  # Randomly choose between 2 (TV Series) and 4 (Mini-Series)
            # Add more categories as needed in the format: "category_name": category_value
        }

        # Normalize input category to lowercase and retrieve mapped value
        category_value = category_mapping.get(sCat.lower(), 0)

        VSlog(f"Converted category '{sCat}' to value: {category_value}")
        return category_value


    def _getSearchInfo(self, title='', sCat="movie"):
        """
        Retrieves search information including title, category, and year.

        :param title: Title of the content to search for (default is empty).
        :param sCat: Category of content ("movie" or "series").
        :return: Dictionary containing search information or error details.
        """
        oInputParameterHandler = cInputParameterHandler()

        # Validate content type
        if sCat not in ["movie", "series"]:
            VSlog('Invalid content type. Expected "movie" or "series".')
            return {"error": "Invalid content type. Use 'movie' or 'series'."}

        # Initialize search text
        sSearchText = title.strip()
        if not sSearchText:
            json_file = FILMS_JSON if sCat == "movie" else SERIES_JSON
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    suggestions = json.load(f)
                # Sélection aléatoire + extraction titre
                random_entry = random.choice(suggestions)
                sSearchText = random_entry.get('title', '')
                VSlog(f'Loaded random title: {sSearchText}')

                if not sSearchText:
                    return {"error": "Entrée sans titre détectée"}
            except FileNotFoundError:
                error_message = f"File not found: {json_file}"
                VSlog(error_message)
                return {"error": error_message}
            except json.JSONDecodeError:
                error_message = f"Failed to decode JSON from file: {json_file}"
                VSlog(error_message)
                return {"error": error_message}

        # Determine category
        if oInputParameterHandler.exist('cat'):
            searchCat = int(oInputParameterHandler.getValue('cat'))
            VSlog(f'Category retrieved from input parameters: {searchCat}')
        else:
            searchCat = self._convert_category(sCat)
            VSlog(f'Category converted from sCat parameter: {searchCat}')

        # Determine title
        if oInputParameterHandler.exist('title'):
            searchTitle = self._removeNonLetterCaracter(oInputParameterHandler.getValue('title'))
            VSlog(f'Title retrieved from input parameters: {searchTitle}')
        else:
            searchTitle = self._removeNonLetterCaracter(sSearchText)
            VSlog(f'Title processed from input or default: {searchTitle}')

        # Determine year
        if oInputParameterHandler.exist('year'):
            searchYear = str(oInputParameterHandler.getValue('year'))
            VSlog(f'Year retrieved from input parameters: {searchYear}')
        else:
            searchYear = ""
            VSlog('Year not provided; defaulting to empty.')

        # Return search info
        search_info = {'title': searchTitle, 'cat': searchCat, 'year': searchYear}
        VSlog(f'Constructed search info: {search_info}')
        return search_info

    def _isYearCorrect(self, result, searchInfo):
        """
        Checks if the year of the search result matches the search criteria.

        :param result: The search result to check.
        :param searchInfo: The search information containing user preferences.
        :return: 1 if the year does not match, -1 if it matches, 0 if neutral.
        """
        resultYear = result['params'].getValue('sYear')
        searchYear = searchInfo.get('year', '')

        VSlog("Checking year correctness:")
        VSlog(f"Search Year: {searchYear}, Result Year: {resultYear}")

        if resultYear:
            if resultYear != searchYear:
                VSlog(f"Year mismatch: Result Year ({resultYear}) does not match Search Year ({searchYear}).")
                return 1
            else:
                VSlog(f"Year match excluded: Exact match found with year {resultYear}.")
                return -1
        else:
            VSlog("Result year is missing. Defaulting to neutral (1).")
            return 1

    def _isMovieTitleCorrect(self, result, searchInfo):
        """
        Checks if the movie title of the search result matches the search criteria.

        :param result: The search result to check.
        :param searchInfo: The search information containing user preferences.
        :return: 2 if the title matches exactly, 1 if it partially matches, -1 if it does not match, 0 if neutral.
        """
        resultTitle = result['params'].getValue('sMovieTitle')
        VSlog("Checking movie title correctness:")
        VSlog(f"Search title: {searchInfo['title']}, Result title: {resultTitle}")

        if resultTitle:
            if self._checkAllSearchWordInTitle(searchInfo['title'], resultTitle):
                normalizedSearchTitle = searchInfo['title'].lower()
                normalizedResultTitle = self._removeNonLetterCaracter(resultTitle).lower()
                
                VSlog("All search words found in result title. Normalized titles for comparison:")
                VSlog(f"Normalized Search Title: {normalizedSearchTitle}")
                VSlog(f"Normalized Result Title: {normalizedResultTitle}")

                if normalizedSearchTitle == normalizedResultTitle:
                    VSlog("Exact title match found.")
                    return 2
                else:
                    VSlog("Partial title match found.")
                    return 1
            else:
                VSlog(f"Exclude result because not all search words are in the title: {resultTitle}")
                return -1
        else:
            VSlog("Result title is missing. Defaulting to neutral (0).")
            return 0

    def _isLangCorrect(self, result, searchInfo):
        """
        Checks if the language of the search result matches the user's language preferences.

        :param result: The search result to check.
        :param searchInfo: The search information containing user preferences.
        :return: 1 if the language matches, -1 if it doesn't, 0 if neutral.
        """
        resultLang = str(result['params'].getValue('sLang')).lower()
        autoPlayLang = self.addons.getSetting('autoPlayLang')  # 0 = fr, vostfr; 1 = fr; 2 = all

        VSlog("Checking language correctness:")
        VSlog(f"Result language: {resultLang}, AutoPlay language setting: {autoPlayLang}")

        if resultLang and resultLang != 'false':
            if autoPlayLang == '1':
                if 'vf' in resultLang or 'truefrench' in resultLang:
                    VSlog(f"Language match: 'fr' detected in resultLang: {resultLang}")
                    return 1
                elif 'en' in resultLang or 'vostfr' in resultLang:
                    VSlog(f"Exclude result due to 'en' or 'vostfr' in resultLang: {resultLang}")
                    return -1
            elif autoPlayLang == '0':
                if 'vf' in resultLang or 'truefrench' in resultLang or 'vostfr' in resultLang:
                    VSlog(f"Language match: 'vf', 'truefrench', or 'vostfr' detected in resultLang: {resultLang}")
                    return 1
            elif autoPlayLang == '2':
                VSlog(f"Language setting allows all. Accepting resultLang: {resultLang}")
                return 1
        else:
            VSlog("Result language is empty or marked as 'false'. Defaulting to neutral.")

        VSlog("Language correctness check resulted in no match.")
        return 0


    def _isCategorieCorrect(self, result, searchInfo):
        """
        Checks if the category of the search result matches the search criteria.

        :param result: The search result to check.
        :param searchInfo: The search information containing user preferences.
        :return: 1 if the category matches, -1 if it doesn't, 0 if neutral.
        """
        searchCat = searchInfo['cat']
        try:
            resultMeta = int(result['params'].getValue('sMeta'))
        except (ValueError, TypeError):
            VSlog("Error converting result meta value to integer. Defaulting to 0.")
            resultMeta = 0

        VSlog("Checking category correctness:")
        VSlog(f"Search category: {searchCat}, Result meta: {resultMeta}")

        if searchCat >= 0 and resultMeta != 0:
            if searchCat == 1 and resultMeta != 1:
                VSlog(f"Exclude result because it is not a movie (meta: {resultMeta})")
                return -1
            # Currently, series validation is limited
            elif searchCat in [2, 4] and resultMeta not in [2, 5]:
                VSlog(f"Exclude result because it is not a series (meta: {resultMeta})")
                return -1
            else:
                VSlog("Category is correct.")
                return 1

        VSlog("Category is neutral or does not match any exclusion criteria.")
        return 0

    def _getScoreOfThisResult(self, result, searchInfo):
        """
        Calculates the score for a search result based on various criteria.

        :param result: The search result to score.
        :param searchInfo: The search information containing user preferences.
        :return: The total score for the result.
        """
        VSlog("Calculating score for the result:")
        VSlog(f"Search info: {searchInfo}")
        VSlog(f"Result params: {result['params']}")

        yearScore = self._isYearCorrect(result, searchInfo)
        VSlog(f"Year score: {yearScore}")

        titleScore = self._isMovieTitleCorrect(result, searchInfo)
        VSlog(f"Title score: {titleScore}")

        langScore = self._isLangCorrect(result, searchInfo)
        VSlog(f"Language score: {langScore}")

        catScore = self._isCategorieCorrect(result, searchInfo)
        VSlog(f"Category score: {catScore}")

        # Check if any individual score disqualifies the result
        if yearScore < 0:
            VSlog("Year score is negative. Excluding result.")
        if titleScore < 0:
            VSlog("Title score is negative. Excluding result.")
        if langScore < 0:
            VSlog("Language score is negative. Excluding result.")
        if catScore < 0:
            VSlog("Category score is negative. Excluding result.")

        if yearScore < 0 or titleScore < 0 or langScore < 0 or catScore < 0:
            VSlog("Result disqualified due to negative scores.")
            return 0

        totalScore = yearScore + titleScore + langScore + catScore
        if totalScore == 4: #rigged it
            totalScore = 5
        VSlog(f"Total score for this result: {totalScore}")
        return totalScore

    def _checkAllSearchWordInTitle(self, searchTitle, resultTitle):
        """
        Checks if all words in the search title are present in the result title.

        :param searchTitle: The search title to check.
        :param resultTitle: The result title to check against.
        :return: True if all words are present, False otherwise.
        """
        VSlog("Checking if all words in search title are in result title.")
        VSlog(f"Original search title: '{searchTitle}', Result title: '{resultTitle}'")
        
        searchTitle = searchTitle.lower()
        resultTitle = resultTitle.lower()
        
        VSlog(f"Lowercased search title: '{searchTitle}', Lowercased result title: '{resultTitle}'")

        for word in searchTitle.split():
            if word not in resultTitle:
                VSlog(f"Word '{word}' not found in result title.")
                return False
            VSlog(f"Word '{word}' found in result title.")
        
        VSlog("All words in the search title are present in the result title.")
        return True

    def _displayAllResult(self, searchInfo):
        """
        Displays all search results in the GUI.

        :param searchInfo: The search information containing user preferences.
        """
        VSlog("Starting to display all results.")
        
        try:
            # Initialize GUI and display the global search info
            searchGui = cGui()
            allSearchInfo = f"{searchInfo['title']} {searchInfo['year']}"
            VSlog(f"Search info: {allSearchInfo}")
            searchGui.addText('globalSearch', self.addons.VSlang(30081) % allSearchInfo, 'search.png')
            VSlog("Added global search info to the GUI.")

            # Check if there are any video links
            if len(self.allVideoLink) == 0:
                VSlog("No video links found. Displaying 'no information' message.")
                searchGui.addText('globalSearch')  # "Aucune information"
            else:
                # Iterate over results by criteria
                maxCriteria = max(self.allVideoLink.keys(), default=0)
                VSlog(f"Maximum criteria found: {maxCriteria}")
                
                for numCriteria in range(maxCriteria, 0, -1):
                    if numCriteria in self.allVideoLink.keys():
                        VSlog(f"Processing results with {numCriteria} criteria.")
                        for result in self.allVideoLink[numCriteria]:
                            VSlog(f"Displaying result: {result}")
                            self._displayOneResult(searchGui, result)

            # Set content type and end directory
            cGui.CONTENT = 'files'
            searchGui.setEndOfDirectory()
            VSlog("Finished displaying all results. End of directory set.")

        except Exception as e:
            VSlog(f"Error while displaying all results: {e}")
            traceback.print_exc()

        VSlog("Finished execution of _displayAllResult.")

    def _displayOneResult(self, searchGui, result):
        """
        Displays a single search result in the GUI.

        :param searchGui: The GUI object to display the result.
        :param result: The search result to display.
        """
        VSlog("Starting to display a single result.")
        
        try:
            # Retrieve result parameters
            resultParams = result['params']
            VSlog(f"Retrieved result parameters: {resultParams}")

            # Initialize the title with the main title
            title = resultParams.getValue('sTitle')
            if not title:
                VSlog("No title found for the result. Skipping this result.")
                return
            VSlog(f"Initial title: {title}")

            # Add language information to the title
            lang = resultParams.getValue('sLang')
            if lang:
                title += f" ({lang})"
                VSlog(f"Added language to title: {lang}")

            # Add year information to the title
            year = resultParams.getValue('sYear')
            if year:
                title += f" {year}"
                VSlog(f"Added year to title: {year}")

            # Add hoster information to the title
            hoster = resultParams.getValue('sHosterIdentifier')
            if hoster:
                title += f" - [COLOR skyblue]{hoster}[/COLOR]"
                VSlog(f"Added hoster to title: {hoster}")

            # Add quality information to the title
            quality = resultParams.getValue('sQual')
            if quality:
                title += f" [{quality.upper()}]"
                VSlog(f"Added quality to title: {quality}")

            # Add search site name information to the title
            searchSiteName = resultParams.getValue('searchSiteName')
            if searchSiteName:
                title += f" - [COLOR olive]{searchSiteName}[/COLOR]"
                VSlog(f"Added search site name to title: {searchSiteName}")

            # Set the title for the result
            result['guiElement'].setTitle(title)
            VSlog(f"Final title set for the result: {title}")

            # Add the result to the GUI
            searchGui.addFolder(result['guiElement'], result['params'], False)
            VSlog("Added result to the GUI.")

        except Exception as e:
            VSlog(f"Error while displaying result: {e}")
            traceback.print_exc()

        VSlog("Finished displaying a single result.")

    def _launchSearch(self, listPlugins, targetFunction, argsList):

        # active le mode "recherche globale"
        window(10101).setProperty('search', 'true')

        listThread = []
        if self.progressTotal > 1:
            for plugin in listPlugins:
                thread = threading.Thread(target=targetFunction, name=plugin['name'], args=tuple([plugin] + argsList))
                thread.start()
                listThread.append(thread)
        else:
            self._pluginSearch(listPlugins[0], argsList[0], argsList[1])
        return listThread

    def _finishSearch(self, listThread):
        # On attend que les thread soient finis
        for thread in listThread:
            thread.join()

        window(10101).setProperty('search', 'false')

    def _pluginSearch(self, plugin, sSearchText, updateProcess=False):
        try:
            plugins = __import__('resources.sites.%s' % plugin['identifier'], fromlist=[plugin['identifier']])
            function = getattr(plugins, plugin['search'][1])
            urlSearch = plugin['search'][0]
            if '%s' in urlSearch:
                sUrl = urlSearch % str(sSearchText)
            else:
                sUrl = urlSearch + str(sSearchText)

            function(sUrl)
            if updateProcess:
                self.listRemainingPlugins.remove(plugin['name'])
                self._progressUpdate()

            VSlog('Load Search: ' + str(plugin['identifier']))
        except Exception as e:
            VSlog(plugin['identifier'] + ': search failed (' + str(e) + ')')

    def _executePluginForSearch(self, sSiteName, sFunction, parameters):
        """
        Executes a specified function from a plugin for a given site.

        :param sSiteName: The name of the site.
        :param sFunction: The function to execute.
        :param parameters: The parameters to pass to the function.
        :return: True if the execution is successful, False otherwise.
        """
        VSlog(f"Starting execution of plugin for site: {sSiteName}, function: {sFunction} with parameters: {parameters}")

        try:
            # Import the specified site module dynamically
            VSlog(f"Attempting to import plugin module for site: {sSiteName}")
            plugins = __import__(f'resources.sites.{sSiteName}', fromlist=[sSiteName])
            VSlog(f"Successfully imported module for site: {sSiteName}")

            # Retrieve the specified function from the imported module
            VSlog(f"Retrieving function '{sFunction}' from the module.")
            function = getattr(plugins, sFunction)
            VSlog(f"Function '{sFunction}' successfully retrieved from module '{sSiteName}'.")

            # Execute the function with the provided parameters
            VSlog(f"Executing function '{sFunction}' with parameters: {parameters}")
            function(parameters)
            VSlog(f"Function '{sFunction}' executed successfully.")

            result = True

        except Exception as error:
            # Log the error details if an exception occurs
            VSlog(f"Error while executing plugin for site: {sSiteName}, function: {sFunction}. Error: {error}")
            traceback.print_exc()
            result = False

        VSlog(f"Execution of plugin for site: {sSiteName} complete. Result: {'Success' if result else 'Failure'}")
        return result

    def _playHosterGui(self, sFunction, parameters=None):
        """
        Executes a specified function from the cHosterGui class.

        :param sFunction: The function to execute.
        :param parameters: The parameters to pass to the function (optional).
        :return: The result of the function execution, or None if an error occurs.
        """
        try:
            VSlog(f"Initializing hoster GUI import for function '{sFunction}' with parameters: {parameters}")
            
            # Import the cHosterGui class from the hoster module
            plugins = __import__('resources.lib.gui.hoster', fromlist=['cHosterGui']).cHosterGui()
            VSlog("Successfully imported cHosterGui class.")

            # Retrieve the specified function from the cHosterGui instance
            function = getattr(plugins, sFunction)
            VSlog(f"Successfully retrieved function '{sFunction}' from cHosterGui.")

            # Call the function with or without parameters
            if parameters:
                VSlog(f"Calling function '{sFunction}' with parameters: {parameters}")
                result = function(*parameters)
            else:
                VSlog(f"Calling function '{sFunction}' with no parameters.")
                result = function()

            VSlog(f"Function '{sFunction}' executed successfully. Result: {result}")
            return result

        except Exception as e:
            # Log any exception that occurs during the process
            VSlog(f"Error occurred while executing '{sFunction}' in _playHosterGui: {e}")
            traceback.print_exc()
            return None
'''

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def modify_files():
    VSlog("Starting file modification process")

    edit_live_file()

    create_monitor_file()
    add_vstreammonitor_import()

    add_netflix_like_recommendations()

    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/gui/hoster.py').replace('\\', '/')
    VSlog(f"Modifying file: {file_path}")
    add_parameter_to_function(file_path, 'showHoster', 'oInputParameterHandler=False')

    # Recherche de tous les fichiers .py dans le répertoire
    file_paths = glob.glob(os.path.join(VSPath('special://home/addons/plugin.video.vstream/resources/sites/').replace('\\', '/'), "*.py"))

    for path in file_paths:
        file_path = VSPath(path).replace('\\', '/')
        VSlog(f"Processing file: {file_path}")
        rewrite_file_to_avoid_regex_infinite_loops(file_path)
        modify_showEpisodes(file_path)

    player_file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/player.py').replace('\\', '/')
    VSlog(f"Processing player file: {player_file_path}")

    # Read the file content
    with open(player_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Define the regex pattern to find the target block
    existing_pattern = r"^( *)if not self\.sEpisode:\n\1 {4}ret = dialog\(\)\.VSselect\(\['Reprendre depuis %02d:%02d:%02d' % \(h, m, s\), 'Lire depuis le début'\], 'Reprendre la lecture'\)"

    # Search for the target block in the file content
    if re.search(existing_pattern, content, re.MULTILINE):
        VSlog("Target block already present in the file. No modifications needed.")
    else:
        # Define the regex pattern to find the target line to be replaced
        pattern = r"^( *)ret\s*=\s*dialog\(\)\.VSselect\(\[.*Reprendre depuis.*\],.*Reprendre la lecture.*\)"
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        if matches:
            for match in matches:
                # Calculate the indentation level of the matched line
                indent_level = len(match.group(1))
                VSlog(f"Found duplicate line at indentation level: {indent_level}")

                # Construct the new code block with proper indentation
                new_code = (
                    " " * indent_level + "ret = 0\n" +
                    " " * indent_level + "if not self.sEpisode:\n" +
                    " " * (indent_level + 4) + "ret = dialog().VSselect(['Reprendre depuis %02d:%02d:%02d' % (h, m, s), 'Lire depuis le début'], 'Reprendre la lecture')\n"
                )

                # Replace the matched line with the new code block
                content = content.replace(match.group(0), new_code)

            # Write the updated content back to the file
            with open(player_file_path, 'w', encoding='utf-8') as file:
                file.write(content)

            VSlog("Player file updated successfully with new code block.")
        else:
            VSlog("Target line not found in the file. No modifications applied.")

def modify_showEpisodes(file_path):
    """
    Analyzes and modifies the `showEpisodes` function in the given file to ensure:
    - Proper episode numbering with `S<num> E<num>` format.
    - Season and episode data extraction from the URL.
    - Handles accents in a standard manner.
    - Ensures `showEpisode` is renamed to `showEpisodes`, updating all references in the file.
    """

    def get_indentation(line):
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Check and ensure `import unicodedata` is at the beginning of the file
    if not any("import unicodedata" in line for line in lines):
        for i, line in enumerate(lines):
            if line.strip().startswith("import") or line.strip().startswith("from"):
                lines.insert(i + 1, "import unicodedata\n")
                break
        else:
            lines.insert(0, "import unicodedata\n")

    # Check and ensure `import re` is at the beginning of the file
    if not any("import re" in line for line in lines):
        for i, line in enumerate(lines):
            if line.strip().startswith("import") or line.strip().startswith("from"):
                lines.insert(i + 1, "import re\n")
                break
        else:
            lines.insert(0, "import re\n")

        # Check if VSlog import is already added
    vslog_import_added = any("from resources.lib.comaddon import" in line and "VSlog" in line for line in lines)

    # Add VSlog to the import statement if not present
    if not vslog_import_added:
        for i, line in enumerate(lines):
            if "from resources.lib.comaddon import" in line:
                lines[i] = line.strip() + ", VSlog\n"
                break

    # Rename `showEpisode` to `showEpisodes` if needed
    show_episode_exists = any("def showEpisode" in line for line in lines)
    if show_episode_exists:
        # Replace all occurrences of `showEpisode` with `showEpisodes`
        updated_lines = []
        for line in lines:
            updated_lines.append(re.sub(r'\bshowEpisode\b', 'showEpisodes', line))
        lines = updated_lines

    corrected_lines = []
    in_show_episodes = False
    episode_counter_added = False
    logic_already_added = False

    # Check if the logic is already added in the function
    logic_marker = "# Clean existing S<num> or E<num> from sMovieTitle"
    logic_already_in_file = any(logic_marker in line for line in lines)

    for line in lines:
        stripped_line = line.strip()
        current_indent = get_indentation(line)

        # Detect the start of the function showEpisodes
        if "def showEpisodes" in stripped_line or "showSXE" in stripped_line:
            in_show_episodes = True
            corrected_lines.append(line)
            continue

        # Detect the start of the for loop
        if in_show_episodes and stripped_line.startswith("for "):
            if not episode_counter_added and not logic_already_in_file:
                corrected_lines.append(f"{' ' * current_indent}episode_counter = 1  # Initialize episode counter\n")
                corrected_lines.append(f"{' ' * current_indent}sTitleTemp = ''\n")
                corrected_lines.append(f"{' ' * current_indent}season_number_default = 0\n")
                corrected_lines.append(f"{' ' * current_indent}episode_number_default = 0\n")
                corrected_lines.append(f"{' ' * current_indent}oParser = cParser()\n")

                episode_counter_added = True

        # Reposition logic for `sTitle` validation and formatting before oOutputParameterHandler.addParameter
        if (
            in_show_episodes
            and "oOutputParameterHandler.addParameter('sMovieTitle'," in stripped_line
            and not logic_already_in_file
        ):
            match = re.search(r"oOutputParameterHandler\.addParameter\('sMovieTitle',\s*(\w+)\)", stripped_line)
            if match and not logic_already_added:
                variable_name = match.group(1)
                site_name = 'SITE_NAME'
                sTitle_indent = current_indent

                # Add the new logic before the `oOutputParameterHandler.addParameter` line
                corrected_lines.extend([
                    f"{' ' * sTitle_indent}VSlog(f'{{ {site_name} }}.py title initial: {{ {variable_name} }}')\n",
                    f"{' ' * sTitle_indent}{variable_name} = ''.join(c for c in unicodedata.normalize('NFD', {variable_name}) if unicodedata.category(c) != 'Mn')  # Normalize accents\n",
                    f"{' ' * sTitle_indent}VSlog(f'Normalized {variable_name}: {{ {variable_name} }}')\n",
                    f"{' ' * sTitle_indent}pattern = r\"(Saison|Season|S)\\s*(\\d+)\\s*([Ee]pisode|E)\\s*(\\d+)\"\n",
                    f"{' ' * sTitle_indent}VSlog(f'Pattern set to: {{ pattern }}')\n",
                    f"{' ' * sTitle_indent}{variable_name} = re.sub(pattern, lambda m: f\" S{{m.group(2)}} E{{m.group(4)}}\", {variable_name}, flags=re.IGNORECASE)\n",
                    f"{' ' * sTitle_indent}VSlog(f'Regex replaced {variable_name}: {{ {variable_name} }}')\n",
                    f"{' ' * sTitle_indent}match = re.search(pattern, {variable_name}, flags=re.IGNORECASE)\n",
                    f"{' ' * sTitle_indent}VSlog(f'Match found: {{ match.groups() if match else None }}')\n",
                    f"{' ' * sTitle_indent}if match:\n",
                    f"{' ' * (sTitle_indent + 4)}season_number_default = int(match.group(2))\n",
                    f"{' ' * (sTitle_indent + 4)}episode_number_default = int(match.group(4))\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'Default season: {{ season_number_default }}, episode: {{ episode_number_default }}')\n",
                    f"{' ' * sTitle_indent}if not re.search(r'\\s*S\\d+\\s*E\\d+', {variable_name}):\n",
                    f"{' ' * (sTitle_indent + 4)}# Clean existing S<num> or E<num> from sMovieTitle\n",
                    f"{' ' * (sTitle_indent + 4)}{variable_name} = re.sub(r'(Saison\\s*\\d+|\\s*S\\d+\\s*|[Ee]pisode\\s*\\d+|\\s*E\\d+\\s*)', '', {variable_name}, flags=re.IGNORECASE).strip()\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'Cleaned {variable_name}: {{ {variable_name} }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sSaison = oParser.parse(sUrl, 'saison-(\\d+)')\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'sSaison: {{ sSaison }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sSaison2 = oParser.parse(sUrl, '(\\d+)-saison')\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'sSaison2: {{ sSaison2 }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sEpisode = oParser.parse(sUrl, 'episode-(\\d+)')\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'sEpisode: {{ sEpisode }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sEpisode2 = oParser.parse(sUrl, '(\\d+)-episode')\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'sEpisode2: {{ sEpisode2 }}')\n",
                    f"{' ' * (sTitle_indent + 4)}season_number = -1\n",
                    f"{' ' * (sTitle_indent + 4)}season_number2 = -1\n",
                    f"{' ' * (sTitle_indent + 4)}episode_number = -1\n",
                    f"{' ' * (sTitle_indent + 4)}episode_number2 = -1\n",
                    f"{' ' * (sTitle_indent + 4)}if sSaison and len(sSaison) > 1 and len(sSaison[1]) > 0:\n",
                    f"{' ' * (sTitle_indent + 8)}season_number = int(sSaison[1][0])  # Extract possible season data\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'season_number: {{ season_number }}')\n",
                    f"{' ' * (sTitle_indent + 4)}if sSaison2 and len(sSaison2) > 1 and len(sSaison2[1]) > 0:\n",
                    f"{' ' * (sTitle_indent + 8)}season_number2 = int(sSaison2[1][0])\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'season_number2: {{ season_number2 }}')\n",
                    f"{' ' * (sTitle_indent + 4)}if sEpisode and len(sEpisode) > 1 and len(sEpisode[1]) > 0:\n",
                    f"{' ' * (sTitle_indent + 8)}episode_number = int(sEpisode[1][0])  # Extract possible season data\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'episode_number: {{ episode_number }}')\n",
                    f"{' ' * (sTitle_indent + 4)}if sEpisode2 and len(sEpisode2) > 1 and len(sEpisode2[1]) > 0:\n",
                    f"{' ' * (sTitle_indent + 8)}episode_number2 = int(sEpisode2[1][0])\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'episode_number2: {{ episode_number2 }}')\n",
                    f"{' ' * (sTitle_indent + 4)}if max(season_number, season_number2) >= 0:\n",
                    f"{' ' * (sTitle_indent + 8)}sTitleTemp += ' S' + str(max(season_number, season_number2, season_number_default))\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'Updated sTitleTemp with season: {{ sTitleTemp }}')\n",
                    f"{' ' * (sTitle_indent + 4)}else:\n",
                    f"{' ' * (sTitle_indent + 8)}sTitleTemp += ' S' + str(season_number_default)\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'Fallback season added to sTitleTemp: {{ sTitleTemp }}')\n",
                    f"{' ' * (sTitle_indent + 4)}if max(episode_number, episode_number2) >= 0 and abs(episode_counter - max(episode_number, episode_number2)) < 2:\n",
                    f"{' ' * (sTitle_indent + 8)}sTitleTemp += ' E' + str(max(episode_number, episode_number2, episode_number_default))\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'Updated sTitleTemp with episode: {{ sTitleTemp }}')\n",
                    f"{' ' * (sTitle_indent + 4)}else:\n",
                    f"{' ' * (sTitle_indent + 8)}sTitleTemp += ' E' + str(episode_counter)\n",
                    f"{' ' * (sTitle_indent + 8)}VSlog(f'Fallback episode added to sTitleTemp: {{ sTitleTemp }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sTitle += sTitleTemp\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'Final sTitle: {{ sTitle }}')\n",
                    f"{' ' * (sTitle_indent + 4)}sTitleTemp = ''\n",
                    f"{' ' * (sTitle_indent + 4)}episode_counter += 1  # Increment episode counter\n",
                    f"{' ' * (sTitle_indent + 4)}VSlog(f'Episode counter incremented to: {{ episode_counter }}')\n",
                    f"{' ' * sTitle_indent}VSlog(f'{{ {site_name} }}.py title final: {{ {variable_name} }}')\n"
                ])

                logic_already_added = True

            corrected_lines.append(line)
            continue

        # Detect the end of the function
        if in_show_episodes and stripped_line.startswith("def "):
            in_show_episodes = False
            episode_counter_added = False
            logic_already_added = False

        corrected_lines.append(line)

    # Write the corrected lines back to the file
    with open(file_path, 'w') as file:
        file.writelines(corrected_lines)
        
# Try to import the resource module (works on Unix-like systems)
try:
    import resource
except ImportError:
    resource = None

# Configuration constants
MAX_REPETITION_BOUND = 100
DEFAULT_TIMEOUT = 0.5
MAX_INPUT_LENGTH = 10000  # Maximum length of input sample strings

# Configuration for whitelist/blacklist constructs
BLACKLIST_REGEX_CONSTRUCTS = [
    # Example patterns that are known to be potentially dangerous
    # r'(\w+\s*)+',
    # r'(.+)+'
]
WHITELIST_REGEX_CONSTRUCTS = [
    # For example, you might explicitly allow certain constructs.
    # Currently left empty.
]

######################################
# 2. OS-Level Resource Limits
######################################

def set_resource_limits():
    """
    Set OS-level resource limits for CPU time and memory usage, if possible.
    """
    if resource is not None:
        try:
            # Limit CPU time to 1 second
            resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
            # Limit memory usage to 100MB
            resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
        except Exception as e:
            VSlog(f"Resource limit setting failed: {e}")

######################################
# 7. Whitelist/Blacklist for Regex Constructs
######################################

def is_regex_blacklisted(pattern):
    """
    Check if a regex pattern matches any blacklisted constructs.
    """
    for black in BLACKLIST_REGEX_CONSTRUCTS:
        if re.search(black, pattern):
            return True
    return False

######################################
# 3. Advanced Static Analysis for Regex Vulnerabilities
######################################

def is_vulnerable_regex(pattern):
    """
    Advanced heuristic check for potential catastrophic backtracking.
    Checks for nested quantifiers and blacklisted constructs.
    """
    # Check for nested quantifiers such as (.+)+ or similar patterns.
    if re.search(r'(\(.+?\))\s*[\*\+]\s*[\*\+]', pattern):
        return True
    # Check for multiple adjacent quantifiers
    if re.search(r'[\*\+]{2,}', pattern):
        return True
    # Use blacklist check to catch explicitly dangerous constructs.
    if is_regex_blacklisted(pattern):
        return True
    return False

######################################
# Regex Safety & Equivalence Functions
######################################

def safe_regex_pattern(regex_pattern):
    """
    Rewrites a given regex pattern to avoid infinite loops or excessive backtracking,
    preserving the original semantics when possible.
    """
    try:
        original_pattern = regex_pattern
        safe_pattern = original_pattern

        # If the pattern is blacklisted, skip transformation.
        if is_regex_blacklisted(safe_pattern):
            VSlog("Regex pattern is blacklisted; skipping transformation.")
            return safe_pattern

        # Warn if the regex appears vulnerable.
        if is_vulnerable_regex(safe_pattern):
            VSlog("Warning: Detected potentially vulnerable regex pattern.")

        # Step 1: Replace greedy quantifiers with lazy ones (e.g., .* -> .*?)
        new_pattern = re.sub(r'(\.\*)(?!\?)', r'\1?', safe_pattern)
        if safe_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After replacing greedy quantifiers: {safe_pattern}")

        # Step 2: Replace unbounded repetitions (e.g., .{1,} -> .{1,MAX_REPETITION_BOUND})
        new_pattern = re.sub(r'\.\{(\d+),\}', rf'.{{\1,{MAX_REPETITION_BOUND}}}', safe_pattern)
        if safe_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After replacing unbounded repetitions: {safe_pattern}")

        # Step 3: Simplify nested quantifiers (e.g., (?:...)+ -> (?:...){1,MAX_REPETITION_BOUND})
        new_pattern = re.sub(r'(\(\?:.*?\))\+', rf'\1{{1,{MAX_REPETITION_BOUND}}}', safe_pattern)
        if safe_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After simplifying nested quantifiers: {safe_pattern}")

        # Test equivalence on generated samples
        if not test_equivalence(original_pattern, safe_pattern):
            VSlog("Transformed regex does not behave identically; reverting changes.")
            safe_pattern = original_pattern

        return safe_pattern
    except re.error as regex_error:
        VSlog(f"Regex error: {regex_error}")
        return regex_pattern
    except ValueError as value_error:
        VSlog(f"Value error: {value_error}")
        return regex_pattern
    except Exception as e:
        VSlog(f"Unexpected error: {e}")
        return regex_pattern

def safe_findall(regex, sample, timeout=DEFAULT_TIMEOUT):
    """
    Runs re.findall() in a separate thread with a timeout to avoid hangs.
    Truncates the input sample if it exceeds MAX_INPUT_LENGTH.
    """
    if len(sample) > MAX_INPUT_LENGTH:
        sample = sample[:MAX_INPUT_LENGTH]

    def task():
        try:
            if resource is not None:
                set_resource_limits()
            return re.compile(regex).findall(sample)
        except Exception as e:
            VSlog(f"Error in safe_findall task: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(task)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            VSlog(f"Timeout occurred for regex: {regex} on sample: {sample}")
            return None

def test_equivalence(original, transformed, samples=None, max_dynamic_samples=20):
    """
    Test if two regex patterns produce the same results on sample inputs.
    """
    if samples is None:
        samples = generate_test_samples(original, max_samples=max_dynamic_samples)

    try:
        for sample in samples:
            original_matches = safe_findall(original, sample)
            transformed_matches = safe_findall(transformed, sample)
            if original_matches is None or transformed_matches is None:
                VSlog(f"Skipping sample due to timeout: {repr(sample)}")
                continue
            if original_matches != transformed_matches:
                VSlog(f"Mismatch found for input: {repr(sample)}")
                VSlog(f"Original: {original_matches}, Transformed: {transformed_matches}")
                return False
        return True
    except re.error as regex_error:
        VSlog(f"Regex error during testing: {regex_error}")
        return False
    except Exception as e:
        VSlog(f"Unexpected error during testing: {e}")
        return False

def generate_test_samples(pattern, max_samples=20):
    """
    Generate diverse test cases based on the given regex pattern.
    """
    def random_string(length, char_set=string.ascii_letters + string.digits):
        return ''.join(random.choices(char_set, k=length))

    def generate_from_char_class(char_class):
        # Generate a random string from a char class.
        chars = re.sub(r'\-', '', char_class)
        ranges = re.findall(r'(\w)-(\w)', char_class)
        for start, end in ranges:
            chars += ''.join(chr(c) for c in range(ord(start), ord(end)+1))
        return ''.join(random.choices(chars, k=random.randint(1, 5)))

    def expand_pattern(component):
        test_cases = []
        try:
            if '|' in component:
                for part in component.split('|'):
                    test_cases.extend(expand_pattern(part))
            elif component.startswith('[') and component.endswith(']'):
                char_class = component[1:-1]
                test_cases.append(generate_from_char_class(char_class))
            elif component == '.*':
                test_cases.append(random_string(random.randint(1, 20)))
            elif component.startswith('^') or component.endswith('$'):
                core = component.strip('^$')
                test_cases.append(core + random_string(random.randint(1, 5)))
            else:
                test_cases.append(random_string(random.randint(1, 10)))
        except Exception as e:
            test_cases.append(f"Error generating case: {e}")
        return test_cases

    test_cases = set()
    test_cases.add("")
    try:
        components = re.findall(r'\(.*?\)|\[[^\]]+\]|\.\*|\^.*?\$|[^\|\[\]\(\)\^\$]+', pattern)
        for component in components:
            test_cases.update(expand_pattern(component))
        while len(test_cases) < max_samples:
            test_cases.add(random_string(random.randint(1, 10)))
    except Exception as e:
        test_cases.add(f"Error processing pattern: {e}")

    return list(test_cases)[:max_samples]

def is_valid_regex(pattern):
    """
    Check if a string is a valid regex pattern.
    """
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False

######################################
# AST & Code Transformation Functions
######################################

def check_for_regex_in_function_calls(code):
    """
    Check for regex patterns used in function calls like re.compile() or re.search().
    """
    VSlog("Checking for regex in function calls...")
    regex_patterns = []
    function_calls = re.findall(r'(re\.(compile|match|search|findall|sub))\((.*)\)', code)
    for call in function_calls:
        args = call[2]
        regex_match = re.search(r'\'([^\']+)\'|"([^"]+)"', args)
        if regex_match:
            regex_pattern = regex_match.group(1) or regex_match.group(2)
            if is_valid_regex(regex_pattern):
                regex_patterns.append(regex_pattern)
    VSlog(f"Found regex patterns in function calls: {regex_patterns}")
    return regex_patterns

def find_regex_in_ast(tree):
    """
    Traverse the AST to find regex patterns assigned to variables.
    """
    VSlog("Searching for regex patterns in AST...")
    regex_patterns = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if 'pattern' in target.id.lower() or 'regex' in target.id.lower():
                        if isinstance(node.value, (ast.Str, ast.Constant)):
                            regex_value = node.value.s if hasattr(node.value, 's') else node.value.value
                            if isinstance(regex_value, str) and is_valid_regex(regex_value):
                                regex_patterns.append((regex_value, target.id, node.lineno, node.col_offset))
    VSlog(f"Found regex patterns in AST: {regex_patterns}")
    return regex_patterns

class RegexTransformer(ast.NodeTransformer):
    """
    AST transformer that rewrites regex string literals to safer versions.
    """
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            if any(token in node.value for token in ['\\', '.', '*', '+', '?', '^', '$', '[', ']', '(', ')']):
                if is_valid_regex(node.value):
                    safe_pattern = safe_regex_pattern(node.value)
                    if safe_pattern != node.value:
                        VSlog(f"Transforming regex: {node.value} -> {safe_pattern}")
                        return ast.copy_location(ast.Constant(value=safe_pattern), node)
        return node

    def visit_Str(self, node):
        if is_valid_regex(node.s):
            safe_pattern = safe_regex_pattern(node.s)
            if safe_pattern != node.s:
                VSlog(f"Transforming regex: {node.s} -> {safe_pattern}")
                return ast.copy_location(ast.Str(s=safe_pattern), node)
        return node
        
######################################
# File Rewriting & CLI Handling
######################################

def convert_ast_code(tree):
    """"Helper function to unparse AST using custom Unparser"""
    buffer = StringIO()
    Unparser(tree, file=buffer)
    return buffer.getvalue()

def rewrite_file_to_avoid_regex_infinite_loops(file_path, dry_run=False, backup=False):
    """
    Rewrites the given file to avoid infinite loops in regular expressions.
    Only modifies insecure regex patterns.
    """
    try:
        VSlog(f"Reading file: {file_path}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents = file.read()

        tree = ast.parse(file_contents)
        transformer = RegexTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        if hasattr(ast, "unparse"):
            new_code = ast.unparse(new_tree)
        else:
            VSlog("ast.unparse() not available; using custom unparser.")
            new_code = convert_ast_code(new_tree)

        try:
            compile(new_code, file_path, 'exec')
        except Exception as compile_error:
            VSlog(f"Compilation error after AST transformation: {compile_error}")
            return

        if new_code != file_contents:
            if dry_run:
                diff = difflib.unified_diff(
                    file_contents.splitlines(), new_code.splitlines(),
                    fromfile='original', tofile='modified', lineterm=''
                )
                VSlog("Dry run diff (no changes written):")
                for line in diff:
                    VSlog(line)
            else:
                if backup:
                    backup_file = file_path + ".bak"
                    shutil.copy2(file_path, backup_file)
                    VSlog(f"Backup created at: {backup_file}")
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(new_code)
                VSlog("File rewritten to avoid regex infinite loops and inefficiencies.")
        else:
            VSlog("No changes made to the file.")
    except FileNotFoundError as e:
        VSlog(f"Error: {e}")
    except IOError as e:
        VSlog(f"File IO error: {e}")
    except Exception as e:
        VSlog(f"Unexpected error while modifying file: {e}")

def add_parameter_to_function(file_path, function_name, parameter, after_parameter=None):
    VSlog(f"Starting to add parameter '{parameter}' to function '{function_name}' in file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False

        with open(file_path, 'w', encoding='utf-8') as file:
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith(f"def {function_name}("):
                    # Only modify if the parameter isn't already present
                    if parameter not in line:
                        VSlog(f"Modifying line: {stripped_line}")
                        start_paren_index = line.find('(')
                        closing_paren_index = line.rfind(')')
                        
                        # Fallback if the parenthesis aren't found as expected
                        if start_paren_index == -1 or closing_paren_index == -1:
                            VSlog("Warning: Couldn't parse the function signature correctly. Appending parameter.")
                            line = line.rstrip('\n')[:-1] + f', {parameter})\n'
                        else:
                            # Extract the existing parameters
                            param_list_str = line[start_paren_index+1:closing_paren_index]
                            params = [p.strip() for p in param_list_str.split(',') if p.strip()]
                            
                            if after_parameter and after_parameter in params:
                                # Insert the new parameter right after the specified one
                                index = params.index(after_parameter)
                                params.insert(index + 1, parameter)
                            else:
                                # Append if no after_parameter is provided or it's not found
                                params.append(parameter)
                            
                            # Reassemble the function definition with the new parameter list
                            new_param_list = ', '.join(params)
                            line = line[:start_paren_index+1] + new_param_list + line[closing_paren_index:]
                        modified = True
                file.write(line)

        if modified:
            VSlog(f"Parameter '{parameter}' successfully added to function '{function_name}' in file: {file_path}")
        else:
            VSlog(f"No modifications needed for function '{function_name}' in file: {file_path}")

    except FileNotFoundError:
        VSlog(f"Error: File not found - {file_path}")
    except Exception as e:
        VSlog(f"Error while modifying file '{file_path}': {str(e)}")

def add_parameter_to_function_call(file_path, function_name, parameter):
    VSlog(f"Starting to add parameter '{parameter}' to calls of function '{function_name}' in file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False
        # This regex matches a function call like: function_name( ... )
        # It captures the opening part, the content inside, and the closing parenthesis.
        pattern = re.compile(rf'({function_name}\()\s*(.*?)\s*(\))')

        def replacer(match):
            start, inner, end = match.groups()
            # If the parameter already appears in the call, leave it unchanged.
            if parameter in inner:
                return match.group(0)
            # If there are no existing arguments, simply insert the parameter.
            if inner.strip() == '':
                return f'{start}{parameter}{end}'
            else:
                return f'{start}{inner}, {parameter}{end}'

        with open(file_path, 'w', encoding='utf-8') as file:
            for line in lines:
                # Skip lines that define the function (i.e. lines starting with "def")
                if f'{function_name}(' in line and not line.strip().startswith('def'):
                    new_line = pattern.sub(replacer, line)
                    if new_line != line:
                        VSlog(f"Modifying function call in line: {line.strip()}")
                        line = new_line
                        modified = True
                file.write(line)

        if modified:
            VSlog(f"Parameter '{parameter}' successfully added to calls of function '{function_name}' in file: {file_path}")
        else:
            VSlog(f"No modifications needed for calls of function '{function_name}' in file: {file_path}")

    except FileNotFoundError:
        VSlog(f"Error: File not found - {file_path}")
    except Exception as e:
        VSlog(f"Error while modifying file '{file_path}': {str(e)}")

class AssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments = defaultdict(list)
        self.function_params = defaultdict(dict)  # Store function info

    def visit_Attribute(self, node):
        # Explicitly ignore attribute assignments
        pass

    def visit_FunctionDef(self, node):
        params = {arg.arg for arg in node.args.args}
        start_line = node.lineno
        # Fallback for Python <3.8
        end_line = getattr(node, 'end_lineno', None) or self._estimate_function_end(node)
        self.function_params[start_line] = {
            'params': params,
            'start_line': start_line,
            'end_line': end_line
        }
        self.generic_visit(node)

    def _estimate_function_end(self, node):
        """More reliable function end detection"""
        if node.body:
            last_node = node.body[-1]
            return getattr(last_node, 'end_lineno', last_node.lineno)
        return node.lineno

    def visit_For(self, node):
        self._record_assignment(node.target, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self._record_assignment(node.target, node.lineno)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars:
                self._record_assignment(item.optional_vars, node.lineno)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.assignments[name].append(node.lineno - 1)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.assignments[name].append(node.lineno - 1)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.assignments[node.name].append(node.lineno - 1)
        self.generic_visit(node)

    def visit_Assign(self, node):
        for target in node.targets:
            self._record_assignment(target, node.lineno)
        self.generic_visit(node)

    def _record_assignment(self, node, lineno):
        if isinstance(node, ast.Name):
            self.assignments[node.id].append(lineno - 1)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                self._record_assignment(elt, lineno)
        elif isinstance(node, ast.Starred):
            self._record_assignment(node.value, lineno)

class TransactionalInserter:

    def __init__(self, target_line: str, condition: str, parent_blocks: Optional[List[str]] = None):
        self.original_target = target_line.strip()
        self.condition = condition.strip()
        self.parent_blocks = parent_blocks or []
        self.normalized_target = self._normalize_line(target_line)
        self.valid_changes = []
        self.failed_changes = []
        self.var_status_cache = {}
        self.condition_vars = self._parse_condition_vars()
        self.required_indent = None
        self.line_parents = {}

        # Add these new initializations
        self.assignments = defaultdict(list)

    def _extract_condition_tokenize(self, statement, keywords=("if", "elif", "while", "assert", "for", "except")):
        """
        Extract the condition part from a statement using tokenization.
        It finds the keyword token and collects all tokens until a colon or newline.
        """
        tokens = tokenize.generate_tokens(io.StringIO(statement).readline)
        condition_tokens = []
        capture = False
        for toknum, tokval, _, _, _ in tokens:
            # Check for the starting keyword:
            if not capture and tokval in keywords:
                capture = True
                continue
            if capture:
                # Stop capturing if we hit a colon or newline (end of statement)
                if tokval == ":" or toknum == tokenize.NEWLINE:
                    break
                condition_tokens.append(tokval)
        return " ".join(condition_tokens).strip()

    def _normalize_line(self, line: str) -> str:
        line = re.sub(r'#.*$', '', line)
        line = re.sub(r'\s*=\s*', '=', line)
        line = re.sub(r'\(\s+', '(', line)
        line = re.sub(r'\s+\)', ')', line)
        return line.strip()

    def _parse_condition_vars(self) -> Set[str]:
        """Parse variables from condition with error handling and logging"""
        try:
            bare_condition = self._extract_condition_tokenize(self.condition)
            VSlog(f"Bare condition: {bare_condition}")
            condition_ast = ast.parse(bare_condition, mode='eval').body
            variables = set()
            
            for node in ast.walk(condition_ast):
                if isinstance(node, ast.Name):
                    variables.add(node.id)
                elif isinstance(node, ast.Attribute):
                    # Handle attribute chains like obj.attr.sub
                    attr = node
                    while isinstance(attr, ast.Attribute):
                        attr = attr.value
                    if isinstance(attr, ast.Name):
                        variables.add(attr.id)
            
            VSlog(f"Parsed condition variables: {variables or 'None'}")
            return variables
            
        except SyntaxError as e:
            VSlog(f"❌ Condition syntax error: {e.text.strip()} (line {e.lineno}, col {e.offset})")
            VSlog(f"    {' ' * (e.offset-1)}^")
            return set()
        except Exception as e:
            VSlog(f"❌ Condition parsing failed: {str(e)}")
            return set()

    def _parse_assignments(self, lines: List[str]):
        """Parse variable assignments from provided code lines"""
        code = ''.join(lines)
        try:
            tree = ast.parse(code)
            visitor = AssignmentVisitor()
            visitor.visit(tree)
            self.assignments = visitor.assignments
            self.function_params = visitor.function_params
        except Exception as e:
            VSlog(f"AST parsing error: {e}")
            # Initialize empty structures on error
            self.assignments = defaultdict(list)
            self.function_params = defaultdict(set)

    def _get_line_indent(self, line: str) -> str:
        return re.match(r'^(\s*)', line).group(1)

    def _validate_insertion(self, original_lines: List[str], line_num: int):
        indent = self._get_line_indent(original_lines[line_num])
        next_line_num = line_num + 1
        if next_line_num < len(original_lines):
            next_indent = self._get_line_indent(original_lines[next_line_num])
            if len(next_indent) > len(indent):
                indent_increment = next_indent[len(indent):]
            else:
                # Default to detected indentation (tabs or spaces)
                indent_increment = '\t' if '\t' in indent else '    '
        else:
            indent_increment = '\t' if '\t' in indent else '    '
            # Use indent_increment when inserting the new line

        modified_lines = original_lines.copy()
        modified_lines[line_num] = f"{indent}{self.condition}\n"
        modified_lines.insert(line_num+1, f"{indent}{indent_increment}{original_lines[line_num].lstrip()}")

        expected_indent = indent + indent_increment
        actual_indent = self._get_line_indent(modified_lines[line_num+1])

        try:
            ast.parse(''.join(modified_lines))
            return True, modified_lines
        except IndentationError as e:
            # Enhanced indentation error logging
            error_line = e.lineno  # 1-based line number in modified code
            context_line = modified_lines[error_line-1].rstrip()
            context_start = max(0, error_line-3)
            context_end = min(len(modified_lines), error_line+2)
            
            VSlog(f"❌ INDENTATION ERROR at line {error_line}: {e.msg}")
            VSlog(f"   Actual code state during failure. Problematic line: {context_line}")
            VSlog(f"   {' ' * (e.offset-1)}^")  # Show error position
            for i in range(context_start, context_end):
                prefix = ">>>" if i+1 == error_line else "   "
                line = modified_lines[i].rstrip() if i < len(modified_lines) else ""
                VSlog(f"{i+1:4d} {prefix} {line}")
            VSlog(f"   Expected indent: {len(expected_indent)} spaces")
            VSlog(f"   Current indent: {len(actual_indent)} spaces")
            return False, original_lines
        except SyntaxError as e:
            # Detailed syntax error logging
            error_line = e.lineno  # 1-based line number in modified code
            context_line = modified_lines[error_line-1].rstrip()
            context_start = max(0, error_line-3)
            context_end = min(len(modified_lines), error_line+2)
            
            VSlog(f"❌ SYNTAX ERROR at line {error_line}: {e.msg}")
            VSlog(f"   Actual code state during failure. Problematic line: {context_line}")
            if e.text:  # Show error position if available
                VSlog(f"   {e.text.rstrip()}")
                VSlog(f"   {' ' * (e.offset-1)}^")
            for i in range(context_start, context_end):
                prefix = ">>>" if i+1 == error_line else "   "
                line = modified_lines[i].rstrip() if i < len(modified_lines) else ""
                VSlog(f"{i+1:4d} {prefix} {line}")
            return False, original_lines
        except Exception as e:
            VSlog(f"Validation error: {str(e)}")
            return False, original_lines

    def _check_variables(self, lines: List[str], line_num: int) -> Dict[str, bool]:
        if not self.condition_vars:
            VSlog("⚠️  No variables found in condition")
        var_status = {var: False for var in self.condition_vars}
        try:
            code = ''.join(lines[:line_num + 1])
            table = symtable.symtable(code, "<string>", "exec")
            current_scope = self._find_scope(table, line_num + 1)
            
            for var in self.condition_vars:
                # First check: symtable parameter detection
                try:
                    symbol = current_scope.lookup(var)
                    if symbol.is_parameter():
                        var_status[var] = True
                        continue
                except KeyError:
                    pass
                
                # Second check: AST-based parameter detection
                if self._is_function_parameter(var, line_num):
                    var_status[var] = True
                    continue
                
                # Existing assignment checks
                try:
                    symbol = current_scope.lookup(var)
                    if symbol.is_local():
                        has_prior_assignment = any(
                            ln < line_num for ln in self.assignments.get(var, [])
                        )
                        var_status[var] = has_prior_assignment
                    else:
                        var_status[var] = True
                except KeyError:
                    pass
        except Exception as e:
            VSlog(f"Variable check error: {e}")
        return var_status

    def _parse_ast_hierarchy(self, lines: List[str]) -> None:
        code = ''.join(lines)
        self.line_parents = {}
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        class ParentTracker(ast.NodeVisitor):
            def __init__(self):
                self.stack = []
                self.line_map = {}

            def visit(self, node):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    for line in range(node.lineno - 1, node.end_lineno):
                        if line not in self.line_map:
                            self.line_map[line] = []
                        self.line_map[line] = [self._get_node_name(n) for n in self.stack]
                self.stack.append(node)
                self.generic_visit(node)
                self.stack.pop()

            def _get_node_name(self, node):
                if isinstance(node, ast.FunctionDef):
                    return f"FunctionDef:{node.name}"
                elif isinstance(node, ast.ClassDef):
                    return f"ClassDef:{node.name}"
                elif isinstance(node, ast.For):
                    return "For"
                elif isinstance(node, ast.While):
                    return "While"
                elif isinstance(node, ast.If):
                    return "If"
                elif isinstance(node, ast.With):
                    return "With"
                elif isinstance(node, ast.Try):
                    return "Try"
                return None

        tracker = ParentTracker()
        tracker.visit(tree)
        self.line_parents = tracker.line_map

    def _find_scope(self, table: symtable.SymbolTable, line_num: int) -> symtable.SymbolTable:
        def recurse(scope):
            # Handle scopes without children
            if not scope.get_children():
                if scope.get_lineno() <= line_num:
                    return scope
                return None
                
            # Find child scope that contains the line
            for child in scope.get_children():
                if scope.get_lineno() <= line_num <= child.get_lineno():
                    return recurse(child)
            return scope
            
        return recurse(table) or table  # Fallback to root scope
    
    def _is_function_parameter(self, var: str, line_num: int) -> bool:
        """Enhanced AST-based parameter check"""
        target_line = line_num + 1  # Convert to 1-based
        for func_info in self.function_params.values():
            if func_info['start_line'] <= target_line <= func_info['end_line']:
                if var in func_info['params']:
                    return True
        return False

    def _log_change(self, original_lines: List[str], line_num: int, var_status: Dict[str, bool]):
        context_size = 2
        start = max(0, line_num - context_size)
        end = min(len(original_lines), line_num + context_size + 1)

        VSlog("\n[Before] Context:")
        for i in range(start, end):
            prefix = ">>>" if i == line_num else "   "
            VSlog(f"{i+1:4d} {prefix} {original_lines[i].rstrip()}")

        indent = self._get_line_indent(original_lines[line_num])
        modified_lines = original_lines.copy()
        modified_lines[line_num] = f"{indent}{self.condition}\n"
        modified_lines.insert(line_num+1, f"{indent}    {original_lines[line_num].lstrip()}")

        VSlog("\n[After] Context:")
        mod_start = max(0, line_num - context_size)
        mod_end = min(len(modified_lines), line_num + context_size + 2)
        for i in range(mod_start, mod_end):
            prefix = ">>>" if i in (line_num, line_num+1) else "   "
            line = modified_lines[i].rstrip() if i < len(modified_lines) else ""
            VSlog(f"{i+1:4d} {prefix} {line}")

        VSlog("\nVariable Validation:")
        all_defined = all(var_status.values())
        for var, defined in var_status.items():
            status = "✅ Defined" if defined else "❌ Undefined"
            VSlog(f"  {var.ljust(25)} {status}")
        VSlog("\n🔧 All variables defined - attempting insertion" if all_defined else "\n⛔ Missing variables - skipping")

        # # Detailed definition analysis
        # VSlog("\nVariable Assignment Details:")
        # for var in self.condition_vars:
        #     if var_status[var]:
        #         # Check if it's a function parameter
        #         is_param = self._is_function_parameter(var, line_num)
                
        #         # Get all valid assignments before target line
        #         assignment_lines = [
        #             ln for ln in self.assignments.get(var, [])
        #             if ln < line_num  # Only show assignments before insertion point
        #         ]

        #         # Build reason message
        #         reasons = []
        #         if is_param:
        #             reasons.append("defined as function parameter")
        #         if assignment_lines:
        #             reasons.append(f"assigned at line(s) {[ln+1 for ln in assignment_lines]}")
                
        #         VSlog(f"  ✅ {var}:")
        #         if reasons:
        #             VSlog(f"    └─ Reason: {' + '.join(reasons)}")
                    
        #             # Show code previews for assignments
        #             for ln in assignment_lines:
        #                 if ln < len(original_lines):
        #                     code_line = original_lines[ln].rstrip()
        #                     VSlog(f"        ├─ Line {ln+1}: {code_line}")
        #         else:
        #             VSlog(f"    └─ [UNKNOWN DEFINITION SOURCE]")
        #     else:
        #         VSlog(f"  ❌ {var}: No definition found before line {line_num+1}")

        # VSlog("\n" + ("="*60))
        # VSlog("Validation Result: " + ("✅ All variables defined - proceeding" 
        #                              if all_defined 
        #                              else "⛔ Missing definitions - insertion blocked"))

    def process_file(self, file_path: str, encoding: str = 'utf-8', dry_run: bool = False) -> bool:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                original_lines = f.readlines()
        except Exception as e:
            VSlog(f"❌ File error: {e}")
            return False

        # Add this critical line here ▼
        self._parse_assignments(original_lines)  # ✅ Now has access to actual file content
        self._parse_ast_hierarchy(original_lines)
        backup_path = f"{file_path}.bak"
        shutil.copy2(file_path, backup_path)
        VSlog(f"🔒 Backup created: {backup_path}")

        modified_lines = original_lines.copy()
        changes = []

        for line_num in reversed(range(len(original_lines))):
            line = original_lines[line_num]
            if self.normalized_target not in self._normalize_line(line):
                continue

            if self.parent_blocks:
                current_parents = self.line_parents.get(line_num, [])
                expected_parents = [f"{type_.split(':')[0]}:{name}" for type_, name in (p.split(':', 1) for p in self.parent_blocks)]
                if current_parents != expected_parents:
                    VSlog(f"⛔ Parent blocks mismatch at line {line_num+1}")
                    continue

            VSlog(f"\n{'='*40} Processing line {line_num+1} {'='*40}")
            var_status = self._check_variables(original_lines, line_num)
            self._log_change(original_lines, line_num, var_status)

            if not all(var_status.values()):
                self.failed_changes.append(line_num)
                continue

            valid, temp_modified = self._validate_insertion(modified_lines, line_num)
            if valid:
                changes.append(line_num)
                modified_lines = temp_modified.copy()
                VSlog(f"✅ Validation passed - keeping changes at line {line_num+1}")
            else:
                self.failed_changes.append(line_num)
                modified_lines = modified_lines.copy()
                VSlog(f"⛔ Reverting changes at line {line_num+1}")

        try:
            ast.parse(''.join(modified_lines))
        except Exception as e:
            VSlog(f"❌ Final validation failed: {e}")
            modified_lines = original_lines.copy()

        if dry_run:
            VSlog("\n🔍 Dry run results:")
            VSlog(''.join(modified_lines))
            return True

        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.writelines(modified_lines)
            VSlog(f"✅ Successfully updated {len(changes)} locations")
            if self.failed_changes:
                VSlog(f"⛔ Skipped {len(self.failed_changes)} insertions")
            return True
        except Exception as e:
            VSlog(f"❌ Write failed: {e}")
            shutil.move(backup_path, file_path)
            VSlog("🔙 Restored from backup")
            return False

def add_condition_to_statement(
    file_path: str,
    condition: str,
    target_line: str,
    parent_blocks: Optional[List[str]] = None,
    encoding: str = 'utf-8',
    dry_run: bool = False
) -> bool:
    VSlog(f"\n{'='*40} Insertion Request {'='*40}")
    VSlog(f"File: {file_path}")
    VSlog(f"Condition: {condition}")
    VSlog(f"Target: {target_line}")
    VSlog(f"Parent blocks: {parent_blocks or 'None'}")

    inserter = TransactionalInserter(target_line, condition, parent_blocks)
    return inserter.process_file(file_path, encoding, dry_run)

def add_codeblock_after_block(file_path, block_header, codeblock, insert_after_line=None):
    """
    Searches for a block in the file that starts with `block_header` (e.g., "def addVstreamVoiceControl():"),
    then inserts the provided multi-line `codeblock` after a specified line within that block or (if not provided)
    at the end of the block. The inserted code block is re-indented to match the insertion point, preserving its internal indentation. No changes are
    made if an identical code block (line by line) is already present.
    
    :param file_path: Path to the file to modify.
    :param block_header: A string representing the header of the block (e.g., "def addVstreamVoiceControl():").
    :param codeblock: A multi-line string containing the code block to insert.
    :param insert_after_line: (Optional) A string representing the line within the block after which to insert
                              the code block. If not provided, the code block is added at the end of the block.
    """
    VSlog(f"Starting to add code block after block '{block_header}' in file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        modified = False
        block_found = False
        i = 0

        while i < len(lines):
            line = lines[i]
            new_lines.append(line)

            # Look for the block header
            if not block_found and line.strip() == block_header.strip():
                block_found = True
                header_indent = len(line) - len(line.lstrip())
                insertion_done = False
                i += 1

                # Process the block's body (lines indented more than the header)
                while i < len(lines):
                    next_line = lines[i]
                    # Add blank lines without special processing.
                    if next_line.strip() == "":
                        new_lines.append(next_line)
                        i += 1
                        continue

                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent > header_indent:
                        # Within the block.
                        if (insert_after_line is not None and not insertion_done and 
                            next_line.strip() == insert_after_line.strip()):
                            # Found the specified insertion line.
                            new_lines.append(next_line)
                            i += 1
                            insertion_indent = next_indent
                            # Format the code block to be inserted with the insertion line's indent.
                            formatted_codeblock_lines = []
                            for cb_line in codeblock.splitlines():
                                if not cb_line.strip():
                                    formatted_codeblock_lines.append("\n")
                                else:
                                    formatted_codeblock_lines.append(" " * insertion_indent + cb_line + "\n")
                            
                            # Check if the code block is already present immediately after.
                            already_present = True
                            for j, fcbl in enumerate(formatted_codeblock_lines):
                                if i + j >= len(lines) or lines[i + j].rstrip("\n") != fcbl.rstrip("\n"):
                                    already_present = False
                                    break
                            
                            if already_present:
                                VSlog("Code block already present after the specified insertion line; skipping insertion.")
                                i += len(formatted_codeblock_lines)
                            else:
                                new_lines.extend(formatted_codeblock_lines)
                                VSlog("Inserted code block after the specified insertion line.")
                                modified = True
                            insertion_done = True
                        else:
                            new_lines.append(next_line)
                            i += 1
                    else:
                        # End of the block reached.
                        break

                # If no insertion line was provided or it wasn't found, insert at the end of the block.
                if (insert_after_line is None or not insertion_done):
                    # Use a typical indent level for block bodies.
                    insertion_indent = header_indent + 4
                    formatted_codeblock_lines = []
                    for cb_line in codeblock.splitlines():
                        if not cb_line.strip():
                            formatted_codeblock_lines.append("\n")
                        else:
                            formatted_codeblock_lines.append(" " * insertion_indent + cb_line + "\n")
                    
                    # Check if the code block is already present.
                    already_present = True
                    for j, fcbl in enumerate(formatted_codeblock_lines):
                        if i + j >= len(lines) or lines[i + j].rstrip("\n") != fcbl.rstrip("\n"):
                            already_present = False
                            break
                    if already_present:
                        VSlog("Code block already present at the end of the block; skipping insertion.")
                        i += len(formatted_codeblock_lines)
                    else:
                        new_lines.extend(formatted_codeblock_lines)
                        VSlog("Inserted code block at the end of the block.")
                        modified = True
                continue  # Continue processing the rest of the file after handling the block
            i += 1

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            VSlog(f"File updated successfully with new code block after '{block_header}'.")
        else:
            VSlog("No modifications made to file.")

    except FileNotFoundError:
        VSlog(f"Error: File not found - {file_path}")
    except Exception as e:
        VSlog(f"Error while modifying file '{file_path}': {str(e)}")

def ping_server(server: str, timeout=10, retries=1, backoff_factor=2, verify_ssl=True):
    """
    Ping server to check if it's reachable, with retry mechanism and optional SSL verification.

    Args:
        server (str): Server URL to ping.
        timeout (int): Timeout for each request in seconds.
        retries (int): Number of retry attempts on failure.
        backoff_factor (int): Exponential backoff multiplier for retry delays.
        verify_ssl (bool): Whether to verify SSL certificates. Default is True.
        
    Returns:
        bool: True if the server is reachable, False otherwise.
    """
    if not server.startswith(("http://", "https://")):
        server = "https://" + server

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(server, headers=headers, timeout=timeout, verify=verify_ssl)
            if response.status_code == 200:
                VSlog(f"Ping succeeded for {server}. Status code: {response.status_code}")
                return True
            else:
                VSlog(f"Ping failed for {server}. Status code: {response.status_code}")
                return False
        except SSLError as ssl_error:
            if verify_ssl:
                VSlog(f"Ping failed for {server}. SSL Error: {ssl_error}")
                return ping_server(server, timeout, retries, backoff_factor, False)  # SSL errors are critical if SSL verification is enabled
            else:
                VSlog(f"Ping attempt {attempt} failed for {server}. Ignoring SSL Error due to verify_ssl=False.")
        except RequestException as error:
            VSlog(f"Ping attempt {attempt} failed for {server}. Error: {error}")

            if attempt < retries:
                delay = backoff_factor * (2 ** (attempt - 1))
                VSlog(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                VSlog(f"All {retries} attempts failed for {server}.")
                return False

def cloudflare_protected(url):
    """Check if a URL is protected by Cloudflare."""
    VSlog(f"Checking if {url} is Cloudflare protected.")
    try:
        response = requests.get(url)
        content = response.text
        target_position = content.find("Checking if the")
        if target_position != -1:
            VSlog(f"Cloudflare protection detected for {url}.")
            return True
        else:
            VSlog(f"No Cloudflare protection detected for {url}.")
            return False
    except requests.RequestException as e:
        VSlog(f"Error while checking Cloudflare protection for {url}: {e}")
        return False

def is_using_cloudflare(url):
    """Check if a URL uses Cloudflare based on HTTP headers."""
    VSlog(f"Checking Cloudflare headers for {url}.")
    try:
        response = requests.get(url)
        headers = response.headers
        cloudflare_headers = ['server', 'cf-ray', 'cf-cache-status', 'cf-request-id']
        for header in cloudflare_headers:
            if header in headers and 'cloudflare' in headers[header].lower():
                VSlog(f"Cloudflare header detected: {header}={headers[header]}.")
                return True
        VSlog(f"No Cloudflare headers detected for {url}.")
        return False
    except requests.RequestException as e:
        VSlog(f"Error while checking headers for {url}: {e}")
        return False

def set_wiflix_url(url):
    """Set a new URL for Wiflix in the sites.json file."""
    VSlog(f"Setting new Wiflix URL to {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\','/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if 'wiflix' in data['sites']:
            data['sites']['wiflix']['url'] = url
            data['sites']['wiflix']['cloudflare'] = "False" if not is_using_cloudflare(url) else "True"
            with open(sites_json, 'w') as fichier:
                json.dump(data, fichier, indent=4)
            VSlog(f"Wiflix URL updated successfully in {sites_json}.")
        else:
            VSlog("Wiflix entry not found in sites.json.")
    except Exception as e:
        VSlog(f"Error while updating Wiflix URL: {e}")

def get_wiflix_url():
    """Retrieve the Wiflix URL from its website."""
    VSlog("Retrieving Wiflix URL from its website.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\','/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if 'wiflix' in data['sites']:
            site_info_new_address = data['sites']['wiflix']['site_info']

        response = requests.get(site_info_new_address)
        html_content = response.text

        # Rechercher l'URL dans l'attribut onclick
        match = re.search(r"window\.location\.href='(.*?)'", html_content)

        # Extraire et afficher l'URL si elle existe
        if match:
            url = match.group(1).replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"Wiflix URL found: {url}")
            return url
        VSlog("No web addresses found..")
        return None
    except requests.RequestException as e:
        VSlog(f"Error while retrieving Wiflix URL: {e}")
        return None
        
def get_frenchstream_url():
    """Retrieve the FrenchStream URL from its website."""
    VSlog("Retrieving FrenchStream URL from its website.")
    try:
        response = requests.get("https://fstream.one/")
        content = response.text
        target_position_string = "https://"
        target_position = content.find(target_position_string)
        if target_position == -1:
            VSlog(f"Target position '{target_position_string}' not found in the response.")
            return None
        content_before_target = content[target_position:]
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content_before_target)
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"FrenchStream URL found: {url}")
            return url
        VSlog("No web addresses found after 'Stream est :'.")
        return None
    except requests.RequestException as e:
        VSlog(f"Error while retrieving FrenchStream URL: {e}")
        return None

def set_frenchstream_url(url):
    """Set a new URL for FrenchStream in the sites.json file."""
    VSlog(f"Setting new FrenchStream URL to {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if 'french_stream_lol' in data['sites']:
            data['sites']['french_stream_lol']['url'] = url
            data['sites']['french_stream_lol']['cloudflare'] = "False" if not is_using_cloudflare(url) else "True"
            with open(sites_json, 'w') as fichier:
                json.dump(data, fichier, indent=4)
            VSlog("FrenchStream URL updated successfully.")
        else:
            VSlog("FrenchStream entry not found in sites.json.")
    except Exception as e:
        VSlog(f"Error while updating FrenchStream URL: {e}")

def activate_site(site_name, active_value="True"):
    """Activate a site in the sites.json file using the given active_value (default "True")."""
    VSlog(f"Activating site: {site_name} with active value: {active_value}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if site_name in data['sites']:
            data['sites'][site_name]['active'] = active_value
            with open(sites_json, 'w') as fichier:
                json.dump(data, fichier, indent=4)
            VSlog(f"Site {site_name} activated successfully.")
    except Exception as e:
        VSlog(f"Error while activating site {site_name}: {e}")

def ajouter_papadustream():
    """Add the PapaDuStream site to sites.json and create papadustream.py if not present."""
    VSlog("Starting the process to add PapaDuStream.")
    
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    papadustream_py = VSPath('special://home/addons/plugin.video.vstream/resources/sites/papadustream.py').replace('\\', '/')

    VSlog(f"Paths resolved - sites_json: {sites_json}, papadustream_py: {papadustream_py}")

    try:
        # Load sites.json
        VSlog("Attempting to read sites.json...")
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
            VSlog(f"Successfully loaded sites.json. Current sites: {list(data.get('sites', {}).keys())}")

        # Check if PapaDuStream already exists
        if "papadustream" not in data.get('sites', {}):
            VSlog("PapaDuStream not found in sites.json, proceeding to add it.")
            
            # Get PapaDuStream URL
            url = get_papadustream_url()
            VSlog(f"Retrieved PapaDuStream URL: {url}")

            if url:
                # Add PapaDuStream to sites.json
                new_site = {
                    "label": "PapaDuStream",
                    "active": "True",
                    "url": url
                }
                data['sites']['papadustream'] = new_site
                VSlog("Updated sites.json with PapaDuStream data.")

                with open(sites_json, 'w') as fichier:
                    json.dump(data, fichier, indent=4)
                VSlog("Saved updated sites.json successfully.")
            else:
                VSlog("Failed to retrieve PapaDuStream URL. Aborting addition to sites.json.")
        else:
            VSlog("PapaDuStream already exists in sites.json. Skipping addition.")

        # Check if papadustream.py exists
        VSlog("Checking if papadustream.py exists...")
        if not os.path.exists(papadustream_py):
            VSlog("papadustream.py not found. Creating file...")
            with open(papadustream_py, 'w', encoding='utf-8') as fichier:
                script_content = """# -*- coding: utf-8 -*-
# vStream https://github.com/Kodi-vStream/venom-xbmc-addons.
import re
import datetime
import time

from resources.lib.gui.hoster import cHosterGui
from resources.lib.gui.gui import cGui
from resources.lib.handler.inputParameterHandler import cInputParameterHandler
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.parser import cParser
from resources.lib.comaddon import progress, siteManager
from resources.lib.util import cUtil

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0'
headers = {'User-Agent': UA}

SITE_IDENTIFIER = 'papadustream'
SITE_NAME = 'PapaDuStream'
SITE_DESC = 'S\u00e9ries en streaming'

URL_MAIN = siteManager().getUrlMain(SITE_IDENTIFIER)

SERIE_NEWS = (URL_MAIN + 'categorie-series/', 'showSeries')
SERIE_GENRES = (True, 'showSerieGenres')
SERIE_ANNEES = (URL_MAIN, 'showSerieYears')
SERIE_VOSTFRS = (URL_MAIN + 'categorie-series/series-vostfr/', 'showSeries')

URL_SEARCH = (URL_MAIN + 'index.php?do=search', 'showSeries')
URL_SEARCH_SERIES = ('', 'showSeries')

MY_SEARCH_SERIES = (True, 'showSearch')

SERIE_SERIES = (True, 'showMenuTvShows')

def load():
    showMenuTvShows()

def showMenuTvShows():
    oGui = cGui()

    oOutputParameterHandler = cOutputParameterHandler()
    oOutputParameterHandler.addParameter('siteUrl', MY_SEARCH_SERIES[0])
    oGui.addDir(SITE_IDENTIFIER, MY_SEARCH_SERIES[1], 'Recherche S\u00e9ries ', 'search.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', SERIE_NEWS[0])
    oGui.addDir(SITE_IDENTIFIER, SERIE_NEWS[1], 'S\u00e9ries (Derniers ajouts)', 'news.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', SERIE_GENRES[0])
    oGui.addDir(SITE_IDENTIFIER, SERIE_GENRES[1], 'S\u00e9ries (Genres)', 'genres.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', SERIE_ANNEES[0])
    oGui.addDir(SITE_IDENTIFIER, SERIE_ANNEES[1], 'S\u00e9ries (Ann\u00e9es)', 'annees.png', oOutputParameterHandler)

    oOutputParameterHandler.addParameter('siteUrl', SERIE_VOSTFRS[0])
    oGui.addDir(SITE_IDENTIFIER, SERIE_VOSTFRS[1], 'S\u00e9ries (VOSTFR)', 'vostfr.png', oOutputParameterHandler)

    oGui.setEndOfDirectory()

def showSearch():
    oGui = cGui()
    sSearchText = oGui.showKeyBoard()
    if sSearchText:
        sUrl = sSearchText
        showSeries(sUrl)
        oGui.setEndOfDirectory()
        return

def showSerieGenres():
    oGui = cGui()
    listeGenre = [['Action', 'action-s'], ['Animation', 'animation-s'], ['Aventure', 'aventure-s'],
                  ['Biopic', 'biopic-s'], ['Com\u00e9die', 'comedie-s'], ['Documentaire', 'documentaire-s'],
                  ['Drame', 'drame-s'], ['Famille', 'famille-s'], ['Fantastique', 'fantastique-s'],
                  ['Guerre', 'guerre-s'], ['Historique', 'historique-s'], ['Horreur', 'horreur-s'],
                  ['Judiciaire', 'judiciare-s'], ['Musique', 'musical-s'], ['Policier', 'policier-s'],
                  ['Romance', 'romance-s'], ['Science-Fiction', 'science-fiction-s'], ['Thriller', 'thriller-s'],
                  ['western', 'western-s']]

    oOutputParameterHandler = cOutputParameterHandler()
    for sTitle, sUrl in listeGenre:
        oOutputParameterHandler.addParameter('siteUrl', URL_MAIN.rstrip('/') + '/categorie-series/' + sUrl + '/')
        oGui.addDir(SITE_IDENTIFIER, 'showSeries', sTitle, 'genres.png', oOutputParameterHandler)

    oGui.setEndOfDirectory()

def showSerieYears():
    oGui = cGui()
    oOutputParameterHandler = cOutputParameterHandler()
    for i in reversed(range(1930, int(datetime.datetime.now().year) + 1)):
        sYear = str(i)
        oOutputParameterHandler.addParameter('siteUrl', URL_MAIN.rstrip('/') + '/categorie-series/annee/' + sYear + '/' )
        oOutputParameterHandler.addParameter('sYear', sYear)
        oGui.addDir(SITE_IDENTIFIER, 'showSeries', sYear, 'annees.png', oOutputParameterHandler)

    oGui.setEndOfDirectory()

def __checkForNextPage(sHtmlContent):
    oParser = cParser()
    sPattern = r'navigation.+?<span>\\d+</span>.+?<a href="([^"]+).+?>([^<]+)</a>'
    aResult = oParser.parse(sHtmlContent, sPattern)
    if aResult[0]:
        sNextPage = aResult[1][0][0]
        sNumberMax = aResult[1][0][1]
        sNumberNext = re.search('page/([0-9]+)', sNextPage).group(1)
        sPaging = sNumberNext + '/' + sNumberMax
        return sNextPage, sPaging

    return False, 'none'

def showSeries(sSearch=''):
    oGui = cGui()
    oParser = cParser()

    if sSearch:
        pdata = 'do=search&subaction=search&search_start=0&full_search=0&result_from=1&story=' + sSearch
        oRequest = cRequestHandler(URL_SEARCH[0])
        oRequest.setRequestType(1)
        oRequest.addHeaderEntry('Referer', URL_MAIN)
        oRequest.addHeaderEntry('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        oRequest.addHeaderEntry('Accept-Language', 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3')
        oRequest.addHeaderEntry('Content-Type', 'application/x-www-form-urlencoded')
        oRequest.addParametersLine(pdata)
        sHtmlContent = oRequest.request()

    else:
        oInputParameterHandler = cInputParameterHandler()
        sUrl = oInputParameterHandler.getValue('siteUrl')
        oRequestHandler = cRequestHandler(sUrl)
        sHtmlContent = oRequestHandler.request()

    # thumb url title
    sPattern = r'class="short_img.+?img_box.+?with_mask.+?href="([^"]+)".+?title="([^"]+).+?img src="([^"]+)'
    aResult = oParser.parse(sHtmlContent, sPattern)

    if aResult[0]:
        total = len(aResult[1])
        progress_ = progress().VScreate(SITE_NAME)
        oOutputParameterHandler = cOutputParameterHandler()
        for aEntry in aResult[1]:
            progress_.VSupdate(progress_, total)
            if progress_.iscanceled():
                break

            sUrl2 = aEntry[0]
            sThumb = aEntry[2]
            if 'http' not in sThumb:
                sThumb = URL_MAIN[:-1] + sThumb
            sTitle = aEntry[1]

            if sSearch:
                if not cUtil.CheckOccurence(sSearchText, sTitle):
                    continue  # Filtre de recherche

            sDisplayTitle = sTitle

            oOutputParameterHandler.addParameter('siteUrl', sUrl2)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sThumb', sThumb)

            oGui.addTV(SITE_IDENTIFIER, 'showSaisons', sDisplayTitle, '', sThumb, '', oOutputParameterHandler)

        progress_.VSclose(progress_)

    else:
        oGui.addText(SITE_IDENTIFIER)

    if not sSearch:
        sNextPage, sPaging = __checkForNextPage(sHtmlContent)
        if sNextPage:
            oOutputParameterHandler = cOutputParameterHandler()
            oOutputParameterHandler.addParameter('siteUrl', sNextPage)
            oGui.addNext(SITE_IDENTIFIER, 'showSeries', 'Page ' + sPaging, oOutputParameterHandler)

        oGui.setEndOfDirectory()

def showSaisons():
    oGui = cGui()
    oParser = cParser()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')

    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()

    sPattern = r'property="og:description".+?content="([^"]+)'
    aResult = oParser.parse(sHtmlContent, sPattern)
    sDesc = ''
    if aResult[0]:
        sDesc = ('[I][COLOR grey]%s[/COLOR][/I] %s') % ('Synopsis : ', aResult[1][0])

    sPattern = 'class="th-hover" href="([^"]+).+?alt=".+?saison ([^"]+).+?([^<]*)'
    aResult = oParser.parse(sHtmlContent, sPattern)

    if aResult[0]:
        oOutputParameterHandler = cOutputParameterHandler()
        for aEntry in reversed(aResult[1]):

            sUrl2 = aEntry[0]
            sSaison = aEntry[1]  # SAISON 2
            sThumb = aEntry[2]
            if 'http' not in sThumb:
                sThumb = URL_MAIN[:-1] + sThumb
            sTitle = ("%s S%s") % (sMovieTitle, sSaison)

            oOutputParameterHandler.addParameter('siteUrl', sUrl2)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('sDesc', sDesc)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)

            oGui.addSeason(SITE_IDENTIFIER, 'showEpisodes', sTitle, '', sThumb, sDesc, oOutputParameterHandler)

    else:
        oGui.addText(SITE_IDENTIFIER)

    oGui.setEndOfDirectory()


def showEpisodes():
    oGui = cGui()
    oParser = cParser()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sDesc = oInputParameterHandler.getValue('sDesc')
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()

        
    sStart = 'class="saisontab'
    sEnd = 'class="clear'
    sHtmlContent = oParser.abParse(sHtmlContent, sStart, sEnd)

    sPattern = r'<a href="([^"]+)".+?\u00e9pisode (\\d+)'
    aResult = oParser.parse(sHtmlContent, sPattern)

    if aResult[0]:
        oOutputParameterHandler = cOutputParameterHandler()
        for aEntry in aResult[1]:
            sUrl2 = aEntry[0]
            sEpisode = aEntry[1].replace('\u00e9', 'e').strip() # episode 2
            if 'http' not in sUrl2:
                sUrl2 = URL_MAIN[:-1] + sUrl2
            sTitle = '%s E%s' % (sMovieTitle, sEpisode)

            oOutputParameterHandler.addParameter('siteUrl', sUrl2)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sDesc', sDesc)

            oGui.addEpisode(SITE_IDENTIFIER, 'showHostersEpisode', sTitle, '', sThumb, sDesc, oOutputParameterHandler)

    else:
        oGui.addText(SITE_IDENTIFIER)

    oGui.setEndOfDirectory()

def showHostersEpisode():
    oGui = cGui()
    oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    sDesc = oInputParameterHandler.getValue('sDesc')

    oParser = cParser()
    oRequestHandler = cRequestHandler(sUrl)
    sHtmlContent = oRequestHandler.request()
    cook = oRequestHandler.GetCookies()

    sStart = '<ul class="player-list">'
    sEnd = '<div class="clearfix"></div>'
    sHtmlContent = oParser.abParse(sHtmlContent, sStart, sEnd)
    sPattern = r"class=\\"lien.+?getxfield\\(this, '([^']+)', '([^']+)', '([^']+)"
    aResult = oParser.parse(sHtmlContent, sPattern)
    
    dle_login_hash = '728f50a3c1a0d285442fbb76a04e52351fc22cb3';
    
    if aResult[0]:
        oOutputParameterHandler = cOutputParameterHandler()
        for aEntry in aResult[1]:
            videoId = aEntry[0]
            xfield = aEntry[1]
            token = aEntry[2]
            hosterName = sLang = ''
            if ('_') in xfield:
                hosterName, sLang = xfield.strip().split('_')
                sLang = sLang.upper()

                oHoster = cHosterGui().checkHoster(hosterName)
                if not oHoster:
                    continue

            sUrl2 = URL_MAIN + 'engine/ajax/controller.php?mod=getxfield&id=' + videoId + '&xfield=' + xfield + '&g_recaptcha_response=' + token + '&user_hash=' + dle_login_hash

            sDisplayTitle = ('%s (%s) [COLOR coral]%s[/COLOR]') % (sTitle, sLang, hosterName)         

            oOutputParameterHandler.addParameter('siteUrl', sUrl2)
            oOutputParameterHandler.addParameter('sMovieTitle', sTitle)
            oOutputParameterHandler.addParameter('sDesc', sDesc)
            oOutputParameterHandler.addParameter('sThumb', sThumb)
            oOutputParameterHandler.addParameter('referer', sUrl)
            oOutputParameterHandler.addParameter('cook', cook)
            oOutputParameterHandler.addParameter('sHost', hosterName)
            oOutputParameterHandler.addParameter('sLang', sLang)

            oGui.addLink(SITE_IDENTIFIER, 'showHosters', sDisplayTitle, sThumb, sDesc, oOutputParameterHandler)

    oGui.setEndOfDirectory()

def showHosters(oInputParameterHandler = False):
    oGui = cGui()
    if not oInputParameterHandler:
        oInputParameterHandler = cInputParameterHandler()
    sUrl = oInputParameterHandler.getValue('siteUrl')
    sMovieTitle = oInputParameterHandler.getValue('sMovieTitle')
    sThumb = oInputParameterHandler.getValue('sThumb')
    referer = oInputParameterHandler.getValue('referer')
    cook = oInputParameterHandler.getValue('cook')

    oRequest = cRequestHandler(sUrl)
    oRequest.addHeaderEntry('Referer', referer)
    if cook:
        oRequest.addHeaderEntry('Cookie', cook)
    sHtmlContent = oRequest.request()

    oParser = cParser()
    sPattern = r'<iframe src=\\"([^\\"]+)'
    aResult = oParser.parse(sHtmlContent, sPattern)

    if aResult[0]:
        sHosterUrl = aResult[1][0]
        oHoster = cHosterGui().checkHoster(sHosterUrl)
        if oHoster:
            oHoster.setDisplayName(sMovieTitle)
            oHoster.setFileName(sMovieTitle)
            cHosterGui().showHoster(oGui, oHoster, sHosterUrl, sThumb, oInputParameterHandler=oInputParameterHandler)

    oGui.setEndOfDirectory()"""
                fichier.write(script_content)
                VSlog(f"Created papadustream.py with the required content at: {papadustream_py}.")
        else:
            VSlog(f"papadustream.py already exists at: {papadustream_py}. Skipping file creation.")
    except Exception as e:
        VSlog(f"An error occurred: {str(e)}")

def get_papadustream_url():
    """Retrieve the PapaDuStream URL from its website."""
    VSlog("Retrieving PapaDuStream URL from its website.")
    try:
        response = requests.get("https://www.astuces-aide-informatique.info/22553/papadustream")
        content = response.text
        target_position = content.find("Papa Du Stream à ce jour :")
        if target_position == -1:
            VSlog("Target position 'Papa Du Stream à ce jour :' not found in the response.")
            return None
        content_after_target = content[target_position:]
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content_after_target)
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"PapaDuStream URL found: {url}")
            return url
        VSlog("No web addresses found after 'Papa Du Stream à ce jour :'.")
        return None
    except requests.RequestException as e:
        VSlog(f"Error while retrieving PapaDuStream URL: {e}")
        return None
    
def set_papadustream_url(url):
    """Set a new URL for PapaDuStream in the sites.json file."""
    VSlog(f"Setting new PapaDuStream URL to {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    
    try:
        # Load the JSON file
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        
        # Ensure the 'papadustream' entry exists
        if 'papadustream' not in data['sites']:
            VSlog("PapaDuStream entry not found. Adding it.")
            ajouter_papadustream()
            with open(sites_json, 'r') as fichier:
                data = json.load(fichier)  # Reload data after modification
        
        # Update the URL and cloudflare status
        if 'papadustream' in data['sites']:
            data['sites']['papadustream']['url'] = url
            cloudflare_status = is_using_cloudflare(url)
            data['sites']['papadustream']['cloudflare'] = "False" if not cloudflare_status else "True"
            VSlog(f"Updated PapaDuStream URL to {url} with Cloudflare status: {'Enabled' if cloudflare_status else 'Disabled'}.")
        else:
            VSlog("Failed to find or add the PapaDuStream entry.")
            return
        
        # Save changes to the JSON file
        with open(sites_json, 'w') as fichier:
            json.dump(data, fichier, indent=4)
        VSlog("PapaDuStream URL updated successfully.")
    
    except Exception as e:
        VSlog(f"Error while setting PapaDuStream URL: {e}")

def get_darkiworld_url():
    """Retrieve the Darkiworld URL from its website."""
    VSlog("Retrieving Darkiworld URL from its website.")
    try:
        response = requests.get("https://www.julsa.fr/darkiworld-la-nouvelle-adresse-url-pour-acceder-au-site/")
        content = response.text
        target_position = content.find("Darkiworld, rendez-vous sur")
        if target_position == -1:
            VSlog("Target position 'Darkiworld, rendez-vous sur' not found in the response.")
            return None
        content_after_target = content[target_position:]
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content_after_target) 
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https")
            VSlog(f"Darkiworld URL found: {url}")
            return url
        VSlog("No web addresses found after 'Darkiworld'.")
        return None
    except requests.RequestException as e:
        VSlog(f"Error while retrieving Darkiworld URL: {e}")
        return None
        
def set_darkiworld_url(url):
    """Set a new URL for Darkworld in the sites.json file."""
    VSlog(f"Setting new Darkiworld URL to {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    
    try:
        # Load the JSON file
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        
        # Update the URL and cloudflare status
        if 'darkiworld' in data['sites']:
            data['sites']['darkiworld']['url'] = url
            cloudflare_status = is_using_cloudflare(url)
            data['sites']['darkiworld']['cloudflare'] = "False" if not cloudflare_status else "True"
            VSlog(f"Updated Darkiworld URL to {url} with Cloudflare status: {'Enabled' if cloudflare_status else 'Disabled'}.")
        else:
            VSlog("Failed to find the Darkiworld entry.")
            return
        
        # Save changes to the JSON file
        with open(sites_json, 'w') as fichier:
            json.dump(data, fichier, indent=4)
        VSlog("Darkiworld URL updated successfully.")
    
    except Exception as e:
        VSlog(f"Error while setting Darkiworld URL: {e}")

def get_elitegol_url():
    """Retrieve EliteGol URL with content validation and fallback to saved URL."""
    VSlog("Starting EliteGol URL retrieval process")
    
    CONFIG_FILE = VSPath('special://home/addons/service.vstreamupdate/site_config.ini').replace('\\', '/')

    default_url = 'https://jokertv.ru/'

    def save_valid_url(url):
        try:
            config = configparser.ConfigParser()
            config["elitegol"] = {"current_url": url}
            with open(CONFIG_FILE, "w") as configfile:
                config.write(configfile)
        except Exception as e:
            VSlog(f"Cannot save valid url: {str(e)}")
    
    def load_and_validate_url():

        VSlog("load_and_validate_url()")

        try:
            config = configparser.ConfigParser()
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
                if "elitegol" in config and "current_url" in config["elitegol"]:
                    saved_url = config["elitegol"]["current_url"]
                    if validate_url_content(saved_url):
                        return saved_url
                else:
                    return default_url
        except FileNotFoundError:
            VSlog("No saved URL file found")
            return default_url
        except Exception as e:
            VSlog(f"URL load error: {str(e)}")
            return default_url
    
    def validate_url_content(url):
        try:
            response = requests.get(url, timeout=15)
            return 'match' in response.text.lower()
        except Exception as e:
            VSlog(f"Content validation failed for {url}: {str(e)}")
            return False
    
    current_valid_url = None
    
    try:
        # First source: fulldeals.fr
        try:
            response = requests.get("https://fulldeals.fr/streamonsport/", timeout=10)
            content = response.text
            target_pos = content.find("<strong>la vraie adresse")
            
            if target_pos != -1:
                section = content[target_pos:]
                urls = re.findall(r'href="(https?://[^"]+)"', section)
                if urls:
                    raw_url = urls[0]
                    processed_url = raw_url.replace("http", "https").replace("httpss", "https").rstrip('/') + '/'
                    VSlog(f"Found fulldeals URL candidate: {processed_url}")
                    if validate_url_content(processed_url):
                        current_valid_url = processed_url
        except Exception as e:
            VSlog(f"fulldeals processing error: {str(e)}")
        
        # Second source: lefoot.ru (only if first failed)
        if not current_valid_url:
            try:
                response = requests.get("https://lefoot.ru/", timeout=10)
                content = response.text
                urls = re.findall(r'href="(https?://[^"]+)"', content)
                if urls:
                    raw_url = urls[0]
                    processed_url = raw_url.replace("http", "https").replace("httpss", "https").rstrip('/') + '/'
                    VSlog(f"Found lefoot URL candidate: {processed_url}")
                    if validate_url_content(processed_url):
                        current_valid_url = processed_url
            except Exception as e:
                VSlog(f"lefoot processing error: {str(e)}")
        
        # Save and return if found new valid URL
        if current_valid_url:
            save_valid_url(current_valid_url)
            return current_valid_url
        
        # Fallback to saved URL
        saved_url = load_and_validate_url()
        if saved_url:
            VSlog("Using validated fallback URL")
            return saved_url
        
        VSlog("No valid URLs found in current check or saved file")
        return None

    except Exception as e:
        VSlog(f"Critical error: {str(e)}")
        default_url = load_and_validate_default_url()
        return default_url if default_url else None
    
def set_elitegol_url(url):
    """Set a new URL for EliteGol in the sites.json file."""
    VSlog(f"Setting new EliteGol URL to {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    
    try:
        # Load the JSON file
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        
        # Update the URL and cloudflare status
        if 'elitegol' in data['sites']:
            data['sites']['elitegol']['url'] = url
            cloudflare_status = is_using_cloudflare(url)
            data['sites']['elitegol']['cloudflare'] = "False" if not cloudflare_status else "True"
            VSlog(f"Updated EliteGol URL to {url} with Cloudflare status: {'Enabled' if cloudflare_status else 'Disabled'}.")
        else:
            VSlog("Failed to find or add the EliteGol entry.")
            return
        
        # Save changes to the JSON file
        with open(sites_json, 'w') as fichier:
            json.dump(data, fichier, indent=4)
        VSlog("EliteGol URL updated successfully.")
    
    except Exception as e:
        VSlog(f"Error while setting EliteGol URL: {e}")
        
def get_livetv_url():
    """Retrieve LiveTV URL with content validation using several means.
    Only a valid final (redirected) URL is saved to the config file when detected.
    The default URL is used only as a last resort.
    """
    VSlog("Starting LiveTV URL retrieval process")
    
    CONFIG_FILE = VSPath('special://home/addons/service.vstreamupdate/site_config.ini').replace('\\', '/')
    default_url = "https://livetv.sx/frx/"
    bypass_url = "https://livetv774.me"
    
    def save_valid_url(url):
        try:
            config = configparser.ConfigParser()
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
            if "livetv" not in config:
                config["livetv"] = {}
            config["livetv"]["current_url"] = url
            with open(CONFIG_FILE, "w") as configfile:
                config.write(configfile)
            VSlog(f"URL saved successfully: {url}")
        except Exception as e:
            VSlog(f"Cannot save valid URL: {str(e)}")
    
    def load_and_validate_url():
        """Attempt to load a URL from config and validate it.
        Returns the effective URL if valid, otherwise None.
        """
        VSlog("load_and_validate_url()")
        try:
            config = configparser.ConfigParser()
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
                if "livetv" in config and "current_url" in config["livetv"]:
                    saved_url = config["livetv"]["current_url"]
                    effective_url = validate_url_content(saved_url)
                    if effective_url:
                        return effective_url
        except Exception as e:
            VSlog(f"URL load error: {str(e)}")
        return None
    
    def validate_url_content(url):
        """Check if the URL's content contains the keyword 'matchs'.
        Returns the final effective URL (after redirection) if valid, or None.
        """
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            effective_url = response.url  # Final URL after any redirects
            if "matchs" in response.text.lower():
                if effective_url != url:
                    VSlog(f"Redirection detected: {url} -> {effective_url}")
                return effective_url
            else:
                VSlog(f"Content validation failed for {url}: keyword 'matchs' not found")
                return None
        except Exception as e:
            VSlog(f"Content validation failed for {url}: {str(e)}")
            return None

    current_valid_url = None

    # Candidate 0: Try the URL saved in the json file.
    if not current_valid_url:
        sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    
        try:
            # Load the JSON file
            with open(sites_json, 'r') as fichier:
                data = json.load(fichier)

            if 'livetv' in data['sites']:
                effective_url = data['sites']['livetv']['url']
                if effective_url:
                    VSlog(f"sites.json saved URL is valid: {effective_url}")
                    save_valid_url(effective_url)
                    current_valid_url = effective_url   

    # Candidate 1: Try the URL saved in the config file.
    if not current_valid_url:
        effective_url = load_and_validate_url()
        if effective_url:
            VSlog(f"Saved URL is valid: {effective_url}")
            save_valid_url(effective_url)
            current_valid_url = effective_url

    # Candidate 2: Try the bypass URL.
    if not current_valid_url:
        effective_url = validate_url_content(bypass_url)
        if effective_url:
            VSlog(f"Bypass URL is valid: {effective_url}")
            save_valid_url(effective_url)
            current_valid_url = effective_url

    # Candidate 3: Try to extract URL from an external source.
    if not current_valid_url:
        try:
            response = requests.get(
                "https://top-infos.com/live-tv-sx-nouvelle-adresse/",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    )
                },
                timeout=10
            )
            content = response.text
            target_position = content.find("LiveTV est accessible via")
            if target_position != -1:
                content_after_target = content[target_position:]
                web_addresses = re.findall(
                    r'https?://[\w\.-]+(?:\.[\w\.-]+)+(?::\d+)?(?:/[\w\.-]*)*(?:\?[\w&=.-]*)?(?:#[\w.-]*)?',
                    content_after_target
                )
                if web_addresses:
                    # Prefer the second match if it contains "livetv"
                    if len(web_addresses) > 1 and "livetv" in web_addresses[1]:
                        candidate_url = web_addresses[1].replace("httpss", "https").rstrip('/') + '/'
                    else:
                        candidate_url = web_addresses[0].replace("httpss", "https").rstrip('/') + '/'
                    VSlog(f"Candidate URL found from external source: {candidate_url}")
                    effective_url = validate_url_content(candidate_url)
                    if effective_url:
                        VSlog(f"External candidate URL is valid: {effective_url}")
                        save_valid_url(effective_url)
                        current_valid_url = effective_url
        except Exception as e:
            VSlog(f"Error retrieving URL from external source: {str(e)}")
    
    # Candidate 4: Last resort, use the default URL.
    if not current_valid_url:
        effective_url = validate_url_content(default_url)
        if effective_url:
            VSlog(f"Default URL is valid: {effective_url}")
            save_valid_url(effective_url)
            current_valid_url = effective_url
        else:
            current_valid_url = default_url
            VSlog("Default URL failed content validation, returning as fallback")
    
    return current_valid_url

def set_livetv_url(url):
    """Met à jour l'URL de LiveTV dans le fichier sites.json."""
    VSlog(f"Mise à jour de l'URL de LiveTV vers {url}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        
        if 'livetv' in data['sites']:
            data['sites']['livetv']['url'] = url
            cloudflare_status = is_using_cloudflare(url)
            data['sites']['livetv']['cloudflare'] = "False" if not cloudflare_status else "True"
            VSlog(f"URL de LiveTV mise à jour : {url}, Cloudflare : {'Activé' if cloudflare_status else 'Désactivé'}.")
        else:
            VSlog("Entrée LiveTV non trouvée dans sites.json.")
            return
        
        with open(sites_json, 'w') as fichier:
            json.dump(data, fichier, indent=4)
        VSlog("Mise à jour réussie de l'URL de LiveTV.")
    except Exception as e:
        VSlog(f"Erreur lors de la mise à jour de l'URL de LiveTV : {e}")

# Thread lock to ensure thread-safe file access
file_lock = threading.Lock()

def check_all_sites():
    """Check the status of all sites in parallel and update their 'active' state in sites.json."""
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')

    try:
        with file_lock:
            with open(sites_json, 'r') as fichier:
                data = json.load(fichier)

        # Validate the structure of the loaded JSON data
        if 'sites' not in data or not isinstance(data['sites'], dict):
            VSlog("Invalid JSON structure: 'sites' key is missing or is not a dictionary.")
            return

        sites_to_check = list(data['sites'].keys())

        # Limit the number of threads with max_workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(lambda site: check_site(site, data), sites_to_check)

        # Write all updates to the file at once
        with file_lock:
            with open(sites_json, 'w') as fichier:
                json.dump(data, fichier, indent=4)

    except Exception as e:
        VSlog(f"Error while checking all sites: {e}")

def check_site(site_name, data):
    """Check the status of a site and update its 'active' state in the data structure."""
    VSlog(f"Checking status of site: {site_name}.")

    try:
        if site_name in data['sites']:
            site_url = data['sites'][site_name].get('url')
            if not site_url:
                VSlog(f"Site {site_name} is missing a 'url' key.")
                return

            is_active = ping_server(site_url) and not cloudflare_protected(site_url)
            data['sites'][site_name]['active'] = "True" if is_active else "False"

            VSlog(f"Site {site_name} status updated to {'active' if is_active else 'inactive'}.")

    except Exception as e:
        VSlog(f"Error while checking site {site_name}: {e}")

def edit_live_file():
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/sites/livetv.py').replace('\\', '/')
    
    try:
        # Read the file contents
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        VSlog(f"Error reading file: {e}")
        return

    # Check if the file already includes .replace('frx/', '')
    if ".replace('frx/', '')" in content:
        VSlog("The file is already modified.")
        return

    # Replace the target string with the appended .replace('frx/', '')
    new_content = content.replace(
        "siteManager().getUrlMain(SITE_IDENTIFIER)",
        "siteManager().getUrlMain(SITE_IDENTIFIER).replace('frx/', '')"
    )

    try:
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        VSlog("File modified successfully.")
    except Exception as e:
        VSlog(f"Error writing file: {e}")
        
def create_recommendation_files_to_watch():
    # paths of files
    films_path = VSPath('special://home/addons/plugin.video.vstream/resources/20filmslesplusrecents.json').replace('\\', '/')
    series_path = VSPath('special://home/addons/plugin.video.vstream/resources/20serieslesplusrecents.json').replace('\\', '/')

    def get_movies_examples():
        return [
            {
                "title": "Dune : Deuxième Partie",
                "year": 2024,
                "imdb_id": "tt15239678",
                "genre": "Science-Fiction",
                "description": "Suite de l'adaptation du roman de Frank Herbert. Paul Atreides mène une rébellion dans le désert aride de la planète Dune.",
                "poster": "https://exemple.com/posters/dune2.jpg",
                "rating": 8.7,
                "added": datetime.now().isoformat()
            },
            {
                "title": "Oppenheimer",
                "year": 2023,
                "imdb_id": "tt15398776",
                "genre": "Biopic/Historique",
                "description": "L'histoire du père de la bombe atomique et des dilemmes moraux de cette découverte.",
                "poster": "https://exemple.com/posters/oppenheimer.jpg",
                "rating": 8.4,
                "added": datetime.now().isoformat()
            }
        ]

    def get_series_examples():
        return [
            {
                "title": "Stranger Things Saison 5",
                "year": 2024,
                "imdb_id": "tt4574334",
                "genre": "Horreur/Fantastique",
                "description": "Dernière saison de la série culte se déroulant à Hawkins. Les héros affrontent le Néant une dernière fois.",
                "poster": "https://exemple.com/posters/st5.jpg",
                "seasons": 5,
                "episodes": 45,
                "added": datetime.now().isoformat()
            },
            {
                "title": "Loki Saison 2",
                "year": 2023,
                "imdb_id": "tt9140554",
                "genre": "Super-héros/Science-Fiction",
                "description": "Suite des aventures du dieu de la malice à travers le multivers.",
                "poster": "https://exemple.com/posters/loki2.jpg",
                "seasons": 2,
                "episodes": 12,
                "added": datetime.now().isoformat()
            }
        ]

    def initialise_file(chemin, donnees):
        repertoire = os.path.dirname(chemin)
        if not os.path.exists(repertoire):
            os.makedirs(repertoire, exist_ok=True)
        
        if not os.path.exists(chemin):
            with open(chemin, 'w', encoding='utf-8') as f:
                json.dump(donnees, f, indent=4, ensure_ascii=False)

    # Initialisation of the movies
    initialise_file(
        films_path,
        get_movies_examples()
    )

    # Initialisation of the tv shows
    initialise_file(
        series_path,
        get_series_examples()
    )

# def save_watched_recommendations_to_json():
#     oDb = cDb()
#     ADDON = addon()
#     recommendations = {}

#     try:
#         # Get all watched content (movies + shows)
#         watched_content = oDb.get_catWatched('1', limit=None) + oDb.get_catWatched('4', limit=None)
        
#         # Create set of all watched TMDB IDs (integer format)
#         watched_ids = {int(item['tmdb_id']) for item in watched_content}

#         for item in watched_content:
#             title = item['title']
#             tmdb_id = item['tmdb_id']
#             media_type = 'movie' if item['cat'] == 1 else 'tv'

#             # Get recommendations
#             if media_type == 'movie':
#                 data = self.get_recommandations_by_id_movie(tmdb_id)
#             else:
#                 data = self.get_recommandations_by_id_tv(tmdb_id)

#             if data.get('results'):
#                 date_field = 'release_date' if media_type == 'movie' else 'first_air_date'
                
#                 # Filter recommendations
#                 filtered = [
#                     rec for rec in data['results']
#                     if all([
#                         rec.get('id') not in watched_ids,  # Exclude watched items
#                         rec.get(date_field),  # Require valid date
#                         not rec.get('adult', False)  # Optional: exclude adult content
#                     ])
#                 ]

#                 # Sort and limit
#                 sorted_recs = sorted(
#                     filtered,
#                     key=lambda x: x[date_field],
#                     reverse=True
#                 )[:10]

#                 if sorted_recs:
#                     recommendations[title] = {
#                         'tmdb_id': tmdb_id,
#                         'type': media_type,
#                         'recommendations': sorted_recs
#                     }

#         # Save to JSON
#         filename = f"recommendations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
#         profile_path = ADDON.getAddonInfo('profile')
#         file_path = os.path.join(profile_path, filename)

#         with open(file_path, 'w', encoding='utf-8') as f:
#             json.dump(recommendations, f, indent=4, ensure_ascii=False)

#         return file_path

#     except Exception as e:
#         print(f"Recommendation export error: {str(e)}")
#         return None
#     finally:
#         del oDb

class cUpdate:

    def getUpdateSetting(self):
        """Handles update settings and site checks."""
        VSlog("update.py: Starting update settings procedure.")

        try:            
            # Update URLs for sites
            VSlog("Updating site URLs.")
            set_wiflix_url(get_wiflix_url())
            set_frenchstream_url(get_frenchstream_url())
            set_papadustream_url(get_papadustream_url())
            set_elitegol_url(get_elitegol_url())
            set_livetv_url(get_livetv_url())
            set_darkiworld_url(get_darkiworld_url())

            check_all_sites()

            activate_site("channelstream", "False")

            # Add new site if necessary
            VSlog("Adding PapaDuStream if not present.")
            ajouter_papadustream()

            create_recommendation_files_to_watch()

            # Modify files as required
            VSlog("Modifying necessary files.")
            modify_files()

            insert_update_service_addon()

            addVstreamVoiceControl()
            
        except Exception as e:
            VSlog(f"An error occurred during update settings: {e}")
