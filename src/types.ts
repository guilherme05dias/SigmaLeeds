export type ContactStatus = 'PENDENTE' | 'ENVIADO' | 'IGNORAR' | 'ERRO' | 'EM_PROCESSAMENTO' | 'INVALIDO';

export interface Contact {
  id: string | number;
  Nome: string;
  Numero: string;
  Status: ContactStatus;
  Empresa?: string;
  Observacao?: string;
  DataEnvio?: string;
}

export interface Stats {
  pendentes: number;
  enviados: number;
  ignorados: number;
  erros: number;
  invalidos: number;
  processando: number;
}

export interface CampaignSummary {
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
