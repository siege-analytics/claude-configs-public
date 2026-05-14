---
name: qml-component-review
description: "Review extracted QML components for conformance with the ChordLibrary decomposition pattern (properties-in / signals-out with state groups)."
disable-model-invocation: true
allowed-tools: Read Grep Glob
paths: "**/plugin/ui/*.qml"
---

# QML Component Review Skill

Review QML components extracted from ChordLibrary.qml for conformance with the project's architectural pattern. This skill enforces the **properties-in / signals-out with state groups** pattern established by WalkthroughPanel.qml.

## Architecture: Properties-In / Signals-Out with State Groups

### Pattern (Felgo-inspired, Django analogy)

| Layer | Django Equivalent | QML Equivalent |
|-------|------------------|----------------|
| Data | `models.py` | State QtObjects (`libraryState`, `tuningState`, `calcState`) |
| Logic | `views.py` | ChordLibrary.qml (the router — startup, signal handling, function dispatch) |
| Presentation | `templates/` | `ui/*.qml` panels (properties in, signals out, no direct state mutation) |

### Why not singletons?

We use properties-in/signals-out instead of `pragma Singleton` because:
1. MuseScore's plugin sandbox may not fully support `qmldir` singleton declarations
2. Explicit property dependencies make each component self-documenting
3. The WalkthroughPanel pattern is already proven in production
4. Components remain testable in isolation

## Review Checklist

When reviewing an extracted QML component, verify ALL of the following:

### 1. Interface Declaration (top of file)

```qml
// REQUIRED: Every extracted panel must declare:

Item {  // or ColumnLayout, Flickable, etc.
    id: panelName

    // --- Input properties (data flows IN from parent) ---
    // Pass state groups, not individual properties
    property var library    // libraryState QtObject
    property var tuning     // tuningState QtObject
    property var theme      // theme QtObject (colors)
    // ... only the state groups this panel actually reads

    // --- Output signals (actions flow OUT to parent) ---
    signal someActionRequested(string param1, int param2)
    signal anotherAction()

    // --- Internal state (private to this component) ---
    property bool _internalFlag: false
}
```

**Rules:**
- Properties are READ-ONLY from the component's perspective — never assign to `library.voicingsData` from within the panel
- Signals use past-tense or requested-suffix naming: `insertRequested`, `tuningChanged`, `presetLoaded`
- Internal properties are prefixed with `_` (underscore)
- No `import "model/SomeModule.js"` — JS module calls happen in ChordLibrary.qml's signal handlers, not in the panel

### 2. No Direct State Mutation

```qml
// WRONG — panel directly modifies parent state:
Button {
    onClicked: library.voicingsData = newData  // NEVER
}

// CORRECT — panel emits signal, parent handles it:
Button {
    onClicked: panelName.rebuildRequested()
}
```

The ONLY place that mutates state is ChordLibrary.qml's signal handlers.

### 3. No JS Module Imports

```qml
// WRONG — panel imports JS modules directly:
import "model/IRealParser.js" as IRealParser

// CORRECT — parent wires the result via properties or signal handlers
// The panel just emits: importRequested(text)
// ChordLibrary.qml handles: IRealParser.parseUrl(text) in the signal handler
```

Exception: `theme` color references are fine since they're just property reads.

### 4. Signal Wiring in ChordLibrary.qml

For each extracted panel, ChordLibrary.qml must have a wiring block:

```qml
ImportPanel {
    id: importPanel
    visible: currentTab === 3
    Layout.fillWidth: true
    Layout.fillHeight: true

    // Wire state groups
    library: libraryState
    tuning: tuningState
    theme: theme

    // Handle signals
    onRebuildRequested: loadTuningVoicings()
    onResetRequested: { _tuningVoicingCache = {}; loadFromCache(); loadTuningVoicings() }
    onImportIRealRequested: function(text) { importIRealPro(text) }
    onPresetSaveRequested: function(path) { savePreset(path) }
    onPresetLoadRequested: function(path) { loadPreset(path) }
}
```

### 5. State Group Conformance

State groups in ChordLibrary.qml must follow this structure:

```qml
QtObject {
    id: libraryState
    property var voicingsData: []
    property var filteredData: []
    property var standardVoicingsData: []
    property bool dataLoaded: false
    property bool usingTuningVoicings: false
    property string filterContext: ""
    property string filterCategory: ""
    property string filterQuality: ""
    property string searchText: ""
    property var contextList: ["All Contexts"]
    property var categoryList: ["All Types"]
    property var qualityList: ["All Qualities"]
}

QtObject {
    id: tuningState
    property string selectedTuning: "standard"
    property var tuningList: [...]
    property var tuningLabels: ({})
    property var tuningStringCounts: ({})
    property int tuningMaxStrings: 6
    property var tuningMidi: ({})
}

QtObject {
    id: calcState
    property int maxFret: 12
    property int maxStretch: 4
    property bool allowOpen: true
    property bool rootInBass: true
    property int minNotes: 3
    property int maxMuted: 3
    property int maxPerQuality: 0
}
```

### 6. Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Component file | PascalCase + Panel suffix | `ImportPanel.qml` |
| Component id | camelCase + Panel suffix | `importPanel` |
| Input properties | camelCase, state group names | `library`, `tuning`, `theme` |
| Output signals | camelCase + action verb | `rebuildRequested`, `tuningChanged` |
| Internal properties | `_` prefix + camelCase | `_isLoading`, `_presetPath` |
| Internal functions | `_` prefix + camelCase | `_validateInput()` |

### 7. File Header Comment

Every extracted panel must have a header comment:

```qml
// ImportPanel.qml — Import tab UI for the Chord Library plugin.
// Extracted from ChordLibrary.qml (Phase A2, #75).
//
// Input state groups: library, tuning, theme
// Signals: rebuildRequested, resetRequested, importIRealRequested(text),
//          presetSaveRequested(path), presetLoadRequested(path),
//          urlApplyRequested(url)
```

### 8. deploy.sh Not Needed

Since `plugin/` is self-contained and `deploy.sh` uses `rsync`, new QML files in `plugin/ui/` are automatically deployed. No deploy.sh changes needed.

## Common Mistakes

1. **Passing `voicingsData` directly instead of `libraryState`** — pass the state group object, not individual properties
2. **Calling functions from parent** — `parent.loadTuningVoicings()` is wrong; emit a signal instead
3. **Inline JS business logic** — keep logic in ChordLibrary.qml's signal handlers or JS modules, not in the panel
4. **Missing `visible` binding** — every panel needs `visible: currentTab === N`
5. **Forgetting Layout properties** — panels need `Layout.fillWidth: true; Layout.fillHeight: true`

## Verification Steps

After extracting a panel:

1. `python3 -m pytest tests/ -v` — all tests must pass (pure refactor, no behavior change)
2. `bash deploy.sh` — deploy to MuseScore
3. Quit and relaunch MuseScore — QML caching requires full restart
4. Open the plugin, navigate to the extracted tab, verify all functionality works
5. Check the console for QML errors: `View > Developer Console` in MuseScore
