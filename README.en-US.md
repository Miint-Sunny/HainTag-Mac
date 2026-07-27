<div align="center">

<img src="native_app/resources/icon.ico" width="96" />

# HainTag · Hain's Tag Workshop

**"Turning the images in your mind into a language machines can understand."**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows_10%2F11-0078d4.svg)]()
[![Release](https://img.shields.io/github/v/release/1756141021/HainTag?color=green)](https://github.com/1756141021/HainTag/releases)
[![Downloads](https://img.shields.io/badge/Downloads-Release-orange)](https://github.com/1756141021/HainTag/releases)

AI Art TAG Generation · Management · Workflow — An all-in-one Windows desktop tool

If you find it useful, please recommend it to your friends. Giving it a ⭐ Star is the greatest support!

[About Hain ☽](README.hein.md) · [中文](README.md)

</div>

---

### What is this?

HainTag is a Windows desktop application designed for AI art workflows such as Stable Diffusion and NovelAI.

Using your own LLM (any API compatible with the OpenAI format), it transforms natural language descriptions into Danbooru tag system TAGs, providing a complete toolchain from generation, editing, and completion to image management and metadata processing.

**All data is stored locally; nothing is uploaded, and there is no dependency on cloud services.**

---

### Download and Installation

#### Windows

Go to the **[Releases](https://github.com/1756141021/HainTag/releases)** page to download the latest version.

1. Download `HainTag-vX.X.X-windows.zip`
2. Extract to any directory
3. Run `HainTag.exe` — No installation required, works out of the box.

> **System Requirements**: Windows 10 / 11, 64-bit

#### macOS

On macOS, the app is currently run from source. HainTag is a standalone desktop application, not a ComfyUI custom node; do not place it in `ComfyUI/custom_nodes` or node directories.

Choose your own program directory. The following example places the program in `~/Applications/HainTag`:

```bash
cd ~/Applications
git clone https://github.com/1756141021/HainTag.git
cd HainTag
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m native_app
```

If `git clone` errors out during the `Receiving objects` / `Unpacking objects` stage, delete the incomplete `~/Applications/HainTag` folder and run the `git clone` command again. You can also try cloning into a different parent directory, such as `~/Downloads`.

The program directory is only for the code. User data will be written to `~/Library/Application Support/HainTag/`.

---

### 0.9.1 Update Highlights

This version focuses on completing the actual interaction loops of the workbench: Right-click menus, OC, History, Storage Dock, and Image Interrogation have been integrated back into the original interfaces rather than being superficial UI changes.

| Update | Description |
|------|------|
| **Main Workbench v3** | Output area is now an editable TAG stream, retaining hover, category colors, left-click drag sorting, right-click drag weight, and dual pages (Full / No-Character) |
| **Shortest OC Path** | Add OCs on the spot via the `+` button in the title bar; left-click chips to quickly adjust Clothing / Order / Depth, right-click to remove or edit |
| **History Timeline** | Recent generations are displayed at the bottom; "View All" opens the full history panel, allowing backfilling of inputs, full TAGs, and no-character TAGs |
| **Storage Dock** | Multiple floating cards snap into a condensed bar when close to each other; a single remaining member restores automatically and hides to avoid blocking the workspace |
| **Menu Generalization** | Right-click menus for Input, Output, Library, History, Dock, and Storage now use unified i18n, theme, font, and scaling interfaces |
| **Image Interrogation** | Local / LLM options are now switched within the same card; both local and LLM interrogation retain batch processing, presets, thresholds, category colors, and copy/send functions |

### Too many features? Worried about bloat?

Concerned about feature bloat? Every feature in HainTag is an independent card—if you don't open a feature, it stays invisible and consumes no extra memory. Memory usage automatically decreases after a period of inactivity. The software itself is lightweight and ready to use.

---

### Feature Overview

#### 📌 Floating & Pinning Cards

Any card can be dragged out of the main window to become an independent floating window. The main window supports "Always on Top"—drag the TAG output next to your WebUI to compare and refine while drawing, which is especially useful for multi-monitor setups. Multiple floating windows can be snapped into the Storage Dock and restored individually.

---

#### 🎨 TAG Generation & Editing

| Feature | Description |
|------|------|
| **LLM-Driven Generation** | Connect to any OpenAI-compatible API (Local models / Claude / GPT / DeepSeek...), with streaming output |
| **Category Highlighting** | Output TAGs are automatically colored by category—Character, Scene, Clothing, Pose, Expression, Style, Quality—for instant clarity |
| **Danbooru Auto-complete** | Real-time matching against a 150k-word dictionary; hover to see Chinese translations and usage frequency, eliminating the need to check the wiki |
| **Weight Dragging** | Right-click and drag a TAG up or down to adjust weights in real-time; parentheses syntax is added/removed automatically |
| **Drag Sorting** | Left-click and drag TAGs to adjust their order, with highlighting of source and target positions |
| **TAG Extraction Markers** | Use custom `[TAGS]...[/TAGS]` markers to precisely extract TAG fields from long LLM text outputs |
| **Generation History Timeline** | Recent generations are visible at the bottom of the workbench; full history can be opened and backfilled with one click |

#### 📝 Prompts & Context

| Feature | Description |
|------|------|
| **Prompt Manager** | Multiple prompt cards; each supports fine-grained control over message position via Order (Sorting) and Depth (Insertion Depth) |
| **Example Image System** | Drag in reference images to automatically parse embedded metadata, which is then sent to the LLM as few-shot examples |
| **Memory Mode** | Maintains full conversation context, supporting multi-turn additive generation—e.g., "The last one was great, give me another similar one" |
| **Prompt Preview** | One-click view of the final message list and token count sent to the API, so you know exactly what is being generated |

#### 🖼️ Artist & OC Libraries

| Feature | Description |
|------|------|
| **Artist Library** | Manage artist names, LoRAs / trigger words, and reference images; copy to prompt with one click |
| **OC Character Library** | Original Character management with a clothing subsystem—independently toggle multiple outfits; automatically merge character and enabled clothing TAGs upon sending |
| **Insertion Control** | Independent Order / Depth settings for each character/outfit to precisely control the position of messages in the conversation |
| **Title Bar OC Quick-chips** | Currently active OCs are displayed directly in the workbench title bar for on-the-spot addition, outfit switching, editing, or removal |

#### 📂 Image Manager

| Feature | Description |
|------|------|
| **Thumbnail Grid** | Multi-threaded loading + LRU cache ensures smooth scrolling even with massive image libraries |
| **Lightbox Large View** | Full-screen viewing with keyboard/mouse paging |
| **Floating Detail Panel** | Instant metadata preview on hover; supports pinning |
| **File Operations** | Move, rename (F2), delete (to recycle bin), cut, and paste |
| **Favorites Tagging** | Persistent favorites with a "Show Favorites Only" filter |
| **Folder Navigation** | Forward/backward history stack, supporting mouse side buttons |

#### 🔧 Metadata Tools

| Feature | Description |
|------|------|
| **Metadata Viewer** | Supports four formats: A1111 / Forge, ComfyUI, NovelAI (including LSB steganography decoding), and Fooocus |
| **Metadata Destroyer** | Binary chunk-level operation with zero IDAT loss; supports batch processing—wipe privacy with one click before sharing |
| **Metadata Editor** | Directly modify prompts and generation parameters embedded in images |

#### 🔍 Image Interrogation

| Feature | Description |
|------|------|
| **Local Inference** | Use cl_tagger ONNX models to recognize Danbooru tags offline; supports existing model directories (e.g., ComfyUI) |
| **LLM Interrogation** | Send images via multimodal APIs to let the LLM generate tag descriptions |
| **Auto Environment Config** | Automatically downloads the Python embedded environment and dependencies when onnxruntime is unavailable |
| **Sensitivity Control** | Independent threshold sliders for general tags vs. character tags, with 8 category filter switches |
| **Confidence Toggle** | One-click switch to show/hide the confidence percentage for each tag |

#### ✨ Appearance & Experience

| Feature | Description |
|------|------|
| **Dark / Light Themes** | Frosted glass texture with adjustable card transparency |
| **Custom Background** | Choose a favorite image; the app automatically extracts the primary palette to generate a matching color scheme |
| **Multilingual** | Chinese / English |
| **New User Guide** | A 6-step highlighted guide pops up on first launch to get you started |
| **Generation History** | Automatically records all generations for easy one-click backfilling |
| **Hotkey Panel** | Press F1 to view all shortcuts and mouse gestures |
| **Embedded Fonts** | Pre-installed LxgwWenKai Screen (SIL OFL license) for beautiful Chinese typography out of the box |
| **Error Reporting** | Automatically generates sanitized crash reports; sensitive information like API keys will never be leaked |

---

### Running from Source

If you are not using the Windows distribution package, follow the macOS source method described above. The key is to select a parent directory first, then clone the repository into a `HainTag` folder within it, for example: `~/Applications/HainTag`.

---

### Configuring API

After the first launch, enter the following in the settings panel:

| Field | Description |
|------|------|
| API Base URL | OpenAI-compatible interface address, e.g., `https://api.openai.com/v1` |
| API Key | Your API key |
| Model | Click ↻ to pull the list of available models from the API |

Supports any service compatible with the OpenAI Chat Completions format—OpenAI, Claude (via compatibility layer), DeepSeek, local Ollama, vLLM, etc.

---

### Open Source License

[GNU General Public License v3.0](LICENSE)
