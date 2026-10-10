# Guide d'implémentation — `pixelplay.library`

## 1. Objectif et périmètre

`pixelplay.library` regroupe les briques **réutilisables** et **agnostiques de
l'application** : ni outil de diagnostic/POC (→ `pixelplay.debug`), ni jeu
(→ `pixelplay.games`), ni orchestration (→ `menu.py`, `cli.py`).

**Règle d'or de dépendance :** les flèches pointent *toujours* vers `library`.

```
debug/ ─┐
games/ ─┼──► library/
menu.py ┘
```

`library` ne doit **jamais** importer `debug`, `games`, `menu` ni `cli`.

Deux familles de modules :

| Famille | Modules | Matériel requis ? |
|---|---|---|
| **I/O (BLE)** | `panel.py`, `sender.py` | oui |
| **Purs** | `render.py`, `control.py`, `text.py`, `keys.py` | non (testables) |

## 2. Contraintes techniques

- Python ≥ 3.11 (annotations `tuple[int, int]`).
- `from __future__ import annotations` en tête de **chaque** module.
- Dépendances externes : `Pillow` (partout) et `pypixelcolor` **uniquement dans
  `panel.py`**.
- Alias local `Color = tuple[int, int, int]` dans les modules qui manipulent des
  couleurs.
- Pas d'autre E/S que le BLE : pas de `print` (seule exception : erreur
  transitoire du thread d'envoi), pas de fichier, pas de réseau.

## 3. Arborescence

```
src/pixelplay/library/
├── __init__.py   # agrège et ré-exporte l'API publique du sous-package
├── panel.py      # Panel (connexion + push d'une frame) et use_panel()
├── sender.py     # FrameSender (thread « dernier arrivé gagne »)
├── render.py     # renderers purs -> PIL.Image
├── control.py    # Sprite (élément déplaçable) + PALETTE
├── text.py       # police bitmap 4x6 + métriques + draw_text
└── keys.py       # KeyRepeater (auto-repeat clavier)
```

## 4. Graphe de dépendances interne

```
panel.py    ──► pypixelcolor
sender.py   ──► panel.py
render.py     (aucun import interne)
control.py    (aucun import interne)
text.py       (aucun import interne)
keys.py       (aucun import interne)
__init__.py ──► tous
```

## 5. Détail des modules

### 5.1 `panel.py` — accès matériel

Seul module qui touche le BLE (via `pypixelcolor.Client`). Il ne réimplémente
aucune logique bas niveau : il normalise la frame et l'encode.

**`Panel(address, brightness=None)`**

- Se connecte immédiatement (`Client(address).connect()`).
- Récupère `get_device_info()` ; en cas d'échec → `disconnect()` puis re-raise
  (pas de fuite de connexion).
- Expose `width`, `height`, `led_type`, `device_info`.
- Applique `brightness` (0-100) **après** connexion si fourni.

**Membres :**

| Membre | Rôle |
|---|---|
| `size` (property) | `(width, height)` |
| `describe()` | texte multi-ligne lisible (taille, LED, device) |
| `send_png_bytes(png_bytes)` | `send_image_hex(bytes.hex(), ".png")` |
| `send_frame(img)` | convertit en `RGB`, redimensionne si nécessaire, encode en PNG mémoire, puis `send_png_bytes` |
| `close()` | `disconnect()` idempotent (avale les exceptions) |
| `__enter__` / `__exit__` | context manager → `close()` en sortie |

> **Point clé de perf :** `send_frame` produit une image déjà au bon
> format/taille, donc `pypixelcolor` **saute** son propre resize/ré-encodage.

**`use_panel(address, brightness=None, panel=None)`** — context manager :

```python
@contextmanager
def use_panel(address, brightness=None, panel=None):
    if panel is not None:
        yield panel          # panneau "emprunté" : jamais fermé
        return
    with Panel(address, brightness=brightness) as owned:
        yield owned          # panneau "possédé" : fermé en sortie
```

> Un panneau **emprunté** (partagé par le launcher) n'est jamais fermé : le
> propriétaire reste responsable de son cycle de vie.

### 5.2 `sender.py` — envoi asynchrone

`FrameSender(panel, fps)` est un `threading.Thread` **daemon** qui pousse *la
dernière frame soumise*.

- `fps <= 0` → envoi au plus vite ; sinon intervalle `1/fps`.
- **Dernier arrivé gagne** : `submit()` remplace la frame en attente (protégée
  par `Lock` + `Event`).
- `stop()` demande l'arrêt ; `run()` boucle tant que l'événement d'arrêt n'est
  pas levé.
- Compteur `sent` (frames effectivement envoyées).
- Les erreurs d'envoi sont **imprimées**, jamais propagées (le thread survit aux
  erreurs transitoires).
- ⚠️ **Ne pas** nommer l'événement `_stop` (cela masquerait `Thread._stop`).

API : `submit(img)`, `stop()`, `run()`, attribut `sent`.

### 5.3 `render.py` — renderers purs

Fonctions pures `(t, width, height, [color]) -> Image.Image` en mode `RGB` à la
taille demandée.

| Fonction | Description | Défaut couleur |
|---|---|---|
| `render_bars(t, w, h, color)` | barres verticales défilant | `(0, 120, 255)` |
| `render_gradient(t, w, h)` | dégradé animé sinusoïdal | — |
| `render_bouncing_ball(t, w, h, color)` | balle rebondissante | `(255, 64, 0)` |

Helpers privés : `_new_frame(w, h, bg)` → `(Image, ImageDraw)`,
`_ping_pong(period, value)` → valeur `[0, 1]` qui va-et-vient.

Registre : `RENDERERS = {"bars": ..., "gradient": ..., "ball": ...}` (utilisé par
la CLI et `bench`).

> Un renderer est **déterministe** : même `t` ⇒ même image (indispensable pour
> tester le mouvement *et* la répétition de période).

### 5.4 `control.py` — élément déplaçable

`Sprite(size=3, color=PALETTE[0])` : carré dont `(x, y)` est le **centre**,
toujours borné au panneau. Le sprite **ne connaît pas** la taille du panneau :
elle est passée aux méthodes.

- Taille : `size` = demi-côté (le carré couvre `2*size+1` px).
- `PALETTE` : 6 couleurs cyclées par `cycle_color()`.

| Méthode | Effet |
|---|---|
| `set_position(x, y, w, h)` | place et **clampe** dans `[0, w-1] × [0, h-1]` |
| `move(dx, dy, w, h)` | relatif, clampe |
| `center(w, h)` | centre `(w//2, h//2)` |
| `cycle_color()` | couleur suivante (boucle) |
| `render(w, h)` | image `RGB` noire avec le sprite |

### 5.5 `text.py` — police bitmap 4x6

Police en **données pures** (pas de fichier, pas de dépendance supplémentaire,
rendu identique multi-plateforme/Pillow).

- Constantes : `GLYPH_W = 4`, `GLYPH_H = 6`, `SPACING = 1`.
- `GLYPHS: dict[str, tuple[str, ...]]` : 6 lignes de 4 caractères (`'1'` = pixel
  allumé). Couvre `A-Z`, `0-9` et quelques symboles.
- `UNKNOWN` : bloc plein — un caractère non tabulé devient **visible** (un typo
  saute aux yeux plutôt que de disparaître).
- `glyph(char)` : lookup insensible à la casse, `UNKNOWN` par défaut.

Métriques :

| Fonction | Sens |
|---|---|
| `text_advance(scale, spacing)` | pas horizontal entre glyphes |
| `text_width(text, scale, spacing)` | largeur d'une ligne (gap inclus, pas de gap final) |
| `text_height(scale)` | hauteur d'une ligne |
| `text_pitch(scale, spacing)` | pas vertical entre lignes |

Rendu : `draw_text(draw, x, y, text, color, scale=1, spacing=SPACING)` — coin
**haut-gauche** en `(x, y)`. Le clipping hors image est assuré par PIL (pas de
contrôle de bornes côté appelant).

### 5.6 `keys.py` — auto-repeat clavier

`KeyRepeater(delay=REPEAT_DELAY, every=REPEAT_EVERY)` transforme les événements
clavier en **une action par appui**, puis répète.

- Constantes : `REPEAT_DELAY = 3`, `REPEAT_EVERY = 1` (en ticks).
- `press(key)` → `True` si nouvel appui, `False` si auto-repeat OS (à ignorer).
- `release(key)`, `clear()` (perte de focus), `due()` → avance d'un tick et
  renvoie les touches à répéter.
- Le compte est en **ticks**, donc indépendant du moment exact de l'événement :
  un appui court fire exactement une fois.

### 5.7 `__init__.py` — façade

Ré-exporte l'API publique du sous-package et fixe `__all__` (trié). Exemple
d'usage :

```python
from pixelplay.library import Panel, FrameSender, Sprite, render_bouncing_ball
```

## 6. Invariants / contrats à respecter

- Toute image produite ou acceptée est en **`RGB`**.
- `render_*` renvoie exactement `(width, height)`.
- `Sprite` clampe toujours sa position dans le panneau.
- `FrameSender` ne lève jamais dans `run()`.
- `use_panel` ne ferme jamais un panneau emprunté.
- `library` n'importe jamais `debug`/`games`/`menu`/`cli`.

## 7. Ajouter un nouveau renderer

1. Écrire `def render_xxx(t, width, height, color=...) -> Image.Image` dans
   `render.py` en utilisant `_new_frame`.
2. L'ajouter au dict `RENDERERS` sous une clé courte.
3. Exporter la fonction dans `library/__init__.py` (`import` + `__all__`).
4. Ajouter le cas de test paramétré : il sera pris automatiquement par
   `@pytest.mark.parametrize("name", sorted(RENDERERS))`.

## 8. Tester sans matériel — patterns du dépôt

Fichiers de tests sous `tests/library/` (`pytest.ini` : `testpaths = tests`,
`pythonpath = src`).

**Fake BLE** — injecter un faux client via `Panel.__new__` (contourne `__init__`
qui ouvrirait le BLE) :

```python
class FakeClient:
    def __init__(self):
        self.calls = []

    def send_image_hex(self, hex_string, extension, *args, **kwargs):
        self.calls.append((hex_string, extension))


def _make_panel(width=32, height=32):
    panel = Panel.__new__(Panel)
    panel._client = FakeClient()
    panel.width, panel.height = width, height
    panel.led_type, panel.device_info = "RGB", None
    return panel
```

On décode ensuite le PNG pour vérifier taille/mode/pixels (`_decode`).

**Thread `FrameSender`** — `FakePanel` enregistrant les `send_frame`, puis boucle
avec deadline + `stop()`/`join()` et assertion `not sender.is_alive()`.

**Renderers** — double `parametrize` (nom × taille) vérifiant
`Image`/`RGB`/taille ; tests de mouvement (`t=0` vs `t=0.1`) et de répétition
(`t=0` vs `t=1.0`).

**Police** — validation de forme de tous les glyphes, casse, `UNKNOWN`, couverture
`A-Z0-9`, métriques, pixels allumés, mise à l'échelle et clipping.

**Sprite** — démarrage à l'origine, centrage, clampage (set/move), cycle couleur,
rendu pixel à pixel, puis chaîne `render → send_frame`.

## 9. Checklist pour un nouveau module `library`

- [ ] `from __future__ import annotations` en tête.
- [ ] Aucun import vers `debug`/`games`/`menu`/`cli`.
- [ ] Docstring de module + docstrings « parameters » au format NumPy (comme les
      autres).
- [ ] E/S matérielles isolées (comme `panel.py`).
- [ ] Export dans `library/__init__.py` + entrée dans `__all__`.
- [ ] Tests ajoutés sous `tests/library/` sans matériel.
- [ ] `pytest` vert + imports de la surface publique vérifiés.

## 10. Correspondance tests ↔ modules

| Module | Fichier de test |
|---|---|
| `library/panel.py` | `tests/library/test_panel.py` |
| `library/render.py` | `tests/library/test_render.py` |
| `library/control.py` | `tests/library/test_control.py` |
| `library/text.py` | `tests/library/test_text.py` |
| `library/sender.py` | `tests/library/test_control.py` (test du thread) |
| `library/keys.py` | couvert indirectement (`tests/games/test_tetris.py`) |
