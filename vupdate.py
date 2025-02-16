# -*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons

import datetime, time
import xbmc
import xbmcvfs
import shutil
import os
import traceback
import json
import requests
import re
import ast
import socket
import textwrap
import difflib
import random
import string
from string import Template
import glob
import concurrent.futures
import threading
import xml.etree.ElementTree as ET

from requests.exceptions import RequestException, SSLError
from resources.lib import logger
from resources.lib.logger import VSlog, VSPath

from io import StringIO

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
            f"{method_indent}    updated_flag_path = os.path.join(addon_path, \"updatededededededededededed\")\n",
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
            return
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

def modify_files():
    VSlog("Starting file modification process")

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
                    f"{' ' * sTitle_indent}{variable_name} = re.sub(pattern, lambda m: f\" S{{m.group(2)}} E{{m.group(3)}}\", {variable_name}, flags=re.IGNORECASE)\n",
                    f"{' ' * sTitle_indent}VSlog(f'Regex replaced {variable_name}: {{ {variable_name} }}')\n",
                    f"{' ' * sTitle_indent}match = re.search(pattern, {variable_name}, flags=re.IGNORECASE)\n",
                    f"{' ' * sTitle_indent}VSlog(f'Match found: {{ match.groups() if match else None }}')\n",
                    f"{' ' * sTitle_indent}if match:\n",
                    f"{' ' * (sTitle_indent + 4)}season_number_default = int(match.group(2))\n",
                    f"{' ' * (sTitle_indent + 4)}episode_number_default = int(match.group(3))\n",
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

def add_parameter_to_function(file_path, function_name, parameter):
    VSlog(f"Starting to add parameter '{parameter}' to function '{function_name}' in file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified = False

        with open(file_path, 'w', encoding='utf-8') as file:
            for line in lines:
                if line.strip().startswith(f'def {function_name}('):
                    if parameter not in line:
                        VSlog(f"Modifying line: {line.strip()}")
                        # Find the position of the closing parenthesis
                        closing_paren_index = line.rfind(')')
                        # Insert the new parameter before the closing parenthesis
                        line = line[:closing_paren_index] + f', {parameter}' + line[closing_paren_index:]
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
    try:
        response = requests.get("http://www.wiflix.name")
        content = response.text
        target_position = content.find("NOS SITES")
        if target_position == -1:
            VSlog("Target position 'NOS SITES' not found in the response.")
            return None
        content_before_target = content[target_position:]
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content_before_target)
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"Wiflix URL found: {url}")
            return url
        VSlog("No web addresses found after 'NOS SITES'.")
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
                if not oUtil.CheckOccurence(sSearchText, sTitle):
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

def get_elitegol_url():
    """Retrieve the EliteGol URL from its website."""
    VSlog("Retrieving EliteGol URL from its website.")
    try:
        response = requests.get("https://fulldeals.fr/streamonsport/")
        content = response.text
        target_position = content.find("<strong>la vraie adresse")
        if target_position == -1:
            VSlog("Target position '<strong>la vraie adresse' not found in the response.")
            return None
        content_after_target = content[target_position:]
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content_after_target) 
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"EliteGol URL found: {url}")
            return url

        response = requests.get("https://lefoot.ru/")
        content = response.text
        web_addresses = re.findall('href="(https?://[\\w.-]+(?:\\.[\\w\\.-]+)+(?:/[\\w\\.-]*)*)', content)
        if web_addresses:
            url = web_addresses[0].replace("http", "https").replace("httpss", "https") + "/"
            VSlog(f"EliteGol URL found: {url}")
            return url
        VSlog("No web addresses found after 'EliteGol'.")
        return None
    except requests.RequestException as e:
        VSlog(f"Error while retrieving EliteGol URL: {e}")
        return None
    
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

def get_livetv_url():
    current_url = "https://livetv819.me"
    bypass_url = "https://livetv774.me"
    default_url = "https://livetv.sx/frx/"
    url = ""

    def good_live_tv_url(test_url):
        nonlocal current_url  # so we can update current_url if needed
        try:
            final_response = requests.get(
                test_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/91.0.4472.124 Safari/537.36"
                },
                timeout=10,
                allow_redirects=True
            )
        except requests.RequestException as e:
            VSlog(f"Erreur lors de la requête: {e}")
            return False

        effective_url = final_response.url  # URL after redirects
        content = final_response.text

        # Check if the keyword "Matchs" exists in the response content
        if content.find("Matchs") == -1:
            VSlog("Url non trouvée.")
            return False
        else:
            # If we're testing current_url and it got redirected, update it.
            if test_url == current_url and effective_url != test_url:
                VSlog(f"Redirection détectée: {test_url} -> {effective_url}")
                current_url = effective_url
            VSlog(f"Url trouvée: {effective_url}")
            return True

    VSlog("Récupération de l'URL de LiveTV.")

    try:
        if good_live_tv_url(default_url):
            return default_url

        if good_live_tv_url(current_url):
            return current_url

        if good_live_tv_url(bypass_url):
            return bypass_url

        response = requests.get(
            "https://top-infos.com/live-tv-sx-nouvelle-adresse/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/91.0.4472.124 Safari/537.36"
            },
            timeout=10
        )

        content = response.text
        target_position = content.find("LiveTV est accessible via")

        if target_position == -1:
            VSlog("Texte clé non trouvé dans la page.")
        else:
            content_after_target = content[target_position:]
            web_addresses = re.findall(
                r'https?://[\w.-]+(?:\.[\w.-]+)+(?::\d+)?(?:/[\w.-]*)*(?:\?[\w&=.-]*)?(?:#[\w.-]*)?',
                content_after_target
            )

            if web_addresses:
                # Prefer the second match if it contains "livetv"
                if len(web_addresses) > 1 and "livetv" in web_addresses[1]:
                    url = web_addresses[1].replace("httpss", "https") + "/"
                else:
                    url = web_addresses[0].replace("httpss", "https") + "/"

                if not url.startswith("http"):
                    url = "https://" + url
                VSlog(f"URL de LiveTV trouvée : {url}")

                if good_live_tv_url(url):
                    return url
            else:
                VSlog("Aucune adresse trouvée après le texte clé.")

        return default_url
    except requests.RequestException as e:
        VSlog(f"Erreur lors de la récupération de l'URL de LiveTV : {e}")
        return default_url

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

            # Modify files as required
            VSlog("Modifying necessary files.")
            modify_files()

            insert_update_service_addon()
            
        except Exception as e:
            VSlog(f"An error occurred during update settings: {e}")
