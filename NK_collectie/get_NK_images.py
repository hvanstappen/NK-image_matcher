import requests
import csv
import os
import time
import urllib.parse

# --- Configuratie ---

# 1. De naam van je CSV-bestand
CSV_FILE = 'images_NK_rest20260129.csv'  # Pas dit aan als je bestand anders heet

# 2. De map waar de afbeeldingen worden opgeslagen
DOWNLOAD_FOLDER = 'images_rest20260129'

# 3. Wachttijd in seconden na elke download
WAIT_TIME = 1


# --- Einde Configuratie ---

def download_images():
    # 1. Zorg dat de downloadmap bestaat
    if not os.path.exists(DOWNLOAD_FOLDER):
        try:
            os.makedirs(DOWNLOAD_FOLDER)
            print(f"Map '{DOWNLOAD_FOLDER}' aangemaakt.")
        except OSError as e:
            print(f"FOUT: Kon map '{DOWNLOAD_FOLDER}' niet aanmaken. {e}")
            return

    # 2. Lees het CSV-bestand
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8') as file:
            # Gebruik DictReader om rijen als dictionaries te lezen
            reader = csv.DictReader(file)

            # Controleer of de verwachte kolomnaam bestaat
            if 'reproduction_url' not in reader.fieldnames:
                print(f"FOUT: Het CSV-bestand '{CSV_FILE}'")
                print(f"heeft geen kolom met de header 'reproduction_url'.")
                print(f"Gevonden headers: {reader.fieldnames}")
                return

            # Gebruik enumerate voor een teller (handig voor feedback)
            # reader.line_num geeft het regelnummer inclusief de header
            for i, row in enumerate(reader):

                # Haal de URL op basis van de kolomnaam
                url = row.get('reproduction_url', '').strip()

                # Sla rijen over waar de URL leeg is
                if not url:
                    print(f"Rij {i + 2} overgeslagen: 'reproduction_url' is leeg.")
                    continue

                # Sla rijen over die niet op een URL lijken
                if not url.startswith('http'):
                    print(f"Rij {i + 2} overgeslagen: '{url}' is geen valide URL.")
                    continue

                # 3. Download de afbeelding
                try:
                    print(f"\nItem {i + 1} (Rij {i + 2}): Poging tot downloaden...")
                    print(f"  URL: {url}")

                    # Haal de data op met een timeout van 10 sec
                    response = requests.get(url, timeout=30)

                    # Controleer op fouten (bv. 404 Not Found, 500 Server Error)
                    response.raise_for_status()

                    # 4. Bepaal de bestandsnaam uit de URL
                    path = urllib.parse.urlparse(url).path
                    filename = os.path.basename(path)

                    # Als de URL geen duidelijke bestandsnaam heeft
                    if not filename or '.' not in filename:
                        # Probeer de extensie te raden op basis van de server response
                        content_type = response.headers.get('content-type')
                        ext = '.jpg'  # Veilige gok
                        if content_type:
                            if 'image/png' in content_type:
                                ext = '.png'
                            elif 'image/gif' in content_type:
                                ext = '.gif'
                            elif 'image/jpeg' in content_type:
                                ext = '.jpg'
                            elif 'image/webp' in content_type:
                                ext = '.webp'

                        # Gebruik de teller als bestandsnaam
                        filename = f"image_{i + 1}{ext}"
                        print(f"  ... Kon geen bestandsnaam uit URL afleiden, gebruikt: {filename}")

                    # 5. Sla het bestand op
                    save_path = os.path.join(DOWNLOAD_FOLDER, filename)

                    with open(save_path, 'wb') as img_file:
                        img_file.write(response.content)

                    print(f"  ... Succesvol opgeslagen als: {save_path}")

                except requests.exceptions.Timeout:
                    print(f"  ... FOUT: De request naar {url} duurde te lang (timeout).")
                except requests.exceptions.HTTPError as e:
                    print(f"  ... FOUT: HTTP Error {e.response.status_code} voor {url}.")
                except requests.exceptions.RequestException as e:
                    print(f"  ... FOUT: Kon {url} niet ophalen. {e}")
                except IOError as e:
                    print(f"  ... FOUT: Kon bestand niet opslaan. {e}")

                # 6. Wacht x seconden
                print(f"Wacht {WAIT_TIME} seconden...")
                time.sleep(WAIT_TIME)

    except FileNotFoundError:
        print(f"FOUT: Kan het bestand '{CSV_FILE}' niet vinden.")
        print("Zorg dat het bestand in dezelfde map staat als het script, of pas 'CSV_FILE' aan.")
    except Exception as e:
        print(f"Een onverwachte algemene fout is opgetreden: {e}")

    print("\n--- Script voltooid. ---")


# Voer de hoofdfunctie uit
if __name__ == "__main__":
    download_images()