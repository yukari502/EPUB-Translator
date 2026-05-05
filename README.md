# EPUB Translator

A powerful, high-performance, and immersive desktop EPUB translation tool built with Electron, React, and Vite. Designed to bypass CORS restrictions natively, it allows users to translate EPUB books seamlessly using the free Google Translate Web API, DeepSeek, OpenAI, Gemini, or any custom API—all without relying on heavy backend proxies.

## 🚀 Features

- **Immersive Bilingual Reading & Translating**: Displays beautiful translation blocks embedded right beneath the original text. You can also toggle translations or switch to "Translate Only" mode.
- **Native Desktop App**: Built on Electron, unlocking direct requests to APIs (like Google Translate Web) by disabling `webSecurity`, completely evading browser CORS limitations.
- **High Concurrency & Auto-Retry**: Achieves massive throughput with customizable batch configurations. Includes an intelligent Exponential Backoff strategy to gracefully handle API rate-limit errors and retry failed chunks automatically.
- **Real-Time Translation Streaming**: Watch your text turn into your target language right before your eyes! Translations are piped into the DOM in real-time, preserving your exact scroll position and minimizing flickering.
- **Pause & Resume**: Large book? Stop the translation at any time with the "Pause" feature using native `AbortController` functionality. Resume exactly where you left off.
- **Robust Original HTML Parsing**: Safely unpacks, cleans, translates, and repackages EPUB files without destroying structural integrity or original images. Retains complex Japanese vertical layouts and rubys.
- **Free Google Web API Protection**: Automatically limits concurrency when using free web APIs to protect your IP from anti-bot CAPTCHA bans.
- **Instant Toggle (Revert)**: Need to check the original text? Hit the "Show Original" button to instantly toggle between original and translated content without losing data.

## 📦 Quick Start

### Prerequisites
- Node.js (v18 or higher recommended)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server (Live Reloading):
```bash
npm run dev
```

### Building for Release

To package the application for your operating system:
```bash
npm run build
```
The packaged executable (e.g., `.exe` for Windows) will be generated inside the `dist/` directory (the exact path depends on electron-builder). 

## 🛠️ Usage

1. **Load Book**: Click the "Open EPUB" button to load your local `.epub` file.
2. **Settings**: Click the gear icon to open Settings. 
   - Choose your translation provider (e.g., Google Translate Web Free, DeepSeek, OpenAI).
   - Insert your API Key if required.
   - Adjust concurrency levels based on your token limits.
3. **Translate**: Select a chapter from the sidebar and click "Translate Chapter", or click "Translate All" for a full book overhaul. 
4. **Export**: Click "Export" to download the finalized, fully translated `.epub` file directly to your system.

## 🛡️ Architecture & Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Desktop Runtime**: Electron + `vite-plugin-electron`
- **EPUB Engine**: JSZip (for unpacking/repacking XML architecture)
- **Styling**: Pure CSS (minimalist and easily modifiable)

## 📄 License

MIT License
