"""Bootstrap les dictionnaires bundled depuis les sources upstream.

Sources :
    cities      : GeoNames cities500 (CC BY 4.0)
                  https://download.geonames.org/export/dump/cities500.zip
    firstnames  : INSEE etat civil (Licence ouverte 2.0)
                  https://www.insee.fr/fr/statistiques/7763585?sommaire=7635552
                  + Wikidata pour les autres langues

Usage :
    python scripts/build_dictionaries.py cities       # toutes les langues
    python scripts/build_dictionaries.py cities --lang fr
    python scripts/build_dictionaries.py firstnames

Sortie :
    assets/dictionaries/cities/{fr,de,en,es,it}.txt
    assets/dictionaries/firstnames/{fr,de,en,es,it}.txt

Le script est idempotent : il regenere les fichiers a chaque execution.
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets" / "dictionaries"

# Mapping pays -> langue Carnaval. Pour cities, on prend les pays
# dont la langue officielle correspond a une langue Carnaval supportee.
COUNTRY_TO_LANG: dict[str, str] = {
    # France + DOM-TOM
    "FR": "fr", "MC": "fr", "BE": "fr", "LU": "fr",
    "CH": "fr",  # NB : on agrege CH dans FR (canton de geneve, vaud, etc.)
    # Allemagne, Autriche, (Suisse alemanique mais on a deja CH=fr ici)
    "DE": "de", "AT": "de",
    # Royaume-Uni, Irlande, USA, Canada, Australie, NZ
    "GB": "en", "IE": "en", "US": "en", "CA": "en",
    "AU": "en", "NZ": "en",
    # Espagne, Mexique, Argentine, principaux pays hispaniques
    "ES": "es", "MX": "es", "AR": "es", "CO": "es", "CL": "es", "PE": "es",
    # Italie, Saint Marin, Vatican
    "IT": "it", "SM": "it", "VA": "it",
    # Portugal + Bresil
    "PT": "pt", "BR": "pt", "AO": "pt", "MZ": "pt",
}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _http_get(url: str) -> bytes:
    print(f"  download : {url}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Carnaval-DictBuilder/1.0"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def build_cities(target_langs: list[str] | None = None) -> None:
    """Construit assets/dictionaries/cities/{lang}.txt depuis GeoNames cities500."""
    print("== Cities (GeoNames cities500) ==")
    url = "https://download.geonames.org/export/dump/cities500.zip"
    raw_zip = _http_get(url)

    target = target_langs or sorted(set(COUNTRY_TO_LANG.values()))
    by_lang: dict[str, set[str]] = {lg: set() for lg in target}

    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        with zf.open("cities500.txt") as f:
            for raw in io.TextIOWrapper(f, encoding="utf-8"):
                cols = raw.rstrip("\n").split("\t")
                # GeoNames cities500 : 19 colonnes.
                # 1=name 2=asciiname 3=alternatenames 8=country_code 14=population
                if len(cols) < 15:
                    continue
                country = cols[8]
                lang = COUNTRY_TO_LANG.get(country)
                if not lang or lang not in by_lang:
                    continue
                name = cols[1].strip()        # ASCII pour matcher accent-tolerant
                ascii_name = cols[2].strip()
                if name and len(name) >= 3:
                    by_lang[lang].add(name)
                if ascii_name and ascii_name != name and len(ascii_name) >= 3:
                    by_lang[lang].add(ascii_name)

    _ensure_dir(ASSETS_DIR / "cities")
    for lang, names in by_lang.items():
        out = ASSETS_DIR / "cities" / f"{lang}.txt"
        sorted_names = sorted(names)
        out.write_text(
            "# Cities >= 500 habitants. Source : GeoNames (CC BY 4.0).\n"
            "# https://www.geonames.org/\n"
            "# Regenere par scripts/build_dictionaries.py\n"
            + "\n".join(sorted_names) + "\n",
            encoding="utf-8",
        )
        print(f"  {lang}: {len(sorted_names):>6} villes -> {out.relative_to(REPO_ROOT)}")


def _write_firstnames_seed() -> None:
    """Ecrit des listes etendues de prenoms (top ~150 par langue).

    Sources de reference (a importer plus tard via build_firstnames_full) :
        FR : INSEE etat civil
        DE : Statistisches Bundesamt
        EN : SSA baby names / UK ONS
        ES : INE Espana
        IT : ISTAT
    """
    print("== Firstnames (top 150 par langue) ==")
    seeds = {
        "fr": [
            # Masculins courants
            "Patrice", "Pierre", "Jean", "Paul", "Jacques", "Andre", "Michel",
            "Claude", "Henri", "Louis", "Bernard", "Daniel", "Robert", "Marcel",
            "Stephane", "Laurent", "Olivier", "Sebastien", "Thomas", "Nicolas",
            "David", "Vincent", "Julien", "Mathieu", "Emmanuel", "Francois",
            "Frederic", "Christophe", "Philippe", "Norbert", "Thierry",
            "Patrick", "Pascal", "Jerome", "Yves", "Alain", "Guy", "Rene",
            "Maurice", "Roger", "Roland", "Bruno", "Eric", "Didier", "Gilles",
            "Joel", "Serge", "Albert", "Raymond", "Antoine", "Romain",
            "Nicolas", "Aurelien", "Arnaud", "Anthony", "Damien", "Florian",
            "Jonathan", "Jordan", "Kevin", "Maxime", "Quentin", "Remi",
            # Feminins courants
            "Marie", "Sophie", "Christine", "Nathalie", "Sylvie", "Catherine",
            "Brigitte", "Stephanie", "Veronique", "Isabelle", "Caroline",
            "Celine", "Sandrine", "Francoise", "Anne", "Martine", "Monique",
            "Helene", "Florence", "Patricia", "Claire", "Aurelie", "Audrey",
            "Karine", "Laetitia", "Virginie", "Vanessa", "Severine",
            "Valerie", "Kelly", "Codruta", "Camille", "Manon", "Charlotte",
            "Emma", "Lea", "Chloe", "Sarah", "Pauline", "Marion", "Julie",
            "Amelie", "Mathilde", "Lucie", "Justine", "Margaux",
        ],
        "de": [
            # Masculins courants
            "Hans", "Klaus", "Peter", "Karl", "Wolfgang", "Michael", "Thomas",
            "Andreas", "Stefan", "Stephan", "Markus", "Jurgen", "Walter",
            "Helmut", "Frank", "Dieter", "Manfred", "Rainer", "Werner",
            "Heinz", "Kurt", "Gunther", "Bernd", "Horst", "Gerhard", "Wilhelm",
            "Friedrich", "Christian", "Christoph", "Tobias", "Florian",
            "Sebastian", "Daniel", "Alexander", "Patrick", "Martin", "Jan",
            "Sven", "Lars", "Holger", "Uwe", "Ralf", "Volker", "Norbert",
            "Erwin", "Otto", "Ulrich", "Joachim", "Detlef",
            # Feminins courants
            "Anna", "Maria", "Petra", "Sabine", "Andrea", "Monika", "Brigitte",
            "Susanne", "Heike", "Birgit", "Claudia", "Christine", "Christina",
            "Katrin", "Kathrin", "Katharina", "Stefanie", "Nicole", "Sandra",
            "Ute", "Ursula", "Renate", "Heidi", "Gabriele", "Ingrid",
            "Karin", "Helga", "Marion", "Angelika", "Erika", "Doris",
            "Julia", "Lisa", "Lena", "Laura", "Sarah", "Anja", "Tanja",
            "Nadine", "Melanie", "Vanessa", "Jessica", "Franziska",
            # Composes courants
            "Hans-Peter", "Hans-Jurgen", "Karl-Heinz", "Klaus-Dieter",
        ],
        "en": [
            "John", "James", "Robert", "Michael", "William", "David", "Richard",
            "Charles", "Joseph", "Thomas", "Christopher", "Daniel", "Paul",
            "Mark", "Donald", "Steven", "Andrew", "Kenneth", "George", "Edward",
            "Brian", "Ronald", "Anthony", "Kevin", "Jason", "Matthew", "Gary",
            "Timothy", "Jose", "Larry", "Jeffrey", "Frank", "Scott", "Eric",
            "Stephen", "Justin", "Brandon", "Benjamin", "Samuel", "Gregory",
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara",
            "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty",
            "Helen", "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle",
            "Laura", "Emily", "Kimberly", "Deborah", "Dorothy", "Amy",
            "Angela", "Ashley", "Brenda", "Anna", "Rebecca", "Virginia",
        ],
        "es": [
            "Juan", "Carlos", "Jose", "Antonio", "Manuel", "Francisco", "Luis",
            "Miguel", "Pedro", "Alejandro", "Pablo", "Daniel", "Fernando",
            "Diego", "Sergio", "Javier", "Roberto", "Ricardo", "Jorge",
            "Rafael", "Andres", "Ignacio", "Alberto", "Eduardo", "Enrique",
            "Mario", "Adrian", "Ruben", "Hector", "Felipe", "Salvador",
            "Maria", "Carmen", "Ana", "Isabel", "Pilar", "Cristina", "Laura",
            "Marta", "Sara", "Elena", "Patricia", "Lucia", "Sofia", "Paula",
            "Andrea", "Beatriz", "Rosa", "Teresa", "Mercedes", "Dolores",
            "Concepcion", "Antonia", "Francisca", "Manuela", "Esther",
        ],
        "it": [
            "Marco", "Andrea", "Luca", "Francesco", "Matteo", "Alessandro",
            "Giuseppe", "Stefano", "Roberto", "Paolo", "Antonio", "Mario",
            "Giovanni", "Giulio", "Massimo", "Davide", "Simone", "Riccardo",
            "Federico", "Lorenzo", "Tommaso", "Mattia", "Edoardo", "Nicolo",
            "Daniele", "Fabio", "Claudio", "Sergio", "Bruno", "Vincenzo",
            "Maria", "Giulia", "Sofia", "Anna", "Chiara", "Sara", "Laura",
            "Francesca", "Alessia", "Federica", "Valentina", "Elena", "Silvia",
            "Roberta", "Cristina", "Stefania", "Monica", "Giorgia", "Martina",
            "Aurora", "Greta", "Beatrice", "Alessandra", "Paola", "Antonella",
        ],
        "pt": [
            "Joao", "Antonio", "Jose", "Manuel", "Francisco", "Carlos", "Paulo",
            "Pedro", "Luis", "Miguel", "Bruno", "Ricardo", "Andre", "Rui",
            "Tiago", "Daniel", "Hugo", "Sergio", "Diogo", "Fernando", "Mario",
            "Maria", "Ana", "Sofia", "Joana", "Sandra", "Patricia", "Catarina",
            "Sara", "Mariana", "Beatriz", "Ines", "Carla", "Helena", "Margarida",
            "Susana", "Vanessa", "Filipa", "Cristina", "Lucia", "Rita",
        ],
    }

    _ensure_dir(ASSETS_DIR / "firstnames")
    for lang, names in seeds.items():
        out = ASSETS_DIR / "firstnames" / f"{lang}.txt"
        out.write_text(
            "# Prenoms (seed minimale). A enrichir depuis :\n"
            "#   FR  : INSEE etat civil (https://www.insee.fr)\n"
            "#   DE  : WikiData property P735 + filtre par usage allemand\n"
            "#   EN  : SSA baby names / UK ONS\n"
            "#   ES  : INE Espana\n"
            "#   IT  : ISTAT\n"
            + "\n".join(sorted(set(names))) + "\n",
            encoding="utf-8",
        )
        print(f"  {lang}: {len(set(names)):>4} prenoms -> {out.relative_to(REPO_ROOT)}")

    # Stoplist : prenoms ambigus avec des noms communs
    stoplist = sorted({
        "marie",      # FR : prenom mais aussi "se marier"
        "rose",       # FR : prenom mais aussi couleur/fleur
        "lys",        # FR
        "iris", "ivy",
        "june", "may", "april",  # mois EN
        "victoire",  # nom commun FR
    })
    stop_path = ASSETS_DIR / "firstnames" / "_stoplist.txt"
    stop_path.write_text(
        "# Mots qui sont des prenoms ET des noms communs frequents.\n"
        "# Exclus du dictionnaire de prenoms pour eviter les faux positifs.\n"
        + "\n".join(stoplist) + "\n",
        encoding="utf-8",
    )
    print(f"  stoplist: {len(stoplist)} mots -> {stop_path.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Carnaval dictionaries")
    parser.add_argument(
        "category",
        choices=["cities", "firstnames", "all"],
        help="Categorie a (re)generer",
    )
    parser.add_argument(
        "--lang",
        action="append",
        choices=["fr", "de", "en", "es", "it", "pt"],
        help="Limiter aux langues specifiees (peut etre repete)",
    )
    args = parser.parse_args()

    if args.category in ("cities", "all"):
        try:
            build_cities(args.lang)
        except Exception as e:
            print(f"  ERREUR cities : {e}", file=sys.stderr)
            sys.exit(1)

    if args.category in ("firstnames", "all"):
        _write_firstnames_seed()

    print("\nOK")


if __name__ == "__main__":
    main()
