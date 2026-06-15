import React, { useState } from 'react';
import { pythonCodeFiles } from '../data/code_files';
import { FileCode, Folder, Copy, Check, Info, Server, Layers, Settings, FileSpreadsheet } from 'lucide-react';

export default function CodeExplorer() {
  const [selectedFile, setSelectedFile] = useState(pythonCodeFiles[0]);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getIcon = (path: string) => {
    if (path.includes('docker')) return <Server className="w-4 h-4 text-cyan-400" />;
    if (path.includes('database') || path.includes('session')) return <Layers className="w-4 h-4 text-emerald-400" />;
    if (path.includes('middleware') || path.includes('filters')) return <Settings className="w-4 h-4 text-amber-400" />;
    if (path.includes('requirements')) return <FileSpreadsheet className="w-4 h-4 text-purple-400" />;
    return <FileCode className="w-4 h-4 text-blue-400" />;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-4 md:p-6" id="code-explorer-section">
      {/* Sidebar file tree */}
      <div className="lg:col-span-4 border-r border-slate-800 pr-0 lg:pr-4">
        <h3 className="text-white font-medium mb-3 text-sm flex items-center gap-2">
          <Folder className="w-4 h-4 text-blue-400" />
           matching_bot_project /
        </h3>
        <p className="text-slate-400 text-xs mb-4">
          Click on any file below to view the clean, fully-commented Python code written directly to your workspace:
        </p>
        <div className="space-y-1 max-h-[480px] overflow-y-auto pr-2 custom-scrollbar">
          {pythonCodeFiles.map((file) => (
            <button
              key={file.path}
              onClick={() => setSelectedFile(file)}
              className={`w-full text-left p-3 rounded-lg flex items-start gap-3 transition-all ${
                selectedFile.path === file.path
                  ? 'bg-blue-600/15 border-l-2 border-blue-500 text-white'
                  : 'text-slate-300 hover:bg-slate-800/40'
              }`}
            >
              <div className="mt-0.5">{getIcon(file.path)}</div>
              <div>
                <span className="text-xs font-mono block break-all font-medium">{file.path}</span>
                <span className="text-[10px] text-slate-400 font-sans line-clamp-1 mt-0.5">{file.description}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Code Display viewer */}
      <div className="lg:col-span-8 flex flex-col h-[520px] bg-slate-950 rounded-lg overflow-hidden border border-slate-800">
        <div className="bg-slate-900/50 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span className="text-xs font-mono text-slate-300 ml-2 font-medium break-all">{selectedFile.path}</span>
          </div>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-750 px-3 py-1.5 rounded-md transition-all cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy Code</span>
              </>
            )}
          </button>
        </div>

        <div className="px-4 py-3 bg-blue-950/20 border-b border-slate-850 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <p className="text-[11px] text-slate-300 leading-relaxed">
            <span className="font-semibold text-blue-300">File Description:</span> {selectedFile.description}
          </p>
        </div>

        <div className="flex-1 overflow-auto p-4 font-mono text-xs text-slate-300 leading-relaxed custom-scrollbar">
          <pre className="whitespace-pre">{selectedFile.content}</pre>
        </div>
      </div>
    </div>
  );
}
