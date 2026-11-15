"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Mic,
  MicOff,
  Volume2,
  Play,
  Pause,
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle,
  Send,
  Sparkles,
  ExternalLink,
  RotateCcw,
  Copy,
  Mail,
  ShieldAlert,
  ChevronRight,
  Layers,
  ArrowRight,
  Info,
  Loader2
} from "lucide-react";

interface Clause {
  id?: string;
  clause_id?: string;
  clause_number: string;
  title: string;
  page_number: number;
  quote: string;
  risk_level: "High Risk" | "Medium Risk" | "Safe" | string;
  risk_badge?: string;
  advice?: string;
  evon_insight?: string;
}

interface DocumentInfo {
  doc_id: string;
  title: string;
  filename: string;
  page_count: number;
  total_clauses: number;
  high_risk_count: number;
  medium_risk_count: number;
  safe_count: number;
  overall_risk_score: number;
  clauses?: Clause[];
}

interface QueryResponse {
  user_query: string;
  detected_language: string;
  confidence?: number;
  executive_bullet_points: string[];
  cited_clauses: Clause[];
  actionable_advice?: string;
  spoken_summary: string;
  audio_base64?: string;
  audio_format?: string;
  tts_voice?: string;
}

const API_BASE = "http://localhost:8000";

const LOCALIZED_SUGGESTED_PROMPTS: Record<string, string[]> = {
  "en-IN": [
    "What happens if I terminate before the 24-month lock-in period?",
    "Are society maintenance charges of ₹4,500 included in the rent?",
    "When will my security deposit of ₹2,40,000 be refunded?",
    "What is the annual rent escalation rate under Clause 2.1?",
    "Is subletting or commercial use permitted under Clause 6.1?",
    "Can I make renovations or structural alterations under Clause 15.2?",
    "Who pays the stamp duty and e-registration charges under Clause 19.1?",
  ],
  "hi-IN": [
    "क्या 24 महीने के लॉक-इन पीरियड से पहले लीज समाप्त करने पर जुर्माना लगेगा?",
    "क्या किराए में ₹4,500 का सोसायटी मेंटेनेंस शुल्क शामिल है?",
    "₹2,40,000 की सुरक्षा जमा राशि कब और कैसे वापस मिलेगी?",
    "खंड 2.1 के तहत वार्षिक किराया वृद्धि की दर क्या है?",
    "क्या खंड 6.1 के तहत सबलेटिंग या व्यावसायिक उपयोग की अनुमति है?",
    "क्या खंड 15.2 के तहत मरम्मत या ढांचागत बदलाव किए जा सकते हैं?",
    "खंड 19.1 के तहत स्टाम्प ड्यूटी और रजिस्ट्रेशन शुल्क कौन भरेगा?",
  ],
  "mr-IN": [
    "24 महिन्यांच्या लॉक-इन कालावधीपूर्वी करार संपवल्यास काय दंड होईल?",
    "दरमहा ₹4,500 चे सोसायटी देखभाल शुल्क भाड्यात समाविष्ट आहे का?",
    "₹2,40,000 ची सुरक्षा ठेव कधी परत केली जाईल?",
    "कलम 2.1 अंतर्गत वार्षिक भाडेवाढ किती आहे?",
    "कलम 6.1 अंतर्गत पोटभाडेकरू ठेवण्यास किंवा व्यावसायिक वापरास परवानगी आहे का?",
    "कलम 15.2 नुसार जागेत संरचनात्मक बदल करता येतील का?",
    "कलम 19.1 नुसार मुद्रांक शुल्क आणि नोंदणी खर्च कोण देईल?",
  ],
  "kn-IN": [
    "24 ತಿಂಗಳ ಲಾಕ್-ಇನ್ ಅವಧಿಗೆ ಮುನ್ನ ಗುತ್ತಿಗೆ ರದ್ದುಗೊಳಿಸಿದರೆ ಏನು ಪರಿಣಾಮ?",
    "ತಿಂಗಳ ₹4,500 ಸೊಸೈಟಿ ನಿರ್ವಹಣಾ ವೆಚ್ಚವು ಬಾಡಿಗೆಯಲ್ಲಿ ಸೇರಿದೆಯೇ?",
    "₹2,40,000 ಭದ್ರತಾ ಠೇವಣಿಯನ್ನು ಯಾವಾಗ ಮರುಪಾವತಿಸಲಾಗುತ್ತದೆ?",
    "ಷರತ್ತು 2.1 ರ ಅಡಿಯಲ್ಲಿ ವಾರ್ಷಿಕ ಬಾಡಿಗೆ ಏರಿಕೆ ದರ ಎಷ್ಟು?",
    "ಷರತ್ತು 6.1 ರ ಅಡಿಯಲ್ಲಿ ಉಪ-ಬಾಡಿಗೆಗೆ ಅವಕಾಶವಿದೆಯೇ?",
    "ಷರತ್ತು 15.2 ರ ಅಡಿಯಲ್ಲಿ ಬದಲಾವಣೆಗಳನ್ನು ಮಾಡಬಹುದೇ?",
    "ಷರತ್ತು 19.1 ರ ಪ್ರಕಾರ ಮುದ್ರಾಂಕ ಶುಲ್ಕವನ್ನು ಯಾರು ಪಾವತಿಸಬೇಕು?",
  ],
  "ta-IN": [
    "24 மாத லாக்-இன் காலத்திற்கு முன் வெளியேறினால் என்ன நடக்கும்?",
    "மாதாந்திர ₹4,500 சொசைட்டி பராமரிப்பு கட்டணம் வாடகையில் அடங்குமா?",
    "₹2,40,000 பாதுகாப்பு வைப்புத்தொகை எப்போது திரும்ப வழங்கப்படும்?",
    "பிரிவு 2.1 இன் கீழ் ஆண்டு வாடகை உயர்வு விகிதம் என்ன?",
    "பிரிவு 6.1 இன் கீழ் உள்வாடகைக்கு அனுமதி உள்ளதா?",
    "பிரிவு 15.2 இன் கீழ் மாற்றங்களைச் செய்ய முடியுமா?",
    "பிரிவு 19.1 இன் படி முத்திரைத்தாள் கட்டணத்தை யார் செலுத்துவது?",
  ],
  "te-IN": [
    "24 నెలల లాక్-ఇన్ కాలానికి ముందే రద్దు చేస్తే ఏమి జరుగుతుంది?",
    "నెలకు ₹4,500 సొసైటీ నిర్వహణ ఛార్జీలు అద్దెలో చేర్చబడి ఉన్నాయా?",
    "₹2,40,000 సెక్యూరిటీ డిపాజిట్ ఎప్పుడు తిరిగి చెల్లించబడుతుంది?",
    "క్లాజ్ 2.1 ప్రకారం వార్షిక అద్దె పెరుగుదల ఎంత?",
    "క్లాజ్ 6.1 కింద సబ్-లీజుకు అనుమతి ఉందా?",
    "క్లాజ్ 15.2 కింద నిర్మాణ మార్పులు చేయవచ్చా?",
    "క్లాజ్ 19.1 ప్రకారం స్టాంప్ డ్యూటీ ఎవరు చెల్లించాలి?",
  ],
  "bn-IN": [
    "২৪ মাসের লক-ইন সময়সীমার আগে লিজ বাতিল করলে কী জরিমানা হবে?",
    "মাসিক ₹৪,৫০০ সোসাইটি রক্ষণাবেক্ষণ চার্জ কি ভাড়ার অন্তর্ভুক্ত?",
    "₹২,৪০,০০০ জামানত কখন এবং কীভাবে ফেরত পাওয়া যাবে?",
    "ধারা ২.১ অনুযায়ী বার্ষিক ভাড়া বৃদ্ধির হার কত?",
    "ধারা ৬.১ অনুযায়ী সাবলেট বা বাণিজ্যিক ব্যবহারের অনুমতি আছে কি?",
    "ধারা ১৫.২ অনুযায়ী কাঠামোগত পরিবর্তন করা যাবে কি?",
    "ধারা ১৯.১ অনুযায়ী স্ট্যাম্প ডিউটি ও রেজিস্ট্রেশন খরচ কে দেবে?",
  ],
  "gu-IN": [
    "24 મહિનાના લૉક-ઇન સમયગાળા પહેલાં લીઝ રદ કરવાથી શું થશે?",
    "માસિક ₹4,500 નો સોસાયટી મેઇન્ટેનન્સ ચાર્જ ભાડામાં સામેલ છે?",
    "₹2,40,000 ની સિક્યોરિટી ડિપોઝિટ ક્યારે પરત મળશે?",
    "કલમ 2.1 હેઠળ વાર્ષિક ભાડા વધારાનો દર કેટલો છે?",
    "કલમ 6.1 હેઠળ સબલેટિંગ કે વ્યાપારી ઉપયોગની મંજૂરી છે?",
    "કલમ 15.2 હેઠળ માળખાકીય ફેરફાર કરી શકાય?",
    "કલમ 19.1 મુજબ સ્ટેમ્પ ડ્યુટી અને નોંધણી ખર્ચ કોણ ચૂકવશે?",
  ],
};

function getSuggestedPrompts(clauses?: Clause[], langCode: string = "en-IN"): string[] {
  const normLang = langCode === "indic-auto" ? "en-IN" : langCode;
  const localizedDefaults = LOCALIZED_SUGGESTED_PROMPTS[normLang] || LOCALIZED_SUGGESTED_PROMPTS["en-IN"];

  if (!clauses || clauses.length === 0) {
    return localizedDefaults;
  }

  // If active document has clauses, return localized prompts for the active contract
  return localizedDefaults;
}

const TIMBRE_VOICES = [
  { name: "Shivani", gender: "Female", desc: "Expressive & Natural" },
  { name: "Avinash", gender: "Male", desc: "Authoritative & Deep" },
  { name: "Lakshmi", gender: "Female", desc: "Warm & Clear" },
  { name: "Kalpana", gender: "Female", desc: "Professional Tone" },
  { name: "Shubham", gender: "Male", desc: "Conversational" },
  { name: "Prakash", gender: "Male", desc: "Formal Legal Tone" },
  { name: "Devansh", gender: "Male", desc: "Crisp & Energetic" },
  { name: "Yashraj", gender: "Male", desc: "Polite & Calm" }
];

// Pure 16kHz mono 16-bit PCM WAV encoder using Web Audio API
function exportWAV(audioData: Float32Array, sampleRate: number = 16000): Blob {
  const buffer = new ArrayBuffer(44 + audioData.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + audioData.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); // 16-bit
  writeString(36, "data");
  view.setUint32(40, audioData.length * 2, true);

  let offset = 44;
  for (let i = 0; i < audioData.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, audioData[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([buffer], { type: "audio/wav" });
}

export default function LegalPortalPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [activeDocId, setActiveDocId] = useState<string>("sample_andheri_lease");
  const [activeDoc, setActiveDoc] = useState<DocumentInfo | null>(null);
  const [activeTab, setActiveTab] = useState<"clauses" | "pdf">("clauses");
  const [highlightedClauseId, setHighlightedClauseId] = useState<string | null>(null);
  const [isLoadingDoc, setIsLoadingDoc] = useState<boolean>(true);

  // Audio recording state
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [recordingDuration, setRecordingDuration] = useState<number>(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [languageCode, setLanguageCode] = useState<string>("indic-auto");
  const [voice, setVoice] = useState<string>("Shivani");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Text query input
  const [textInput, setTextInput] = useState<string>("");

  // Response state
  const [latestResponse, setLatestResponse] = useState<QueryResponse | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [emailModalOpen, setEmailModalOpen] = useState<boolean>(false);
  const [negotiationDraft, setNegotiationDraft] = useState<string>("");

  const suggestedPrompts = useMemo(() => {
    return getSuggestedPrompts(activeDoc?.clauses, languageCode);
  }, [activeDoc?.clauses, languageCode]);

  // Refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const pcmChunksRef = useRef<Float32Array[]>([]);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const clauseRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (activeDocId) {
      fetchDocumentDetails(activeDocId);
    }
  }, [activeDocId]);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.documents || []);
        if (data.documents && data.documents.length > 0 && !activeDocId) {
          setActiveDocId(data.documents[0].doc_id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      showToast("Cannot reach backend server. Make sure port 8000 is running.");
    }
  };

  const fetchDocumentDetails = async (id: string) => {
    setIsLoadingDoc(true);
    try {
      const res = await fetch(`${API_BASE}/api/documents/${id}`);
      if (res.ok) {
        const data = await res.json();
        setActiveDoc(data);
      } else {
        showToast("Error loading document details.");
      }
    } catch (err) {
      console.error("Failed to load document:", err);
      showToast("Could not load document details.");
    } finally {
      setIsLoadingDoc(false);
    }
  };

  // Recording with native Web Audio API (Pristine 16kHz Mono WAV)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      pcmChunksRef.current = [];

      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      // ScriptProcessorNode for raw PCM extraction
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        pcmChunksRef.current.push(new Float32Array(inputData));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setIsRecording(true);
      setRecordingDuration(0);
      drawWaveform();
    } catch (err) {
      console.error("Microphone access error:", err);
      showToast("Microphone access denied. Please grant permission in your browser.");
    }
  };

  const stopRecording = () => {
    if (!isRecording) return;
    setIsRecording(false);

    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    // Merge PCM chunks into a single Float32Array
    const chunks = pcmChunksRef.current;
    const totalLength = chunks.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Export as genuine 16kHz WAV
    const wavBlob = exportWAV(merged, 16000);
    setAudioBlob(wavBlob);

    // Auto-send voice query immediately
    handleSendVoiceQuery(wavBlob);
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isRecording]);

  const drawWaveform = () => {
    if (!canvasRef.current || !analyserRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const render = () => {
      animationFrameRef.current = requestAnimationFrame(render);
      analyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = (canvas.width / bufferLength) * 2;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height * 0.9;
        ctx.fillStyle = "#5D6DF6";
        ctx.beginPath();
        ctx.roundRect(x, canvas.height - barHeight, barWidth - 2, barHeight, [4, 4, 0, 0]);
        ctx.fill();
        x += barWidth;
      }
    };
    render();
  };

  // Real backend query via voice
  const handleSendVoiceQuery = async (blobToSend?: Blob) => {
    const targetBlob = blobToSend || audioBlob;
    if (!targetBlob) return;

    setIsProcessing(true);
    const formData = new FormData();
    formData.append("audio_file", targetBlob, "speech.wav");
    formData.append("doc_id", activeDocId);
    formData.append("language_code", languageCode);
    formData.append("voice", voice);

    try {
      const res = await fetch(`${API_BASE}/api/query/voice`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errJson.detail || "Voice query processing failed.");
      }

      const data: QueryResponse = await res.json();
      applyResponse(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("Voice query error:", err);
      showToast(`Query error: ${msg}`);
    } finally {
      setIsProcessing(false);
      setAudioBlob(null);
    }
  };

  // Real backend query via text
  const handleSendTextQuery = async (queryText?: string) => {
    const q = (queryText || textInput).trim();
    if (!q) return;

    setIsProcessing(true);
    try {
      const res = await fetch(`${API_BASE}/api/query/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          doc_id: activeDocId,
          language_code: languageCode,
          voice: voice,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errJson.detail || "Query processing failed.");
      }

      const data: QueryResponse = await res.json();
      applyResponse(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error("Query error:", err);
      showToast(`Query error: ${msg}`);
    } finally {
      setIsProcessing(false);
      setTextInput("");
    }
  };

  const applyResponse = (data: QueryResponse) => {
    setLatestResponse(data);

    // Decode base64 audio and prepare playback
    if (data.audio_base64) {
      const byteCharacters = atob(data.audio_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: data.audio_format || "audio/wav" });
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);

      setTimeout(() => {
        if (audioPlayerRef.current) {
          audioPlayerRef.current.currentTime = 0;
          audioPlayerRef.current
            .play()
            .then(() => setIsPlayingAudio(true))
            .catch((e) => console.log("Autoplay was blocked by browser:", e));
        }
      }, 250);
    }

    // Auto-scroll and highlight cited clause
    if (data.cited_clauses && data.cited_clauses.length > 0) {
      const firstClause = data.cited_clauses[0];
      const clauseId = firstClause.clause_id || firstClause.clause_number.replace(/\s+/g, "_");
      setHighlightedClauseId(clauseId);
      setActiveTab("clauses");

      setTimeout(() => {
        const el = clauseRefs.current[clauseId] || clauseRefs.current[firstClause.clause_number];
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 300);
    }
  };

  // Upload custom PDF document
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    showToast(`Parsing ${file.name} with PyMuPDF & indexing in Qdrant...`);

    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        showToast("New agreement indexed successfully!");
        await fetchDocuments();
        setActiveDocId(data.document.doc_id);
      } else {
        showToast("Upload failed: only PDF format supported.");
      }
    } catch (err) {
      console.error(err);
      showToast("Error uploading document to backend server.");
    }
  };

  const openNegotiationModal = (clause: Clause) => {
    const draft = `Subject: Proposed Amendment to ${clause.clause_number} (${clause.title}) - Tenancy Agreement\n\nDear Landlord / Property Manager,\n\nThank you for sharing the draft agreement for Flat No. 804, Sea Breeze Apartments. Upon reviewing ${clause.clause_number} with our legal review portal, we noticed that:\n\n"${clause.quote}"\n\nAs standard market practice in Indian tenancy, we kindly propose amending this clause to:\n\n"Either party may terminate the agreement after the initial lock-in period by providing 60 days (2 months) advance written notice, or payment of rent in lieu thereof, without additional forfeiture."\n\nWe look forward to signing once this adjustment is incorporated.\n\nWarm regards,\nA. Kumar (Tenant)`;
    setNegotiationDraft(draft);
    setEmailModalOpen(true);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#E6E9EF] text-[#2E3440]">
      {/* HEADER */}
      <header className="sticky top-0 z-40 bg-[#E6E9EF]/90 backdrop-blur-md border-b border-white/60 shadow-sm">
        <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 neu-sm flex items-center justify-center font-serif text-lg font-bold text-[#5D6DF6] bg-[#E6E9EF]">
              LV
            </div>
            <div>
              <div className="text-lg font-extrabold tracking-tight flex items-center gap-1.5">
                <span className="text-[#5D6DF6]">Lexi</span>
                <span className="text-[#2E3440]">Voice</span>
              </div>
              <div className="text-[10px] font-semibold text-[#7C859B] tracking-wider uppercase">
                Voice-Interactive Legal Document Intelligence
              </div>
            </div>
          </div>

          {/* Document Switcher & Upload */}
          <div className="flex items-center gap-3">
            {documents.length > 1 && (
              <select
                value={activeDocId}
                onChange={(e) => setActiveDocId(e.target.value)}
                className="neu-inset px-3 py-1.5 text-xs font-bold text-[#5D6DF6] bg-transparent outline-none cursor-pointer max-w-[200px] truncate"
              >
                {documents.map((d) => (
                  <option key={d.doc_id} value={d.doc_id}>
                    {d.title}
                  </option>
                ))}
              </select>
            )}

            <label className="neu-btn px-3 py-2 text-xs font-bold flex items-center gap-1.5 cursor-pointer hover:text-[#5D6DF6]">
              <Upload className="w-3.5 h-3.5" />
              <span>Upload PDF</span>
              <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
            </label>
          </div>
        </div>
      </header>

      {/* MAIN 50/50 SPLIT WORKSPACE */}
      <main className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-6 flex-1 flex flex-col">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start flex-1">
          {/* ========================================================================= */}
          {/* LEFT 50%: REAL DOCUMENT VIEWER & CLAUSE INTELLIGENCE */}
          {/* ========================================================================= */}
          <div className="lg:col-span-6 flex flex-col gap-5">
            {/* Document Header & Risk Banner */}
            <div className="neu p-5 flex flex-col gap-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/60 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl neu-sm flex items-center justify-center text-[#5D6DF6]">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold tracking-tight">
                      {activeDoc?.title || "Residential Tenancy Agreement.pdf"}
                    </h2>
                    <p className="text-[11px] text-[#7C859B]">
                      {activeDoc?.total_clauses || 0} Clauses Extracted via PyMuPDF • Indexed in Qdrant
                    </p>
                  </div>
                </div>

                {/* Tab switch */}
                <div className="neu-inset p-1 flex items-center gap-1 text-xs font-semibold">
                  <button
                    onClick={() => setActiveTab("clauses")}
                    className={`px-3 py-1 rounded-full transition-all ${
                      activeTab === "clauses" ? "neu-btn font-bold text-[#5D6DF6]" : "text-[#7C859B]"
                    }`}
                  >
                    Parsed Clauses
                  </button>
                  <button
                    onClick={() => setActiveTab("pdf")}
                    className={`px-3 py-1 rounded-full transition-all ${
                      activeTab === "pdf" ? "neu-btn font-bold text-[#5D6DF6]" : "text-[#7C859B]"
                    }`}
                  >
                    Original PDF View
                  </button>
                </div>
              </div>

              {/* Real Risk Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="neu-sm p-3 text-center">
                  <div className="text-[10px] uppercase font-bold text-[#7C859B]">Overall Risk</div>
                  <div className="text-2xl font-black text-[#EF4444] mt-0.5">
                    {activeDoc?.overall_risk_score ?? "--"}
                    <span className="text-xs font-normal text-[#7C859B]">/100</span>
                  </div>
                </div>
                <div className="neu-sm p-3 text-center">
                  <div className="text-[10px] uppercase font-bold text-[#EF4444]">High Risk</div>
                  <div className="text-2xl font-black text-[#EF4444] mt-0.5">
                    {activeDoc?.high_risk_count ?? 0}
                  </div>
                </div>
                <div className="neu-sm p-3 text-center">
                  <div className="text-[10px] uppercase font-bold text-[#F59E0B]">Medium Risk</div>
                  <div className="text-2xl font-black text-[#F59E0B] mt-0.5">
                    {activeDoc?.medium_risk_count ?? 0}
                  </div>
                </div>
                <div className="neu-sm p-3 text-center">
                  <div className="text-[10px] uppercase font-bold text-[#10B981]">Standard/Safe</div>
                  <div className="text-2xl font-black text-[#10B981] mt-0.5">
                    {activeDoc?.safe_count ?? 0}
                  </div>
                </div>
              </div>
            </div>

            {/* View Body: Either Real Extracted Clauses or Original PDF */}
            {activeTab === "clauses" ? (
              <div className="flex flex-col gap-4 max-h-[750px] overflow-y-auto pr-1">
                {isLoadingDoc ? (
                  <div className="neu p-10 flex flex-col items-center justify-center gap-3 text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-[#5D6DF6]" />
                    <p className="text-xs font-bold text-[#7C859B]">
                      Parsing document clauses with PyMuPDF & loading vectors...
                    </p>
                  </div>
                ) : activeDoc?.clauses && activeDoc.clauses.length > 0 ? (
                  activeDoc.clauses.map((cl: Clause, idx: number) => {
                    const cId = cl.clause_id || cl.id || cl.clause_number.replace(/\s+/g, "_");
                    const isHighlighted = highlightedClauseId === cId || highlightedClauseId === cl.clause_number;

                    const badgeBg =
                      cl.risk_level === "High Risk"
                        ? "bg-red-100 text-red-700 border-red-300"
                        : cl.risk_level === "Medium Risk"
                        ? "bg-amber-100 text-amber-800 border-amber-300"
                        : "bg-emerald-100 text-emerald-800 border-emerald-300";

                    return (
                      <div
                        key={idx}
                        ref={(el) => {
                          clauseRefs.current[cId] = el;
                          clauseRefs.current[cl.clause_number] = el;
                        }}
                        className={`neu p-5 transition-all duration-300 ${
                          isHighlighted ? "neu-highlight bg-[#F4F6FB]" : ""
                        }`}
                      >
                        {/* Clause Top */}
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-sm text-[#2E3440]">{cl.clause_number}</span>
                              <span className="text-xs text-[#7C859B]">• Page {cl.page_number}</span>
                            </div>
                            <h4 className="text-sm font-semibold text-[#475569] mt-0.5">{cl.title}</h4>
                          </div>
                          <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full border ${badgeBg}`}>
                            ● {cl.risk_badge || cl.risk_level}
                          </span>
                        </div>

                        {/* Real Verbatim Quote */}
                        <div className="neu-inset p-3 my-3 text-xs leading-relaxed text-[#4B5563] italic border-l-2 border-[#5D6DF6]">
                          “{cl.quote}”
                        </div>

                        {/* LexiVoice Insight */}
                        <p className="text-xs text-[#2E3440] leading-relaxed">
                          <strong className="text-[#5D6DF6] font-bold">LexiVoice insight: </strong>
                          {cl.advice || cl.evon_insight || "Review against standard statutory benchmarks."}
                        </p>

                        {/* Actions */}
                        <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-white/60">
                          {cl.risk_level !== "Safe" && (
                            <button
                              onClick={() => openNegotiationModal(cl)}
                              className="neu-btn px-3 py-1.5 text-xs font-bold text-[#5D6DF6] hover:bg-[#5D6DF6] hover:text-white flex items-center gap-1"
                            >
                              <span>Negotiate Clause</span>
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          )}
                          <button
                            onClick={() => handleSendTextQuery(`Explain ${cl.clause_number} and how it impacts me.`)}
                            className="neu-btn px-3 py-1.5 text-xs font-semibold text-[#7C859B] hover:text-[#2E3440] flex items-center gap-1"
                          >
                            <Volume2 className="w-3 h-3" />
                            <span>Ask Timbre</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="neu p-10 text-center text-xs text-[#7C859B]">
                    No clauses detected in this document. Upload a contract to begin.
                  </div>
                )}
              </div>
            ) : (
              /* Original PDF Viewer */
              <div className="neu p-2 h-[750px] flex flex-col">
                <div className="p-2 flex items-center justify-between text-xs text-[#7C859B] border-b border-white/60">
                  <span>Interactive PDF Document View</span>
                  <a
                    href={`${API_BASE}/api/documents/${activeDocId}/pdf`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 font-bold text-[#5D6DF6] hover:underline"
                  >
                    <span>Open Raw PDF</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <iframe
                  src={`${API_BASE}/api/documents/${activeDocId}/pdf`}
                  className="w-full flex-1 rounded-xl border-0 mt-2 bg-white"
                  title="PDF Viewer"
                />
              </div>
            )}
          </div>

          {/* ========================================================================= */}
          {/* RIGHT 50%: LIVE VOICE ASSISTANT & REAL-TIME INTELLIGENCE PORTAL */}
          {/* ========================================================================= */}
          <div className="lg:col-span-6 flex flex-col gap-5">
            {/* LIVE VOICE RECORDER CARD */}
            <div className="neu p-6 flex flex-col items-center text-center relative overflow-hidden">
              <div className="w-full flex items-center justify-between mb-4">
                <div className="text-left">
                  <h3 className="text-sm font-extrabold tracking-tight uppercase text-[#7C859B] flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-[#5D6DF6]" />
                    <span>LexiVoice Assistant</span>
                  </h3>
                  <p className="text-xs text-[#2E3440] font-medium">
                    Speaks in English or Regional Indic Languages via Timbre v3.0
                  </p>
                </div>

                {/* Voice & Language Dropdowns */}
                <div className="flex items-center gap-2">
                  <select
                    value={voice}
                    onChange={(e) => setVoice(e.target.value)}
                    className="neu-inset px-2.5 py-1 text-xs font-bold text-[#5D6DF6] bg-transparent outline-none cursor-pointer"
                    title="Timbre Voice Model"
                  >
                    {TIMBRE_VOICES.map((v) => (
                      <option key={v.name} value={v.name}>
                        {v.name} ({v.gender})
                      </option>
                    ))}
                  </select>

                  <select
                    value={languageCode}
                    onChange={(e) => setLanguageCode(e.target.value)}
                    className="neu-inset px-2.5 py-1 text-xs font-bold text-[#5D6DF6] bg-transparent outline-none cursor-pointer"
                  >
                    <option value="indic-auto">Indic-Auto (Detect)</option>
                    <option value="en-IN">English (India)</option>
                    <option value="hi-IN">Hindi (हिन्दी)</option>
                    <option value="mr-IN">Marathi (मराठी)</option>
                    <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
                    <option value="ta-IN">Tamil (தமிழ்)</option>
                    <option value="te-IN">Telugu (తెలుగు)</option>
                    <option value="bn-IN">Bengali (বাংলা)</option>
                    <option value="gu-IN">Gujarati (ગુજરાતી)</option>
                  </select>
                </div>
              </div>

              {/* Central Mic Button */}
              <div className="my-4 flex flex-col items-center justify-center">
                <div className="relative">
                  {isRecording && (
                    <div className="absolute inset-0 rounded-full bg-red-400/30 neu-pulse-ring"></div>
                  )}
                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isProcessing}
                    className={`w-24 h-24 rounded-full flex flex-col items-center justify-center transition-all duration-300 relative z-10 ${
                      isRecording
                        ? "neu-danger scale-105"
                        : "neu hover:scale-105 active:scale-95 text-[#5D6DF6]"
                    }`}
                  >
                    {isRecording ? (
                      <>
                        <MicOff className="w-9 h-9 animate-bounce text-white" />
                        <span className="text-[10px] font-extrabold uppercase mt-1 tracking-wider text-white">
                          Stop ({recordingDuration}s)
                        </span>
                      </>
                    ) : (
                      <>
                        <Mic className="w-9 h-9" />
                        <span className="text-[10px] font-extrabold uppercase mt-1 tracking-wider text-[#7C859B]">
                          Push to Speak
                        </span>
                      </>
                    )}
                  </button>
                </div>

                {/* Real-time Waveform Canvas */}
                <div className="w-full max-w-[320px] h-10 mt-3 flex items-center justify-center">
                  {isRecording ? (
                    <canvas ref={canvasRef} width={300} height={40} className="w-full h-full" />
                  ) : (
                    <p className="text-xs text-[#7C859B] italic">
                      Tap mic and speak your contract question in English or regional language
                    </p>
                  )}
                </div>
              </div>

              {/* Suggested Prompts */}
              <div className="w-full mt-3 pt-3 border-t border-white/60">
                <div className="text-[10px] uppercase font-bold text-[#7C859B] mb-2 text-left">
                  Suggested Prompts
                </div>
                <div className="flex flex-wrap gap-2 text-left">
                  {suggestedPrompts.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendTextQuery(q)}
                      disabled={isProcessing}
                      className="neu-btn px-3 py-1.5 text-xs text-[#2E3440] hover:text-[#5D6DF6] hover:border-[#5D6DF6]/50 transition-all font-medium text-left"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Text Input Bar */}
              <div className="w-full mt-4 neu-inset p-1.5 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Or type your legal question here..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendTextQuery()}
                  disabled={isProcessing}
                  className="w-full bg-transparent border-0 outline-none px-3 text-xs text-[#2E3440] placeholder:text-[#7C859B]"
                />
                <button
                  onClick={() => handleSendTextQuery()}
                  disabled={isProcessing || !textInput.trim()}
                  className="neu-primary w-8 h-8 rounded-full flex items-center justify-center shrink-0 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* PROCESSING INDICATOR */}
            {isProcessing && (
              <div className="neu p-5 flex items-center justify-center gap-3 animate-pulse">
                <div className="w-4 h-4 border-2 border-[#5D6DF6] border-t-transparent rounded-full animate-spin"></div>
                <div className="text-xs font-bold text-[#5D6DF6]">
                  Prisma STT transcribing → RAG matching clauses → Timbre synthesizing natural voice...
                </div>
              </div>
            )}

            {/* REAL RESPONSE INTELLIGENCE CARD */}
            {latestResponse && (
              <div className="neu p-6 flex flex-col gap-4">
                {/* User Query Transcribed Badge */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/60 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
                    <span className="text-xs font-bold text-[#7C859B] uppercase tracking-wider">
                      Transcribed Speech (Prisma v3.0)
                    </span>
                  </div>
                  <span className="text-[11px] font-bold text-[#5D6DF6] bg-[#5D6DF6]/10 px-2 py-0.5 rounded-full">
                    {latestResponse.detected_language} • Live API
                  </span>
                </div>
                <div className="text-sm font-semibold text-[#2E3440] italic">
                  “{latestResponse.user_query}”
                </div>

                {/* Timbre Spoken Summary Audio Player */}
                <div className="neu-inset p-4 flex flex-col gap-3 bg-gradient-to-r from-[#5D6DF6]/5 to-transparent border border-white/60">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-[#5D6DF6] text-white flex items-center justify-center">
                        <Volume2 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[#2E3440]">Timbre Spoken Answer</div>
                        <div className="text-[10px] text-[#7C859B]">
                          Natural Voice: {latestResponse.tts_voice || voice} • Live Gnani Model
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        if (audioPlayerRef.current) {
                          if (isPlayingAudio) {
                            audioPlayerRef.current.pause();
                            setIsPlayingAudio(false);
                          } else {
                            audioPlayerRef.current.play();
                            setIsPlayingAudio(true);
                          }
                        }
                      }}
                      className="neu-primary px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5"
                    >
                      {isPlayingAudio ? (
                        <>
                          <Pause className="w-3.5 h-3.5" />
                          <span>Pause</span>
                        </>
                      ) : (
                        <>
                          <Play className="w-3.5 h-3.5" />
                          <span>Replay</span>
                        </>
                      )}
                    </button>
                  </div>

                  <p className="text-xs leading-relaxed text-[#334155]">
                    {latestResponse.spoken_summary}
                  </p>

                  {audioUrl && (
                    <audio
                      ref={audioPlayerRef}
                      src={audioUrl}
                      onEnded={() => setIsPlayingAudio(false)}
                      className="hidden"
                    />
                  )}
                </div>

                {/* 2-3 Executive Bullet Points */}
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-[#7C859B] mb-2 flex items-center gap-1.5">
                    <CheckCircle className="w-4 h-4 text-[#10B981]" />
                    <span>Executive Takeaways (Nemotron 3.5 Reasoning)</span>
                  </div>
                  <div className="flex flex-col gap-2">
                    {latestResponse.executive_bullet_points?.map((bp, i) => (
                      <div key={i} className="neu-sm p-3 flex items-start gap-2.5 text-xs text-[#2E3440] leading-relaxed">
                        <span className="w-5 h-5 rounded-full bg-[#5D6DF6]/10 text-[#5D6DF6] font-bold flex items-center justify-center shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <span>{bp}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Cited Clauses References */}
                {latestResponse.cited_clauses && latestResponse.cited_clauses.length > 0 && (
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-[#7C859B] mb-2 flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-[#5D6DF6]" />
                      <span>Cited Clauses in Lease Document</span>
                    </div>
                    <div className="flex flex-col gap-2">
                      {latestResponse.cited_clauses.map((c, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            const cId = c.clause_id || c.clause_number.replace(/\s+/g, "_");
                            setHighlightedClauseId(cId);
                            setActiveTab("clauses");
                            const el = clauseRefs.current[cId] || clauseRefs.current[c.clause_number];
                            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                          }}
                          className="neu-btn px-4 py-2.5 flex items-center justify-between text-xs cursor-pointer hover:border-[#5D6DF6]"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[#5D6DF6]">{c.clause_number}</span>
                            <span className="text-[#7C859B]">({c.title})</span>
                            <span className="text-[10px] text-[#7C859B]">• Page {c.page_number}</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[#5D6DF6] font-bold">
                            <span>Jump to Clause</span>
                            <ChevronRight className="w-3.5 h-3.5" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actionable Advice & Negotiation Button */}
                {latestResponse.actionable_advice && (
                  <div className="neu-sm p-3.5 bg-amber-50/50 border border-amber-200/60 rounded-xl flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-xs font-bold text-amber-900">LexiVoice Actionable Strategy</div>
                        <div className="text-xs text-amber-800 mt-0.5 leading-relaxed">
                          {latestResponse.actionable_advice}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* NEGOTIATION EMAIL MODAL */}
      {emailModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="neu w-full max-w-2xl p-6 bg-[#E6E9EF] shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-white/60 pb-3">
              <div className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-[#5D6DF6]" />
                <h3 className="font-bold text-sm text-[#2E3440]">AI Legal Counter-Proposal Draft</h3>
              </div>
              <button
                onClick={() => setEmailModalOpen(false)}
                className="neu-btn w-8 h-8 flex items-center justify-center text-xs font-bold text-[#7C859B]"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-[#7C859B]">
              LexiVoice has drafted this polite, legally sound counter-proposal. You can edit and copy it to email your landlord.
            </p>

            <textarea
              rows={10}
              value={negotiationDraft}
              onChange={(e) => setNegotiationDraft(e.target.value)}
              className="neu-inset p-4 text-xs font-mono text-[#2E3440] leading-relaxed w-full outline-none resize-none"
            />

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setEmailModalOpen(false)}
                className="neu-btn px-4 py-2 text-xs font-bold text-[#7C859B]"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(negotiationDraft);
                  showToast("Draft copied to clipboard!");
                  setEmailModalOpen(false);
                }}
                className="neu-primary px-5 py-2 text-xs font-bold rounded-full flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" />
                <span>Copy to Clipboard</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TOAST NOTIFICATION */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 neu-primary px-4 py-2.5 rounded-2xl shadow-xl flex items-center gap-2 text-xs font-bold animate-in fade-in slide-in-from-bottom-4">
          <Info className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* FOOTER */}
      <footer className="py-4 text-center text-xs text-[#7C859B] border-t border-white/60 mt-auto">
        Built for The Great Indian AI Internship Challenge • Powered by Gnani Prisma & Timbre + NVIDIA NIM Nemotron
      </footer>
    </div>
  );
}
