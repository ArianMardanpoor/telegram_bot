// Types for the Telegram Dating & Matchmaking Bot Interactive Simulation

export interface SimulatedUser {
  id: number;
  tg_id: number;
  first_name: string;
  username?: string;
  age: number;
  gender: 'Male' | 'Female';
  city: string;
  is_vip: boolean;
  vip_quota: number;
  referrer_id?: number;
  joined_channel: boolean;
  completed_registration: boolean;
}

export interface SimulatedQuestion {
  id: number;
  question_text: string;
  option_a: string;
  option_b: string;
  category: string;
}

export interface ChatMessage {
  id: string;
  sender_id: number;
  sender_name: string;
  text: string;
  timestamp: string;
  original_text?: string;
  filtered: boolean;
}

export interface CodeFile {
  path: string;
  description: string;
  language: string;
  content: string;
}
