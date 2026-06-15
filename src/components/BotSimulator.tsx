import React, { useState, useEffect, useRef } from 'react';
import { User, ShieldCheck, Heart, Sparkles, MessageSquare, AlertCircle, RefreshCw, Send, CheckCircle2, UserCheck, Trash2, ArrowRight } from 'lucide-react';
import { SimulatedUser, SimulatedQuestion, ChatMessage } from '../types';

// Mock Question Bank of 20 questions
const SIMULATED_QUESTIONS: SimulatedQuestion[] = [
  {
    id: 1,
    category: 'رابطه عاطفی',
    question_text: 'کدام گزینه در رابطه زناشویی برای شما از اهمیت بشتری برخوردار است؟',
    option_a: 'احترام متقابل و درک کامل شرایط',
    option_b: 'عشق پرشور همراه با هیجان عاطفی'
  },
  {
    id: 2,
    category: 'تفریحات',
    question_text: 'ترجیح می‌دهید اوقات فراغت خود را چگونه و در کجا سپری کنید؟',
    option_a: 'استراحت در خانه، مطالعه و تماشای فیلم',
    option_b: 'تفریحات گروهی، شلوغی و سفرهای عمیق'
  },
  {
    id: 3,
    category: 'حل‌مسئله',
    question_text: 'اگر در بین زوجین مشکلی پیش بیاید، کدام رویکرد تفاهمی‌تر است؟',
    option_a: 'گفتگوی منطقی، صبورانه و سریع',
    option_b: 'سکوت موقت و حل مسئله به مرور زمان'
  },
  {
    id: 4,
    category: 'مالی',
    question_text: 'مدیریت هزینه‌ها در زندگی مشترک از نظر شما چگونه است؟',
    option_a: 'برنامه‌ریزی دقیق مالی و پس‌انداز منظم',
    option_b: 'تعادل مالی بدون سخت‌گیری بیش از حد'
  },
  {
    id: 5,
    category: 'اشتغال',
    question_text: 'با شاغل بودن دوجانبه در تامین معیشت هم‌نظر هستید؟',
    option_a: 'بله، همکاری در تامین شرایط معیشتی الزامی است',
    option_b: 'خیر، ترجیح می‌دهم تمرکز روی کارهای خانه باشد'
  },
];

export default function BotSimulator() {
  // Simulator State
  const [ali, setAli] = useState<SimulatedUser>({
    id: 1,
    tg_id: 12345678,
    first_name: 'علی (Ali)',
    username: 'ali_dev',
    age: 26,
    gender: 'Male',
    city: 'تهران (Tehran)',
    is_vip: false,
    vip_quota: 3,
    joined_channel: false,
    completed_registration: false,
  });

  const [zahra, setZahra] = useState<SimulatedUser>({
    id: 2,
    tg_id: 87654321,
    first_name: 'زهرا (Zahra)',
    username: 'zahra_teh',
    age: 24,
    gender: 'Female',
    city: 'تهران (Tehran)',
    is_vip: false,
    vip_quota: 2,
    joined_channel: true, // Auto joined
    completed_registration: true, // Already registered
  });

  // Flow State
  // 'onboarding' | 'queuing' | 'questionnaire' | 'approval' | 'anonymous_chat'
  const [aliStatus, setAliStatus] = useState<'start' | 'channel_join' | 'onboarding_details' | 'ready'>('start');
  const [queueType, setQueueType] = useState<'free' | 'vip' | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchTimer, setSearchTimer] = useState(0);
  const [currentStep, setCurrentStep] = useState<'setup' | 'matching' | 'dating_game' | 'consent' | 'chat'>('setup');

  // Interactive Game Questions State
  const [qIndex, setQIndex] = useState(0);
  const [aliAnswer, setAliAnswer] = useState<string | null>(null);
  const [zahraAnswer, setZahraAnswer] = useState<string | null>(null);
  const [compatibilityPercent, setCompatibilityPercent] = useState(85);
  const [aliAnswersList, setAliAnswersList] = useState<string[]>([]);
  const [zahraAnswersList, setZahraAnswersList] = useState<string[]>([]);

  // Approval steps
  const [aliApproved, setAliApproved] = useState(false);
  const [zahraApproved, setZahraApproved] = useState(false);

  // Chat message stack
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [aliInput, setAliInput] = useState('');
  const [zahraInput, setZahraInput] = useState('');

  // Refs for auto-scroll
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);

  // Queue Sim Timer
  useEffect(() => {
    let interval: any;
    if (isSearching) {
      interval = setInterval(() => {
        setSearchTimer((prev) => {
          if (prev >= 2) {
            setIsSearching(false);
            setCurrentStep('dating_game');
            setQIndex(0);
            setAliAnswer(null);
            setZahraAnswer(null);
            return 0;
          }
          return prev + 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isSearching]);

  // Handle Onboarding Completion for Ali
  const handleCompleteOnboarding = () => {
    setAli((prev) => ({
      ...prev,
      completed_registration: true,
    }));
    setAliStatus('ready');
  };

  const handleStartMatching = (type: 'free' | 'vip') => {
    if (type === 'vip' && ali.vip_quota <= 0) {
      alert("شما فاقد سهمیه مچینگ ویژه هستید! برای برخورداری از سهمیه به سیستم زیرمجموعه‌گیری رجوع کنید.");
      return;
    }

    if (type === 'vip') {
      setAli((prev) => ({ ...prev, vip_quota: prev.vip_quota - 1 }));
    }

    setQueueType(type);
    setIsSearching(true);
    setSearchTimer(0);
    setCurrentStep('matching');
  };

  // Synchronized Game Answer Registers
  const handleAnswerSubmit = (user: 'ali' | 'zahra', option: 'A' | 'B') => {
    if (user === 'ali') {
      setAliAnswer(option);
      const updatedList = [...aliAnswersList];
      updatedList[qIndex] = option;
      setAliAnswersList(updatedList);
    } else {
      setZahraAnswer(option);
      const updatedList = [...zahraAnswersList];
      updatedList[qIndex] = option;
      setZahraAnswersList(updatedList);
    }
  };

  // Advanced sync questionnaire steps
  useEffect(() => {
    if (aliAnswer && zahraAnswer) {
      // Both users have answered this index! Let's schedule progression after brief visual feedback
      const timer = setTimeout(() => {
        if (qIndex < SIMULATED_QUESTIONS.length - 1) {
          setQIndex((prev) => prev + 1);
          setAliAnswer(null);
          setZahraAnswer(null);
        } else {
          // Calculate compatibility based on identical options selected
          let score = 0;
          for (let i = 0; i < SIMULATED_QUESTIONS.length; i++) {
            if (aliAnswersList[i] === zahraAnswersList[i]) score += 1;
          }
          const pct = Math.round((score / SIMULATED_QUESTIONS.length) * 100);
          setCompatibilityPercent(pct);
          setCurrentStep('consent');
        }
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [aliAnswer, zahraAnswer, qIndex, aliAnswersList, zahraAnswersList]);

  // Skip game to view compatibility approvals
  const handleSkipQuestionnaire = () => {
    // Fill mockup choices for both users
    const aliChoices = ['A', 'B', 'A', 'A', 'B'];
    const zahraChoices = ['A', 'A', 'A', 'B', 'B'];
    setAliAnswersList(aliChoices);
    setZahraAnswersList(zahraChoices);
    setCompatibilityPercent(80); // 4 out of 5 matches
    setCurrentStep('consent');
  };

  // Handle Approvals
  const handleApprove = (user: 'ali' | 'zahra') => {
    if (user === 'ali') setAliApproved(true);
    if (user === 'zahra') setZahraApproved(true);
  };

  useEffect(() => {
    if (aliApproved && zahraApproved) {
      setCurrentStep('chat');
      setChatMessages([
        {
          id: 'system_init',
          sender_id: 0,
          sender_name: 'System Bot',
          text: '🗣️ اتصال برقرار شد! گفتگوی ناشناس شما آغاز گردید. جهت حفظ حریم امن، آیدی تلگرام و لینک‌ها فیلتر خواهند شد.',
          timestamp: new Date().toLocaleTimeString(),
          filtered: false,
        }
      ]);
    }
  }, [aliApproved, zahraApproved]);

  // Regex filter messaging logic (mocking the python service)
  const handleSendMessage = (sender: 'ali' | 'zahra') => {
    const text = sender === 'ali' ? aliInput : zahraInput;
    if (!text.trim()) return;

    // Filter Logic
    let filteredText = text;
    let isFiltered = false;

    // 1. Username Regex
    if (/@([a-zA-Z0-9_]{3,32})/.test(text)) {
      filteredText = filteredText.replace(/@([a-zA-Z0-9_]{3,32})/g, '[🚷 آیدی فیلتر شد]');
      isFiltered = true;
    }

    // 2. URL Regex
    const urlPattern = /(https?:\/\/[^\s]+|www\.[^\s]+|[^\s]+\.(com|ir|org|net))/g;
    if (urlPattern.test(text)) {
      filteredText = filteredText.replace(urlPattern, '[🚷 لینک فیلتر شد]');
      isFiltered = true;
    }

    // 3. Persian/Standard Phone Number
    const phonePattern = /(09\d{9})|(\+98\d{9})/g;
    if (phonePattern.test(text)) {
      filteredText = filteredText.replace(phonePattern, '[🚷 تلفن فیلتر شد]');
      isFiltered = true;
    }

    const newMessage: ChatMessage = {
      id: Math.random().toString(),
      sender_id: sender === 'ali' ? ali.tg_id : zahra.tg_id,
      sender_name: sender === 'ali' ? 'پارتنر آقا' : 'پارتنر خانم',
      text: filteredText,
      original_text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      filtered: isFiltered,
    };

    setChatMessages((prev) => [...prev, newMessage]);

    if (sender === 'ali') setAliInput('');
    else setZahraInput('');
  };

  // Referral rewards simulation
  const handleSimulateReferralJoin = () => {
    // User registers successfully using link
    setAli((prev) => ({
      ...prev,
      vip_quota: prev.vip_quota + 1,
    }));
    alert("🎉 تبریک!\nیک کلاینت با لینک اختصاصی شما جذب شد و ثبت‌نام خود را به درستی به اتمام رساند. ۱ سهمیه مچ ویژه (VIP) به ظرفیت شما اضافه گردید!");
  };

  const resetAllSimulator = () => {
    setAliStatus('start');
    setAli({
      ...ali,
      joined_channel: false,
      completed_registration: false,
    });
    setZahra({
      ...zahra,
      joined_channel: true,
      completed_registration: true,
    });
    setAliAnswer(null);
    setZahraAnswer(null);
    setAliAnswersList([]);
    setZahraAnswersList([]);
    setAliApproved(false);
    setZahraApproved(false);
    setChatMessages([]);
    setCurrentStep('setup');
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl p-4 md:p-6" id="simulator-section">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-800 pb-4 mb-6 gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Heart className="w-5 h-5 text-rose-500 fill-rose-500 animate-pulse" />
            شبیه‌ساز تعاملی هسته ربات همسریابی تلگرام (Bot Simulator)
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            یک شبیه‌سازی گام‌به‌گام و مصور از تجربیات کاربری (User Experience)، تفاهم‌سنجی FSM و لایه‌های ایمنی چت ناشناس:
          </p>
        </div>
        <button
          onClick={resetAllSimulator}
          className="flex items-center gap-1 text-xs text-slate-300 hover:text-white bg-slate-800 border border-slate-700 px-3 py-1.5 rounded-lg transition-all cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          ریست شبیه‌ساز (Reset Sim)
        </button>
      </div>

      {/* Simulator Core Steps viewports */}
      {currentStep === 'setup' && (
        <div className="space-y-6">
          <div className="bg-slate-950 p-4 border border-slate-800 rounded-lg">
            <h3 className="text-emerald-400 font-medium text-sm flex items-center gap-2 mb-2">
              <ShieldCheck className="w-4 h-4" />
              مرحله اول: تایید اجباری عضویت کانال و احراز اطلاعات هویتی (Onboarding)
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed mb-4">
              در لایه ربات تلگرام، ما یک میدلور طراحی کرده‌ایم (<code className="text-amber-400 font-mono">ForceJoinMiddleware</code>). 
              هر کاربری که بخواهد دکمه‌ای ارسال کند، ابتدا تلگرام عضویت وی در کانال را کنترل می‌کند. 
              جهت کاهش فرخوانی وب سرویس تلگرام، اطلاعات بررسی شده را با TTL متمایز ۱۰ دقیقه‌ای در Redis کش می‌کنیم.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
              {/* Ali's Phone screen simulation mockup */}
              <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-lg flex flex-col h-[320px]">
                <div className="bg-slate-950 border-b border-slate-800/80 px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 rounded-full bg-blue-500"></div>
                    <span className="text-xs text-white font-mono">Ali - Telegram Box</span>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-medium bg-emerald-950 border border-emerald-900/40 px-2 py-0.5 rounded-full">
                    مشتری غیر فعال
                  </span>
                </div>

                <div className="flex-1 p-4 overflow-y-auto space-y-4 font-sans text-xs">
                  {aliStatus === 'start' && (
                    <div className="space-y-3">
                      <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-300">
                        💬 <strong>پیام خوش آمدگویی:</strong><br />
                        برای عضویت در سیستم لطفا دکمه /start را ارسال کنید:
                      </div>
                      <button
                        onClick={() => setAliStatus('channel_join')}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium p-2.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-all"
                      >
                         ارسال فرمان /start
                      </button>
                    </div>
                  )}

                  {aliStatus === 'channel_join' && (
                    <div className="space-y-3">
                      <div className="bg-blue-950/20 border border-blue-900/20 text-slate-200 p-4 rounded-lg">
                        ⚠️ <strong>جهت مچ‌یابی و دیت‌یابی ناشناس، عضویت در کانال ما الزامی است!</strong><br />
                        <span className="text-cyan-400 text-[11px] block mt-1">
                          (میدلور ForceJoin در این گام عضویت کاربر را صحت‌سنجی می‌کند...)
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <a
                          href="#channel"
                          onClick={(e) => {
                            e.preventDefault();
                            setAli((prev) => ({ ...prev, joined_channel: true }));
                            alert("عضویت علی در کانال پشتیبانی شبیه‌سازی شد (ثبت در Redis cache)");
                          }}
                          className={`p-2.5 text-center text-xs rounded-lg font-medium transition-all ${
                            ali.joined_channel
                              ? 'bg-emerald-950 border border-emerald-900 text-emerald-400'
                              : 'bg-slate-800 hover:bg-slate-750 text-white'
                          }`}
                        >
                          {ali.joined_channel ? '📢 عضو شدید' : '📢 عضویت در کانال'}
                        </a>
                        <button
                          onClick={() => {
                            if (!ali.joined_channel) {
                              alert("ابتدا باید دکمه عضویت در کانال را بزنید تا میدلور تایید کند!");
                              return;
                            }
                            setAliStatus('onboarding_details');
                          }}
                          className="bg-blue-600 hover:bg-blue-500 text-white font-medium p-2 rounded-lg cursor-pointer transition-all"
                        >
                          ✅ بررسی عضویت مجدد
                        </button>
                      </div>
                    </div>
                  )}

                  {aliStatus === 'onboarding_details' && (
                    <div className="space-y-3">
                      <div className="bg-slate-950 border border-slate-850 p-3 rounded-lg text-slate-300">
                        🙋‍♂️ <strong>کارت عضویت خود را تکمیل کنید:</strong><br />
                        <p className="mt-1 text-slate-400 text-[11px]">
                          جنسیت: مرد | سن: {ali.age} | شهر: {ali.city}
                        </p>
                      </div>
                      <div className="space-y-1">
                        <label className="text-[10px] text-slate-400">نام شهر محل سکونت:</label>
                        <input
                          type="text"
                          value={ali.city.replace(' (Tehran)', '')}
                          onChange={(e) => setAli({ ...ali, city: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white outline-none text-xs"
                          placeholder="تهران"
                        />
                      </div>
                      <button
                        onClick={handleCompleteOnboarding}
                        className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold p-2.5 rounded-lg flex items-center justify-center gap-1 cursor-pointer transition-all"
                      >
                         ذخیره اطلاعات و منوی اصلی
                      </button>
                    </div>
                  )}

                  {aliStatus === 'ready' && (
                    <div className="space-y-4 text-center mt-3">
                      <div className="inline-flex p-3 rounded-full bg-emerald-950/40 border border-emerald-900">
                        <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                      </div>
                      <p className="text-white font-medium text-xs">ثبت‌نام کامل انجام شد!</p>
                      <p className="text-slate-400 text-[11px]">صفحه دیت‌یابی و مچ‌یابی علی فعال شد.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Matching Panel and Explanatory summary */}
              <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                <div>
                  <h4 className="text-white text-sm font-medium mb-2 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    استراتژی مچینگ و توالی فرآیندها
                  </h4>
                  <ul className="text-slate-300 text-xs space-y-2 list-disc list-inside">
                    <li>یک کاربر پس از اونبوردینگ به عضو فعال تبدیل می‌شود.</li>
                    <li>موتور مچینگ از داده‌ساختار لیست‌ها در Redis برای ایجاد صف‌های متمایز جنسیتی استفاده می‌کند.</li>
                    <li>
                      همسریابی ویژه (VIP) از اطلاعات فیلتر جغرافیایی (شهر) یا بازه سنی استفاده کرده و سهمیه کاربران را کاهش می‌دهد.
                    </li>
                  </ul>

                  <div className="bg-slate-900 p-3 rounded-lg border border-slate-800/80 mt-4">
                    <span className="text-[10px] text-purple-400 block font-semibold mb-1">🎁 هدیه سهمیه‌گیری فعال:</span>
                    <p className="text-[11px] text-slate-300">
                      کاربران با کپی کردن اینک دعوت اختصاصی خود، در ازای ورود دوستان معتبر، شارژ سهمیه مچ ویژه دریافت می‌کنند:
                    </p>
                    <button
                      onClick={handleSimulateReferralJoin}
                      className="mt-2.5 w-full bg-purple-900/30 hover:bg-purple-900/50 border border-purple-800 text-purple-300 py-1.5 px-3 rounded text-xs transition-all cursor-pointer flex items-center justify-center gap-1"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      شبیه‌سازی جذب کلاینت با لینک دعوت اختصاصی (+۱ VIP)
                    </button>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-850">
                  {ali.completed_registration ? (
                    <div className="space-y-2">
                      <p className="text-slate-400 text-[10px] font-mono text-center">
                        Active Queues State: Available to match with opposite gender (Zahra)
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          onClick={() => handleStartMatching('free')}
                          className="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-3 rounded-lg text-xs transition-all cursor-pointer flex items-center justify-center gap-1"
                        >
                          🎲 شروع مچینگ تصادفی
                        </button>
                        <button
                          onClick={() => handleStartMatching('vip')}
                          className="bg-amber-600 hover:bg-amber-500 text-white font-medium py-2 px-3 rounded-lg text-xs transition-all cursor-pointer flex items-center justify-center gap-1"
                        >
                          👑 شروع مچینگ هم‌شهری ویژه
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center p-3 text-slate-500 text-xs">
                      ⚠️ برای فعال شدن کلیدهای مچینگ، ابتدا کارت اونبوردینگ علی را تکمیل کنید.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Queuing simulation state screen */}
      {currentStep === 'matching' && (
        <div className="bg-slate-950 p-6 border border-slate-800 rounded-lg text-center space-y-4">
          <div className="relative inline-block">
            <div className="w-16 h-16 rounded-full border-4 border-blue-600 border-t-transparent animate-spin"></div>
            <Heart className="w-6 h-6 text-red-500 fill-red-500 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <h3 className="text-white font-medium text-sm">در حال تطبیق یابی و جستجو در صف Redis...</h3>
          <div className="max-w-md mx-auto bg-slate-900 border border-slate-800 p-4 rounded-lg space-y-2 text-left font-mono text-xs">
            <p className="text-blue-400"># Redis Activity Logs:</p>
            <p className="text-slate-300">
              <span className="text-emerald-400">ADD</span> user:state:12345678 - status: queuing
            </p>
            <p className="text-slate-300">
              <span className="text-emerald-400">PUSH</span> match:queue:Male:{queueType === 'vip' ? 'vip:tehran' : 'free'}
            </p>
            <p className="text-slate-300">
              <span className="text-emerald-400">RPOP</span> match:queue:Female:{queueType === 'vip' ? 'vip:tehran' : 'free'} ...
            </p>
            <p className="text-amber-400 animate-pulse">
              🚀 یافت شدن جفت! مچ‌شدن علی با شناسه {ali.tg_id} و زهرا با شناسه {zahra.tg_id} ...
            </p>
          </div>
        </div>
      )}

      {/* Synchronized Dating Questionnaire (FSM Demonstration) */}
      {currentStep === 'dating_game' && (
        <div className="space-y-4">
          <div className="bg-blue-950/20 border border-blue-900/30 p-4 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
            <div className="text-xs text-slate-300">
              <p className="font-semibold text-blue-300">🎮 مکانیزم تفاهم‌سنجی سینکرونایز (Synchronized FSM):</p>
              <p className="mt-1 leading-relaxed">
                برای جلوگیری از رها شدن بات توسط یک کاربر، ربات به صورت توالی هماهنگ کار می‌کند. 
                <strong> کاربر ۲ تنها زمانی می‌تواند سوال N را ببیند که کاربر ۱ نیز به سوال N-1 پاسخ داده باشد.</strong> 
                هر سوال با انقضای ۳ دقیقه‌ای در Redis ست می‌شود.
              </p>
            </div>
          </div>

          <div className="flex justify-between items-center bg-slate-950 px-4 py-2 border border-slate-850 rounded-lg">
            <span className="text-xs text-slate-300">شناسه مسابقه مچینگ: <code className="text-amber-400 font-mono">match_id: 1045</code></span>
            <button
              onClick={handleSkipQuestionnaire}
              className="bg-slate-800 hover:bg-slate-750 text-white text-[11px] font-medium py-1 px-3 rounded cursor-pointer transition-all flex items-center gap-1"
            >
              🚀 پرش مستقیم به پایان پرسشنامه (دیدن تفاهم درصد)
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Phone A: Ali’s screen */}
            <div className="bg-slate-950 border border-slate-850 rounded-xl overflow-hidden p-4 flex flex-col h-[340px]">
              <div className="border-b border-slate-800 pb-2 mb-3 flex justify-between items-center">
                <span className="text-white text-xs font-semibold">تلفن علی (Ali)</span>
                <span className="text-[10px] text-slate-400">FSM State: Questionnaire</span>
              </div>

              <div className="flex-1 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="bg-blue-950/30 border border-blue-900/10 p-3 rounded-lg">
                    <span className="text-[10px] text-blue-400 block font-semibold">سوال {qIndex + 1} از ۵:</span>
                    <p className="text-xs text-white mt-1 leading-relaxed">{SIMULATED_QUESTIONS[qIndex].question_text}</p>
                  </div>

                  {aliAnswer ? (
                    <div className="p-3 bg-emerald-950/30 border border-emerald-900/40 rounded-lg text-emerald-400 text-xs text-center">
                      ⏳ پاسخ شما ثبت شد. منتظر جواب پارتنر خانم (Zahra) بمانید...
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <button
                        onClick={() => handleAnswerSubmit('ali', 'A')}
                        className="w-full text-left text-xs bg-slate-900 hover:bg-slate-850 text-slate-300 p-2.5 rounded-lg border border-slate-800/80 transition-all cursor-pointer"
                      >
                        🅰️ {SIMULATED_QUESTIONS[qIndex].option_a}
                      </button>
                      <button
                        onClick={() => handleAnswerSubmit('ali', 'B')}
                        className="w-full text-left text-xs bg-slate-900 hover:bg-slate-850 text-slate-300 p-2.5 rounded-lg border border-slate-800/80 transition-all cursor-pointer"
                      >
                        🅱️ {SIMULATED_QUESTIONS[qIndex].option_b}
                      </button>
                    </div>
                  )}
                </div>

                <div className="text-[10px] text-slate-400 text-center font-mono">
                  redis key: date:timeout:1045 (TTL limits check)
                </div>
              </div>
            </div>

            {/* Phone B: Zahra’s screen */}
            <div className="bg-slate-950 border border-slate-850 rounded-xl overflow-hidden p-4 flex flex-col h-[340px]">
              <div className="border-b border-slate-800 pb-2 mb-3 flex justify-between items-center">
                <span className="text-white text-xs font-semibold">تلفن زهرا (Zahra)</span>
                <span className="text-[10px] text-slate-400">FSM State: Questionnaire</span>
              </div>

              <div className="flex-1 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="bg-purple-950/30 border border-purple-900/10 p-3 rounded-lg">
                    <span className="text-[10px] text-purple-400 block font-semibold">سوال {qIndex + 1} از ۵:</span>
                    <p className="text-xs text-white mt-1 leading-relaxed">{SIMULATED_QUESTIONS[qIndex].question_text}</p>
                  </div>

                  {zahraAnswer ? (
                    <div className="p-3 bg-emerald-950/30 border border-emerald-900/40 rounded-lg text-emerald-400 text-xs text-center">
                      ⏳ پاسخ شما ثبت شد. منتظر جواب پارتنر آقا (Ali) بمانید...
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <button
                        onClick={() => handleAnswerSubmit('zahra', 'A')}
                        className="w-full text-left text-xs bg-slate-900 hover:bg-slate-850 text-slate-300 p-2.5 rounded-lg border border-slate-800/80 transition-all cursor-pointer"
                      >
                        🅰️ {SIMULATED_QUESTIONS[qIndex].option_a}
                      </button>
                      <button
                        onClick={() => handleAnswerSubmit('zahra', 'B')}
                        className="w-full text-left text-xs bg-slate-900 hover:bg-slate-850 text-slate-300 p-2.5 rounded-lg border border-slate-800/80 transition-all cursor-pointer"
                      >
                        🅱️ {SIMULATED_QUESTIONS[qIndex].option_b}
                      </button>
                    </div>
                  )}
                </div>

                <div className="text-[10px] text-slate-400 text-center font-mono">
                  DB record: user_answers table inserts rows on write
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Consent Page */}
      {currentStep === 'consent' && (
        <div className="bg-slate-950 border border-slate-850 rounded-xl p-6 text-center space-y-6">
          <div className="inline-flex items-center justify-center p-3 rounded-full bg-rose-950/40 border border-rose-900 mb-2">
            <Heart className="w-10 h-10 text-rose-500 fill-rose-500" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">تفاهم‌سنجی به پایان رسید!</h3>
            <p className="text-xs text-slate-300 mt-1 max-w-lg mx-auto">
              شما و شریک عاطفی مشترک تان بر اساس مدل تحلیل اشتراکات، به برآورد تفاهم تائید‌شده زیر رسیده‌اید:
            </p>
            <div className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-rose-500 to-amber-500 font-mono my-4">
              {compatibilityPercent}% تفاهم عقیدتی
            </div>
          </div>

          <div className="max-w-2xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-850">
            {/* Ali Approval */}
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex flex-col justify-between align-middle">
              <span className="text-xs text-slate-400 block mb-2">پوشه رضایت آقا (Ali)</span>
              {aliApproved ? (
                <div className="text-emerald-400 text-xs font-semibold flex items-center justify-center gap-1.5 py-2">
                  <CheckCircle2 className="w-4 h-4" />
                   موافقت خود را اعلام کردید
                </div>
              ) : (
                <button
                  onClick={() => handleApprove('ali')}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-2.5 px-4 rounded-lg transition-all cursor-pointer"
                >
                  ✅ موافقم؛ شروع گفتگو ناشناس
                </button>
              )}
            </div>

            {/* Zahra Approval */}
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-lg flex flex-col justify-between align-middle">
              <span className="text-xs text-slate-400 block mb-2">پوشه رضایت خانم (Zahra)</span>
              {zahraApproved ? (
                <div className="text-emerald-400 text-xs font-semibold flex items-center justify-center gap-1.5 py-2">
                  <CheckCircle2 className="w-4 h-4" />
                   موافقت خود را اعلام کردید
                </div>
              ) : (
                <button
                  onClick={() => handleApprove('zahra')}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-2.5 px-4 rounded-lg transition-all cursor-pointer"
                >
                  ✅ موافقم； شروع گفتگو ناشناس
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Anonymous Chat Room with regex filters! */}
      {currentStep === 'chat' && (
        <div className="space-y-6">
          <div className="bg-amber-950/30 border border-amber-900/30 p-3 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div className="text-[11px] text-amber-300">
              <p className="font-semibold">⚠️ آزمایشگاه لایه‌های امنیت حریم خصوصی (Privacy Filters Playground):</p>
              <p className="mt-0.5 leading-relaxed">
                پیام‌ها را با درج عبارات مشکوک مانند آیدی‌ها (مثال: @ali_dev_test)، شماره‌های تماس (09121234567) یا تارنماها (http://google.com) تایپ کنید تا تصفیه و سانسور خودکار پیام توسط ریجکس‌ها را مستقیما ببینید!
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Phone Ali Screen (Left) */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden p-4 flex flex-col h-[400px]">
              <div className="border-b border-slate-850 pb-2 mb-3 flex justify-between items-center">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                  <span className="text-white text-xs font-semibold">گفتگوی علی (Ali)</span>
                </div>
                <span className="text-[10px] text-slate-400">انتقال ایمن: active</span>
              </div>

              {/* Message Feed inside Ali phone */}
              <div className="flex-1 overflow-y-auto space-y-2 p-2 bg-slate-900/45 rounded-lg custom-scrollbar">
                {chatMessages.map((msg, idx) => (
                  <div
                    key={msg.id + idx}
                    className={`p-2.5 rounded-lg max-w-[85%] text-xs ${
                      msg.sender_id === 0
                        ? 'bg-blue-950/40 border border-blue-900/20 text-slate-300 mx-auto text-center'
                        : msg.sender_id === ali.tg_id
                        ? 'bg-blue-600 text-white ml-auto'
                        : 'bg-slate-800 text-slate-100 mr-auto'
                    }`}
                  >
                    {msg.sender_id !== 0 && (
                      <span className="text-[9px] block text-slate-400 font-bold mb-0.5">
                        {msg.sender_id === ali.tg_id ? 'شما (آقا)' : 'همسر خانم'}
                      </span>
                    )}
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    {msg.filtered && (
                      <span className="text-[9px] font-mono text-amber-400 mt-1 block">
                        ⚙️ سانسور شد (Privacy Filter applied)
                      </span>
                    )}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  value={aliInput}
                  onChange={(e) => setAliInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage('ali')}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
                  placeholder="اینجا پیام بنویسید... (تست آیدی: @test)"
                />
                <button
                  onClick={() => handleSendMessage('ali')}
                  className="bg-blue-600 hover:bg-blue-500 text-white p-2.5 rounded-lg cursor-pointer transition-all"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Phone Zahra Screen (Right) */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden p-4 flex flex-col h-[400px]">
              <div className="border-b border-slate-850 pb-2 mb-3 flex justify-between items-center">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                  <span className="text-white text-xs font-semibold">گفتگوی زهرا (Zahra)</span>
                </div>
                <span className="text-[10px] text-slate-400">انتقال ایمن: active</span>
              </div>

              {/* Message Feed inside Zahra phone */}
              <div className="flex-1 overflow-y-auto space-y-2 p-2 bg-slate-900/45 rounded-lg custom-scrollbar">
                {chatMessages.map((msg, idx) => (
                  <div
                    key={msg.id + idx + '_zahra'}
                    className={`p-2.5 rounded-lg max-w-[85%] text-xs ${
                      msg.sender_id === 0
                        ? 'bg-blue-950/40 border border-blue-900/20 text-slate-300 mx-auto text-center'
                        : msg.sender_id === zahra.tg_id
                        ? 'bg-pink-600 text-white ml-auto'
                        : 'bg-slate-800 text-slate-100 mr-auto'
                    }`}
                  >
                    {msg.sender_id !== 0 && (
                      <span className="text-[9px] block text-slate-400 font-bold mb-0.5">
                        {msg.sender_id === zahra.tg_id ? 'شما (خانم)' : 'همسر آقا'}
                      </span>
                    )}
                    <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                    {msg.filtered && (
                      <span className="text-[9px] font-mono text-amber-400 mt-1 block">
                        ⚙️ سانسور شد (Privacy Filter applied)
                      </span>
                    )}
                  </div>
                ))}
              </div>

              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  value={zahraInput}
                  onChange={(e) => setZahraInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage('zahra')}
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-white outline-none"
                  placeholder="اینجا پیام بنویسید... (تست تلفن: 09120000000)"
                />
                <button
                  onClick={() => handleSendMessage('zahra')}
                  className="bg-pink-600 hover:bg-pink-500 text-white p-2.5 rounded-lg cursor-pointer transition-all"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
