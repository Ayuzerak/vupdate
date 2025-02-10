# -*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons

import datetime, time
import xbmc
import xbmcvfs
import shutil
import os

import json
import requests
import re

import ast
import socket
import textwrap

import random
import string
import glob
import concurrent.futures
import threading
import xml.etree.ElementTree as ET

from requests.exceptions import RequestException, SSLError
from resources.lib import logger
from resources.lib.logger import VSlog, VSPath

def update_service_addon():
    # URL du fichier zip
    sUrl = "https://raw.githubusercontent.com/Ayuzerak/vupdate/refs/heads/main/service.vstreamupdate.zip"
    
    # Résolution du répertoire des add-ons via le chemin spécial Kodi
    addons_dir = VSPath('special://home/addons/')
    if not os.path.exists(addons_dir):
        print("Le répertoire des add-ons n'existe pas :", addons_dir)
        return

    # Définition des chemins pour l'addon et sa sauvegarde
    addon_name = "service.vstreamupdate"
    backup_name = "_service.vstreamupdate"
    addon_path = os.path.join(addons_dir, addon_name)
    backup_path = os.path.join(addons_dir, backup_name)
    
    # Vérification si la mise à jour a déjà été effectuée en cherchant le fichier 'updated'
    updated_flag_path = os.path.join(addon_path, "updateded")
    if os.path.exists(updated_flag_path):
        print("La mise à jour a déjà été effectuée. Aucune action supplémentaire n'est nécessaire.")
        return

    zip_file_path = os.path.join(addons_dir, addon_name + ".zip")

    # Étape 1. Téléchargement du fichier zip dans le dossier des add-ons.
    print("Téléchargement du fichier zip depuis :", sUrl)
    try:
        response = requests.get(sUrl, stream=True)
        response.raise_for_status()  # Lève une erreur pour les codes d'état incorrects
        with open(zip_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print("Téléchargement terminé :", zip_file_path)
    except Exception as e:
        print("Erreur lors du téléchargement du fichier :", e)
        return

    # Vérification que le fichier téléchargé est une archive zip valide.
    if not zipfile.is_zipfile(zip_file_path):
        print("Le fichier téléchargé n'est pas une archive zip valide.")
        os.remove(zip_file_path)
        return

    # Étape 2. Sauvegarde du dossier addon existant, s'il existe.
    if os.path.exists(addon_path):
        # Suppression d'un éventuel dossier de sauvegarde précédent
        if os.path.exists(backup_path):
            try:
                shutil.rmtree(backup_path)
                print("Ancien backup supprimé :", backup_path)
            except Exception as e:
                print("Impossible de supprimer l'ancien backup :", e)
                return
        try:
            # Déplacement du dossier addon existant vers le dossier de backup
            shutil.move(addon_path, backup_path)
            print("Backup créé :", backup_path)
        except Exception as e:
            print("Erreur lors de la création du backup :", e)
            return
    else:
        print("Aucun addon existant à sauvegarder.")

    # (Optionnel) S'assurer qu'aucun dossier résiduel ne subsiste.
    if os.path.exists(addon_path):
        try:
            shutil.rmtree(addon_path)
            print("Dossier addon résiduel supprimé :", addon_path)
        except Exception as e:
            print("Erreur lors de la suppression du dossier addon résiduel :", e)
            return

    # Étape 3. Extraction du fichier zip téléchargé dans le dossier des add-ons.
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(addons_dir)
        print("Extraction terminée vers :", addons_dir)
    except Exception as e:
        print("Erreur lors de l'extraction :", e)
        # Restauration du backup en cas d'échec de l'extraction.
        if os.path.exists(backup_path):
            shutil.move(backup_path, addon_path)
            print("Backup restauré depuis :", backup_path)
        os.remove(zip_file_path)
        return

    # Suppression du fichier zip téléchargé après extraction.
    os.remove(zip_file_path)

    # Étape 4. Vérification que le dossier extrait contient addon.xml.
    addon_xml = os.path.join(addon_path, "addon.xml")
    if os.path.exists(addon_xml):
        print("Mise à jour réussie. addon.xml trouvé dans :", addon_path)
        
        # Création du fichier 'updated' pour indiquer que la mise à jour a été effectuée.
        try:
            with open(updated_flag_path, 'w') as f:
                f.write("Mise à jour effectuée le " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            print("Fichier 'updated' créé dans :", addon_path)
        except Exception as e:
            print("Erreur lors de la création du fichier 'updated' :", e)
        
        # Optionnel : suppression du backup maintenant que la mise à jour est confirmée.
        if os.path.exists(backup_path):
            try:
                shutil.rmtree(backup_path)
                print("Dossier backup supprimé :", backup_path)
            except Exception as e:
                print("Erreur lors de la suppression du dossier backup :", e)
    else:
        print("addon.xml introuvable dans le dossier extrait. Annulation de la mise à jour...")
        # Suppression du nouveau dossier défectueux
        if os.path.exists(addon_path):
            shutil.rmtree(addon_path)
        # Restauration du backup
        if os.path.exists(backup_path):
            shutil.move(backup_path, addon_path)
            print("Backup restauré dans :", addon_path)
        else:
            print("Aucun backup disponible pour restauration!")
        return
        
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


def add_netflix_like_recommandations():
    add_is_recommandations_for_netflix_like_recommandations()
    because_num, recommendations_num = add_translations_to_file_for_netflix_like_recommandations()
    modify_get_catWatched_for_netflix_like_recommandations()
    add_recommendations_for_netflix_like_recommandations(recommendations_num)
    create_recommandations_file_for_netflix_like_recommandations(because_num)
    add_get_recommendations_method_for_netflix_like_recommandations()

def add_is_recommandations_for_netflix_like_recommandations():
    """
    Vérifie et ajoute les définitions de `isRecommandations` :
    - Comme méthode dans la classe `main` si elle est absente.
    - Comme fonction libre en dehors de toute classe si elle est absente.
    """
    # Chemin vers le fichier default.py
    file_path = VSPath('special://home/addons/plugin.video.vstream/default.py').replace('\\', '/')

    # Contenu de la méthode `isRecommandations` à ajouter dans la classe `main`
    method_content = """
    def isRecommandations(self, sSiteName, sFunction):
        return
    """

    # Contenu de la fonction libre `isRecommandations` à ajouter
    function_content = """
def isRecommandations(sSiteName, sFunction): 
    if sSiteName == 'cRecommandations':
        print("HEHEHEHEHEHEHEHEHEHE COUCOU (fonction libre)")

        plugins = __import__('resources.lib.recommandations', fromlist=['cRecommandations']).cRecommandations()
        function = getattr(plugins, sFunction)
        function()
        return True
    return False
"""

    # Vérifier si le fichier default.py existe
    if not os.path.exists(file_path):
        VSlog(f"Fichier introuvable : {file_path}")
        return

    # Lire le contenu actuel du fichier
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Vérifier la présence de la classe main
    if not re.search(r"class main\s*:", content):
        VSlog("La classe `main` est introuvable dans le fichier.")
        return

    # Vérifier si la méthode isRecommandations existe dans la classe main
    if not re.search(r"class main.*?def isRecommandations\(.*\):", content, re.DOTALL):
        # Ajouter la méthode dans la classe `main`
        content = re.sub(
            r"(class main\s*:\s*)\n",
            rf"\1{method_content}\n",
            content,
            count=1,
            flags=re.DOTALL
        )
        VSlog("La méthode `isRecommandations` a été ajoutée à la classe `main`.")

    else:
        VSlog("La méthode `isRecommandations` existe déjà dans la classe `main`.")

    # Vérifier si une fonction libre `isRecommandations` existe déjà
    if not re.search(r"^def isRecommandations\(.*\):", content, re.MULTILINE):
        # Ajouter la fonction libre à la fin du fichier
        content += function_content
        VSlog("La fonction libre `isRecommandations` a été ajoutée.")

    else:
        VSlog("La fonction libre `isRecommandations` existe déjà.")

    # Écrire les modifications dans le fichier
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    VSlog(f"Les modifications ont été appliquées à {file_path}.")

def add_translations_to_file_for_netflix_like_recommandations():
    # Example usage
    file_path = VSPath('special://home/userdata/guisettings.xml').replace("\\", "/")
    language_setting = get_setting_value_from_file(file_path, "locale.language")
    (because_num_fr_fr, recommendations_num_fr_fr) = add_translations_to_fr_fr_po_file_for_netflix_like_recommandations()
    (because_num_fr_ca, recommendations_num_fr_ca) = add_translations_to_fr_ca_po_file_for_netflix_like_recommandations()
    (because_num_en_gb, recommendations_num_en_gb) = add_translations_to_en_gb_po_file_for_netflix_like_recommandations()
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

def add_translations_to_fr_fr_po_file_for_netflix_like_recommandations():
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/language/resource.language.fr_fr/strings.po').replace('\\', '/')

    my_recommendations_num = None
    because_num = None

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        existing_translations = {
            "Because you watched": {"translated": "Parce que vous avez regardé", "msgctxt_num": None},
            "My Recommendations": {"translated": "Mes Recommandations", "msgctxt_num": None}
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
        VSlog(f"Erreur dans fr_fr: {str(e)}")
        return 0

def add_translations_to_fr_ca_po_file_for_netflix_like_recommandations():
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
            "My Recommendations": {"translated": "Mes Recommandations", "msgctxt_num": None}
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

def add_translations_to_en_gb_po_file_for_netflix_like_recommandations():
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
        VSlog(f"Erreur dans en_gb: {str(e)}")
        return 0

def modify_get_catWatched_for_netflix_like_recommandations():
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

def add_recommendations_for_netflix_like_recommandations(recommendations_num):
    """
    Adds recommendation blocks for Netflix-like recommendations in the methods `showMovies` and `showSeries`
    in `home.py` after `# Nouveautés` or before `# Populaires`, scoped to each method.
    """
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/home.py').replace('\\', '/')

    # Code blocks to insert
    movies_recommendations_code = f"""
        #Recommandations
        oOutputParameterHandler.addParameter('siteUrl', 'movies/recommandations')
        oGui.addDir('cRecommandations', 'showMoviesRecommandations', self.addons.VSlang({recommendations_num}), 'listes.png', oOutputParameterHandler)
"""
    series_recommendations_code = f"""
        #Recommandations
        oOutputParameterHandler.addParameter('siteUrl', 'shows/recommandations')
        oGui.addDir('cRecommandations', 'showShowsRecommandations', self.addons.VSlang({recommendations_num}), 'listes.png', oOutputParameterHandler)
"""

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        VSlog(f"File not found: {file_path}")
        return

    updated_content = content

    # Helper function to check and insert recommendations
    def process_method(method_name, recommendation_code, marker_name):
        nonlocal updated_content
        # Regex to find the method body
        method_pattern = re.compile(rf"(def {method_name}\(self\):)(\s+.*?)(?=\n\s*def|\Z)", re.DOTALL)
        match = method_pattern.search(updated_content)
        if not match:
            VSlog(f"{method_name} method not found.")
            return

        method_header = match.group(1)
        method_body = match.group(2)
        full_method = match.group(0)

        # Check if recommendation already exists in this method
        if "movies/recommandations" in method_body or "shows/recommandations" in method_body:
            VSlog(f"Recommendations already exist in {method_name}.")
            return

        # Find insertion point
        if "# Nouveautés" in method_body:
            insertion_point = "# Nouveautés"
            new_body = method_body.replace(insertion_point, insertion_point + recommendation_code, 1)
        elif "# Populaires" in method_body:
            insertion_point = "# Populaires"
            new_body = method_body.replace(insertion_point, recommendation_code + insertion_point, 1)
        else:
            VSlog(f"Markers not found in {method_name}.")
            return

        new_method = method_header + new_body
        updated_content = updated_content.replace(full_method, new_method, 1)
        VSlog(f"Added recommendations to {method_name}.")

    # Process showMovies for movies recommendations
    process_method("showMovies", movies_recommendations_code, "movies")

    # Process showSeries for series recommendations
    process_method("showSeries", series_recommendations_code, "series")

    # Write changes if modified
    if updated_content != content:
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            VSlog(f"Successfully updated {file_path}.")
        except Exception as e:
            VSlog(f"Error writing file: {str(e)}")
    else:
        VSlog("No changes needed.")

def create_recommandations_file_for_netflix_like_recommandations(because_num):
    """
    Vérifie si le fichier recommandations.py existe dans le chemin cible.
    S'il n'existe pas, le fichier est créé avec le contenu prédéfini.
    """

    VSlog("create_recommandations_file_for_netflix_like_recommandations()")

    # Chemin vers le répertoire cible
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/recommandations.py').replace('\\', '/')

    try:
        # Vérification de l'existence du fichier
        if not os.path.exists(file_path):
            VSlog(f"Fichier {file_path} non trouvé. Création en cours.")

            # Contenu prédéfini pour recommandations.py
            file_content = f"""from resources.lib.comaddon import dialog, addon, VSlog
from resources.lib.gui.gui import cGui
from resources.lib.handler.outputParameterHandler import cOutputParameterHandler
from resources.lib.db import cDb
from resources.sites.themoviedb_org import SITE_IDENTIFIER as SITE_TMDB

SITE_IDENTIFIER = 'cRecommandations'
SITE_NAME = 'Recommandations'

class cRecommandations:
    DIALOG = dialog()
    ADDON = addon()

    def showRecommandations(self, category, content_type, icon):
        \"""
        Generic method to fetch and display recommendations.

        :param category: The category ID for the type of content ('1' for movies, '4' for shows).
        :param content_type: The type of content ('showMovies' or 'showSeries').
        :param icon: The icon file to use ('films.png' or 'series.png').
        \"""
        oGui = cGui()
        try:
            VSlog(f"Fetching recommendations for category {category}")
            
            with cDb() as DB:
                row = DB.get_catWatched(category, 5)  # Fetch the last 5 watched items
                if not row:
                    VSlog("No watched items found in this category.")
                    oGui.setEndOfDirectory()
                    return

                for data in row:
                    oOutputParameterHandler = cOutputParameterHandler()
                    oOutputParameterHandler.addParameter('sTmdbId', data['tmdb_id'])
                    oOutputParameterHandler.addParameter(
                        'siteUrl', f"{'movie' if category == '1' else 'tv'}/{data['tmdb_id']}/recommendations"
                    )
                    title = self.ADDON.VSlang({because_num}) + ' ' + data['title']
                    VSlog(f"Title {title} recommanded from views.")
                    oGui.addMovie(SITE_TMDB, content_type, title, icon, '', '', oOutputParameterHandler)

        except Exception as e:
            VSlog(f"Error fetching recommendations: {e}")
        finally:
            # Force the 'files' view for better clarity
            cGui.CONTENT = 'files'
            oGui.setEndOfDirectory()

    def showMoviesRecommandations(self):
        \"""Fetch and display movie recommendations.\"""
        self.showRecommandations('1', 'showMovies', 'films.png')

    def showShowsRecommandations(self):
        \"""Fetch and display TV show recommendations.\"""
        self.showRecommandations('4', 'showSeries', 'series.png')
"""

            # Création du fichier avec le contenu prédéfini
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(file_content)

            VSlog(f"Fichier {file_path} créé avec succès.")
        else:
            VSlog(f"Fichier {file_path} déjà existant. Aucune action requise.")

    except Exception as e:
        VSlog(f"Erreur lors de la création du fichier recommandations.py : {e}")

def add_get_recommendations_method_for_netflix_like_recommandations():
    """
    Ajoute la méthode `get_recommandations_by_id_movie` à tmdb.py si elle est absente.
    """
    # Chemin vers le fichier tmdb.py
    file_path = VSPath('special://home/addons/plugin.video.vstream/resources/lib/tmdb.py').replace('\\', '/')

    # Contenu de la méthode à ajouter
    method_content = """
    def get_recommandations_by_id_movie(self, tmdbid): 
        meta = self._call('movie/'+tmdbid+'/recommendations')

        if 'errors' not in meta and 'status_code' not in meta:
            return meta
        else:
            meta = {}
        return meta
"""

    # Vérifier si le fichier tmdb.py existe
    if not os.path.exists(file_path):
        VSlog(f"Fichier introuvable : {file_path}")
        return

    # Lire le contenu actuel du fichier
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Vérifier si la méthode est déjà présente
    if re.search(r"def get_recommandations_by_id_movie\(.*\):", content):
        VSlog("La méthode `get_recommandations_by_id_movie` est déjà présente.")
        return

    # Ajouter la méthode à la fin de la classe
    if "class" in content:
        content = re.sub(
            r"(class\s+\w+\(.*?\):)",  # Recherche de la première classe dans le fichier
            rf"\1{method_content}",
            content,
            count=1,
            flags=re.DOTALL
        )
    else:
        # Si aucune classe n'est définie, on ajoute simplement le contenu à la fin
        content += method_content

    # Écrire les modifications dans le fichier
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

    VSlog(f"La méthode `get_recommandations_by_id_movie` a été ajoutée à {file_path}.")

def modify_files():
    VSlog("Starting file modification process")

    create_monitor_file()
    add_vstreammonitor_import()

    add_netflix_like_recommandations()

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
                    f"{' ' * sTitle_indent}pattern = r\"(Saison|Season)\\s*(\\d+)\\s*[Ee]pisode\\s*(\\d+)\"\n",
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

def safe_regex_pattern(regex_pattern):
    """
    Rewrites a given regex pattern to avoid infinite loops or excessive backtracking,
    ensuring the original pattern's semantics are preserved.
    
    Args:
        regex_pattern (str): The potentially insecure regex pattern.
        
    Returns:
        str: A safer version of the regex pattern, or the original pattern if no safe
             transformation can guarantee identical behavior.
    """
    try:
        original_pattern = regex_pattern
        safe_pattern = original_pattern

        # Step 1: Replace greedy quantifiers with lazy ones (e.g., .* -> .*?)
        new_pattern = re.sub(r'(\.\*)(?!\?)', r'\1?', safe_pattern)
        if original_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After replacing greedy quantifiers: {safe_pattern}")

        # Step 2: Replace unbounded repetitions (e.g., .{1,} -> .{1,100})
        new_pattern = re.sub(r'\.\{\d*,\}', r'.{1,100}', safe_pattern)
        if safe_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After replacing unbounded repetitions: {safe_pattern}")

        # Step 3: Avoiding catastrophic backtracking by simplifying nested quantifiers
        new_pattern = re.sub(r'(\(\?:.*\))\+', r'\1{1,100}', safe_pattern)
        if safe_pattern != new_pattern:
            safe_pattern = new_pattern
            VSlog(f"After simplifying nested quantifiers: {safe_pattern}")

        # Test the equivalence of the patterns on representative input samples
        if not test_equivalence(original_pattern, safe_pattern):
            safe_pattern = original_pattern  # Fallback to original if behavior changes.

        return safe_pattern
    except re.error as regex_error:
        VSlog(f"Regex error: {regex_error}")
        return regex_pattern  # Return the original pattern if error occurs.
    except ValueError as value_error:
        VSlog(f"Value error: {value_error}")
        return regex_pattern  # Return the original pattern if escape sequence is invalid.
    except Exception as e:
        VSlog(f"Unexpected error: {e}")
        return regex_pattern

def test_equivalence(original, transformed, samples=None, max_dynamic_samples=20):
    """
    Test if two regex patterns produce the same results on sample inputs.
    
    Args:
        original (str): The original regex pattern.
        transformed (str): The transformed regex pattern.
        samples (list): A list of strings to test against (default: dynamically generated cases).
        max_dynamic_samples (int): Maximum number of dynamically generated test cases.

    Returns:
        bool: True if the patterns are equivalent; False otherwise.
    """
    if samples is None:
        # Generate diverse test cases based on the regex structure
        samples = generate_test_samples(original, max_samples=max_dynamic_samples)

    try:
        for sample in samples:
            original_matches = re.findall(original, sample)
            transformed_matches = re.findall(transformed, sample)
            if original_matches != transformed_matches:
                print(f"Mismatch found for input: {repr(sample)}")
                return False
        return True
    except re.error as regex_error:
        print(f"Regex error during testing: {regex_error}")
        return False
    except Exception as e:
        print(f"Unexpected error during testing: {e}")
        return False


def check_for_regex_in_function_calls(code):
    """
    Check for regex patterns used in function calls like re.compile() or re.search().
    """
    VSlog("Checking for regex in function calls...")
    
    regex_patterns = []
    function_calls = re.findall(r'(re\.(compile|match|search|findall|sub))\((.*)\)', code)
    
    for call in function_calls:
        # Extract the regex pattern argument
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
    
    Args:
        tree: The AST tree of the Python code.
    
    Returns:
        list: A list of (regex_pattern, variable_name, line_number, column_offset) tuples.
    """
    VSlog("Searching for regex patterns in AST...")
    
    regex_patterns = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Str):
                    # Check if the variable name contains 'pattern' or 'regex'
                    if 'pattern' in target.id.lower() or 'regex' in target.id.lower():
                        regex_pattern = node.value.s
                        if is_valid_regex(regex_pattern):
                            regex_patterns.append((regex_pattern, target.id, node.lineno, node.col_offset))
    
    VSlog(f"Found regex patterns in AST: {regex_patterns}")
    
    return regex_patterns

def is_valid_regex(pattern):
    """
    Check if a string is a valid regex pattern.
    
    Args:
        pattern (str): The regex pattern to check.
        
    Returns:
        bool: True if the pattern is valid, False if not.
    """
    try:
        re.compile(pattern)  # Try to compile the pattern
        return True
    except re.error:
        return False

def rewrite_file_to_avoid_regex_infinite_loops(file_path):
    """
    Rewrites the given file to avoid infinite loops in regular expressions.
    Ensures only insecure regex patterns are modified.
    
    Args:
        file_path (str): The path to the Python file to be processed.
    """
    try:
        VSlog(f"Reading file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents = file.read()

        # Parse the file contents into an AST
        tree = ast.parse(file_contents)
        regex_patterns_ast = find_regex_in_ast(tree)

        # Check for regex in function calls
        regex_patterns_calls = check_for_regex_in_function_calls(file_contents)

        # Combine patterns and ensure tuple structure
        regex_patterns = []
        for item in regex_patterns_ast + regex_patterns_calls:
            if len(item) == 1:
                regex_patterns.append((item[0], "Unknown", -1, -1))
            elif len(item) == 4:
                regex_patterns.append(item)

        # Analyze and replace insecure regex patterns
        modified_file_contents = file_contents
        for pattern, variable_name, lineno, col_offset in regex_patterns:
            try:
                unsafe_pattern = pattern
                safe_pattern = safe_regex_pattern(unsafe_pattern)

                if unsafe_pattern != safe_pattern:
                    VSlog(f"Modifying regex in variable '{variable_name}' (Line {lineno}, Column {col_offset})")
                    old_code_snippet = f'"{unsafe_pattern}"'
                    new_code_snippet = f'"{safe_pattern}"'
                    modified_file_contents = modified_file_contents.replace(old_code_snippet, new_code_snippet)
            except Exception as e:
                VSlog(f"Error processing pattern '{pattern}': {e}")

        # Write the modified content back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(modified_file_contents)

        if modified_file_contents != file_contents:
            VSlog("File rewritten to avoid regex infinite loops and inefficiencies.")
    
    except FileNotFoundError as e:
        VSlog(f"Error: {e}")
    except IOError as e:
        VSlog(f"File IO error: {e}")
    except Exception as e:
        VSlog(f"Unexpected error while modifying file: {e}")

def generate_test_samples(pattern, max_samples=20):
    """
    Generate diverse test cases based on the given regex pattern.

    Args:
        pattern (str): The regex pattern to analyze.
        max_samples (int): Maximum number of test cases to generate.

    Returns:
        list: A list of dynamically generated test case strings.
    """

    def random_string(length, char_set=string.ascii_letters + string.digits):
        """Generate a random string from the given character set."""
        return ''.join(random.choices(char_set, k=length))

    def generate_from_char_class(char_class):
        """Generate random strings matching a character class."""
        chars = re.sub(r'\-', '', char_class)  # Handle ranges (basic support)
        if '-' in char_class:
            # Handle ranges explicitly (e.g., a-z, 0-9)
            ranges = re.findall(r'(\w)-(\w)', char_class)
            for start, end in ranges:
                chars += ''.join(chr(c) for c in range(ord(start), ord(end) + 1))
        return ''.join(random.choices(chars, k=random.randint(1, 5)))

    def expand_pattern(pattern):
        """Expand components of the regex pattern to generate matches."""
        test_cases = []
        try:
            if '|' in pattern:  # Handle alternations
                alternations = pattern.split('|')
                for alt in alternations:
                    test_cases.extend(expand_pattern(alt))  # Flatten the results
            elif '[' in pattern and ']' in pattern:  # Handle character classes
                char_class = re.search(r'\[([^\]]+)\]', pattern).group(1)
                test_cases.append(generate_from_char_class(char_class))
            elif pattern == '.*':  # Handle greedy match
                test_cases.append(random_string(random.randint(1, 20)))
            elif pattern.startswith('^') or pattern.endswith('$'):  # Anchors
                core = pattern.strip('^$')
                test_cases.append(core + random_string(random.randint(1, 5)))
            else:
                # Fallback to directly generating a random match
                test_cases.append(random_string(random.randint(1, 10)))
        except Exception as e:
            test_cases.append(f"Error generating case: {e}")
        return test_cases

    # Generate test cases based on the pattern
    test_cases = set()  # Use a set to avoid duplicates
    test_cases.add("")  # Always include an empty string for robustness

    try:
        components = re.findall(r'\(.*?\)|\[[^\]]+\]|\.\*|\^.*\$|[^\|\[\]\(\)\^\$]+', pattern)
        for component in components:
            test_cases.update(expand_pattern(component))  # Ensure flat results

        # Ensure we have enough samples
        while len(test_cases) < max_samples:
            test_cases.add(random_string(random.randint(1, 10)))

    except Exception as e:
        test_cases.add(f"Error processing pattern: {e}")

    return list(test_cases)[:max_samples]

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

def activate_site(site_name):
    """Activate a site in the sites.json file."""
    VSlog(f"Activating site: {site_name}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if site_name in data['sites']:
            data['sites'][site_name]['active'] = "True"
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
            set_darkiworld_url(get_darkiworld_url())

            check_all_sites()

            # Add new site if necessary
            VSlog("Adding PapaDuStream if not present.")
            ajouter_papadustream()

            # Modify files as required
            VSlog("Modifying necessary files.")
            modify_files()

        except Exception as e:
            VSlog(f"An error occurred during update settings: {e}")
