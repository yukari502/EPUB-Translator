import { useState, useRef, useEffect } from 'react';
import { Upload, Download, Languages, BookOpen, ChevronLeft, Menu, Settings, X, Terminal, Undo } from 'lucide-react';
import { EpubParser } from './utils/epub';
import { translateHtmlDocument, type TranslationSettings } from './utils/translator';
import './App.css';

function App() {
  const [epubParser, setEpubParser] = useState<EpubParser | null>(null);
  const [spineFiles, setSpineFiles] = useState<string[]>([]);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [isTranslating, setIsTranslating] = useState(false);
  const [isTranslatingAll, setIsTranslatingAll] = useState(false);
  const [translationProgress, setTranslationProgress] = useState<{current: number, total: number} | null>(null);
  const [showingOriginal, setShowingOriginal] = useState<boolean>(false);
  const [hasTranslation, setHasTranslation] = useState<boolean>(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [logs, setLogs] = useState<{message: string, type: string, time: string}[]>([]);
  
  const [settings, setSettings] = useState<TranslationSettings>({
    mode: 'translate-only',
    provider: 'google-web',
    apiKey: '',
    apiUrl: '',
    model: '',
    targetLanguage: 'Chinese',
    maxConcurrency: 30,
    paragraphsPerRequest: 4,
    glossary: ''
  });
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleCancelTranslation = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  useEffect(() => {
    const handleLog = (e: any) => {
      setLogs(prev => [...prev, e.detail]);
      // Auto-open logs on error
      if (e.detail.type === 'error') {
        setIsLogsOpen(true);
      }
    };
    window.addEventListener('translation-log', handleLog);
    return () => window.removeEventListener('translation-log', handleLog);
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const parser = await EpubParser.load(file);
      setEpubParser(parser);
      const spine = parser.getSpineFiles();
      setSpineFiles(spine);
      if (spine.length > 0) {
        handleFileSelect(spine[0], parser);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to parse EPUB file.');
    }
  };



  const handleFileSelect = async (path: string, parser: EpubParser = epubParser!) => {
    if (!parser) return;
    setActiveFile(path);
    try {
      const text = await parser.getFileText(path);
      setFileContent(text);
      setShowingOriginal(parser.isOriginal(path));
      setHasTranslation(parser.hasTranslation(path));
    } catch (err) {
      console.error(err);
      setFileContent('Error loading file content.');
    }
  };

  const handleTranslate = async () => {
    if (!epubParser || !activeFile || !fileContent) return;
    setIsTranslating(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    try {
      const translatedHtml = await translateHtmlDocument(fileContent, { 
        ...settings, 
        signal: controller.signal,
        onProgress: (partialHtml) => setFileContent(partialHtml)
      });
      if (controller.signal.aborted) return;
      setFileContent(translatedHtml);
      epubParser.saveTranslation(activeFile, translatedHtml);
      setShowingOriginal(false);
      setHasTranslation(true);
    } catch (err: any) {
      if (err.message !== 'Translation aborted by user') {
        console.error(err);
        alert('Translation failed.');
      }
    } finally {
      setIsTranslating(false);
      if (abortControllerRef.current === controller) abortControllerRef.current = null;
    }
  };

  const handleToggleTranslation = () => {
    if (!epubParser || !activeFile) return;
    const result = epubParser.toggleTranslation(activeFile);
    if (result) {
      setFileContent(result.text);
      setShowingOriginal(result.showingOriginal);
    }
  };

  const handleTranslateAll = async () => {
    if (!epubParser || spineFiles.length === 0) return;
    if (!confirm('This will translate all chapters in the book. It may take some time. Continue?')) return;
    
    setIsTranslatingAll(true);
    setTranslationProgress({ current: 0, total: spineFiles.length });
    const controller = new AbortController();
    abortControllerRef.current = controller;
    
    try {
      for (let i = 0; i < spineFiles.length; i++) {
        if (controller.signal.aborted) break;
        const path = spineFiles[i];
        const text = await epubParser.getFileText(path);
        const translatedHtml = await translateHtmlDocument(text, { 
          ...settings, 
          signal: controller.signal,
          onProgress: (partialHtml) => {
            if (path === activeFile) {
              setFileContent(partialHtml);
            }
          }
        });
        if (controller.signal.aborted) break;
        
        epubParser.saveTranslation(path, translatedHtml);
        
        if (path === activeFile) {
          setFileContent(translatedHtml);
          setShowingOriginal(false);
          setHasTranslation(true);
        }
        setTranslationProgress({ current: i + 1, total: spineFiles.length });
      }
      if (!controller.signal.aborted) {
        alert('Full book translation complete! You can now Export the book.');
      }
    } catch (err: any) {
      if (err.message !== 'Translation aborted by user') {
        console.error(err);
        alert('Failed to translate entire book.');
      }
    } finally {
      setIsTranslatingAll(false);
      setTranslationProgress(null);
      if (abortControllerRef.current === controller) abortControllerRef.current = null;
    }
  };

  const handleExport = async () => {
    if (!epubParser) return;
    try {
      const blob = await epubParser.getExportZip();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'translated_book.epub';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Export failed.');
    }
  };

  useEffect(() => {
    const renderToIframe = async () => {
      if (iframeRef.current && fileContent && activeFile && epubParser) {
        try {
          let displayContent = await epubParser.renderForDisplay(activeFile, fileContent);
          const doc = iframeRef.current.contentDocument;
          const win = iframeRef.current.contentWindow;
          let scrollY = 0;
          let scrollX = 0;
          if (win) {
            scrollY = win.scrollY;
            scrollX = win.scrollX;
          }

          if (doc) {
            doc.open();
            displayContent = displayContent.replace('</head>', `
              <style>
                body { 
                  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                  line-height: 1.6; 
                  padding: 2rem; 
                  color: #333; 
                  margin: 0 auto; 
                }
                /* Horizontal layout */
                html:not([class*="vrt"]) body { max-width: 800px; }
                html:not([class*="vrt"]) img { max-width: 100%; height: auto; }
                
                /* Vertical layout (Japanese) */
                html[class*="vrt"] img { max-height: 100vh; width: auto; max-width: 100vw; }
                
                .translation-block { font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif; }
              </style>
            </head>`);
            doc.write(displayContent);
            doc.close();
            
            if (win && scrollY > 0) {
              // Wait for layout to restore scroll position to avoid jumpiness during realtime update
              setTimeout(() => {
                win.scrollTo(scrollX, scrollY);
              }, 10);
            }
          }
        } catch (err) {
          console.error("Failed to render iframe content", err);
        }
      }
    };
    renderToIframe();
  }, [fileContent, activeFile, epubParser]);

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="nav-brand">
          <button className="icon-btn" onClick={() => setSidebarOpen(!sidebarOpen)} style={{ marginRight: '8px' }} title="Toggle Sidebar">
            <Menu size={20} />
          </button>
          <BookOpen className="brand-icon" />
          <h1>EPUB Translator</h1>
        </div>
        <div className="nav-actions">
          <button className={`icon-btn ${isLogsOpen ? 'active-icon' : ''}`} onClick={() => setIsLogsOpen(!isLogsOpen)} title="Debug Logs">
            <Terminal size={20} />
          </button>
          <button className="icon-btn" onClick={() => setIsSettingsOpen(true)} title="Settings">
            <Settings size={20} />
          </button>
          {!epubParser ? (
            <>
              <button className="btn btn-primary" onClick={() => fileInputRef.current?.click()}>
                <Upload size={18} />
                Open EPUB
              </button>
            </>
          ) : (
            <>
              {isTranslatingAll ? (
                <button 
                  className="btn btn-primary" 
                  style={{ backgroundColor: '#dc3545', borderColor: '#dc3545' }}
                  onClick={handleCancelTranslation} 
                  title="Pause translating entire book"
                >
                  <X size={18} />
                  Pause ({translationProgress?.current}/{translationProgress?.total})
                </button>
              ) : (
                <button 
                  className="btn btn-primary" 
                  onClick={handleTranslateAll} 
                  disabled={isTranslating}
                  title="Translate entire book"
                >
                  <Languages size={18} />
                  Translate All
                </button>
              )}
              {isTranslating ? (
                <button 
                  className="btn btn-primary" 
                  style={{ backgroundColor: '#dc3545', borderColor: '#dc3545' }}
                  onClick={handleCancelTranslation} 
                >
                  <X size={18} />
                  Pause
                </button>
              ) : (
                <button 
                  className="btn btn-primary" 
                  onClick={handleTranslate} 
                  disabled={isTranslatingAll}
                >
                  <Languages size={18} />
                  Translate Chapter
                </button>
              )}
              <button 
                className={`btn ${showingOriginal ? 'btn-primary' : 'btn-secondary'}`}
                onClick={handleToggleTranslation} 
                disabled={isTranslating || isTranslatingAll || !hasTranslation}
                title="Toggle between Original and Translated text"
              >
                <Undo size={18} />
                {showingOriginal ? 'Show Translation' : 'Show Original'}
              </button>
              <button className="btn btn-secondary" onClick={handleExport} disabled={isTranslatingAll}>
                <Download size={18} />
                Export
              </button>
            </>
          )}
          <input 
            type="file" 
            accept=".epub" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            style={{ display: 'none' }} 
          />
        </div>
      </header>

      {/* Main Content Area */}
      <div className="main-workspace">
        {/* Sidebar */}
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <div className="sidebar-header">
            <h3>Table of Contents</h3>
            <button className="icon-btn" onClick={() => setSidebarOpen(false)}>
              <ChevronLeft size={20} />
            </button>
          </div>
          <ul className="toc-list">
            {spineFiles.map((path, idx) => (
              <li 
                key={idx} 
                className={activeFile === path ? 'active' : ''}
                onClick={() => handleFileSelect(path)}
              >
                {path.split('/').pop()}
              </li>
            ))}
            {spineFiles.length === 0 && (
              <div className="empty-toc">No files loaded</div>
            )}
          </ul>
        </aside>

        {!sidebarOpen && epubParser && (
          <button className="floating-menu-btn" onClick={() => setSidebarOpen(true)}>
            <Menu size={24} />
          </button>
        )}

        {/* Reader View */}
        <main className="reader-view">
          {fileContent ? (
            <iframe 
              ref={iframeRef} 
              title="Reader" 
              className="reader-iframe"
            />
          ) : (
            <div className="empty-state">
              <BookOpen size={64} className="empty-icon" />
              <h2>Welcome to EPUB Translator</h2>
              <p>Upload an EPUB file to start reading and translating in dual-language mode.</p>
              <div style={{ display: 'flex', gap: '16px', marginTop: '16px' }}>
                <button className="btn btn-primary btn-large" onClick={() => fileInputRef.current?.click()}>
                  <Upload size={20} /> Select EPUB File
                </button>
              </div>
            </div>
          )}
        </main>
        
        {/* Logs Drawer */}
        {isLogsOpen && (
          <aside className="logs-drawer">
            <div className="logs-header">
              <h3>Debug Logs</h3>
              <div>
                <button className="icon-btn" onClick={() => setLogs([])} style={{marginRight: 8}}>Clear</button>
                <button className="icon-btn" onClick={() => setIsLogsOpen(false)}><X size={18} /></button>
              </div>
            </div>
            <div className="logs-content">
              {logs.length === 0 ? <div className="log-empty">No logs yet.</div> : logs.map((log, i) => (
                <div key={i} className={`log-entry log-${log.type}`}>
                  <span className="log-time">[{log.time}]</span> {log.message}
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-overlay" onClick={() => setIsSettingsOpen(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Translation Settings</h2>
              <button className="icon-btn" onClick={() => setIsSettingsOpen(false)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Translation Mode</label>
                <select 
                  value={settings.mode} 
                  onChange={e => setSettings({...settings, mode: e.target.value as any})}
                  className="form-control"
                >
                  <option value="bilingual">Bilingual (Dual-Language)</option>
                  <option value="translate-only">Translate Only (Replace Original)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Target Language</label>
                <select 
                  value={settings.targetLanguage} 
                  onChange={e => setSettings({...settings, targetLanguage: e.target.value})}
                  className="form-control"
                >
                  <option value="Chinese">Chinese (简体中文)</option>
                  <option value="Traditional Chinese">Traditional Chinese (繁體中文)</option>
                  <option value="English">English</option>
                  <option value="Japanese">Japanese (日本語)</option>
                  <option value="Korean">Korean (한국어)</option>
                  <option value="Spanish">Spanish (Español)</option>
                  <option value="French">French (Français)</option>
                  <option value="German">German (Deutsch)</option>
                  <option value="Russian">Russian (Русский)</option>
                </select>
              </div>

              <div className="form-group">
                <label>API Provider</label>
                <select 
                  value={settings.provider} 
                  onChange={e => setSettings({...settings, provider: e.target.value as any})}
                  className="form-control"
                >
                  <option value="google-web">Google Translate (Web Free)</option>
                  <option value="ollama">Ollama / Local API (OpenAI Compatible)</option>
                  <option value="deepseek">DeepSeek (Official)</option>
                  <option value="openai">OpenAI (Official)</option>
                  <option value="gemini">Google Gemini</option>
                  <option value="custom">Custom (OpenAI Compatible API)</option>
                </select>
              </div>

              {settings.provider !== 'google-web' && (
                <>
                  <div className="form-group">
                    <label>API Key {settings.provider === 'ollama' && '(Optional for Local)'}</label>
                    <input 
                      type="password" 
                      value={settings.apiKey} 
                      onChange={e => setSettings({...settings, apiKey: e.target.value})}
                      className="form-control"
                      placeholder="Enter your API Key"
                    />
                  </div>
                  <div className="form-group">
                    <label>Model Name</label>
                    <input 
                      type="text" 
                      value={settings.model} 
                      onChange={e => setSettings({...settings, model: e.target.value})}
                      className="form-control"
                      placeholder={
                        settings.provider === 'deepseek' ? 'deepseek-v4-flash' : 
                        settings.provider === 'ollama' ? 'llama3' : 
                        settings.provider === 'openai' ? 'gpt-3.5-turbo' : 
                        (settings.provider === 'gemini' ? 'gemini-1.5-pro' : 'deepseek-chat')
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Custom API URL {(settings.provider !== 'custom' && settings.provider !== 'deepseek' && settings.provider !== 'ollama') && '(Optional)'}</label>
                    <input 
                      type="text" 
                      value={settings.apiUrl} 
                      onChange={e => setSettings({...settings, apiUrl: e.target.value})}
                      className="form-control"
                      placeholder={
                        settings.provider === 'custom' ? 'https://api.your-provider.com/v1/chat/completions' : 
                        settings.provider === 'ollama' ? 'http://localhost:11434/v1/chat/completions' :
                        settings.provider === 'deepseek' ? 'https://api.deepseek.com/chat/completions' :
                        'Leave empty for default'
                      }
                    />
                  </div>
                </>
              )}
              
              <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '12px' }}>Glossary & Instructions (术语表与提示词)</h3>
                <div className="form-group">
                  <textarea 
                    value={settings.glossary || ''} 
                    onChange={e => setSettings({...settings, glossary: e.target.value})}
                    className="form-control"
                    placeholder="Enter custom terminology or specific instructions for the AI translator. E.g.&#10;John -> 约翰&#10;Please maintain a formal tone."
                    rows={4}
                    style={{ resize: 'vertical' }}
                  />
                </div>
              </div>
              
              <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
                <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '12px' }}>Advanced Optimization</h3>
                <div className="form-group">
                  <label>Max Concurrency (并发数)</label>
                  <input 
                    type="number" 
                    min="1" max="100"
                    value={settings.maxConcurrency || 30} 
                    onChange={e => setSettings({...settings, maxConcurrency: parseInt(e.target.value) || 30})}
                    className="form-control"
                  />
                  <small style={{display: 'block', marginTop: '4px', color: '#888', fontSize: '12px'}}>
                    Number of API requests to send in parallel. High values speed up translation but might hit API rate limits (e.g. 429 Too Many Requests).
                    {settings.provider === 'google-web' && (
                      <span style={{color: '#dc3545', fontWeight: 'bold', display: 'block', marginTop: '4px'}}>
                        ⚠️ Note: High concurrency on Google Translate will cause you to be identified as a bot. Concurrency is internally capped to 3 to prevent IP bans.
                      </span>
                    )}
                  </small>
                </div>

                <div className="form-group">
                  <label>Paragraphs per Request (单次请求最大段落数)</label>
                  <input 
                    type="number" 
                    min="1" max="20"
                    value={settings.paragraphsPerRequest || 4} 
                    onChange={e => setSettings({...settings, paragraphsPerRequest: parseInt(e.target.value) || 4})}
                    className="form-control"
                  />
                  <small style={{display: 'block', marginTop: '4px', color: '#888', fontSize: '12px'}}>
                    Number of paragraphs to send in a single API batch. Fewer paragraphs make translation faster and more stable, but increase total request counts.
                  </small>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={() => setIsSettingsOpen(false)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full Book Translation Progress Overlay */}
      {isTranslatingAll && translationProgress && (
        <div style={{
          position: 'fixed', bottom: '40px', left: '50%', transform: 'translateX(-50%)',
          backgroundColor: '#fff', padding: '24px', borderRadius: '16px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.15)', zIndex: 9999,
          width: '400px', maxWidth: '90vw', border: '1px solid #eee',
          display: 'flex', flexDirection: 'column', alignItems: 'center'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '18px' }}>
            Translating Entire Book...
          </h3>
          <div style={{ width: '100%', backgroundColor: '#f0f0f0', borderRadius: '8px', height: '12px', overflow: 'hidden', marginBottom: '12px' }}>
            <div style={{
              height: '100%', backgroundColor: '#007bff',
              width: `${(translationProgress.current / translationProgress.total) * 100}%`,
              transition: 'width 0.3s ease-in-out'
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', color: '#666', fontSize: '14px', fontWeight: 500 }}>
            <span>Chapter {translationProgress.current} of {translationProgress.total}</span>
            <span>{Math.round((translationProgress.current / translationProgress.total) * 100)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
