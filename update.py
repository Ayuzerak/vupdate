
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
# Fallback AST Unparser Function
######################################

def my_unparse(node, depth=0, max_depth=50):
    """
    A robust fallback AST unparser for AST nodes.
    
    This implementation covers many common node types with safe measures such as:
      - Recursion depth control to prevent infinite recursion.
      - Exception handling to fall back safely using ast.dump().
      - Support for additional AST node types (e.g. lambda, lists, tuples, comprehensions).
    
    If the recursion depth exceeds max_depth or an error occurs, ast.dump(node) is returned.
    """
    def format_body(statements, current_depth):
        """Helper to handle empty code blocks by adding 'pass' with proper indentation"""
        body_lines = []
        for stmt in statements:
            unparsed = my_unparse(stmt, current_depth + 1, max_depth)
            for line in unparsed.split('\n'):
                body_lines.append('    ' * (current_depth + 1) + line)
        if not body_lines:
            body_lines.append('    ' * (current_depth + 1) + 'pass')
        return '\n'.join(body_lines)

    try:
        if depth > max_depth:
            return ast.dump(node)

        # Module-level structure
        if isinstance(node, ast.Module):
            return "\n".join(my_unparse(stmt, depth+1, max_depth) for stmt in node.body)
        
        # Function definitions
        elif isinstance(node, ast.FunctionDef):
            decorators = [f"@{my_unparse(d, depth+1, max_depth)}" for d in node.decorator_list]
            decorator_str = "\n".join(decorators) + "\n" if decorators else ""
            args = my_unparse(node.args, depth+1, max_depth)
            body = format_body(node.body, depth)
            return f"{decorator_str}def {node.name}({args}):\n{body}"
        
        # Class definitions
        elif isinstance(node, ast.ClassDef):
            decorators = [f"@{my_unparse(d, depth+1, max_depth)}" for d in node.decorator_list]
            bases = [my_unparse(b, depth+1, max_depth) for b in node.bases]
            keywords = [my_unparse(kw, depth+1, max_depth) for kw in node.keywords]
            body = format_body(node.body, depth)
            return "\n".join(decorators) + f"\nclass {node.name}({', '.join(bases + keywords)}):\n{body}"

        # Parameter handling
        elif isinstance(node, ast.arguments):
            params = []
            pos_only = [my_unparse(arg, depth+1, max_depth) for arg in node.posonlyargs]
            if pos_only:
                params.extend(pos_only)
                if node.args or node.vararg or node.kwonlyargs or node.kwarg:
                    params.append('/')
                    
            args = node.args
            defaults = node.defaults
            num_defaults = len(defaults)
            for i, arg in enumerate(args):
                arg_str = my_unparse(arg, depth+1, max_depth)
                if i >= len(args) - num_defaults:
                    default = defaults[i - (len(args) - num_defaults)]
                    arg_str += f"={my_unparse(default, depth+1, max_depth)}"
                params.append(arg_str)

            if node.vararg:
                vararg = my_unparse(node.vararg, depth+1, max_depth)
                if getattr(node.vararg, 'annotation', None):
                    vararg += f": {my_unparse(node.vararg.annotation, depth+1, max_depth)}"
                params.append(f"*{vararg}")
            elif node.kwonlyargs:
                params.append('*')
            
            for i, kwarg in enumerate(node.kwonlyargs):
                kwarg_str = my_unparse(kwarg, depth+1, max_depth)
                if i < len(node.kw_defaults):
                    default = node.kw_defaults[i]
                    if default:
                        kwarg_str += f"={my_unparse(default, depth+1, max_depth)}"
                params.append(kwarg_str)
            
            if node.kwarg:
                kwarg = my_unparse(node.kwarg, depth+1, max_depth)
                if getattr(node.kwarg, 'annotation', None):
                    kwarg += f": {my_unparse(node.kwarg.annotation, depth+1, max_depth)}"
                params.append(f"**{kwarg}")
            
            return ", ".join(params)

        # Parameter with type annotation
        elif isinstance(node, ast.arg):
            annotation = f": {my_unparse(node.annotation, depth+1, max_depth)}" if node.annotation else ""
            return f"{node.arg}{annotation}"

        # Assignment statements
        elif isinstance(node, ast.Assign):
            targets = " = ".join(my_unparse(t, depth+1, max_depth) for t in node.targets)
            value = my_unparse(node.value, depth+1, max_depth)
            return f"{targets} = {value}"

        # Expression statements
        elif isinstance(node, ast.Expr):
            return my_unparse(node.value, depth+1, max_depth)

        # Function/method calls
        elif isinstance(node, ast.Call):
            func = my_unparse(node.func, depth+1, max_depth)
            args = [my_unparse(a, depth+1, max_depth) for a in node.args]
            keywords = [my_unparse(k, depth+1, max_depth) for k in node.keywords]
            return f"{func}({', '.join(args + keywords)})"

        # Variable names
        elif isinstance(node, ast.Name):
            return node.id

        # Constants
        elif isinstance(node, ast.Constant):
            return repr(node.value)

        # String literals (Python <3.8)
        elif isinstance(node, ast.Str):
            return repr(node.s)

        # Return statements
        elif isinstance(node, ast.Return):
            value = my_unparse(node.value, depth+1, max_depth) if node.value else ""
            return f"return {value}"

        # Binary operations
        elif isinstance(node, ast.BinOp):
            left = my_unparse(node.left, depth+1, max_depth)
            op = my_unparse(node.op, depth+1, max_depth)
            right = my_unparse(node.right, depth+1, max_depth)
            return f"({left} {op} {right})"

        # Math operators
        elif isinstance(node, ast.Add): return "+"
        elif isinstance(node, ast.Sub): return "-"
        elif isinstance(node, ast.Mult): return "*"
        elif isinstance(node, ast.Div): return "/"
        elif isinstance(node, ast.FloorDiv): return "//"
        elif isinstance(node, ast.Mod): return "%"
        elif isinstance(node, ast.Pow): return "**"

        # Imports
        elif isinstance(node, ast.Import):
            names = ", ".join(
                f"{alias.name} as {alias.asname}" if alias.asname else alias.name
                for alias in node.names
            )
            return f"import {names}"
        
        elif isinstance(node, ast.ImportFrom):
            module = ("." * node.level) + (node.module or "")
            names = ", ".join(
                f"{alias.name} as {alias.asname}" if alias.asname else alias.name
                for alias in node.names
            )
            return f"from {module} import {names}"

        # Control structures
        elif isinstance(node, ast.If):
            test = my_unparse(node.test, depth+1, max_depth)
            body = format_body(node.body, depth)
            if node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    elif_stmt = my_unparse(node.orelse[0], depth+1, max_depth).replace("if", "elif", 1)
                    return f"if {test}:\n{body}\n{elif_stmt}"
                else:
                    orelse = format_body(node.orelse, depth)
                    return f"if {test}:\n{body}\nelse:\n{orelse}"
            return f"if {test}:\n{body}"

        elif isinstance(node, ast.For):
            target = my_unparse(node.target, depth+1, max_depth)
            iter_ = my_unparse(node.iter, depth+1, max_depth)
            body = format_body(node.body, depth)
            orelse = ""
            if node.orelse:
                orelse = f"\nelse:\n{format_body(node.orelse, depth)}"
            return f"for {target} in {iter_}:\n{body}{orelse}"

        elif isinstance(node, ast.While):
            test = my_unparse(node.test, depth+1, max_depth)
            body = format_body(node.body, depth)
            orelse = ""
            if node.orelse:
                orelse = f"\nelse:\n{format_body(node.orelse, depth)}"
            return f"while {test}:\n{body}{orelse}"

        elif isinstance(node, ast.With):
            items = []
            for item in node.items:
                ctx_expr = my_unparse(item.context_expr, depth+1, max_depth)
                var = f" as {my_unparse(item.optional_vars, depth+1, max_depth)}" if item.optional_vars else ""
                items.append(f"{ctx_expr}{var}")
            body = format_body(node.body, depth)
            return f"with {', '.join(items)}:\n{body}"

        # Comparisons
        elif isinstance(node, ast.Compare):
            left = my_unparse(node.left, depth+1, max_depth)
            ops = [my_unparse(op, depth+1, max_depth) for op in node.ops]
            comparators = [my_unparse(c, depth+1, max_depth) for c in node.comparators]
            return f"{left} {' '.join(f'{op} {comp}' for op, comp in zip(ops, comparators))}"

        elif isinstance(node, ast.Eq): return "=="
        elif isinstance(node, ast.NotEq): return "!="
        elif isinstance(node, ast.Lt): return "<"
        elif isinstance(node, ast.LtE): return "<="
        elif isinstance(node, ast.Gt): return ">"
        elif isinstance(node, ast.GtE): return ">="
        elif isinstance(node, ast.Is): return "is"
        elif isinstance(node, ast.IsNot): return "is not"
        elif isinstance(node, ast.In): return "in"
        elif isinstance(node, ast.NotIn): return "not in"

        # Boolean logic
        elif isinstance(node, ast.BoolOp):
            op_str = " and " if isinstance(node.op, ast.And) else " or "
            return f"({op_str.join(my_unparse(v, depth+1, max_depth) for v in node.values)})"

        # Unary operations
        elif isinstance(node, ast.UnaryOp):
            op = my_unparse(node.op, depth+1, max_depth)
            operand = my_unparse(node.operand, depth+1, max_depth)
            space = " " if op == "not" else ""
            return f"{op}{space}{operand}"

        elif isinstance(node, ast.Not): return "not"
        elif isinstance(node, ast.USub): return "-"
        elif isinstance(node, ast.UAdd): return "+"
        elif isinstance(node, ast.Invert): return "~"

        # Data structures
        elif isinstance(node, ast.Dict):
            keys = [my_unparse(k, depth+1, max_depth) if k else "None" 
                   for k in node.keys]
            values = [my_unparse(v, depth+1, max_depth) for v in node.values]
            pairs = [f"{k}: {v}" for k, v in zip(keys, values)]
            return "{" + ", ".join(pairs) + "}"
        
        elif isinstance(node, ast.List):
            elements = ", ".join(my_unparse(e, depth+1, max_depth) for e in node.elts)
            return f"[{elements}]"
        
        elif isinstance(node, ast.Tuple):
            elements = ", ".join(my_unparse(e, depth+1, max_depth) for e in node.elts)
            if len(node.elts) == 1:
                elements += ","
            return f"({elements})"
        
        elif isinstance(node, ast.Set):
            elements = ", ".join(my_unparse(e, depth+1, max_depth) for e in node.elts)
            return f"{{{elements}}}" if elements else "set()"

        # Lambda expressions
        elif isinstance(node, ast.Lambda):
            args = my_unparse(node.args, depth+1, max_depth)
            body = my_unparse(node.body, depth+1, max_depth)
            return f"lambda {args}: {body}"

        # Comprehensions
        elif isinstance(node, ast.ListComp):
            elt = my_unparse(node.elt, depth+1, max_depth)
            gens = " ".join(my_unparse(g, depth+1, max_depth) for g in node.generators)
            return f"[{elt} {gens}]"
        
        elif isinstance(node, ast.SetComp):
            elt = my_unparse(node.elt, depth+1, max_depth)
            gens = " ".join(my_unparse(g, depth+1, max_depth) for g in node.generators)
            return f"{{{elt} {gens}}}"
        
        elif isinstance(node, ast.DictComp):
            key = my_unparse(node.key, depth+1, max_depth)
            value = my_unparse(node.value, depth+1, max_depth)
            gens = " ".join(my_unparse(g, depth+1, max_depth) for g in node.generators)
            return f"{{{key}: {value} {gens}}}"
        
        elif isinstance(node, ast.GeneratorExp):
            elt = my_unparse(node.elt, depth+1, max_depth)
            gens = " ".join(my_unparse(g, depth+1, max_depth) for g in node.generators)
            return f"({elt} {gens})"
        
        elif isinstance(node, ast.comprehension):
            target = my_unparse(node.target, depth+1, max_depth)
            iter_ = my_unparse(node.iter, depth+1, max_depth)
            ifs = [my_unparse(cond, depth+1, max_depth) for cond in node.ifs]
            ifs_str = " if " + " if ".join(ifs) if ifs else ""
            return f"for {target} in {iter_}{ifs_str}"

        # Exception handling
        elif isinstance(node, ast.Try):
            try_body = format_body(node.body, depth)
            excepts = []
            for handler in node.handlers:
                type_str = my_unparse(handler.type, depth+1, max_depth) if handler.type else ""
                name = f" as {handler.name}" if handler.name else ""
                handler_body = format_body(handler.body, depth)
                excepts.append(f"except {type_str}{name}:\n{handler_body}")
            else_body = ""
            if node.orelse:
                else_body = f"\nelse:\n{format_body(node.orelse, depth)}"
            finally_body = ""
            if node.finalbody:
                finally_body = f"\nfinally:\n{format_body(node.finalbody, depth)}"
            return f"try:\n{try_body}\n" + "\n".join(excepts) + else_body + finally_body

        # Async constructs
        elif isinstance(node, ast.AsyncFunctionDef):
            decorators = [f"@{my_unparse(d, depth+1, max_depth)}" for d in node.decorator_list]
            decorator_str = "\n".join(decorators) + "\n" if decorators else ""
            args = my_unparse(node.args, depth+1, max_depth)
            body = format_body(node.body, depth)
            return f"{decorator_str}async def {node.name}({args}):\n{body}"

        elif isinstance(node, ast.AsyncFor):
            target = my_unparse(node.target, depth+1, max_depth)
            iter_ = my_unparse(node.iter, depth+1, max_depth)
            body = format_body(node.body, depth)
            orelse = ""
            if node.orelse:
                orelse = f"\nelse:\n{format_body(node.orelse, depth)}"
            return f"async for {target} in {iter_}:\n{body}{orelse}"

        elif isinstance(node, ast.AsyncWith):
            items = []
            for item in node.items:
                ctx_expr = my_unparse(item.context_expr, depth+1, max_depth)
                var = f" as {my_unparse(item.optional_vars, depth+1, max_depth)}" if item.optional_vars else ""
                items.append(f"{ctx_expr}{var}")
            body = format_body(node.body, depth)
            return f"async with {', '.join(items)}:\n{body}"

        elif isinstance(node, ast.Await):
            value = my_unparse(node.value, depth+1, max_depth)
            return f"await {value}"

        # Type annotations
        elif isinstance(node, ast.AnnAssign):
            target = my_unparse(node.target, depth+1, max_depth)
            annotation = my_unparse(node.annotation, depth+1, max_depth)
            value = f" = {my_unparse(node.value, depth+1, max_depth)}" if node.value else ""
            return f"{target}: {annotation}{value}"

        # Walrus operator
        elif isinstance(node, ast.NamedExpr):
            target = my_unparse(node.target, depth+1, max_depth)
            value = my_unparse(node.value, depth+1, max_depth)
            return f"({target} := {value})"

        # Formatted strings
        elif isinstance(node, ast.JoinedStr):
            parts = [my_unparse(v, depth+1, max_depth) for v in node.values]
            return f"f{''.join(parts)}"

        elif isinstance(node, ast.FormattedValue):
            value = my_unparse(node.value, depth+1, max_depth)
            conversion = f"!{chr(node.conversion)}" if node.conversion != -1 else ""
            format_spec = f":{my_unparse(node.format_spec, depth+1, max_depth)}" if node.format_spec else ""
            return f"{{{value}{conversion}{format_spec}}}"

        # Yield statements
        elif isinstance(node, ast.Yield):
            value = my_unparse(node.value, depth+1, max_depth) if node.value else ""
            return f"yield {value}"

        elif isinstance(node, ast.YieldFrom):
            value = my_unparse(node.value, depth+1, max_depth)
            return f"yield from {value}"

        # Control statements
        elif isinstance(node, ast.Global):
            return f"global {', '.join(node.names)}"

        elif isinstance(node, ast.Nonlocal):
            return f"nonlocal {', '.join(node.names)}"

        elif isinstance(node, ast.Assert):
            test = my_unparse(node.test, depth+1, max_depth)
            msg = f", {my_unparse(node.msg, depth+1, max_depth)}" if node.msg else ""
            return f"assert {test}{msg}"

        elif isinstance(node, ast.Raise):
            expr = my_unparse(node.exc, depth+1, max_depth) if node.exc else ""
            cause = f" from {my_unparse(node.cause, depth+1, max_depth)}" if node.cause else ""
            return f"raise {expr}{cause}" if expr or cause else "raise"

        elif isinstance(node, ast.Pass):
            return "pass"

        elif isinstance(node, ast.Break):
            return "break"

        elif isinstance(node, ast.Continue):
            return "continue"

        # Advanced operators
        elif isinstance(node, ast.BitAnd): return "&"
        elif isinstance(node, ast.BitOr): return "|"
        elif isinstance(node, ast.BitXor): return "^"
        elif isinstance(node, ast.LShift): return "<<"
        elif isinstance(node, ast.RShift): return ">>"

        # Augmented assignment
        elif isinstance(node, ast.AugAssign):
            target = my_unparse(node.target, depth+1, max_depth)
            op = my_unparse(node.op, depth+1, max_depth)
            value = my_unparse(node.value, depth+1, max_depth)
            return f"{target} {op}= {value}"

        # Subscripting
        elif isinstance(node, ast.Subscript):
            value = my_unparse(node.value, depth+1, max_depth)
            slice_part = my_unparse(node.slice, depth+1, max_depth)
            return f"{value}[{slice_part}]"

        elif isinstance(node, ast.Slice):
            lower = my_unparse(node.lower, depth+1, max_depth) if node.lower else ""
            upper = my_unparse(node.upper, depth+1, max_depth) if node.upper else ""
            step = my_unparse(node.step, depth+1, max_depth) if node.step else ""
            return f"{lower}:{upper}" + (f":{step}" if step else "")

        elif isinstance(node, ast.Index):
            return my_unparse(node.value, depth+1, max_depth)

        # Starred expressions
        elif isinstance(node, ast.Starred):
            value = my_unparse(node.value, depth+1, max_depth)
            return f"*{value}"

        # Attribute access
        elif isinstance(node, ast.Attribute):
            value = my_unparse(node.value, depth+1, max_depth)
            return f"{value}.{node.attr}"

        # Pattern matching (Python 3.10+)
        elif isinstance(node, ast.Match):
            subject = my_unparse(node.subject, depth+1, max_depth)
            cases = "\n".join(my_unparse(c, depth+1, max_depth) for c in node.cases)
            return f"match {subject}:\n{cases}"

        elif isinstance(node, ast.match_case):
            pattern = my_unparse(node.pattern, depth+1, max_depth)
            guard = f" if {my_unparse(node.guard, depth+1, max_depth)}" if node.guard else ""
            body = format_body(node.body, depth)
            return f"case {pattern}{guard}:\n{body}"

        # Special constants
        elif isinstance(node, ast.Constant) and node.value is Ellipsis:
            return "..."
        
        # Edge cases
        elif isinstance(node, ast.Set) and not node.elts:
            return "set()"

        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            return f'"""{node.value.s}"""'

        # Final fallback
        else:
            return ast.dump(node)
            
    except Exception as e:
        return ast.dump(node)

######################################
# File Rewriting & CLI Handling
######################################

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
            new_code = my_unparse(new_tree)

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

def get_livetv_url():
    """Récupère l'URL actuelle de LiveTV depuis son site référent."""
    VSlog("Récupération de l'URL de LiveTV.")

    current_url = "https://livetv819.me"
    bypass_url = "https://livetv774.me"
    default_url = "https://livetv.sx"

    try:
        response = requests.get("https://top-infos.com/live-tv-sx-nouvelle-adresse/", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }, timeout=10)

        content = response.text

        if ping_server(current_url):
            default_url = current_url
        elif ping_server(bypass_url):
            default_url = bypass_url

        # Trouver la position du texte clé
        target_position = content.find("LiveTV est accessible via")
        if target_position == -1:
            VSlog("Texte clé non trouvé dans la page.")
            return default_url
        
        # Extraire l'URL après le texte clé
        content_after_target = content[target_position:]
        web_addresses = re.findall(r'https?://[\w.-]+(?:\.[\w.-]+)+(?::\d+)?(?:/[\w.-]*)*(?:\?[\w&=.-]*)?(?:#[\w.-]*)?', content_after_target)
        
        if web_addresses:
            if web_addresses[1] and "livetv" in web_addresses[1]:
                url = web_addresses[1].replace("/frx/", "").replace("httpss", "https") + "/"
            else:
                url = web_addresses[0].replace("/frx/", "").replace("httpss", "https") + "/"

            if not url.startswith("http"):
                url = "https://" + url
            VSlog(f"URL de LiveTV trouvée : {url}")
            # Vérifier si l'URL récupérée redirige ailleurs
            final_response = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }, timeout=10, allow_redirects=True)
            
            final_url = final_response.url
            VSlog(f"URL finale de LiveTV: {final_url}.")
            return final_url

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
