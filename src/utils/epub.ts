import JSZip from 'jszip';

export interface EpubTocItem {
  id: string;
  href: string;
  title: string;
}

export class EpubParser {
  zip: JSZip;
  opfPath: string = '';
  opfContent: string = '';
  basePath: string = '';
  manifest: Record<string, string> = {}; // id to href
  spine: string[] = []; // ids
  
  constructor(zip: JSZip) {
    this.zip = zip;
  }

  static async load(file: File | Blob): Promise<EpubParser> {
    const zip = await JSZip.loadAsync(file);
    const parser = new EpubParser(zip);
    await parser.init();
    return parser;
  }

  async init() {
    // 1. Read META-INF/container.xml
    const containerFile = this.zip.file('META-INF/container.xml');
    if (!containerFile) throw new Error('Invalid EPUB: Missing META-INF/container.xml');
    
    const containerXml = await containerFile.async('text');
    const parser = new DOMParser();
    const containerDoc = parser.parseFromString(containerXml, 'application/xml');
    
    const rootfile = containerDoc.querySelector('rootfile');
    if (!rootfile) throw new Error('Invalid EPUB: Missing rootfile in container.xml');
    
    this.opfPath = rootfile.getAttribute('full-path') || '';
    if (!this.opfPath) throw new Error('Invalid EPUB: Rootfile has no full-path');
    
    this.basePath = this.opfPath.substring(0, this.opfPath.lastIndexOf('/') + 1);

    // 2. Read OPF file
    const opfFile = this.zip.file(this.opfPath);
    if (!opfFile) throw new Error(`Invalid EPUB: Missing OPF file at ${this.opfPath}`);
    
    this.opfContent = await opfFile.async('text');
    const opfDoc = parser.parseFromString(this.opfContent, 'application/xml');

    // 3. Parse manifest
    const manifestItems = opfDoc.querySelectorAll('manifest > item');
    manifestItems.forEach(item => {
      const id = item.getAttribute('id');
      const href = item.getAttribute('href');
      if (id && href) {
        this.manifest[id] = decodeURIComponent(href);
      }
    });

    // 4. Parse spine
    const spineItems = opfDoc.querySelectorAll('spine > itemref');
    spineItems.forEach(item => {
      const idref = item.getAttribute('idref');
      if (idref) {
        this.spine.push(idref);
      }
    });
  }

  getSpineFiles(): string[] {
    return this.spine.map(id => this.basePath + this.manifest[id]);
  }
  
  getFileByPath(path: string) {
    const normalizedPath = path.replace(/\\/g, '/');
    let file = this.zip.file(normalizedPath);
    if (file) return file;
    
    file = this.zip.file(decodeURIComponent(normalizedPath));
    if (file) return file;

    const lowerPath = decodeURIComponent(normalizedPath).toLowerCase();
    for (const relativePath in this.zip.files) {
      if (relativePath.toLowerCase() === lowerPath) {
        return this.zip.files[relativePath];
      }
    }
    return null;
  }

  async getFileText(path: string): Promise<string> {
    const file = this.getFileByPath(path);
    if (!file) throw new Error(`File not found in ZIP: ${path}`);
    return await file.async('text');
  }

  async getExportZip(): Promise<Blob> {
    return await this.zip.generateAsync({ type: 'blob' });
  }

  updateFile(path: string, content: string) {
    this.zip.file(path, content);
  }

  async renderForDisplay(path: string, htmlString: string): Promise<string> {
    // Aggressively remove scripts before parsing to prevent any parser/swallowing issues
    let safeHtml = htmlString.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    safeHtml = safeHtml.replace(/<script\b[^>]*\/>/gi, '');

    const parser = new DOMParser();
    let doc = parser.parseFromString(safeHtml, 'application/xhtml+xml');
    if (doc.querySelector('parsererror')) {
      doc = parser.parseFromString(safeHtml, 'text/html');
    }
    
    // Resolve relative paths function
    const resolvePath = (base: string, rel: string) => {
      const parts = base.split('/');
      parts.pop();
      const relParts = rel.split('/');
      for (const part of relParts) {
        if (part === '.') continue;
        if (part === '..') parts.pop();
        else parts.push(part);
      }
      return parts.join('/');
    };

    // Remove images for display to prevent layout breaking (user requested)
    const images = doc.querySelectorAll('img, image, svg');
    Array.from(images).forEach(img => {
      const placeholder = doc.createElement('div');
      placeholder.style.padding = '20px';
      placeholder.style.textAlign = 'center';
      placeholder.style.color = '#888';
      placeholder.style.border = '1px dashed #ccc';
      placeholder.style.margin = '10px 0';
      placeholder.style.fontFamily = 'sans-serif';
      placeholder.style.fontSize = '14px';
      placeholder.textContent = '[Image Hidden for Display]';
      
      // If it's an <image> inside an <svg>, we want to replace the whole <svg> if possible
      // but we already select svg. If we replace svg, replacing its children might error.
      if (img.parentNode) {
        try {
          img.parentNode.replaceChild(placeholder, img);
        } catch (e) {
          // Ignore if already replaced by parent svg removal
        }
      }
    });

    // Embed stylesheets
    const links = doc.querySelectorAll('link[rel="stylesheet"]');
    for (const link of Array.from(links)) {
      const href = link.getAttribute('href');
      if (href && !href.startsWith('http')) {
        const resolvedPath = resolvePath(path, href);
        try {
          const cssFile = this.getFileByPath(resolvedPath);
          if (cssFile) {
            const cssText = await cssFile.async('text');
            const styleEl = doc.createElement('style');
            styleEl.textContent = cssText;
            link.parentNode?.replaceChild(styleEl, link);
          }
        } catch (err) {
          console.warn('Failed to load css:', resolvedPath);
        }
      }
    }

    let serializer = new XMLSerializer();
    let result = serializer.serializeToString(doc);
    
    // Fix self-closing tags like <script/> or <div/> which break the browser's HTML parser in iframes
    const htmlFixer = new DOMParser();
    const fixedDoc = htmlFixer.parseFromString(result, 'text/html');
    return fixedDoc.documentElement.outerHTML;
  }
}
