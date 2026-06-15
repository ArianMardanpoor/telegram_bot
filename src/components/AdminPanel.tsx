import React, { useState } from 'react';
import { LayoutDashboard, Users, Heart, Sparkles, Send, CheckCircle2, AlertTriangle, Play, HelpCircle } from 'lucide-react';

export default function AdminPanel() {
  const [bText, setBText] = useState('');
  const [bStatus, setBStatus] = useState<'idle' | 'running' | 'completed'>('idle');
  const [progress, setProgress] = useState(0);
  const [metrics, setMetrics] = useState({
    totalUsers: 1420,
    activeMatches: 38,
    vipUsers: 154,
    completedGamePercent: 78,
  });

  const runBroadcastSim = () => {
    if (!bText.trim()) {
      alert("لطفا پیام ارسالی برودکست را بنویسید!");
      return;
    }
    setBStatus('running');
    setProgress(0);
    
    // Simulate async batch delivery tasks
    let count = 0;
    const interval = setInterval(() => {
      count += 20;
      setProgress(count);
      if (count >= 100) {
        clearInterval(interval);
        setBStatus('completed');
        // Let's increment mock users metrics due to broadcast awareness
        setMetrics((prev) => ({
          ...prev,
          totalUsers: prev.totalUsers + 4,
          activeMatches: prev.activeMatches + 2,
        }));
      }
    }, 400);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-4 md:p-6" id="admin-panel-section">
      <div className="border-b border-slate-800 pb-4 mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-white text-lg font-bold flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-indigo-400" />
            پنل ادمین و مانیتورینگ آنلاین ربات (Admin panel Mockup)
          </h2>
          <p className="text-slate-400 text-xs mt-1">
            یک داشبورد عملیاتی همزمان برای مانیتورینگ تراکنش‌ها، تعداد کاربران فعال و تست سیستم ارسال همگانی یا ری‌پورت‌های روزانه:
          </p>
        </div>
        <span className="text-white text-xs bg-indigo-950 border border-indigo-900 text-indigo-300 font-medium px-3 py-1 rounded-full">
           سرویس وب: FastAPI active
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Metric Card 1 */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">کل کاربران ثبت‌نامی</span>
            <span className="text-2xl font-bold font-mono text-white mt-1 block">{metrics.totalUsers}</span>
          </div>
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <Users className="w-5 h-5" />
          </div>
        </div>

        {/* Metric Card 2 */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">دیتهای فعال همزمان</span>
            <span className="text-2xl font-bold font-mono text-emerald-400 mt-1 block">{metrics.activeMatches} زوج</span>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Heart className="w-5 h-5" />
          </div>
        </div>

        {/* Metric Card 3 */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">تعداد کل اعضای VIP</span>
            <span className="text-2xl font-bold font-mono text-amber-500 mt-1 block">{metrics.vipUsers} نفر</span>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-indigo-400">
            <Sparkles className="w-5 h-5 text-amber-500" />
          </div>
        </div>

        {/* Metric Card 4 */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 block font-medium">نرخ اتمام پرسشنامه</span>
            <span className="text-2xl font-bold font-mono text-purple-400 mt-1 block">{metrics.completedGamePercent}%</span>
          </div>
          <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Broadcast block */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-white text-sm font-semibold flex items-center gap-2 mb-2">
              <Send className="w-4 h-4 text-indigo-400" />
              سیستم ارسال پیام همگانی (Async Broadcast Handler)
            </h3>
            <p className="text-slate-400 text-xs leading-relaxed mb-4">
              این ماژول پیام‌های عمومی را بدون قفل کردن حلقه رویدادهای اصلی بات (Event Loop) به صورت همگام در فرم وظایف سنگین پس‌زمینه ارسال می‌کند. 
              استثناهای مسدود شدن توسط مخاطب (<code className="text-rose-500 font-mono">TelegramForbiddenError</code>) فیلتر خواهند شد.
            </p>

            <div className="space-y-3">
              <textarea
                value={bText}
                onChange={(e) => setBText(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs text-white outline-none h-24 resize-none"
                placeholder="متن پیام برودکست خود را اینجا بنویسید (مثال: تخفیف ویژه به مناسبت عید نوروز برای خرید اشتراک VIP ربات...)"
              />
            </div>
          </div>

          <div className="pt-4 border-t border-slate-850 mt-4">
            {bStatus === 'idle' && (
              <button
                onClick={runBroadcastSim}
                className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2 px-4 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center justify-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5 fill-white" />
                شروع ارسال نوتیفیکیشن پس‌زمینه
              </button>
            )}

            {bStatus === 'running' && (
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400 animate-pulse">در حال انجام ارسال دسته‌ای (ثانیه-شمار)...</span>
                  <span className="text-indigo-400 font-bold">{progress}%</span>
                </div>
                <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-500 h-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="text-[10px] text-slate-500 text-center font-mono">
                  Workers activity: sending to users, rate limiting respect (30 messages / sec)...
                </p>
              </div>
            )}

            {bStatus === 'completed' && (
              <div className="space-y-4">
                <div className="bg-emerald-950/40 border border-emerald-900 text-emerald-400 p-3 rounded-lg text-xs flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block">ارسال با موفقیت به پایان رسید!</span>
                    <span className="text-[11px] text-slate-300 block mt-0.5">
                      متریک گزارش نهایی: ۱,۴۰۸ کل ارسالی موفق | ۱۲ مسدود شده توسط کاربر (BotBlocked) | ۰ خطای سرور.
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => { setBStatus('idle'); setBText(''); }}
                  className="w-full bg-slate-800 hover:bg-slate-750 text-white text-xs py-2 px-4 rounded-lg transition-all cursor-pointer"
                >
                  ارسال پیام جدید
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Database backup block */}
        <div className="bg-slate-950 border border-slate-850 p-4 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-white text-sm font-semibold flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 font-semibold" />
              بکاپ‌های زمانی و نگهداری دیتابیس (Database Cron Jobs)
            </h3>
            <p className="text-slate-400 text-xs leading-relaxed mb-4">
              ما اسکریپت بکاپ‌گیری دوره‌ای <code className="text-blue-400 font-mono">mysql_backup.sh</code> را در پوشه اسکریپت‌ها قرار داده‌ایم. 
              این اسکریپت با کرون جاب با فرکانس مشخص روی کانتینر MySQL فایل فشرده بکاپ را ایجاد و آرشیوهای قدیمی‌تر از ۳۰ روز را پاک می‌کند.
            </p>

            <div className="bg-slate-900 border border-slate-800/80 p-3 rounded-lg font-mono text-[11px] space-y-1">
              <span className="text-purple-400"># Crontab configuration rule:</span>
              <p className="text-slate-300">0 3 * * * /app/matching_bot_project/scripts/mysql_backup.sh &gt;&gt; /var/log/cron.log 2&gt;&amp;1</p>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-850 mt-4">
            <div className="flex items-start gap-2 bg-indigo-950/20 border border-indigo-900/30 p-3 rounded-lg text-xs leading-relaxed text-slate-300">
              <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <p>
                تمامی الگوها، کوئری‌های SQL و کانفیگ‌های فرعی دیتابیس در کدهای قرارگرفته در دایرکتوری <code className="text-emerald-400 font-mono">/matching_bot_project</code> موجود و قابل ویرایش هستند.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
