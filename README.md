# Open Immersive Reader

An open-source, beautifully designed web application that replicates the EPUB translation functionality of Immersive Translate.

## Features

- **EPUB Parsing**: Upload any valid `.epub` file and automatically parse its table of contents and spine.
- **Modern Reading Interface**: A beautiful, distraction-free reading environment with a navigable sidebar.
- **Dual-Language Translation**: Emulates the paragraph-by-paragraph bilingual reading experience.
- **Export**: After translating, you can download the modified `.epub` file containing the dual-language text.
- **Premium Aesthetics**: Designed with smooth gradients, glassmorphism elements, and modern typography (Inter).

## Tech Stack

- **React & TypeScript**: For a robust and type-safe frontend.
- **Vite**: Lightning-fast build tool and development server.
- **JSZip**: Handles the extraction and repacking of the EPUB archive.
- **Lucide React**: Clean and modern iconography.

## Getting Started

1. Navigate to the project directory:
   ```bash
   cd d:\Temp_not_synced\translator
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:5173/`.

## How to Use

1. Click on **"Open EPUB"** to select a local `.epub` file, or use the **"Try Test EPUB"** button to load the pre-configured `minimal.epub`.
2. Browse through the chapters using the left sidebar.
3. Click the **"Translate"** button on the top right to apply the dual-language translation to the current chapter. (Currently, this uses a mock translation function. You can replace it with API calls to OpenAI, Gemini, or Google Translate in `src/utils/translator.ts`).
4. Once you are satisfied with the translation, click **"Export"** to download the new `.epub` file.

## Customizing the Translator

To add real translation capabilities, edit the `translateText` function in `src/utils/translator.ts`. You can integrate any translation API here to replace the simulated mock translations.
