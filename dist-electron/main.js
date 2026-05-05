import { BrowserWindow as e, app as t } from "electron";
import n from "node:path";
import { fileURLToPath as r } from "node:url";
//#region electron/main.ts
var i = n.dirname(r(import.meta.url));
process.env.APP_ROOT = n.join(i, "..");
var a = process.env.VITE_DEV_SERVER_URL, o = n.join(process.env.APP_ROOT, "dist-electron"), s = n.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = a ? n.join(process.env.APP_ROOT, "public") : s;
var c;
function l() {
	c = new e({
		width: 1200,
		height: 800,
		icon: n.join(process.env.VITE_PUBLIC, "favicon.svg"),
		webPreferences: {
			preload: n.join(i, "preload.mjs"),
			webSecurity: !1
		}
	}), c.setMenu(null), a ? c.loadURL(a) : c.loadFile(n.join(s, "index.html"));
}
t.on("window-all-closed", () => {
	process.platform !== "darwin" && (t.quit(), c = null);
}), t.whenReady().then(l);
//#endregion
export { o as MAIN_DIST, s as RENDERER_DIST, a as VITE_DEV_SERVER_URL };
