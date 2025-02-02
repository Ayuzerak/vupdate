def load_config(default_url):
    config_update_file = VSPath('special://home/addons/plugin.video.vstream/resources/lib/config_update.json')
    """Charge l'URL actuelle depuis un fichier de configuration."""
    if os.path.exists(config_update_file):
        with open(config_update_file, "r", encoding="utf-8") as f:
            return json.load(f).get("current_url", default_url)
    return default_url

def save_config(new_url):
    """Sauvegarde l'URL mise à jour dans un fichier de configuration."""
    with open(VSPath('special://home/addons/plugin.video.vstream/resources/lib/config_update.json'), "w", encoding="utf-8") as f:
        json.dump({"current_url": new_url}, f, indent=4)

def get_livetv_url():
    """Récupère l'URL actuelle de LiveTV et met à jour le fichier source si nécessaire."""
    VSlog("Récupération de l'URL de LiveTV.")

    default_url = "https://livetv.sx"
    current_url = load_config(default_url)
    bypass_url = "https://livetv774.me"

    try:
        response = requests.get("https://top-infos.com/live-tv-sx-nouvelle-adresse/", headers={
            "User-Agent": "Mozilla/5.0"
        }, timeout=10)

        content = response.text

        # Vérifier quelle URL est accessible
        if ping_server(current_url):
            default_url = current_url
        elif ping_server(bypass_url):
            default_url = bypass_url

        # Vérifier la redirection de l'URL sélectionnée
        final_response = requests.get(default_url, headers={
            "User-Agent": "Mozilla/5.0"
        }, timeout=10, allow_redirects=True)

        final_url = final_response.url

        # Si l'URL finale est différente de "https://livetv.sx", on met à jour le fichier
        if final_url != default_url and final_url != current_url:
            VSlog(f"Mise à jour de current_url : {final_url}")
            save_config(final_url)

        # Trouver la position du texte clé
        target_position = content.find("LiveTV est accessible via")
        if target_position == -1:
            VSlog("Texte clé non trouvé dans la page.")
            return final_url
        
        # Extraire l'URL après le texte clé
        content_after_target = content[target_position:]
        web_addresses = re.findall(r'https?://[\w.-]+(?:\.[\w.-]+)+(?::\d+)?(?:/[\w.-]*)*(?:\?[\w&=.-]*)?(?:#[\w.-]*)?', content_after_target)
        
        if web_addresses:
            url = web_addresses[0].replace("/frx/", "").replace("httpss", "https") + "/"
            if not url.startswith("http"):
                url = "https://" + url

            VSlog(f"URL de LiveTV trouvée : {url}")

            # Vérifier la redirection
            final_response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
            final_url = final_response.url

            # Mise à jour du fichier si nécessaire
            if final_url != url and final_url != current_url:
                VSlog(f"Mise à jour de current_url : {final_url}")
                save_config(final_url)

            VSlog(f"URL finale de LiveTV: {final_url}.")
            return final_url

        VSlog("Aucune adresse trouvée après le texte clé.")
        return final_url

    except requests.RequestException as e:
        VSlog(f"Erreur lors de la récupération de l'URL de LiveTV : {e}")
        return default_url
