const fs = require('fs');
const path = require('path');

const componentsDir = path.join(__dirname, '..', 'src');

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    let isDirectory = fs.statSync(dirPath).isDirectory();
    isDirectory ? walkDir(dirPath, callback) : callback(path.join(dir, f));
  });
}

function replaceInFile(filepath) {
  if (!filepath.endsWith('.tsx')) return;

  let content = fs.readFileSync(filepath, 'utf-8');

  // App.tsx
  content = content.replace(/selection:bg-amber-500\/30 selection:text-slate-900 dark:selection:text-white/g, "selection:bg-app-primary/30 selection:text-app-text");

  // Text replacements
  content = content.replace(/text-slate-900 dark:text-slate-100/g, "text-app-text");
  content = content.replace(/text-slate-700 dark:text-slate-300/g, "text-app-text");
  content = content.replace(/text-slate-600 dark:text-slate-400/g, "text-app-muted");
  content = content.replace(/text-slate-500 dark:text-slate-400/g, "text-app-muted");
  content = content.replace(/text-slate-600 dark:text-slate-500/g, "text-app-muted");
  content = content.replace(/text-amber-600 dark:text-amber-500/g, "text-app-primary");
  content = content.replace(/text-amber-600 dark:text-amber-400/g, "text-app-primary");
  content = content.replace(/text-amber-700 dark:text-amber-300\/90/g, "text-app-primary");
  content = content.replace(/text-amber-700 dark:text-amber-300\/80/g, "text-app-primary");

  // Hover text
  content = content.replace(/hover:text-amber-600 dark:hover:text-amber-400/g, "hover:text-app-primary-hover");
  content = content.replace(/hover:text-amber-500 dark:hover:text-amber-400/g, "hover:text-app-primary-hover");

  // Backgrounds
  content = content.replace(/bg-white dark:bg-slate-950/g, "bg-app-surface");
  content = content.replace(/bg-white dark:bg-slate-900/g, "bg-app-surface");
  content = content.replace(/bg-slate-50 dark:bg-\[\#121212\]/g, "bg-app-surface");
  content = content.replace(/bg-slate-100 dark:bg-slate-900/g, "bg-app-surface-hover");
  content = content.replace(/bg-slate-200 dark:bg-slate-800/g, "bg-app-surface-hover");
  content = content.replace(/bg-slate-300 dark:bg-slate-600/g, "bg-app-muted");
  content = content.replace(/bg-slate-100\/50 dark:bg-slate-900\/50/g, "bg-app-surface-hover/50");
  content = content.replace(/bg-slate-200\/80 dark:bg-slate-800\/80/g, "bg-app-surface-hover/80");

  content = content.replace(/bg-\[\#121212\]/g, "bg-app-surface");
  content = content.replace(/hover:bg-slate-50 dark:hover:bg-slate-800/g, "hover:bg-app-surface-hover");
  content = content.replace(/hover:bg-slate-200 dark:hover:bg-slate-800/g, "hover:bg-app-surface-hover");

  // Borders
  content = content.replace(/border-slate-300 dark:border-slate-800/g, "border-app-border");
  content = content.replace(/border-slate-300 dark:border-slate-700\/50/g, "border-app-border");
  content = content.replace(/border-slate-200 dark:border-slate-800\/50/g, "border-app-border");
  content = content.replace(/border-slate-200 dark:border-slate-700/g, "border-app-border");
  content = content.replace(/border-slate-200 dark:border-slate-800/g, "border-app-border");
  content = content.replace(/border-slate-50 dark:border-\[\#0a0a0a\]/g, "border-app-bg");

  // Special
  content = content.replace(/hover:border-amber-500 hover:text-amber-500 dark:hover:border-amber-500 dark:hover:text-amber-400/g, "hover:border-app-primary hover:text-app-primary");

  fs.writeFileSync(filepath, content, 'utf-8');
}

walkDir(componentsDir, replaceInFile);
console.log("Done replacing.");
