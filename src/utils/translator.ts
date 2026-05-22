export interface TranslationSettings {
  mode: 'bilingual' | 'translate-only';
  provider: 'google-web' | 'openai' | 'gemini' | 'custom' | 'deepseek' | 'ollama';
  apiKey: string;
  apiUrl: string;
  model: string;
  targetLanguage: string;
  maxConcurrency?: number;
  paragraphsPerRequest?: number;
  signal?: AbortSignal;
  onProgress?: (partialHtml: string) => void;
  glossary?: string;
}

function getSystemPrompt(targetLanguage: string, glossary?: string) {
  let prompt = `You are a professional ${targetLanguage} native translator who needs to fluently translate text into ${targetLanguage}.

## Translation Rules
1. Output only the translated content, without explanations or additional content (such as "Here's the translation:" or "Translation as follows:")
2. The returned translation must maintain exactly the same number of paragraphs and format as the original text
3. If the text contains HTML tags, consider where the tags should be placed in the translation while maintaining fluency
4. For content that should not be translated (such as proper nouns, code, etc.), keep the original text.
5. If input contains %%, use %% in your output, if input has no %%, don't use %% in your output`;

  if (glossary && glossary.trim()) {
    prompt += `\n\n## Glossary & Custom Instructions\n${glossary.trim()}`;
  }

  prompt += `\n\n## OUTPUT FORMAT:
- **Single paragraph input** → Output translation directly (no separators, no extra text)
- **Multi-paragraph input** → Use %% as paragraph separator between translations`;

  return prompt;
}

export function addLog(message: string, type: 'info' | 'error' | 'success' = 'info') {
  const event = new CustomEvent('translation-log', { detail: { message, type, time: new Date().toLocaleTimeString() } });
  window.dispatchEvent(event);
}

export async function translateTextBatch(texts: string[], settings: TranslationSettings, maxRetries = 3): Promise<string[]> {
  if (texts.length === 0) return [];

  const separator = '\n\n%%\n\n';
  const combinedText = texts.join(separator);

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      let resultText = '';
      const isCustomOrOpenAI = settings.provider === 'openai' || settings.provider === 'custom' || settings.provider === 'deepseek' || settings.provider === 'ollama';

      if (isCustomOrOpenAI) {
        if (attempt === 1) addLog(`Sending request to ${settings.provider} API (Model: ${settings.model || (settings.provider === 'deepseek' ? 'deepseek-v4-flash' : settings.provider === 'ollama' ? 'llama3' : 'gpt-3.5-turbo')})`, 'info');

        let url = settings.apiUrl;
        if (!url) {
          if (settings.provider === 'openai') url = 'https://api.openai.com/v1/chat/completions';
          else if (settings.provider === 'deepseek') url = 'https://api.deepseek.com/chat/completions';
          else if (settings.provider === 'ollama') url = 'http://localhost:11434/v1/chat/completions';
          else url = 'https://api.openai.com/v1/chat/completions'; // custom fallback
        }

        const headers: Record<string, string> = {
          'Content-Type': 'application/json'
        };
        if (settings.apiKey) {
          headers['Authorization'] = `Bearer ${settings.apiKey}`;
        }

        const response = await fetch(url, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            model: settings.model || (settings.provider === 'deepseek' ? 'deepseek-v4-flash' : settings.provider === 'ollama' ? 'llama3' : 'gpt-3.5-turbo'),
            temperature: 0,
            messages: [
              { role: 'system', content: getSystemPrompt(settings.targetLanguage || 'Chinese', settings.glossary) },
              { role: 'user', content: combinedText }
            ]
          }),
          signal: settings.signal
        });
        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`API Error: ${response.status} - ${errText}`);
        }
        const data = await response.json();
        resultText = data.choices[0].message.content.trim();
        addLog(`Received successful response from ${settings.provider} API`, 'success');
      }
      else if (settings.provider === 'gemini') {
        if (attempt === 1) addLog(`Sending request to Gemini API (Model: ${settings.model || 'gemini-1.5-pro'})`, 'info');
        const url = settings.apiUrl || `https://generativelanguage.googleapis.com/v1beta/models/${settings.model || 'gemini-1.5-pro'}:generateContent?key=${settings.apiKey}`;
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            system_instruction: { parts: [{ text: getSystemPrompt(settings.targetLanguage || 'Chinese', settings.glossary) }] },
            contents: [{ parts: [{ text: combinedText }] }],
            generationConfig: { temperature: 0 }
          }),
          signal: settings.signal
        });
        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Gemini API Error: ${response.status} - ${errText}`);
        }
        const data = await response.json();
        resultText = data.candidates[0].content.parts[0].text.trim();
        addLog(`Received successful response from Gemini API`, 'success');
      } else if (settings.provider === 'google-web') {
        if (attempt === 1) addLog(`Sending ${texts.length} requests to Google Translate Web API`, 'info');
        const langMap: Record<string, string> = {
          'Chinese': 'zh-CN',
          'Traditional Chinese': 'zh-TW',
          'English': 'en',
          'Japanese': 'ja',
          'Korean': 'ko',
          'Spanish': 'es',
          'French': 'fr',
          'German': 'de',
          'Russian': 'ru'
        };
        const tl = langMap[settings.targetLanguage] || 'zh-CN';
        
        // Google Web API cannot handle %% separators reliably, translate each paragraph individually
        // Process sequentially to avoid 429 Too Many Requests (Bot Protection)
        const translatedParts = [];
        for (let i = 0; i < texts.length; i++) {
          const text = texts[i];
          const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${tl}&dt=t`;
          const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'q=' + encodeURIComponent(text),
            signal: settings.signal
          });
          
          if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Google Web API Error: ${response.status} - ${errText}`);
          }
          
          const data = await response.json();
          if (data && data[0]) {
            translatedParts.push(data[0].map((item: any) => item[0]).join(''));
          } else {
            translatedParts.push('[Translation Failed]');
          }
          
          // Add a delay between sequential requests to avoid ban
          if (i < texts.length - 1) {
            await new Promise(r => setTimeout(r, 600));
          }
        }
        
        addLog(`Received successful response from Google Web API`, 'success');
        return translatedParts;
      }

      const translatedParts = resultText.split('%%').map(s => s.trim());
      if (translatedParts.length !== texts.length) {
        addLog(`Translation part count mismatch: expected ${texts.length}, got ${translatedParts.length}. Adjusting...`, 'error');
        while (translatedParts.length < texts.length) {
          translatedParts.push('[Translation Missing]');
        }
      }
      return translatedParts.slice(0, texts.length);

    } catch (err: any) {
      if (settings.signal?.aborted) throw new Error('Translation aborted by user');
      if (attempt === maxRetries) {
        addLog(`Translation failed after ${maxRetries} attempts: ${err.message}`, 'error');
        return texts.map(() => `[Translation Failed]`);
      }
      addLog(`Attempt ${attempt} failed (${err.message}). Retrying...`, 'info');
      // Wait before retrying (exponential backoff)
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt - 1)));
    }
  }
  return texts.map(() => `[Translation Failed]`);
}

export async function translateHtmlDocument(htmlString: string, settings: TranslationSettings): Promise<string> {
  // Aggressively remove scripts before parsing
  let safeHtml = htmlString.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  safeHtml = safeHtml.replace(/<script\b[^>]*\/>/gi, '');

  const parser = new DOMParser();
  let doc = parser.parseFromString(safeHtml, 'application/xhtml+xml');
  if (doc.querySelector('parsererror')) {
    doc = parser.parseFromString(safeHtml, 'text/html');
  }

  const tagsToTranslate = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'li'];
  const targetElements: Element[] = [];
  const textsToTranslate: string[] = [];

  for (const tag of tagsToTranslate) {
    const elements = doc.querySelectorAll(tag);
    for (const el of Array.from(elements)) {
      let hasDirectText = false;
      for (const node of Array.from(el.childNodes)) {
        if (node.nodeType === Node.TEXT_NODE && node.textContent && node.textContent.trim().length > 0) {
          hasDirectText = true;
          break;
        }
      }

      if (hasDirectText && !el.classList.contains('translated') && !el.classList.contains('translation-block')) {
        const originalText = el.innerHTML || '';
        if (originalText.trim().length > 0) {
          targetElements.push(el);
          textsToTranslate.push(originalText.trim());
        }
      }
    }
  }

  const chunkSize = settings.paragraphsPerRequest || 4; // Use user setting or default
  const chunks: {texts: string[], elements: Element[]}[] = [];
  for (let i = 0; i < textsToTranslate.length; i += chunkSize) {
    chunks.push({
      texts: textsToTranslate.slice(i, i + chunkSize),
      elements: targetElements.slice(i, i + chunkSize)
    });
  }

  let maxConcurrency = settings.maxConcurrency || 30; // Max parallel requests
  if (settings.provider === 'google-web') {
    maxConcurrency = Math.min(maxConcurrency, 3); // Cap concurrency to prevent IP bans
  }
  let currentIndex = 0;

  const processNextChunk = async (): Promise<void> => {
    if (settings.signal?.aborted) return;
    if (currentIndex >= chunks.length) return;
    const chunk = chunks[currentIndex++];

    const translatedTexts = await translateTextBatch(chunk.texts, settings);
    if (settings.signal?.aborted) return;

    for (let j = 0; j < chunk.elements.length; j++) {
      const el = chunk.elements[j];
      const translatedText = translatedTexts[j] || '[Translation Missing]';

      if (translatedText === '[Translation Failed]' || translatedText === '[Translation Missing]') {
        // If it failed, keep original text and do NOT mark as translated.
        // This allows the user to click "Translate Chapter" again to retry only the failed parts.
        continue;
      }

      if (settings.mode === 'bilingual') {
        const transEl = doc.createElement(el.tagName);
        transEl.className = 'translation-block translated';
        transEl.style.color = '#555';
        transEl.style.marginTop = '4px';
        transEl.style.marginBottom = '12px';
        transEl.style.paddingLeft = '8px';
        transEl.style.borderLeft = '3px solid #007bff';
        transEl.innerHTML = translatedText;

        el.classList.add('translated');
        if (el.nextSibling) {
          el.parentNode?.insertBefore(transEl, el.nextSibling);
        } else {
          el.parentNode?.appendChild(transEl);
        }
      } else {
        el.innerHTML = translatedText;
        el.classList.add('translated');
      }
    }

    if (settings.onProgress) {
      const serializer = new XMLSerializer();
      settings.onProgress(serializer.serializeToString(doc));
    }

    return processNextChunk();
  };

  const workers = [];
  for (let i = 0; i < maxConcurrency; i++) {
    workers.push(processNextChunk());
  }

  await Promise.all(workers);

  const serializer = new XMLSerializer();
  return serializer.serializeToString(doc);
}
