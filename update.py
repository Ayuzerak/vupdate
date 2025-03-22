# update by vstream 
# -*- coding: utf-8 -*-
# https://github.com/Kodi-vStream/venom-xbmc-addons

from resources.lib.comaddon import addon, siteManager, VSPath, VSlog, isMatrix
from resources.lib.handler.requestHandler import cRequestHandler
import datetime, time
import xbmc
import xbmcvfs
import shutil
import os
import zipfile

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
import configparser
from requests.exceptions import RequestException, SSLError

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
    updated_flag_path = os.path.join(addon_path, "updatededed")
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
        
def modify_files():
    VSlog("Starting file modification process")

    edit_live_file()

    update_service_addon()

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

def add_condition_to_statement(file_path, condition_to_insert, target_line, 
                               parent_blocks=None, encoding='utf-8'):
    """
    Inserts a conditional statement before a target line if variables of the condition
    are defined in accessible scopes; then reindents the target accordingly.
    If the condition is already present immediately above the target line, no insertion is made.

    Parameters:
    - file_path (str): Path to the Python file to modify.
    - condition_to_insert (str): Condition line to add (e.g., "if user.is_admin:", "for ...", "with ...", etc).
    - target_line (str): Line of code (or part of it) to wrap in the condition.
    - parent_blocks (list): Required relative parent block hierarchy 
          (e.g., ["class User:", "def save():"] or ["def save():"]).
    - encoding (str): File encoding (default: 'utf-8').

    Returns:
    - bool: True if file was modified, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
    except Exception as e:
        VSlog(f"Failed to read file {file_path}: {e}")
        return False

    # Determine the starting index and indent for the target’s parent block.
    parent_start_idx = 0
    parent_indent = 0
    if parent_blocks:
        # Use the last block header as the enclosing block.
        last_parent = parent_blocks[-1].strip()
        for idx, line in enumerate(lines):
            if line.strip() == last_parent:
                parent_start_idx = idx
                parent_indent = len(line) - len(line.lstrip())
                break
        else:
            VSlog(f"Parent block {last_parent} not found in file {file_path}.")
            return False

    # Find the target line index using a substring match.
    target_idx = None
    for idx in range(parent_start_idx, len(lines)):
        # Remove inline comments and trailing whitespace.
        line_content = lines[idx].split("#")[0].rstrip()
        if target_line.strip() in line_content.strip():
            target_idx = idx
            break

    if target_idx is None:
        VSlog(f"Target line containing '{target_line.strip()}' not found in file {file_path}.")
        return False

    # Check if the condition is already present immediately above the target line.
    if target_idx > 0 and lines[target_idx - 1].strip() == condition_to_insert.strip():
        VSlog(f"Condition '{condition_to_insert.strip()}' already present above target line in file {file_path}. No insertion needed.")
        return False

    # For "if" conditions, extract variable names from the condition expression.
    condition_vars = []
    cond_strip = condition_to_insert.strip()
    if cond_strip.startswith("if ") and cond_strip.endswith(":"):
        cond_expr_str = cond_strip[3:-1].strip()
        try:
            expr_ast = ast.parse(cond_expr_str, mode='eval')
            condition_vars = [node.id for node in ast.walk(expr_ast) if isinstance(node, ast.Name)]
        except Exception:
            condition_vars = []
    # For non-"if" statements, we assume condition is allowed.
    
    # Helper: check if a given variable appears in an assignment in a line.
    def var_assigned_in_line(var, line):
        pattern = r'\b' + re.escape(var) + r'\s*='
        return re.search(pattern, line) is not None

    # Determine accessible scope:
    # Global scope: lines before the parent's block header (indent == 0)
    # Local scope: lines within the parent's block (between parent's header and target line)
    def is_var_accessible(var):
        if var == "self":
            parent_line = lines[parent_start_idx]
            if parent_line.lstrip().startswith("def ") and re.search(r'\bself\b', parent_line):
                return True
            return False

        # Check global scope.
        for i in range(0, parent_start_idx):
            stripped = lines[i].strip()
            if stripped and (len(lines[i]) - len(lines[i].lstrip()) == 0):
                if var_assigned_in_line(var, lines[i]):
                    return True

        # Check local scope.
        for i in range(parent_start_idx, target_idx):
            if (len(lines[i]) - len(lines[i].lstrip())) > parent_indent:
                if var_assigned_in_line(var, lines[i]):
                    return True
        return False

    # Verify that each variable used in the condition is accessible.
    for var in condition_vars:
        if not is_var_accessible(var):
            VSlog(f"Variable '{var}' is not accessible in file {file_path}. Aborting condition insertion.")
            return False

    # At this point, insert the condition.
    target_line_str = lines[target_idx]
    target_indent_str = target_line_str[:len(target_line_str) - len(target_line_str.lstrip())]

    new_condition_line = target_indent_str + condition_to_insert.rstrip() + "\n"
    indent_unit = " " * 4
    new_target_line = target_indent_str + indent_unit + target_line_str.lstrip()

    lines[target_idx] = new_target_line
    lines.insert(target_idx, new_condition_line)

    try:
        with open(file_path, 'w', encoding=encoding) as f:
            f.writelines(lines)
    except Exception as e:
        VSlog(f"Failed to write file {file_path}: {e}")
        return False

    VSlog(f"Condition inserted successfully in file {file_path}.")
    return True

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

def activate_site(site_name, active=True):
    """Activate a site in the sites.json file."""
    VSlog(f"Activating site: {site_name}.")
    sites_json = VSPath('special://home/addons/plugin.video.vstream/resources/sites.json').replace('\\', '/')
    try:
        with open(sites_json, 'r') as fichier:
            data = json.load(fichier)
        if site_name in data['sites']:
            data['sites'][site_name]['active'] = str(active)
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
    """Retrieve LiveTV URL with content validation and fallback to saved URL.
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
            response_lowered = response.text.lower()
            if "matchs" in response_lowered and "direct" in response_lowered and "nba" in response_lowered:
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

    # Candidate 1: Try the URL saved in the config file.
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

class cUpdate:

    def getUpdateSetting(self):
        """Handles update settings and site checks."""
        VSlog("update.py: Starting update settings procedure.")
        addons = addon()

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

            # Add new site if necessary
            VSlog("Adding PapaDuStream if not present.")
            ajouter_papadustream()

            # Modify files as required
            VSlog("Modifying necessary files.")
            modify_files()

            # Handle settings update time
            setting_time = addons.getSetting('setting_time')
            if not setting_time:
                setting_time = '2000-09-23 10:59:50.877000'
                VSlog("No previous setting time found; initializing with default value.")

            # Calculate time differences
            time_now = datetime.datetime.now()
            time_service = self.__strptime(setting_time)
            time_sleep = datetime.timedelta(hours=24)

            if time_now - time_service > time_sleep:
                VSlog("More than 24 hours since last update; proceeding with site.json update.")

                # Fetch new properties
                sUrl = 'https://raw.githubusercontent.com/Kodi-vStream/venom-xbmc-addons/Beta/plugin.video.vstream/resources/sites.json'
                oRequestHandler = cRequestHandler(sUrl)
                properties = oRequestHandler.request(jsonDecode=True)
                
                if not properties:
                    VSlog("Failed to retrieve properties; aborting update.")
                    return

                # Set new properties and manage directories
                siteManager().setDefaultProps(properties)

                # Update settings time
                addons.setSetting('setting_time', str(time_now))
                VSlog(f"Update completed. Setting time updated to: {time_now}")

        except Exception as e:
            VSlog(f"An error occurred during update settings: {e}")

    def __strptime(self, date):
        """Handles date parsing with Python-specific bug handling."""
        if len(date) > 19:
            date_format = '%Y-%m-%d %H:%M:%S.%f'
        else:
            date_format = '%Y-%m-%d %H:%M:%S'

        try:
            return datetime.datetime.strptime(date, date_format)
        except TypeError:
            return datetime.datetime(*(time.strptime(date, date_format)[0:6]))
