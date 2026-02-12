import requests
import xml.etree.ElementTree as ET
import time

# De basis URL en parameters
# BASE_URL = "https://rcerijswijk.adlibhosting.com/api.wo2/wwwopac.ashx" # Objectgegevens NK collectie
# DATABASE = "collect"
BASE_URL = "https://rce-bhg.adlibhosting.com/api.wo2/wwwopac.ashx" # Herkomstgegevens NK collecti
DATABASE = "HerkomstNK"

LIMIT = 50
START_FROM = 1
OUTPUT_FILE = "../" + DATABASE + ".xml"

# Maak een nieuw, leeg XML-hoofdelement aan voor het gecombineerde bestand.
# We noemen het <adlibXML> om de structuur van de bron te benaderen.
combined_root = ET.Element("adlibXML")
# Maak een <recordList> aan binnen ons hoofdelement om alle records in te verzamelen
record_list = ET.SubElement(combined_root, "recordList")

print(f"Starten met het ophalen van records... (limiet van {LIMIT} per keer)")

while True:
    # Stel de parameters voor deze specifieke aanvraag samen
    params = {
        'database': DATABASE,
        'limit': LIMIT,
        'search': 'all',
        'startfrom': START_FROM
    }

    print(f"Ophalen van records... Start vanaf: {START_FROM}")

    try:
        # Voer de GET-request uit
        response = requests.get(BASE_URL, params=params)
        # Controleer op HTTP-fouten (bijv. 404, 500)
        response.raise_for_status()

        # Parse de XML-content van het antwoord
        # We gebruiken response.content om encoding-problemen te vermijden
        page_root = ET.fromstring(response.content)

        # Zoek alle <record> elementen binnen de <recordList> van deze pagina
        records_on_page = page_root.findall(".//recordList/record")

        # Controleer of er records zijn gevonden
        if not records_on_page:
            # Geen records meer gevonden, dit is het einde
            print("Geen records meer gevonden. Stoppen met ophalen.")
            break

        # Voeg elk gevonden record toe aan onze gecombineerde recordLijst
        for record in records_on_page:
            record_list.append(record)

        print(f"  ... {len(records_on_page)} records toegevoegd. Totaal nu: {len(record_list)}")

        # Verhoog de 'startfrom' parameter voor de volgende iteratie
        START_FROM += LIMIT

        # (Optioneel) Voeg een kleine pauze toe om de server niet te overbelasten
        # time.sleep(0.5) # 0.5 seconden wachten

    except requests.exceptions.RequestException as e:
        print(f"Fout tijdens het ophalen van data: {e}")
        break
    except ET.ParseError as e:
        print(f"Fout tijdens het parsen van XML: {e}")
        print("Reactie van server was mogelijk geen valide XML.")
        break
    except Exception as e:
        print(f"Een onverwachte fout is opgetreden: {e}")
        break

# Nadat de loop is voltooid (of afgebroken)
print("\nOphalen voltooid.")
print(f"Totaal {len(record_list)} records verzameld.")
print(f"Gecombineerd bestand opslaan als '{OUTPUT_FILE}'...")

try:
    # Maak een ElementTree object van ons gecombineerde hoofdelement
    tree = ET.ElementTree(combined_root)

    # Zorg voor mooie inspringing (pretty-print)
    # Dit vereist Python 3.9+
    ET.indent(tree, space="  ")

    # Schrijf de boom naar een bestand, inclusief XML-declaratie en UTF-8 encoding
    tree.write(OUTPUT_FILE, encoding='utf-8', xml_declaration=True)

    print(f"Bestand '{OUTPUT_FILE}' succesvol aangemaakt.")

except Exception as e:
    print(f"Fout tijdens het wegschrijven van het bestand: {e}")