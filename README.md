# Bulletin editor 

A desktop application written in Python for managing school report cards: subjects, coefficients, quizzes, homework, automatic averages, and visual color coding.

Modern interface built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter). Data is stored locally as JSON in the user's AppData folder.

> ⚠️ **Language note**
> The **user interface is written in French**, and all **code comments and docstrings are in French** as well. The README is provided in English for broader accessibility, but the app itself targets French-speaking users (and follows the French grading system, out of 20).

---

##  Features

- **Multiple report cards**: create, open, and delete as many as you want (e.g., one per trimester, one per followed subject, one per child…).
- **Subject management**: each subject has a name and a coefficient, both editable at any time.
- **Quizzes and homework separated**: each subject has two categories of grades, each with its own value and coefficient.
- **Automatic calculations**: column averages, subject average, general average — everything is recalculated in real time.
- **Dual general average display**:
  - **Weighted** by subject coefficients.
  - **Simple** (arithmetic), where every subject counts the same.
- **Automatic color coding** on every grade and average (from green for the best to red for the lowest).
- **Three calculation modes** for the subject average, selectable from a saved options menu:
  - Simple average (all grades count equally)
  - Weighted average (each grade × its coefficient)
  - "Educational system" mode: `(quizzes_average + sum_homework) / (1 + number_of_homework)`
- **Quick editing**: double-click a grade to edit it, ✎ icon on a subject to rename it or change its coefficient.
- **Automatic saving** in AppData (Windows / macOS / Linux), with error handling (corrupted file, permissions, etc.).


---

##  Installation

### Requirements

- Python **3.10 or higher** (uses the `float | None` syntax)
- `pip`

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Frid-gb/bulletin-editor.git
cd bulletin-editor

# 2. (Optional) Create a virtual environment
python -m venv .venv
source .venv/bin/activate     # Linux / macOS
.venv\Scripts\activate        # Windows

# 3. Install the dependency
pip install customtkinter
```

### Run the application

```bash
python bulletin_editor.py
```

---

##  Usage

> Reminder: the interface is in **French**.

### Home screen

- **+ Nouveau bulletin** ("New report card"): creates a blank report card and opens the editor directly.
- **⚙ Options**: opens the options menu (subject average calculation mode).
- Each report card shows its number of subjects and its two general averages.
- **Ouvrir** ("Open"): enters the report card editor.
- **Supprimer** ("Delete"): permanently deletes the report card (with confirmation).

### Report card editor

- Edit the report card **title** at the top (saved automatically).
- **+ Matière** ("Add subject"): adds a subject with its coefficient.
- Each subject card displays:
  - Its **name** and **coefficient**
  - Its **average** (colored by value)
  - Its **coefficiented average** (average × subject coefficient)
  - The **✎** (edit) and **🗑** (delete) buttons
- Two columns, **Interros** (quizzes) and **Devoirs** (homework):
  - **+** button to add a grade (value out of 20 + coefficient).
  - **Double-click** on a grade to edit it.
  - **×** button to delete it.
  - Column average displayed at the bottom, colored.
- Top right: the report card's two **general averages** (weighted and simple).

---

##  Calculation methods

> All grades are on a scale of **0 to 20** (French grading system).

### Column average (quizzes or homework)

Always computed as a **weighted average** using each grade's coefficient:

```
column_average = Σ(value × coefficient) / Σ(coefficient)
```

### Subject average

Depends on the **mode** selected in the options.

#### Mode `simple`

All grades (quizzes + homework) count equally:

```
average = Σ(value) / number_of_grades
```

#### Mode `ponderee` (weighted)

Each grade is weighted by its own coefficient:

```
average = Σ(value × coefficient) / Σ(coefficient)
```

#### Mode `mixte` (mixed) *(default, matches the classic French educational system)*

The quizzes average is treated as **a single grade**, and homework is added individually:

```
average = (quizzes_average + Σ(homework_values)) / (1 + number_of_homework)
```

Special cases:
- no quizzes → simple average of homework
- no homework → simple average of quizzes
- no grades at all → not computed (displays `—`)

### General averages

Two averages are always displayed side by side.

**Weighted general average** (takes subject coefficients into account):

```
weighted_average = Σ(subject_average × subject_coefficient) / Σ(subject_coefficient)
```

**Simple general average** (each subject counts equally):

```
simple_average = Σ(subject_average) / number_of_subjects
```

### Color coding

| Value range     | Color       | Meaning |
|-----------------|-------------|---------|
| `≥ 16`          | Light green | Excellent |
| `14 – 16`       | Green       | Good |
| `12 – 14`       | Yellow      | Average |
| `10 – 12`       | Orange      | Passing |
| `< 10`          | Red         | Failing |
| `none`          | Neutral gray| Not computed |

---

##  Data storage

The application writes two JSON files into the user's AppData folder:

| OS      | Path |
|---------|------|
| Windows | `%APPDATA%\BulletinsNotes\` |
| macOS   | `~/Library/Application Support/BulletinsNotes/` |
| Linux   | `~/.local/share/BulletinsNotes/` |

- **`bulletins.json`**: all report cards and their grades.
- **`settings.json`**: application options (calculation mode, etc.).

### Report card structure

```json
{
  "bulletins": [
    {
      "id": "uuid",
      "titre": "Trimestre 1",
      "matieres": [
        {
          "id": "uuid",
          "nom": "Mathématiques",
          "coefficient": 4,
          "interros": [
            { "valeur": 15, "coefficient": 1 },
            { "valeur": 12, "coefficient": 2 }
          ],
          "devoirs": [
            { "valeur": 17, "coefficient": 1 }
          ]
        }
      ]
    }
  ]
}
```

> Note: JSON keys are in French (`titre`, `matieres`, `interros`, `devoirs`, `valeur`, `coefficient`) to stay consistent with the code and the UI.

### Settings structure

```json
{
  "mode_moyenne_matiere": "mixte"
}
```

Possible values: `"simple"`, `"ponderee"`, `"mixte"`.

---

##  Project structure

```
bulletin-editor/
├── bulletin_editor.py           # Main script (all-in-one)
├── README.md
└── docs/                 # (optional) screenshots
    ├── home.png
    └── editor.png
```

The `bulletin_editor.py` file is organized into clearly delimited sections:

| Section | Content |
|---------|---------|
| 1. Constants | Color thresholds, calculation modes, file names |
| 2. Storage | `Store`, `Settings`, JSON read/write, models |
| 3. Calculations | Pure functions, one responsibility per function |
| 4. Colors | `couleur_pour_valeur()` |
| 5. Dialogs | `DialogueBase` and its subclasses (text, subject, grade, options) |
| 6. Views | `VueAccueil`, `VueEditeur` |
| 7. Application | `BulletinApp` (main window, navigation) |
| 8. Entry point | `main()` with fatal exception handling |

> All section names, class names, function names, and inline comments inside the code are in **French**.

---

## ️ Roadmap / Ideas

Some ideas to extend the project:

- [ ] Configurable quizzes/homework weighting per subject (e.g., 60 / 40)
- [ ] PDF export or printing of the report card
- [ ] Preset subjects (French, Math, History & Geography…)
- [ ] Teacher remarks / comments per subject
- [ ] Average evolution chart over time
- [ ] Custom subject ordering
- [ ] Import / export a single report card to share it
- [ ] Multilingual support (extract strings to a translation file)

---

##  Contributing

Contributions are welcome!

1. Fork the project
2. Create a branch (`git checkout -b feature/my-awesome-idea`)
3. Commit your changes (`git commit -m "Add my awesome idea"`)
4. Push to the branch (`git push origin feature/my-awesome-idea`)
5. Open a Pull Request

Please keep the code **readable and well-commented**. Since the project is French-oriented, prefer French comments to stay consistent, but English is acceptable if you're not comfortable with French.

---


##  Acknowledgements

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern UI components.
- Inspired by the traditional French school report card in Benin, where quizzes and homework don't carry the same weight.

---

##  Contact

A question, a suggestion? Open an [issue](../../issues) on GitHub.
You can also reach me at **frdolingb@gmail.com**