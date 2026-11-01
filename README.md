# FreeCAD-PDM

A distributed, lightweight, and open-source **Product Data Management (PDM) / Product Lifecycle Management (PLM)** workbench for **FreeCAD** (0.21+ / 1.1.0+).

FreeCAD-PDM brings file versioning, document lifecycle states, Bill of Materials (BOM) generation, and collaborative revision tracking directly into FreeCAD through both a native PySide GUI and a headless Command Line Interface (CLI).

---

## Features

* **Local & Configurable Vault**: Fully self-contained local vault backed by an embedded **SQLite** engine operating in **WAL (Write-Ahead Logging)** mode for low overhead and safe concurrent read/write access.
* **Embedded Document Management**:
* Check-In and Check-Out operations with custom revision tagging and commit messages.
* Automatic document state tracking directly integrated via FreeCAD document observers.


* **Native GUI Integration**:
* Embedded `PDMDockWidget` side panel displaying active file metadata and complete revision history.
* Dedicated FreeCAD toolbar and menu actions.
* Compatible with PySide2 (FreeCAD 0.21) and PySide6 (FreeCAD 1.1+).


* **Extensible BOM Extraction**: Extract hierarchical assemblies and component counts into distinct Bill of Materials tables.
* **Flexible Storage Configuration**: Customize the vault and metadata database location via FreeCAD User Preferences (`ParamGet`) or the `FREECAD_PDM_DIR` environment variable.

---

## Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│                   FreeCAD Interface                    │
│   ┌──────────────────────────┐  ┌──────────────────┐   │
│   │  PDM Operations Toolbar  │  │  PDM Explorer    │   │
│   │  & Menus (PySide2/6)     │  │  Dock Widget     │   │
│   └─────────────┬────────────┘  └────────┬─────────┘   │
└─────────────────┼────────────────────────┼─────────────┘
                  │                        │
┌─────────────────▼────────────────────────▼─────────────┐
│                    Adapter Layer                       │
│      Commands  •  Document Observers  •  Metadata      │
└─────────────────────────────┬──────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────┐
│                  Core Business Logic                   │
│   ┌──────────────────────────┐  ┌──────────────────┐   │
│   │      Vault Engine        │  │  BOM Extractor   │   │
│   └─────────────┬────────────┘  └──────────────────┘   │
│                 │                                      │
│   ┌─────────────▼────────────┐                         │
│   │  SQLite (WAL) Database   │                         │
│   │  metadata.db             │                         │
│   └──────────────────────────┘                         │
└────────────────────────────────────────────────────────┘

```

---

## Installation

### Manual Installation

Clone or copy this repository into your FreeCAD `Mod` directory:

#### Windows

```powershell
# For FreeCAD 1.1+
cd %APPDATA%\FreeCAD\v1-1\Mod
git clone https://github.com/your-username/FreeCAD-PDM.git

# For FreeCAD 0.21
cd %APPDATA%\FreeCAD\Mod
git clone https://github.com/your-username/FreeCAD-PDM.git

```

#### Linux

```bash
cd ~/.local/share/FreeCAD/Mod
git clone https://github.com/your-username/FreeCAD-PDM.git

```

#### macOS

```bash
cd ~/Library/Application\ Support/FreeCAD/Mod
git clone https://github.com/your-username/FreeCAD-PDM.git

```

Restart FreeCAD after cloning. The **PDM** workbench will appear in the workbench selector bar and dropdown menu.

---

## Vault & Storage Configuration

By default, FreeCAD-PDM stores its repository and the `metadata.db` database in:

```text
~/.freecad_pdm/

```

### Changing the Vault Location

You can customize the storage path in two ways:

1. **FreeCAD Python Console**:
```python
import FreeCAD
FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/PDM").SetString(
    "VaultPath", r"D:\Projects\PDM_Vault"
)

```


2. **Environment Variable**:
Set `FREECAD_PDM_DIR` in your system environment:
```bash
export FREECAD_PDM_DIR="/path/to/my/custom_vault"

```



---

## Directory Structure

```text
FreeCAD-PDM/
├── InitGui.py              # Workbench bootstrap and UI registration
├── package.xml             # FreeCAD Addon metadata descriptor
├── LICENSE                 # License terms (LGPL-2.1-or-later)
├── README.md               # Documentation
└── pdm/
    ├── __init__.py
    ├── core/               # Engine and persistence layer
    │   ├── db.py           # SQLite connection & schema manager
    │   ├── vault.py        # Vault Check-In / Check-Out engine
    │   └── bom.py          # Bill of Materials extraction logic
    ├── freecad/            # FreeCAD event integration
    │   ├── commands.py     # Workbench command declarations
    │   └── observer.py     # Document state observer
    └── ui/                 # User interface
        └── dock_widget.py  # PDM Explorer DockWidget

```

---

## Requirements

* **FreeCAD**: `v0.21.0` or higher (including FreeCAD `1.1.0`+)
* **Python**: `3.8+`
* **Dependencies**: Native standard library (`sqlite3`, `logging`, `os`, `sys`) and standard FreeCAD Qt bindings (`PySide2` or `PySide6`).

---

## License

This project is licensed under the **LGPL-2.1-or-later** license. See the [LICENSE](LICENSE) file for full details.
