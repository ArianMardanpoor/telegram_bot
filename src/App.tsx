import React, { useState } from 'react';
import { Heart, FileCode, LayoutDashboard, Copy, Download, Github, HelpCircle, Flame, ShieldAlert, Sparkles } from 'lucide-react';
import BotSimulator from './components/BotSimulator';
import CodeExplorer from './components/CodeExplorer';
import AdminPanel from './components/AdminPanel';

export default function App() {
  const [activeTab, setActiveTab] = useState<'simulator' | 'code' | 'admin'>('simulator');

  const downloadAllAsZipText = () => {
    alert(
      "📦 کل پکیج پروژه در پوشه workspace شما با آدرس `/matching_bot_project` به همراه پورت‌ها، داکرکامپوز، نیازمندی‌ها و تمام هندلرها ذخیره شده است.\n\nمی‌توانید کل این ساختار را با زدن روی منوهای تنظیمات بالا سمت راست AI Studio در قالب فایل ZIP اکسپورت و دانلود کنید!"
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans" id="root-container">
      {/* Decorative top ambient bar */}
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-600 via-indigo-600 to-rose-600"></div>

      {/* Primary header panel */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40 px-4 md:px-8 py-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-rose-500/20 border border-indigo-900/40 relative">
              <Heart className="w-6 h-6 text-rose-500 fill-rose-500 animate-pulse" />
              <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full absolute top-1 right-1 border border-slate-950 animate-ping"></div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg md:text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  Dating & Matchmaking Bot Architect
                </h1>
                <span className="text-[10px] text-rose-400 bg-rose-950/40 border border-rose-900/50 px-2.5 py-0.5 rounded-full font-bold">
                  Persian (فارسی)
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 font-medium leading-relaxed">
                A highly scalable, production-grade Telegram Bot architecture using <code className="text-indigo-400 font-mono">aiogram 3.x</code>, <code className="text-purple-400 font-mono">FastAPI</code>, <code className="text-emerald-400 font-mono">MySQL 8.0</code>, and <code className="text-cyan-400 font-mono">Redis</code>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto self-stretch md:self-auto">
            <button
              onClick={downloadAllAsZipText}
              className="flex-1 md:flex-none flex items-center justify-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-800 px-4 py-2 rounded-xl text-xs font-semibold select-none transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export matching_bot_project</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8 space-y-6">
        {/* Navigation Tabs bar */}
        <div className="flex items-center border-b border-slate-900 p-1 bg-slate-950 rounded-xl" id="nav-tabs-wrapper">
          <button
            onClick={() => setActiveTab('simulator')}
            className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'simulator'
                ? 'bg-gradient-to-r from-blue-600/15 to-indigo-600/15 border-b-2 border-blue-500 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Flame className="w-4 h-4 text-rose-500" />
            <span> شبیه‌ساز واقعی ربات (Interactive Simulator)</span>
          </button>
          <button
            onClick={() => setActiveTab('code')}
            className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'code'
                ? 'bg-gradient-to-r from-blue-600/15 to-indigo-600/15 border-b-2 border-blue-500 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-4 h-4 text-blue-400" />
            <span>📁 فایل‌های مرجع پروژه (Python Code Explorer)</span>
          </button>
          <button
            onClick={() => setActiveTab('admin')}
            className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              activeTab === 'admin'
                ? 'bg-gradient-to-r from-blue-600/15 to-indigo-600/15 border-b-2 border-blue-500 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutDashboard className="w-4 h-4 text-indigo-400" />
            <span>📊 مانیتورینگ ادمین (Online Status System)</span>
          </button>
        </div>

        {/* Workspace Display Viewports */}
        <div className="transition-all duration-300">
          {activeTab === 'simulator' && <BotSimulator />}
          {activeTab === 'code' && <CodeExplorer />}
          {activeTab === 'admin' && <AdminPanel />}
        </div>

        {/* Bottom Technical Specifications block */}
        <div className="bg-slate-900/40 border border-slate-900 rounded-xl p-4 md:p-6 mt-8">
          <h3 className="text-white text-sm font-semibold flex items-center gap-2 mb-3">
            <ShieldAlert className="w-4.5 h-4.5 text-indigo-400" />
             ویژگی‌های طلایی معماری ربات همسریابی (Architectural Highlights)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs text-slate-300">
            <div className="space-y-1.5 p-3 rounded-lg bg-slate-950/55 border border-slate-850">
              <span className="font-semibold text-white flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Onboarding & FSM Sync
              </span>
              <p className="leading-relaxed text-slate-400">
                میدلور کنترل کانال با کش‌کردن در Redis از بن‌شدن بات توسط سقف کوئری تلگرام ممانعت می‌کند. پرسشنامه ۲۰ سوالی با همگام‌سازی FSM یک فرآیند تفاهم‌سنجی پایدار رقم می‌زند.
              </p>
            </div>
            <div className="space-y-1.5 p-3 rounded-lg bg-slate-950/55 border border-slate-850">
              <span className="font-semibold text-white flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" /> Fast Match Engine (Redis)
              </span>
              <p className="leading-relaxed text-slate-400">
                لیست‌های Redis به منزله صف مستقیم FIFO برای دختران و پسران مورد استفاده قرار می‌گیرند. مدل ویژه با تفکیک منطقه‌ای بدون ایجاد گلوگاه، کوئری‌های MySQL را سبک نگه می‌دارد.
              </p>
            </div>
            <div className="space-y-1.5 p-3 rounded-lg bg-slate-950/55 border border-slate-850">
              <span className="font-semibold text-white flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Privacy & Broadcaster
              </span>
              <p className="leading-relaxed text-slate-400">
                موتور تصفیه ریجکس از انتقال لینک‌های مخرب یا آیدی‌ها در چت مستقیم ناشناس ممانعت به عمل می‌آورد. برودکستر ناهمگام وظیفه ارسال دسته‌ای را بدون کلاک مسدودساز جلو می‌برد.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer copyright */}
      <footer className="border-t border-slate-900 py-6 px-4 text-center text-slate-500 text-xs mt-auto">
        <p>© 2026 Telegram Matchmaking & Dating Bot Architect. Crafted with React, FastAPI, SQLAlchemy and Redis.</p>
      </footer>
    </div>
  );
}
