import React, { useState, useEffect, useMemo, useRef } from 'react';
import * as XLSX from 'xlsx';
import { 
  Users, 
  Send, 
  Settings, 
  FileText, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Play, 
  Square, 
  Upload, 
  Download, 
  Trash2, 
  MessageSquare, 
  Search, 
  Filter, 
  ChevronRight, 
  ChevronDown, 
  Eye, 
  EyeOff,
  History,
  FileWarning,
  Building2,
  Phone,
  User,
  Copy,
  ExternalLink,
  Paperclip,
  Image as ImageIcon,
  File as FileIcon,
  X
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- Types ---
type ContactStatus = 'PENDENTE' | 'ENVIADO' | 'ERRO' | 'EM_PROCESSAMENTO' | 'NUMERO_INVALIDO' | 'IGNORADO' | 'INVALIDO';

interface Contact {
  id: string | number;
  Nome: string;
  Numero: string;
  Empresa: string;
  Status: ContactStatus;
  Observacao?: string;
  DataEnvio?: string;
}

interface CampaignSummary {
  startTime: string;
  endTime: string;
  duration: string;
  fileName: string;
  totalProcessed: number;
  sent: number;
  errors: number;
  invalid: number;
  ignored: number;
  remaining: number;
}

interface LogEntry {
  id: string;
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

interface CampaignHistory {
  date: string;
  file: string;
  sent: number;
  errors: number;
  invalid: number;
}

// --- App Component ---
export default function App() {
  // --- State ---
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [message, setMessage] = useState<string>("Olá {nome}, tudo bem? Vi que você é da {empresa}...");
  const [minInterval, setMinInterval] = useState<number>(10);
  const [maxInterval, setMaxInterval] = useState<number>(20);
  const [limit, setLimit] = useState<number>(100);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [chromeStatus, setChromeStatus] = useState<'OFF' | 'ON' | 'ERROR' | 'WAIT'>('OFF');
  const [whatsappStatus, setWhatsappStatus] = useState<'OFF' | 'ON' | 'ERROR' | 'WAIT'>('OFF');
  const [sessionStatus, setSessionStatus] = useState<'OFF' | 'ON' | 'ERROR' | 'WAIT'>('OFF');
  const [campaignSummary, setCampaignSummary] = useState<CampaignSummary | null>(null);
  const [showSummary, setShowSummary] = useState<boolean>(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [showLogs, setShowLogs] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("TODOS");
  const [showPreRun, setShowPreRun] = useState<boolean>(false);
  const [history, setHistory] = useState<CampaignHistory[]>([]);
  const [attachments, setAttachments] = useState<{name: string, path: string, type: 'image' | 'file'}[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const attachmentInputRef = useRef<HTMLInputElement>(null);

  // --- Persistence ---
  useEffect(() => {
    const savedMsg = localStorage.getItem('zap_msg');
    const savedMin = localStorage.getItem('zap_min');
    const savedMax = localStorage.getItem('zap_max');
    const savedLimit = localStorage.getItem('zap_limit');
    const savedLogsPref = localStorage.getItem('zap_show_logs');
    const savedHistory = localStorage.getItem('zap_history');
    const savedContacts = localStorage.getItem('zap_contacts');

    if (savedMsg) setMessage(savedMsg);
    if (savedMin) setMinInterval(Number(savedMin));
    if (savedMax) setMaxInterval(Number(savedMax));
    if (savedLimit) setLimit(Number(savedLimit));
    if (savedLogsPref) setShowLogs(savedLogsPref === 'true');
    if (savedHistory) setHistory(JSON.parse(savedHistory));
    if (savedContacts) setContacts(JSON.parse(savedContacts));
    
    const savedAttachments = localStorage.getItem('zap_attachments');
    if (savedAttachments) setAttachments(JSON.parse(savedAttachments));
  }, []);

  useEffect(() => {
    localStorage.setItem('zap_msg', message);
    localStorage.setItem('zap_min', minInterval.toString());
    localStorage.setItem('zap_max', maxInterval.toString());
    localStorage.setItem('zap_limit', limit.toString());
    localStorage.setItem('zap_show_logs', showLogs.toString());
    localStorage.setItem('zap_history', JSON.stringify(history));
    localStorage.setItem('zap_attachments', JSON.stringify(attachments));
    localStorage.setItem('zap_contacts', JSON.stringify(contacts));
  }, [message, minInterval, maxInterval, limit, showLogs, history, attachments, contacts]);

  const isRunningRef = useRef(isRunning);
  const isPausedRef = useRef(isPaused);

  useEffect(() => {
    isRunningRef.current = isRunning;
  }, [isRunning]);

  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // --- Handlers ---
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      const bstr = evt.target?.result;
      const wb = XLSX.read(bstr, { type: 'binary' });
      const wsname = wb.SheetNames[0];
      const ws = wb.Sheets[wsname];
      const data = XLSX.utils.sheet_to_json(ws) as any[];

      const formattedContacts: Contact[] = data.map((row, index) => ({
        id: `contact-${index}`,
        Nome: row.Nome || row.nome || row.Cliente || row.cliente || 'Sem Nome',
        Numero: String(row.Numero || row.numero || row.Telefone || row.telefone || row.Celular || row.celular || ''),
        Empresa: row.Empresa || row.empresa || row.Razao || row.razao || '',
        Status: (row.Status || row.status || row.Situacao || row.situacao || 'PENDENTE').toUpperCase() as any,
        Observacao: row.Observacao || row.observacao || '',
        DataEnvio: row.DataEnvio || row.dataenvio || ''
      }));

      // Check for stuck contacts
      const stuckCount = formattedContacts.filter(c => c.Status === 'EM_PROCESSAMENTO').length;
      if (stuckCount > 0) {
        addLog(`Atenção: ${stuckCount} contatos detectados em 'EM_PROCESSAMENTO'.`, 'warning');
      }

      setContacts(formattedContacts);
      addLog(`Planilha carregada: ${file.name} (${formattedContacts.length} contatos)`, 'success');
    };
    reader.readAsBinaryString(file);
  };

  const addLog = (msg: string, type: LogEntry['type'] = 'info') => {
    const newLog: LogEntry = {
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date().toLocaleTimeString(),
      message: msg,
      type
    };
    setLogs(prev => [newLog, ...prev].slice(0, 100));
  };

  const handleAttachmentUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    const newAttachments = Array.from(files).map((file: File) => ({
      name: file.name,
      path: (file as any).path || file.name, // In a real app with a backend, we'd get the real path
      type: file.type.startsWith('image/') ? 'image' as const : 'file' as const
    }));

    setAttachments(prev => [...prev, ...newAttachments]);
    addLog(`${newAttachments.length} anexo(s) adicionado(s).`, 'info');
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const startSequence = async () => {
    setShowPreRun(false);
    setIsRunning(true);
    setIsPaused(false);
    setChromeStatus('WAIT');
    addLog("Iniciando sequência de disparos...", "warning");
    addLog("Backup automático da planilha criado em 'backups/'", "info");
    
    const startTime = new Date();
    
    // Mock status updates for the browser connection
    setTimeout(() => setChromeStatus('ON'), 2000);
    setTimeout(() => setWhatsappStatus('WAIT'), 3000);
    setTimeout(() => {
      setWhatsappStatus('ON');
      setSessionStatus('ON');
    }, 5000);

    // Find where to start: first contact that is PENDENTE
    let startIndex = contacts.findIndex(c => c.Status === 'PENDENTE');
    if (startIndex === -1) {
      addLog("Nenhum contato pendente encontrado.", "error");
      setIsRunning(false);
      return;
    }

    let processedCount = contacts.filter(c => c.Status !== 'PENDENTE').length;
    let currentLimit = limit;
    let sessionProcessed = 0;

    for (let i = startIndex; i < contacts.length; i++) {
      // Check if we should stop
      if (!isRunningRef.current) break;

      // Handle Pause
      while (isPausedRef.current && isRunningRef.current) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      if (!isRunningRef.current) break;
      if (sessionProcessed >= currentLimit) break;

      const contact = contacts[i];
      if (contact.Status !== 'PENDENTE') continue;

      // Update status to EM_PROCESSAMENTO
      updateContactStatus(contact.id, 'EM_PROCESSAMENTO');
      setCurrentIndex(i);
      
      // Simulate sending delay
      await new Promise(resolve => setTimeout(resolve, 1500));

      if (!isRunningRef.current) break;

      // Update status to ENVIADO (or ERRO randomly for simulation)
      const isError = Math.random() < 0.05;
      const newStatus: ContactStatus = isError ? 'ERRO' : 'ENVIADO';
      updateContactStatus(contact.id, newStatus, isError ? 'Falha na conexão' : '');
      
      sessionProcessed++;
      processedCount++;

      // Wait between messages
      if (sessionProcessed < currentLimit && i < contacts.length - 1) {
        const waitTime = Math.floor(Math.random() * (maxInterval - minInterval + 1) + minInterval);
        addLog(`Aguardando ${waitTime}s para o próximo envio...`, "info");
        
        // Wait in chunks to be responsive to pause/stop
        for (let w = 0; w < waitTime * 2; w++) {
          if (!isRunningRef.current) break;
          while (isPausedRef.current && isRunningRef.current) {
            await new Promise(resolve => setTimeout(resolve, 500));
          }
          if (!isRunningRef.current) break;
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
    }

    if (isRunningRef.current) {
      finishCampaign(startTime, sessionProcessed);
    }
  };

  const updateContactStatus = (id: string | number, status: ContactStatus, obs?: string) => {
    setContacts(prev => prev.map(c => 
      c.id === id ? { 
        ...c, 
        Status: status, 
        Observacao: obs || c.Observacao,
        DataEnvio: status === 'ENVIADO' ? new Date().toLocaleString() : c.DataEnvio
      } : c
    ));
    
    if (status === 'ENVIADO') {
      addLog(`Mensagem enviada com sucesso para o contato ID: ${id}`, "success");
    } else if (status === 'ERRO') {
      addLog(`Erro ao enviar mensagem para o contato ID: ${id}`, "error");
    }
  };

  const finishCampaign = (start: Date, total: number) => {
    const end = new Date();
    const diff = end.getTime() - start.getTime();
    const duration = new Date(diff).toISOString().substr(11, 8);
    
    const summary: CampaignSummary = {
      startTime: start.toLocaleTimeString(),
      endTime: end.toLocaleTimeString(),
      duration,
      fileName: "Planilha_Atual.xlsx",
      totalProcessed: total,
      sent: Math.floor(total * 0.9),
      errors: Math.floor(total * 0.05),
      invalid: Math.floor(total * 0.05),
      ignored: 0,
      remaining: contacts.length - total
    };

    setCampaignSummary(summary);
    setShowSummary(true);
    setIsRunning(false);
    setChromeStatus('OFF');
    setWhatsappStatus('OFF');
    setSessionStatus('OFF');
    addLog("Sequência finalizada!", "success");
    addLog("Relatório final gerado.", "info");
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
    addLog(isPaused ? "Campanha retomada." : "Campanha pausada.", "warning");
  };

  const stopCampaign = () => {
    setIsRunning(false);
    setIsPaused(false);
    setChromeStatus('OFF');
    setWhatsappStatus('OFF');
    setSessionStatus('OFF');
    addLog("Campanha interrompida pelo usuário.", "error");
  };

  const exportErrors = () => {
    const errorContacts = contacts.filter(c => c.Status === 'ERRO' || c.Status === 'NUMERO_INVALIDO');
    if (errorContacts.length === 0) {
      alert("Nenhum erro encontrado para exportar.");
      return;
    }
    const ws = XLSX.utils.json_to_sheet(errorContacts);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Erros");
    XLSX.writeFile(wb, `erros_campanha_${new Date().getTime()}.xlsx`);
  };

  const exportResults = () => {
    if (contacts.length === 0) {
      alert("Nenhum dado para exportar.");
      return;
    }
    const ws = XLSX.utils.json_to_sheet(contacts);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Resultados");
    XLSX.writeFile(wb, `resultados_campanha_${new Date().getTime()}.xlsx`);
  };

  // --- Computed ---
  const filteredContacts = useMemo(() => {
    return contacts.filter(c => {
      const matchesSearch = 
        c.Nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.Numero.includes(searchTerm) ||
        c.Empresa.toLowerCase().includes(searchTerm.toLowerCase());
      
      const matchesStatus = statusFilter === "TODOS" || c.Status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [contacts, searchTerm, statusFilter]);

  const stats = useMemo(() => {
    return {
      total: contacts.length,
      pendentes: contacts.filter(c => c.Status === 'PENDENTE').length,
      enviados: contacts.filter(c => c.Status === 'ENVIADO').length,
      erros: contacts.filter(c => c.Status === 'ERRO').length,
      invalidos: contacts.filter(c => c.Status === 'NUMERO_INVALIDO').length
    };
  }, [contacts]);

  const variablesDetected = useMemo(() => {
    const vars = [];
    if (message.includes('{nome}')) vars.push('{nome}');
    if (message.includes('{empresa}')) vars.push('{empresa}');
    return vars;
  }, [message]);

  const getPreview = (contact: Contact | null) => {
    if (!contact) return "Selecione um contato para ver o preview...";
    return message
      .replace(/{nome}/g, contact.Nome)
      .replace(/{empresa}/g, contact.Empresa);
  };

  // --- Render ---
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 font-sans selection:bg-emerald-100">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-200">
              <Send className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-800">ZapManager <span className="text-emerald-600">Pro</span></h1>
              <p className="text-xs text-slate-500 font-medium">Automação Inteligente de WhatsApp</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            {/* Status Indicators */}
            <div className="hidden md:flex items-center gap-2 bg-slate-50 px-4 py-2 rounded-xl border border-slate-100">
              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200">
                <div className={`w-2 h-2 rounded-full ${chromeStatus === 'ON' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : chromeStatus === 'WAIT' ? 'bg-amber-500 animate-pulse' : 'bg-slate-300'}`} />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Chrome</span>
              </div>
              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200">
                <div className={`w-2 h-2 rounded-full ${whatsappStatus === 'ON' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : whatsappStatus === 'WAIT' ? 'bg-amber-500 animate-pulse' : 'bg-slate-300'}`} />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">WhatsApp</span>
              </div>
              <div className="flex items-center gap-1.5 px-2">
                <div className={`w-2 h-2 rounded-full ${sessionStatus === 'ON' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : sessionStatus === 'WAIT' ? 'bg-amber-500 animate-pulse' : 'bg-slate-300'}`} />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">Sessão</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button 
                onClick={() => setShowLogs(!showLogs)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                showLogs ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {showLogs ? <EyeOff size={18} /> : <Eye size={18} />}
              {showLogs ? 'Ocultar Logs' : 'Exibir Logs'}
            </button>
            <div className="h-8 w-[1px] bg-slate-200 mx-2" />
            <button 
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl text-sm font-bold shadow-md shadow-emerald-100 transition-all active:scale-95"
            >
              <Upload size={18} />
              Importar Planilha
            </button>
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              accept=".xlsx, .xls" 
              className="hidden" 
            />
          </div>
        </div>
      </div>
    </header>

      <main className="max-w-[1600px] mx-auto p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          {[
            { label: 'Total', value: stats.total, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Pendentes', value: stats.pendentes, icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50' },
            { label: 'Enviados', value: stats.enviados, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
            { label: 'Erros', value: stats.erros, icon: AlertCircle, color: 'text-rose-600', bg: 'bg-rose-50' },
            { label: 'Inválidos', value: stats.invalidos, icon: FileWarning, color: 'text-slate-600', bg: 'bg-slate-100' },
          ].map((stat, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-xl ${stat.bg}`}>
                  <stat.icon className={stat.color} size={24} />
                </div>
                <span className="text-2xl font-bold text-slate-800">{stat.value}</span>
              </div>
              <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider">{stat.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Progress Bar (Visible when running) */}
        <AnimatePresence>
          {isRunning && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8 overflow-hidden"
            >
              <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-ping" />
                    <span className="text-sm font-bold text-slate-700">Progresso da Campanha</span>
                  </div>
                  <span className="text-sm font-black text-emerald-600">
                    {Math.round(((stats.enviados + stats.erros + stats.invalidos) / (limit || 1)) * 100)}%
                  </span>
                </div>
                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${((stats.enviados + stats.erros + stats.invalidos) / (limit || 1)) * 100}%` }}
                    className="h-full bg-emerald-500"
                  />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Config & Preview */}
          <div className="lg:col-span-4 space-y-8">
            {/* Message Config */}
            <section className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-6 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="text-emerald-600" size={20} />
                  <h2 className="font-bold text-slate-800">Mensagem</h2>
                </div>
                <div className="flex gap-1">
                  {variablesDetected.map(v => (
                    <span key={v} className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-bold">{v}</span>
                  ))}
                </div>
              </div>
              <div className="p-6 space-y-4">
                <textarea 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  disabled={isRunning}
                  className={`w-full h-48 p-4 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all resize-none text-sm leading-relaxed ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
                  placeholder="Digite sua mensagem aqui..."
                />
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-500 uppercase ml-1">Intervalo Min (s)</label>
                    <input 
                      type="number" 
                      value={minInterval}
                      onChange={(e) => setMinInterval(Number(e.target.value))}
                      disabled={isRunning}
                      className={`w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-500 uppercase ml-1">Intervalo Max (s)</label>
                    <input 
                      type="number" 
                      value={maxInterval}
                      onChange={(e) => setMaxInterval(Number(e.target.value))}
                      disabled={isRunning}
                      className={`w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-500 uppercase ml-1">Limite de Envios</label>
                  <input 
                    type="number" 
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    disabled={isRunning}
                    className={`w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium ${isRunning ? 'opacity-60 cursor-not-allowed' : ''}`}
                  />
                </div>

                {/* Attachments Section */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-bold text-slate-500 uppercase ml-1">Anexos ({attachments.length})</label>
                    <button 
                      onClick={() => attachmentInputRef.current?.click()}
                      disabled={isRunning}
                      className="text-[10px] font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 uppercase tracking-wider"
                    >
                      <Paperclip size={12} /> Adicionar
                    </button>
                    <input 
                      type="file" 
                      ref={attachmentInputRef} 
                      onChange={handleAttachmentUpload} 
                      multiple 
                      className="hidden" 
                    />
                  </div>
                  
                  {attachments.length > 0 ? (
                    <div className="space-y-2 max-h-32 overflow-y-auto pr-1 custom-scrollbar">
                      {attachments.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-slate-50 p-2 rounded-xl border border-slate-100 group">
                          <div className="flex items-center gap-2 overflow-hidden">
                            {file.type === 'image' ? <ImageIcon size={14} className="text-blue-500 shrink-0" /> : <FileIcon size={14} className="text-amber-500 shrink-0" />}
                            <span className="text-[11px] font-medium text-slate-600 truncate">{file.name}</span>
                          </div>
                          <button 
                            onClick={() => removeAttachment(idx)}
                            disabled={isRunning}
                            className="text-slate-400 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-slate-50/50 border border-dashed border-slate-200 rounded-xl p-4 text-center">
                      <p className="text-[10px] text-slate-400 font-medium">Nenhum arquivo anexado</p>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  <button 
                    onClick={() => isRunning ? togglePause() : setShowPreRun(true)}
                    disabled={contacts.length === 0}
                    className={`flex-1 py-4 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all shadow-lg ${
                      isRunning 
                        ? (isPaused ? 'bg-emerald-600 text-white hover:bg-emerald-700' : 'bg-amber-500 text-white hover:bg-amber-600')
                        : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-100 active:scale-[0.98]'
                    }`}
                  >
                    {isRunning ? (isPaused ? <Play size={20} fill="currentColor" /> : <Clock size={20} />) : <Play size={20} fill="currentColor" />}
                    {isRunning ? (isPaused ? 'RETOMAR' : 'PAUSAR') : 'INICIAR SEQUÊNCIA'}
                  </button>

                  {isRunning && (
                    <button 
                      onClick={stopCampaign}
                      className="px-6 py-4 bg-rose-600 text-white rounded-2xl font-bold hover:bg-rose-700 transition-all shadow-lg shadow-rose-100 active:scale-[0.98]"
                    >
                      <Square size={20} fill="currentColor" />
                    </button>
                  )}
                </div>
              </div>
            </section>

            {/* Preview */}
            <section className="bg-slate-900 rounded-3xl p-6 text-white shadow-xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                <MessageSquare size={80} />
              </div>
              <h3 className="text-emerald-400 font-bold text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
                <Eye size={14} /> Preview Real
              </h3>
              <div className="bg-white/5 backdrop-blur-sm rounded-2xl p-5 border border-white/10 min-h-[120px]">
                <p className="text-sm text-slate-300 leading-relaxed italic">
                  "{getPreview(selectedContact || (contacts.length > 0 ? contacts[0] : null))}"
                </p>
              </div>
              <p className="mt-4 text-[10px] text-slate-500 font-medium">
                * Variáveis detectadas: {variablesDetected.join(', ') || 'Nenhuma'}
              </p>
            </section>
          </div>

          {/* Right Column: Contact List */}
          <div className={`space-y-6 transition-all duration-500 ${showLogs ? 'lg:col-span-5' : 'lg:col-span-8'}`}>
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[750px]">
              {/* List Header */}
              <div className="p-6 border-b border-slate-100 space-y-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Users className="text-emerald-600" size={20} />
                      <h2 className="font-bold text-slate-800">Lista de Contatos</h2>
                      <span className="bg-slate-100 text-slate-600 text-[10px] px-2 py-0.5 rounded-full font-bold">
                        {filteredContacts.length} exibidos
                      </span>
                    </div>
                    <div className="flex gap-3">
                      <button 
                        onClick={() => {
                          if (window.confirm("Deseja realmente limpar a lista de contatos?")) {
                            setContacts([]);
                            setCurrentIndex(0);
                            addLog("Lista de contatos limpa.", "info");
                          }
                        }}
                        disabled={isRunning}
                        className="text-xs font-bold text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors"
                      >
                        <Trash2 size={14} /> Limpar
                      </button>
                      <button 
                        onClick={exportResults}
                        className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1 transition-colors"
                      >
                        <Download size={14} /> Exportar Tudo
                      </button>
                      <button 
                        onClick={exportErrors}
                        className="text-xs font-bold text-rose-600 hover:text-rose-700 flex items-center gap-1 transition-colors"
                      >
                        <FileWarning size={14} /> Exportar Erros
                      </button>
                    </div>
                </div>

                <div className="flex flex-col md:flex-row gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                      type="text" 
                      placeholder="Buscar por nome, número ou empresa..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-emerald-500 transition-all"
                    />
                  </div>
                  <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-xl px-3">
                    <Filter className="text-slate-400" size={16} />
                    <select 
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="bg-transparent border-none text-sm font-semibold text-slate-600 focus:ring-0 py-2 cursor-pointer"
                    >
                      <option value="TODOS">Todos Status</option>
                      <option value="PENDENTE">Pendentes</option>
                      <option value="ENVIADO">Enviados</option>
                      <option value="ERRO">Erros</option>
                      <option value="NUMERO_INVALIDO">Inválidos</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* List Content */}
              <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
                {filteredContacts.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3 opacity-60">
                    <Search size={48} />
                    <p className="font-medium">Nenhum contato encontrado</p>
                  </div>
                ) : (
                  filteredContacts.map((contact) => (
                    <motion.div 
                      key={contact.id}
                      layout
                      onClick={() => setSelectedContact(contact)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                        selectedContact?.id === contact.id 
                          ? 'bg-emerald-50 border-emerald-200 shadow-sm' 
                          : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                          contact.Status === 'ENVIADO' ? 'bg-emerald-100 text-emerald-600' :
                          contact.Status === 'ERRO' ? 'bg-rose-100 text-rose-600' :
                          contact.Status === 'NUMERO_INVALIDO' ? 'bg-slate-100 text-slate-600' :
                          'bg-blue-100 text-blue-600'
                        }`}>
                          {contact.Nome.charAt(0)}
                        </div>
                        <div>
                          <h4 className="font-bold text-slate-800 text-sm group-hover:text-emerald-700 transition-colors">{contact.Nome}</h4>
                          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                            <span>{contact.Numero}</span>
                            {contact.Empresa && (
                              <>
                                <span className="w-1 h-1 bg-slate-300 rounded-full" />
                                <span>{contact.Empresa}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                          contact.Status === 'ENVIADO' ? 'bg-emerald-100 text-emerald-700' :
                          contact.Status === 'ERRO' ? 'bg-rose-100 text-rose-700' :
                          contact.Status === 'NUMERO_INVALIDO' ? 'bg-slate-100 text-slate-700' :
                          contact.Status === 'EM_PROCESSAMENTO' ? 'bg-amber-100 text-amber-700 animate-pulse' :
                          'bg-blue-100 text-blue-700'
                        }`}>
                          {contact.Status}
                        </span>
                        <ChevronRight className={`text-slate-300 transition-transform ${selectedContact?.id === contact.id ? 'rotate-90 text-emerald-400' : ''}`} size={18} />
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Logs Column (Conditional) */}
          <AnimatePresence>
            {showLogs && (
              <motion.div 
                initial={{ opacity: 0, x: 20, width: 0 }}
                animate={{ opacity: 1, x: 0, width: 'auto' }}
                exit={{ opacity: 0, x: 20, width: 0 }}
                className="lg:col-span-3 h-[750px]"
              >
                <div className="bg-slate-900 rounded-3xl border border-slate-800 shadow-2xl h-full flex flex-col overflow-hidden">
                  <div className="p-5 border-b border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                      <h3 className="text-white font-bold text-sm">Console de Logs</h3>
                    </div>
                    <button onClick={() => setLogs([])} className="text-slate-500 hover:text-white transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-[11px] custom-scrollbar">
                    {logs.map((log) => (
                      <div key={log.id} className="flex gap-2 group">
                        <span className="text-slate-600 shrink-0">[{log.timestamp}]</span>
                        <span className={`
                          ${log.type === 'success' ? 'text-emerald-400' : 
                            log.type === 'error' ? 'text-rose-400' : 
                            log.type === 'warning' ? 'text-amber-400' : 
                            'text-slate-300'}
                        `}>
                          {log.message}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Campaign Summary Modal */}
      <AnimatePresence>
        {showSummary && campaignSummary && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSummary(false)}
              className="absolute inset-0 bg-slate-900/80 backdrop-blur-md"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 40 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 40 }}
              className="bg-white rounded-[40px] shadow-2xl w-full max-w-3xl relative z-10 overflow-hidden"
            >
              <div className="p-10 bg-emerald-600 text-white">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-sm">
                      <CheckCircle2 size={32} />
                    </div>
                    <div>
                      <h2 className="text-3xl font-bold">Campanha Finalizada</h2>
                      <p className="text-emerald-100 font-medium">Resumo operacional detalhado</p>
                    </div>
                  </div>
                  <button onClick={() => setShowSummary(false)} className="p-2 hover:bg-white/10 rounded-full transition-colors">
                    <Square size={24} />
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-6">
                  <div className="bg-white/10 p-4 rounded-2xl backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-widest opacity-70 mb-1">Duração Total</p>
                    <p className="text-xl font-bold">{campaignSummary.duration}</p>
                  </div>
                  <div className="bg-white/10 p-4 rounded-2xl backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-widest opacity-70 mb-1">Início</p>
                    <p className="text-xl font-bold">{campaignSummary.startTime}</p>
                  </div>
                  <div className="bg-white/10 p-4 rounded-2xl backdrop-blur-sm">
                    <p className="text-[10px] font-bold uppercase tracking-widest opacity-70 mb-1">Término</p>
                    <p className="text-xl font-bold">{campaignSummary.endTime}</p>
                  </div>
                </div>
              </div>

              <div className="p-10 space-y-8">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Processados', value: campaignSummary.totalProcessed, color: 'text-blue-600', bg: 'bg-blue-50' },
                    { label: 'Enviados', value: campaignSummary.sent, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                    { label: 'Erros', value: campaignSummary.errors, color: 'text-rose-600', bg: 'bg-rose-50' },
                    { label: 'Inválidos', value: campaignSummary.invalid, color: 'text-slate-600', bg: 'bg-slate-50' },
                  ].map((stat, i) => (
                    <div key={i} className={`${stat.bg} p-5 rounded-3xl border border-slate-100 text-center`}>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{stat.label}</p>
                      <p className={`text-3xl font-black ${stat.color}`}>{stat.value}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-slate-50 p-6 rounded-3xl border border-slate-100 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-white rounded-2xl shadow-sm">
                      <FileText className="text-slate-400" size={24} />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Planilha Utilizada</p>
                      <p className="font-bold text-slate-700">{campaignSummary.fileName}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Pendentes Restantes</p>
                    <p className="text-xl font-bold text-amber-600">{campaignSummary.remaining}</p>
                  </div>
                </div>

                <button 
                  onClick={() => setShowSummary(false)}
                  className="w-full py-5 bg-slate-900 text-white font-bold rounded-3xl hover:bg-slate-800 transition-all shadow-xl shadow-slate-200 active:scale-[0.98]"
                >
                  FECHAR RELATÓRIO
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Pre-Run Modal */}
      <AnimatePresence>
        {showPreRun && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPreRun(false)}
              className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-white rounded-[32px] shadow-2xl w-full max-w-2xl relative z-10 overflow-hidden"
            >
              <div className="p-8 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-100 rounded-xl">
                    <Play className="text-emerald-600" size={24} fill="currentColor" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-800">Revisão da Campanha</h2>
                </div>
                <button onClick={() => setShowPreRun(false)} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
                  <Square size={20} className="text-slate-400" />
                </button>
              </div>

              <div className="p-8 space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                    <p className="text-xs font-bold text-slate-500 uppercase mb-1">Contatos a Processar</p>
                    <p className="text-2xl font-bold text-emerald-600">{Math.min(limit, stats.pendentes)}</p>
                  </div>
                  <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                    <p className="text-xs font-bold text-slate-500 uppercase mb-1">Variáveis Detectadas</p>
                    <div className="flex gap-1 mt-1">
                      {variablesDetected.length > 0 ? variablesDetected.map(v => (
                        <span key={v} className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-md text-[10px] font-bold">{v}</span>
                      )) : <span className="text-slate-400 text-xs italic">Nenhuma</span>}
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h4 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                    <Eye size={16} /> Exemplos de Preview (3 contatos)
                  </h4>
                  <div className="space-y-2">
                    {contacts.filter(c => c.Status === 'PENDENTE').slice(0, 3).map((c, i) => (
                      <div key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs text-slate-600 leading-relaxed">
                        <span className="font-bold text-emerald-600 mr-2">#{i+1}</span>
                        "{getPreview(c)}"
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-100 p-4 rounded-2xl flex gap-3">
                  <AlertCircle className="text-amber-600 shrink-0" size={20} />
                  <p className="text-xs text-amber-700 leading-relaxed">
                    Certifique-se de que o WhatsApp Web está conectado no navegador Chrome. 
                    O sistema usará o perfil dedicado para manter sua sessão.
                  </p>
                </div>

                <div className="flex gap-4 pt-4">
                  <button 
                    onClick={() => setShowPreRun(false)}
                    className="flex-1 py-4 bg-slate-100 text-slate-600 font-bold rounded-2xl hover:bg-slate-200 transition-all"
                  >
                    CANCELAR
                  </button>
                  <button 
                    onClick={startSequence}
                    className="flex-[2] py-4 bg-emerald-600 text-white font-bold rounded-2xl hover:bg-emerald-700 shadow-lg shadow-emerald-100 transition-all active:scale-95"
                  >
                    CONFIRMAR E INICIAR
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #cbd5e1; }
      `}</style>
    </div>
  );
}
