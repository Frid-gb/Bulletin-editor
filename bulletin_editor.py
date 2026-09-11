"""
Bulletin de notes - Gestion de notes scolaires avec interface CustomTkinter.

Architecture du fichier :
    1. CONSTANTES
    2. STOCKAGE         -> Store (bulletins), Settings (options)
    3. CALCULS          -> fonctions pures, une responsabilité par fonction
    4. COULEURS         -> couleur_pour_valeur()
    5. DIALOGUES        -> CTkToplevel modaux
    6. VUES             -> VueAccueil, VueEditeur
    7. APPLICATION      -> BulletinApp
    8. POINT D'ENTRÉE
"""

import customtkinter as ctk
import json
import os
import sys
import uuid
import platform
import traceback
from pathlib import Path
from tkinter import messagebox


# ============================================================
# 1. CONSTANTES
# ============================================================

APP_NAME = "BulletinsNotes"

# Paliers de couleurs (du plus haut au plus bas)
# On parcourt dans l'ordre et on prend le premier seuil <= valeur.
SEUILS_COULEURS = [
    (16.0, "#2ECC71"),   # >= 16 : vert clair  (excellent)
    (14.0, "#27AE60"),   # >= 14 : vert        (bien)
    (12.0, "#F1C40F"),   # >= 12 : jaune       (moyen)
    (10.0, "#E67E22"),   # >= 10 : orange      (passable)
    (0.0,  "#E74C3C"),   # <  10 : rouge       (insuffisant)
]

COULEUR_NEUTRE = "#888888"   # quand pas de valeur

# Modes possibles pour la moyenne d'une matière
MODES_MOYENNE_MATIERE = {
    "simple":   "Moyenne simple : toutes les notes comptent pareil",
    "ponderee": "Moyenne pondérée : chaque note × son coefficient",
    "mixte":    "Système éducatif : (moyenne interros + somme devoirs) / (1 + nb devoirs)",
}
MODE_MOYENNE_PAR_DEFAUT = "mixte"


# ============================================================
# 2. STOCKAGE
# ============================================================

def get_app_data_dir() -> Path:
    """Retourne le dossier AppData selon l'OS. Repli dans le cwd en cas d'échec."""
    system = platform.system()
    try:
        if system == "Windows":
            base = os.environ.get("APPDATA")
            if not base:
                raise EnvironmentError("Variable APPDATA introuvable")
            return Path(base) / APP_NAME
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        return Path.home() / ".local" / "share" / APP_NAME
    except Exception as exc:
        print(f"[avertissement] AppData inaccessible ({exc}), repli dans le dossier courant")
        return Path.cwd() / APP_NAME


DATA_FILE = get_app_data_dir() / "bulletins.json"
SETTINGS_FILE = get_app_data_dir() / "settings.json"
print(f"[info] Données  : {DATA_FILE}")
print(f"[info] Options  : {SETTINGS_FILE}")


# ------------------------------------------------------------
# 2.a - Lecture / écriture génériques
# ------------------------------------------------------------

def lire_json(path: Path):
    """Lit un fichier JSON. Retourne None si le fichier n'existe pas ou est vide."""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        contenu = f.read().strip()
    if not contenu:
        return None
    return json.loads(contenu)


def ecrire_json(path: Path, donnees) -> None:
    """Écrit un objet Python en JSON, en créant les dossiers si besoin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(donnees, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------
# 2.b - Store des bulletins
# ------------------------------------------------------------

class Store:
    """Gère les bulletins et leur persistance JSON."""

    def __init__(self, path: Path):
        self.path = path
        self.bulletins: list[dict] = []
        self.charger()

    def charger(self) -> None:
        try:
            data = lire_json(self.path)
            if data is None:
                self.bulletins = []
                return
            if not isinstance(data, dict):
                raise ValueError("La racine doit être un objet JSON.")
            if "bulletins" not in data or not isinstance(data["bulletins"], list):
                raise ValueError("Clé 'bulletins' manquante ou invalide.")
            self.bulletins = data["bulletins"]

        except json.JSONDecodeError as exc:
            messagebox.showwarning(
                "Fichier corrompu",
                f"Le fichier JSON est illisible.\n\nDétail : {exc}",
            )
            self.bulletins = []
        except (ValueError, OSError) as exc:
            messagebox.showwarning(
                "Chargement impossible",
                f"{exc}\n\nDémarrage avec une base vide.",
            )
            self.bulletins = []

    def sauvegarder(self) -> None:
        try:
            ecrire_json(self.path, {"bulletins": self.bulletins})
        except OSError as exc:
            messagebox.showerror("Erreur de sauvegarde", f"{exc}")
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Erreur de sérialisation", f"{exc}")


# ------------------------------------------------------------
# 2.c - Options persistantes
# ------------------------------------------------------------

class Settings:
    """Options de l'application (mode de moyenne, etc.), sauvegardées en JSON."""

    DEFAUTS = {
        "mode_moyenne_matiere": MODE_MOYENNE_PAR_DEFAUT,
    }

    def __init__(self, path: Path):
        self.path = path
        self.donnees: dict = dict(self.DEFAUTS)
        self.charger()

    def charger(self) -> None:
        try:
            data = lire_json(self.path)
            if not isinstance(data, dict):
                return
            # On ne garde que les clés connues
            for cle in self.DEFAUTS:
                if cle in data:
                    self.donnees[cle] = data[cle]
            # Validation : mode inconnu -> défaut
            if self.donnees["mode_moyenne_matiere"] not in MODES_MOYENNE_MATIERE:
                self.donnees["mode_moyenne_matiere"] = MODE_MOYENNE_PAR_DEFAUT
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            print(f"[avertissement] Options illisibles, défauts appliqués : {exc}")

    def sauvegarder(self) -> None:
        try:
            ecrire_json(self.path, self.donnees)
        except OSError as exc:
            messagebox.showerror("Erreur options", f"{exc}")

    def obtenir(self, cle: str):
        return self.donnees.get(cle, self.DEFAUTS.get(cle))

    def definir(self, cle: str, valeur) -> None:
        self.donnees[cle] = valeur
        self.sauvegarder()


# ------------------------------------------------------------
# 2.d - Fabriques de structures
# ------------------------------------------------------------

def nouveau_bulletin(titre: str = "Nouveau bulletin") -> dict:
    return {"id": str(uuid.uuid4()), "titre": titre, "matieres": []}


def nouvelle_matiere(nom: str, coefficient: float) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "nom": nom,
        "coefficient": float(coefficient),
        "interros": [],
        "devoirs": [],
    }


def trouver_bulletin(bulletins: list, bulletin_id: str):
    for b in bulletins:
        if isinstance(b, dict) and b.get("id") == bulletin_id:
            return b
    return None


# ============================================================
# 3. CALCULS  (une responsabilité par fonction)
# ============================================================

# ------------------------------------------------------------
# 3.a - Nettoyage / extraction
# ------------------------------------------------------------

def extraire_valeur(note) -> float | None:
    """Extrait la valeur numérique d'une note. None si invalide."""
    if not isinstance(note, dict):
        return None
    try:
        return float(note.get("valeur"))
    except (TypeError, ValueError):
        return None


def extraire_coefficient(note) -> float | None:
    """Extrait le coefficient d'une note. None si invalide ou <= 0."""
    if not isinstance(note, dict):
        return None
    try:
        coef = float(note.get("coefficient", 1))
    except (TypeError, ValueError):
        return None
    return coef if coef > 0 else None


def note_valide(note) -> bool:
    """Une note est valide si sa valeur et son coefficient sont exploitables."""
    return extraire_valeur(note) is not None and extraire_coefficient(note) is not None


def filtrer_notes(notes) -> list[dict]:
    """
    Retourne une liste de notes valides sous la forme {'valeur': float, 'coefficient': float}.
    Toute note invalide est silencieusement ignorée.
    """
    if not isinstance(notes, list):
        return []
    resultat = []
    for n in notes:
        if not note_valide(n):
            continue
        resultat.append({
            "valeur": extraire_valeur(n),
            "coefficient": extraire_coefficient(n),
        })
    return resultat


def extraire_coefficient_matiere(matiere: dict) -> float:
    """Coefficient d'une matière, garanti > 0 (repli 1.0)."""
    try:
        coef = float(matiere.get("coefficient", 1))
    except (TypeError, ValueError):
        return 1.0
    return coef if coef > 0 else 1.0


# ------------------------------------------------------------
# 3.b - Opérations élémentaires sur une liste de notes propres
#     (chacune prend une list[dict] déjà nettoyée)
# ------------------------------------------------------------

def somme_valeurs(notes: list[dict]) -> float:
    """Somme brute des valeurs de notes."""
    return sum(n["valeur"] for n in notes)


def somme_coefficients(notes: list[dict]) -> float:
    """Somme des coefficients de notes."""
    return sum(n["coefficient"] for n in notes)


def somme_valeurs_ponderees(notes: list[dict]) -> float:
    """Somme des (valeur × coefficient)."""
    return sum(n["valeur"] * n["coefficient"] for n in notes)


def nombre_notes(notes: list[dict]) -> int:
    return len(notes)


# ------------------------------------------------------------
# 3.c - Moyennes élémentaires
# ------------------------------------------------------------

def moyenne_arithmetique(notes: list[dict]) -> float | None:
    """Moyenne simple = somme(valeurs) / nombre de notes."""
    if not notes:
        return None
    return somme_valeurs(notes) / nombre_notes(notes)


def moyenne_ponderee(notes: list[dict]) -> float | None:
    """Moyenne pondérée = somme(valeur × coef) / somme(coef)."""
    if not notes:
        return None
    total_coef = somme_coefficients(notes)
    if total_coef <= 0:
        return None
    return somme_valeurs_ponderees(notes) / total_coef


# ------------------------------------------------------------
# 3.d - Moyenne d'une matière selon le mode choisi
# ------------------------------------------------------------

def moyenne_matiere_simple(matiere: dict) -> float | None:
    """Mode 'simple' : toutes les notes (interros + devoirs) comptent pareil."""
    interros = filtrer_notes(matiere.get("interros", []))
    devoirs = filtrer_notes(matiere.get("devoirs", []))
    return moyenne_arithmetique(interros + devoirs)


def moyenne_matiere_ponderee(matiere: dict) -> float | None:
    """Mode 'pondérée' : chaque note × son propre coefficient."""
    interros = filtrer_notes(matiere.get("interros", []))
    devoirs = filtrer_notes(matiere.get("devoirs", []))
    return moyenne_ponderee(interros + devoirs)


def moyenne_matiere_mixte(matiere: dict) -> float | None:
    """
    Mode 'système éducatif' (mode par défaut) :
        numérateur   = moyenne_interros + somme(valeurs des devoirs)
        dénominateur = 1 + nombre de devoirs

    Cas particuliers :
        - aucune note            -> None
        - pas d'interros         -> moyenne simple des devoirs
        - pas de devoirs         -> moyenne simple des interros
    """
    interros = filtrer_notes(matiere.get("interros", []))
    devoirs = filtrer_notes(matiere.get("devoirs", []))

    if not interros and not devoirs:
        return None
    if not interros:
        return moyenne_arithmetique(devoirs)
    if not devoirs:
        return moyenne_arithmetique(interros)

    moy_int = moyenne_arithmetique(interros)
    somme_dev = somme_valeurs(devoirs)
    nb_dev = nombre_notes(devoirs)

    return (moy_int + somme_dev) / (1 + nb_dev)


def calculer_moyenne_matiere(matiere: dict, mode: str) -> float | None:
    """Dispatch vers la bonne méthode de calcul selon le mode choisi."""
    if mode == "simple":
        return moyenne_matiere_simple(matiere)
    if mode == "ponderee":
        return moyenne_matiere_ponderee(matiere)
    if mode == "mixte":
        return moyenne_matiere_mixte(matiere)
    # Mode inconnu -> on retombe sur le mode par défaut
    return moyenne_matiere_mixte(matiere)


# ------------------------------------------------------------
# 3.e - Moyennes générales (par bulletin)
# ------------------------------------------------------------

def collecter_moyennes_matieres(bulletin: dict, mode: str) -> list[tuple[float, float]]:
    """
    Retourne une liste de tuples (moyenne_matiere, coefficient_matiere)
    pour toutes les matières ayant au moins une note.
    """
    matieres = bulletin.get("matieres", [])
    if not isinstance(matieres, list):
        return []

    resultat = []
    for matiere in matieres:
        if not isinstance(matiere, dict):
            continue
        moy = calculer_moyenne_matiere(matiere, mode)
        if moy is None:
            continue
        coef = extraire_coefficient_matiere(matiere)
        resultat.append((moy, coef))
    return resultat


def moyenne_generale_ponderee(entrees: list[tuple[float, float]]) -> float | None:
    """
    Moyenne générale pondérée par les coefficients des matières.
    = somme(moy_matiere × coef_matiere) / somme(coef_matiere)
    """
    if not entrees:
        return None
    total = sum(moy * coef for moy, coef in entrees)
    total_coef = sum(coef for _, coef in entrees)
    if total_coef <= 0:
        return None
    return total / total_coef


def moyenne_generale_simple(entrees: list[tuple[float, float]]) -> float | None:
    """
    Moyenne générale arithmétique simple : chaque matière compte autant,
    indépendamment de son coefficient.
    = somme(moy_matiere) / nombre de matières
    """
    if not entrees:
        return None
    return sum(moy for moy, _ in entrees) / len(entrees)


def calculer_moyennes_generales(bulletin: dict, mode: str) -> dict:
    """
    Calcule toutes les moyennes générales d'un bulletin.

    Retourne un dict avec :
        - 'entrees'  : list[(moy_matiere, coef_matiere)] pour usage annexe
        - 'ponderee' : moyenne générale pondérée par les coefs de matière
        - 'simple'   : moyenne générale arithmétique simple
    """
    entrees = collecter_moyennes_matieres(bulletin, mode)
    return {
        "entrees":  entrees,
        "ponderee": moyenne_generale_ponderee(entrees),
        "simple":   moyenne_generale_simple(entrees),
    }


def moyenne_coefficientee(moyenne: float | None, coefficient: float) -> float | None:
    """Retourne moyenne × coefficient (utile pour visualiser le poids d'une matière)."""
    if moyenne is None:
        return None
    return moyenne * coefficient


# ============================================================
# 4. COULEURS
# ============================================================

def couleur_pour_valeur(valeur) -> str:
    """
    Retourne une couleur hexadécimale selon la valeur.
    Parcourt SEUILS_COULEURS et retourne la couleur du premier seuil atteint.
    Retourne COULEUR_NEUTRE si la valeur est None ou non numérique.
    """
    if valeur is None:
        return COULEUR_NEUTRE
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return COULEUR_NEUTRE
    for seuil, couleur in SEUILS_COULEURS:
        if v >= seuil:
            return couleur
    return COULEUR_NEUTRE


# ============================================================
# 5. DIALOGUES
# ============================================================

class DialogueBase(ctk.CTkToplevel):
    """Base commune : gestion modale, touches Entrée/Échap, résultat."""

    def __init__(self, master, titre: str, largeur: int, hauteur: int):
        super().__init__(master)
        self.title(titre)
        self.geometry(f"{largeur}x{hauteur}")
        self.resizable(False, False)
        self.resultat = None

        self.bind("<Return>", lambda e: self._valider())
        self.bind("<Escape>", lambda e: self._annuler())

        self.transient(master)
        self.after(50, self._finaliser)

    def _finaliser(self):
        """Active le grab_set et donne le focus (appelé après affichage)."""
        try:
            self.grab_set()
            self._focus_initial()
        except Exception:
            pass

    def _focus_initial(self):
        """À surcharger : place le focus sur le premier champ."""
        pass

    def _valider(self):
        """À surcharger : doit set self.resultat puis destroy()."""
        raise NotImplementedError

    def _annuler(self):
        self.resultat = None
        self.destroy()

    def obtenir(self):
        """Affiche le dialogue et bloque jusqu'à sa fermeture."""
        self.wait_window()
        return self.resultat


class DialogueTexte(DialogueBase):
    """Demande une simple chaîne de caractères."""

    def __init__(self, master, titre="Saisie", message="", valeur_defaut=""):
        super().__init__(master, titre, 400, 170)

        ctk.CTkLabel(self, text=message).pack(pady=(20, 8), padx=20, anchor="w")
        self.entry = ctk.CTkEntry(self)
        self.entry.pack(padx=20, fill="x")
        self.entry.insert(0, valeur_defaut)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=20)
        ctk.CTkButton(btns, text="Annuler", width=100, command=self._annuler).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Valider", width=100, command=self._valider).pack(side="left", padx=5)

    def _focus_initial(self):
        self.entry.focus_set()
        self.entry.select_range(0, "end")

    def _valider(self):
        self.resultat = self.entry.get()
        self.destroy()


class DialogueMatiere(DialogueBase):
    """Demande un nom de matière + son coefficient (création ou édition)."""

    def __init__(self, master,
                 titre_fenetre="Nouvelle matière",
                 nom_defaut="",
                 coef_defaut: float = 1.0):
        super().__init__(master, titre_fenetre, 400, 250)

        ctk.CTkLabel(self, text="Nom de la matière :").pack(pady=(20, 4), padx=20, anchor="w")
        self.entry_nom = ctk.CTkEntry(self)
        self.entry_nom.pack(padx=20, fill="x")
        if nom_defaut:
            self.entry_nom.insert(0, nom_defaut)

        ctk.CTkLabel(self, text="Coefficient :").pack(pady=(10, 4), padx=20, anchor="w")
        self.entry_coef = ctk.CTkEntry(self)
        self.entry_coef.pack(padx=20, fill="x")
        self.entry_coef.insert(0, f"{coef_defaut:g}")

        self.erreur = ctk.CTkLabel(self, text="", text_color="#E06060")
        self.erreur.pack(pady=(8, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Annuler", width=100, command=self._annuler).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Valider", width=100, command=self._valider).pack(side="left", padx=5)

    def _focus_initial(self):
        self.entry_nom.focus_set()
        self.entry_nom.select_range(0, "end")

    def _valider(self):
        nom = self.entry_nom.get().strip()
        if not nom:
            self.erreur.configure(text="Le nom ne peut pas être vide.")
            return
        try:
            coef = float(self.entry_coef.get().replace(",", "."))
            if coef <= 0:
                raise ValueError
        except ValueError:
            self.erreur.configure(text="Coefficient invalide (nombre > 0 attendu).")
            return
        self.resultat = (nom, coef)
        self.destroy()


class DialogueNote(DialogueBase):
    """Demande une note (0-20) + son coefficient (création ou édition)."""

    def __init__(self, master,
                 titre="Nouvelle note",
                 note_defaut: float | None = None,
                 coef_defaut: float | None = None):
        super().__init__(master, titre, 400, 270)

        ctk.CTkLabel(self, text="Note (sur 20) :").pack(pady=(20, 4), padx=20, anchor="w")
        self.entry_note = ctk.CTkEntry(self)
        self.entry_note.pack(padx=20, fill="x")
        self.entry_note.insert(0, f"{note_defaut:g}" if note_defaut is not None else "10")

        ctk.CTkLabel(self, text="Coefficient de la note :").pack(pady=(10, 4), padx=20, anchor="w")
        self.entry_coef = ctk.CTkEntry(self)
        self.entry_coef.pack(padx=20, fill="x")
        self.entry_coef.insert(0, f"{coef_defaut:g}" if coef_defaut is not None else "1")

        self.erreur = ctk.CTkLabel(self, text="", text_color="#E06060")
        self.erreur.pack(pady=(8, 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="Annuler", width=100, command=self._annuler).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="Valider", width=100, command=self._valider).pack(side="left", padx=5)

    def _focus_initial(self):
        self.entry_note.focus_set()
        self.entry_note.select_range(0, "end")

    def _valider(self):
        try:
            note = float(self.entry_note.get().replace(",", "."))
            coef = float(self.entry_coef.get().replace(",", "."))
        except ValueError:
            self.erreur.configure(text="Valeurs numériques attendues.")
            return
        if not (0 <= note <= 20):
            self.erreur.configure(text="La note doit être entre 0 et 20.")
            return
        if coef <= 0:
            self.erreur.configure(text="Le coefficient doit être > 0.")
            return
        self.resultat = {"valeur": note, "coefficient": coef}
        self.destroy()


class DialogueOptions(DialogueBase):
    """Menu des options (mode de calcul de la moyenne par matière)."""

    def __init__(self, master, settings: Settings):
        super().__init__(master, "Options", 520, 320)
        self.settings = settings

        ctk.CTkLabel(self, text="Mode de calcul de la moyenne par matière",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 4), padx=20, anchor="w")
        ctk.CTkLabel(self,
                     text="Choisissez comment chaque matière combine ses interros et devoirs.",
                     text_color="gray").pack(padx=20, anchor="w")

        self.var_mode = ctk.StringVar(value=settings.obtenir("mode_moyenne_matiere"))

        cadre = ctk.CTkFrame(self)
        cadre.pack(fill="x", padx=20, pady=16)

        for cle, description in MODES_MOYENNE_MATIERE.items():
            rb = ctk.CTkRadioButton(cadre,
                                    text=description,
                                    variable=self.var_mode,
                                    value=cle)
            rb.pack(anchor="w", padx=14, pady=8)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Annuler", width=110, command=self._annuler).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Enregistrer", width=130, command=self._valider).pack(side="left", padx=6)

    def _focus_initial(self):
        pass

    def _valider(self):
        mode = self.var_mode.get()
        if mode not in MODES_MOYENNE_MATIERE:
            messagebox.showerror("Option invalide", f"Mode inconnu : {mode}")
            return
        self.settings.definir("mode_moyenne_matiere", mode)
        self.resultat = mode
        self.destroy()


# ============================================================
# 6. VUES
# ============================================================

class VueAccueil(ctk.CTkFrame):
    """Liste des bulletins avec création / ouverture / suppression + Options."""

    def __init__(self, master, app: "BulletinApp"):
        super().__init__(master, fg_color="transparent")
        self.app = app

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(top, text="📚 Mes bulletins",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        ctk.CTkButton(top, text="⚙ Options", width=110,
                      command=self.ouvrir_options).pack(side="right", padx=(6, 0))
        ctk.CTkButton(top, text="+ Nouveau bulletin", width=170,
                      command=self.creer_bulletin).pack(side="right", padx=6)

        # Indication du mode actuel
        mode = self.app.settings.obtenir("mode_moyenne_matiere")
        self.label_mode = ctk.CTkLabel(
            self,
            text=f"Mode actuel : {MODES_MOYENNE_MATIERE.get(mode, mode)}",
            text_color="gray",
        )
        self.label_mode.pack(anchor="w", padx=22, pady=(0, 6))

        self.liste = ctk.CTkScrollableFrame(self, label_text="")
        self.liste.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.rafraichir()

    # ---------- Boutons ----------

    def ouvrir_options(self):
        DialogueOptions(self, self.app.settings).obtenir()
        # Rafraîchit l'indication et les moyennes
        mode = self.app.settings.obtenir("mode_moyenne_matiere")
        self.label_mode.configure(text=f"Mode actuel : {MODES_MOYENNE_MATIERE.get(mode, mode)}")
        self.rafraichir()

    def creer_bulletin(self):
        dlg = DialogueTexte(self, titre="Nouveau bulletin",
                            message="Titre du bulletin :",
                            valeur_defaut="Nouveau bulletin")
        resultat = dlg.obtenir()
        if resultat is None:
            return
        titre = resultat.strip() or "Nouveau bulletin"
        b = nouveau_bulletin(titre)
        self.app.store.bulletins.append(b)
        self.app.store.sauvegarder()
        self.app.ouvrir_bulletin(b["id"])

    def supprimer(self, bulletin: dict):
        titre = bulletin.get("titre", "Sans titre")
        if not messagebox.askyesno("Confirmer",
                                   f"Supprimer définitivement « {titre} » ?"):
            return
        try:
            self.app.store.bulletins.remove(bulletin)
            self.app.store.sauvegarder()
        except ValueError:
            messagebox.showerror("Erreur", "Bulletin introuvable.")
        self.rafraichir()

    # ---------- Rendu ----------

    def rafraichir(self):
        for w in self.liste.winfo_children():
            w.destroy()

        bulletins = self.app.store.bulletins
        if not bulletins:
            ctk.CTkLabel(self.liste, text="Aucun bulletin. Créez-en un !",
                         text_color="gray").pack(pady=40)
            return

        mode = self.app.settings.obtenir("mode_moyenne_matiere")
        for b in bulletins:
            self._creer_ligne(b, mode)

    def _creer_ligne(self, bulletin: dict, mode: str):
        ligne = ctk.CTkFrame(self.liste)
        ligne.pack(fill="x", pady=6, padx=4)

        info = ctk.CTkFrame(ligne, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        ctk.CTkLabel(info, text=bulletin.get("titre", "Sans titre"),
                     font=ctk.CTkFont(size=16, weight="bold"),
                     anchor="w").pack(anchor="w")

        nb_mat = len(bulletin.get("matieres", [])) if isinstance(bulletin.get("matieres"), list) else 0
        moyennes = calculer_moyennes_generales(bulletin, mode)

        # Ligne d'informations avec les deux moyennes colorées
        sous = ctk.CTkFrame(info, fg_color="transparent")
        sous.pack(anchor="w")

        ctk.CTkLabel(sous, text=f"{nb_mat} matière(s)  •  ", text_color="gray").pack(side="left")

        ctk.CTkLabel(sous, text="Pondérée : ", text_color="gray").pack(side="left")
        pond = moyennes["ponderee"]
        ctk.CTkLabel(sous,
                     text=(f"{pond:.2f}/20" if pond is not None else "—"),
                     text_color=couleur_pour_valeur(pond),
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        ctk.CTkLabel(sous, text="   Simple : ", text_color="gray").pack(side="left")
        simple = moyennes["simple"]
        ctk.CTkLabel(sous,
                     text=(f"{simple:.2f}/20" if simple is not None else "—"),
                     text_color=couleur_pour_valeur(simple),
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        ctk.CTkButton(ligne, text="Supprimer", width=100,
                      fg_color="#8B2E2E", hover_color="#A63A3A",
                      command=lambda: self.supprimer(bulletin)).pack(side="right", padx=(4, 12))
        ctk.CTkButton(ligne, text="Ouvrir", width=100,
                      command=lambda: self.app.ouvrir_bulletin(bulletin.get("id"))).pack(side="right", padx=4)


class VueEditeur(ctk.CTkFrame):
    """Éditeur d'un bulletin : titre, matières, interros, devoirs."""

    def __init__(self, master, app: "BulletinApp", bulletin: dict):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.bulletin = bulletin

        # Sécurisation de la structure
        self.bulletin.setdefault("matieres", [])
        if not isinstance(self.bulletin["matieres"], list):
            self.bulletin["matieres"] = []

        # ----- Barre supérieure -----
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20, 6))

        ctk.CTkButton(top, text="← Retour", width=100,
                      command=self.retour).pack(side="left")

        ctk.CTkLabel(top, text="Titre :").pack(side="left", padx=(20, 6))
        self.entry_titre = ctk.CTkEntry(top, width=280)
        self.entry_titre.pack(side="left")
        self.entry_titre.insert(0, self.bulletin.get("titre", ""))
        self.entry_titre.bind("<FocusOut>", lambda e: self._enregistrer_titre())
        self.entry_titre.bind("<Return>",   lambda e: self._enregistrer_titre())

        ctk.CTkButton(top, text="+ Matière", width=120,
                      command=self.ajouter_matiere).pack(side="right")

        # ----- Deux moyennes générales en haut à droite -----
        self.cadre_moyennes = ctk.CTkFrame(self, fg_color="transparent")
        self.cadre_moyennes.pack(fill="x", padx=20)

        self.label_moy_ponderee = ctk.CTkLabel(self.cadre_moyennes, text="",
                                               font=ctk.CTkFont(size=15, weight="bold"))
        self.label_moy_ponderee.pack(side="right", padx=(20, 0))

        self.label_moy_simple = ctk.CTkLabel(self.cadre_moyennes, text="",
                                             font=ctk.CTkFont(size=15, weight="bold"))
        self.label_moy_simple.pack(side="right")

        # ----- Zone scrollable -----
        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=20, pady=(6, 20))

        self.rafraichir()

    # ---------- Titre ----------

    def _enregistrer_titre(self):
        nouveau = self.entry_titre.get().strip()
        if not nouveau:
            # Refus d'un titre vide
            self.entry_titre.delete(0, "end")
            self.entry_titre.insert(0, self.bulletin.get("titre", ""))
            return
        if nouveau != self.bulletin.get("titre"):
            self.bulletin["titre"] = nouveau
            self.app.store.sauvegarder()

    def retour(self):
        self._enregistrer_titre()
        self.app.afficher_accueil()

    # ---------- Rafraîchissement ----------

    def _mode_courant(self) -> str:
        return self.app.settings.obtenir("mode_moyenne_matiere")

    def rafraichir(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        mode = self._mode_courant()

        if not self.bulletin["matieres"]:
            ctk.CTkLabel(self.scroll, text="Aucune matière. Ajoutez-en une !",
                         text_color="gray").pack(pady=40)
        else:
            for m in self.bulletin["matieres"]:
                self._creer_carte_matiere(m, mode)

        # Mise à jour des deux moyennes générales
        moyennes = calculer_moyennes_generales(self.bulletin, mode)
        pond = moyennes["ponderee"]
        simple = moyennes["simple"]

        self.label_moy_ponderee.configure(
            text=f"Pondérée (coefs) : {pond:.2f}/20" if pond is not None else "Pondérée (coefs) : —",
            text_color=couleur_pour_valeur(pond),
        )
        self.label_moy_simple.configure(
            text=f"Simple : {simple:.2f}/20" if simple is not None else "Simple : —",
            text_color=couleur_pour_valeur(simple),
        )

    # ---------- Matières ----------

    def ajouter_matiere(self):
        dlg = DialogueMatiere(self, titre_fenetre="Nouvelle matière")
        res = dlg.obtenir()
        if res is None:
            return
        nom, coef = res
        self.bulletin["matieres"].append(nouvelle_matiere(nom, coef))
        self.app.store.sauvegarder()
        self.rafraichir()

    def modifier_matiere(self, matiere: dict):
        try:
            nom_actuel = str(matiere.get("nom", ""))
            coef_actuel = float(matiere.get("coefficient", 1))
        except (TypeError, ValueError):
            nom_actuel, coef_actuel = "", 1.0

        dlg = DialogueMatiere(self,
                              titre_fenetre=f"Modifier « {nom_actuel} »",
                              nom_defaut=nom_actuel,
                              coef_defaut=coef_actuel)
        res = dlg.obtenir()
        if res is None:
            return
        matiere["nom"], matiere["coefficient"] = res
        self.app.store.sauvegarder()
        self.rafraichir()

    def supprimer_matiere(self, matiere: dict):
        nom = matiere.get("nom", "?")
        if not messagebox.askyesno("Confirmer", f"Supprimer la matière « {nom} » ?"):
            return
        try:
            self.bulletin["matieres"].remove(matiere)
            self.app.store.sauvegarder()
        except ValueError:
            messagebox.showerror("Erreur", "Matière introuvable.")
        self.rafraichir()

    def _creer_carte_matiere(self, matiere: dict, mode: str):
        carte = ctk.CTkFrame(self.scroll)
        carte.pack(fill="x", pady=8, padx=4)

        # Calculs pour cette matière
        coef_mat = extraire_coefficient_matiere(matiere)
        moy = calculer_moyenne_matiere(matiere, mode)
        moy_coef = moyenne_coefficientee(moy, coef_mat)

        # ----- En-tête -----
        entete = ctk.CTkFrame(carte, fg_color="transparent")
        entete.pack(fill="x", padx=12, pady=(10, 6))

        # Nom + coef (à gauche)
        ctk.CTkLabel(entete, text=matiere.get("nom", "?"),
                     font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkLabel(entete, text=f"  (coef {coef_mat:g})",
                     text_color="gray").pack(side="left")

        # Boutons (à droite)
        ctk.CTkButton(entete, text="🗑", width=34,
                      fg_color="#8B2E2E", hover_color="#A63A3A",
                      command=lambda: self.supprimer_matiere(matiere)).pack(side="right", padx=4)
        ctk.CTkButton(entete, text="✎", width=34,
                      command=lambda: self.modifier_matiere(matiere)).pack(side="right", padx=4)

        # Moyenne coefficientée (à droite, avant les boutons)
        txt_moycoef = f"Moy. coef. : {moy_coef:.2f}" if moy_coef is not None else "Moy. coef. : —"
        ctk.CTkLabel(entete, text=txt_moycoef,
                     text_color=couleur_pour_valeur(moy),
                     font=ctk.CTkFont(size=13)).pack(side="right", padx=12)

        # Moyenne de la matière (à droite)
        txt_moy = f"Moyenne : {moy:.2f}/20" if moy is not None else "Moyenne : —"
        ctk.CTkLabel(entete, text=txt_moy,
                     text_color=couleur_pour_valeur(moy),
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right", padx=12)

        # ----- Deux colonnes interros / devoirs -----
        colonnes = ctk.CTkFrame(carte, fg_color="transparent")
        colonnes.pack(fill="x", padx=12, pady=(0, 12))

        self._creer_colonne_notes(colonnes, matiere, "interros", "Interros")
        self._creer_colonne_notes(colonnes, matiere, "devoirs",  "Devoirs")

    # ---------- Colonnes de notes ----------

    def _creer_colonne_notes(self, parent, matiere: dict, cle: str, titre: str):
        col = ctk.CTkFrame(parent)
        col.pack(side="left", fill="both", expand=True, padx=6, pady=4)

        entete = ctk.CTkFrame(col, fg_color="transparent")
        entete.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(entete, text=titre,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(entete, text="+", width=30,
                      command=lambda: self.ajouter_note(matiere, cle)).pack(side="right")

        notes = matiere.get(cle, [])
        if not isinstance(notes, list):
            notes = []
            matiere[cle] = notes

        if not notes:
            ctk.CTkLabel(col, text="(aucune)", text_color="gray").pack(pady=6)
        else:
            for i, note in enumerate(notes):
                self._creer_ligne_note(col, matiere, cle, i, note)

            ctk.CTkLabel(col, text="(double-clic pour éditer)",
                         text_color="#666666",
                         font=ctk.CTkFont(size=10)).pack(pady=(2, 0))

        # Moyenne affichée en bas de colonne
        moyenne = moyenne_ponderee(filtrer_notes(notes))
        if moyenne is not None:
            ctk.CTkLabel(col,
                         text=f"Moyenne : {moyenne:.2f}/20",
                         text_color=couleur_pour_valeur(moyenne)).pack(pady=(4, 8))

    def _creer_ligne_note(self, parent, matiere: dict, cle: str, index: int, note: dict):
        """Une ligne : [valeur ×coef] ................ [×]"""
        ligne = ctk.CTkFrame(parent, fg_color="transparent")
        ligne.pack(fill="x", padx=8, pady=2)

        val = extraire_valeur(note)
        coef = extraire_coefficient(note)

        if val is None or coef is None:
            txt = "Note invalide"
            couleur = COULEUR_NEUTRE
        else:
            txt = f"{val:.2f}/20  ×{coef:g}"
            couleur = couleur_pour_valeur(val)

        label = ctk.CTkLabel(ligne, text=txt,
                             text_color=couleur,
                             cursor="hand2")
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Double-Button-1>",
                   lambda e, i=index: self.modifier_note(matiere, cle, i))

        ctk.CTkButton(ligne, text="×", width=26, height=24,
                      fg_color="#8B2E2E", hover_color="#A63A3A",
                      command=lambda i=index: self.supprimer_note(matiere, cle, i)
                      ).pack(side="right")

    # ---------- Opérations sur les notes ----------

    def ajouter_note(self, matiere: dict, cle: str):
        titre = "Nouvelle interro" if cle == "interros" else "Nouveau devoir"
        res = DialogueNote(self, titre=titre).obtenir()
        if res is None:
            return
        matiere.setdefault(cle, [])
        if not isinstance(matiere[cle], list):
            matiere[cle] = []
        matiere[cle].append(res)
        self.app.store.sauvegarder()
        self.rafraichir()

    def modifier_note(self, matiere: dict, cle: str, index: int):
        try:
            note = matiere[cle][index]
        except (KeyError, IndexError, TypeError):
            messagebox.showerror("Erreur", "Note introuvable.")
            return

        val = extraire_valeur(note)
        coef = extraire_coefficient(note)
        if val is None: val = 0.0
        if coef is None: coef = 1.0

        titre = "Modifier l'interro" if cle == "interros" else "Modifier le devoir"
        res = DialogueNote(self, titre=titre,
                           note_defaut=val, coef_defaut=coef).obtenir()
        if res is None:
            return
        note["valeur"] = res["valeur"]
        note["coefficient"] = res["coefficient"]
        self.app.store.sauvegarder()
        self.rafraichir()

    def supprimer_note(self, matiere: dict, cle: str, index: int):
        try:
            del matiere[cle][index]
        except (KeyError, IndexError, TypeError):
            messagebox.showerror("Erreur", "Impossible de supprimer cette note.")
            return
        self.app.store.sauvegarder()
        self.rafraichir()


# ============================================================
# 7. APPLICATION
# ============================================================

class BulletinApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Editeur de Bulletins de notes")
       # self.geometry("100x720")
        self.minsize(850, 520)

        self.store = Store(DATA_FILE)
        self.settings = Settings(SETTINGS_FILE)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.vue_courante: ctk.CTkFrame | None = None
        self.afficher_accueil()

    def changer_vue(self, classe_vue, **kwargs):
        try:
            if self.vue_courante is not None:
                self.vue_courante.destroy()
                self.vue_courante = None
            self.vue_courante = classe_vue(self.container, self, **kwargs)
            self.vue_courante.pack(fill="both", expand=True)
        except Exception as exc:
            traceback.print_exc()
            messagebox.showerror("Erreur d'affichage", f"{exc}")

    def afficher_accueil(self):
        self.after(1, lambda: self.changer_vue(VueAccueil))

    def ouvrir_bulletin(self, bulletin_id):
        bulletin = trouver_bulletin(self.store.bulletins, bulletin_id)
        if bulletin is None:
            messagebox.showerror("Introuvable", "Ce bulletin n'existe plus.")
            self.afficher_accueil()
            return
        self.after(1, lambda: self.changer_vue(VueEditeur, bulletin=bulletin))


# ============================================================
# 8. POINT D'ENTRÉE
# ============================================================

def main():
    try:
        app = BulletinApp()
        app.mainloop()
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror("Erreur fatale",
                                 "Une erreur inattendue est survenue.\n"
                                 "Consultez la console pour la trace complète.")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()