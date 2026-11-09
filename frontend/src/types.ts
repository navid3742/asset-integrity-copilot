export type Page = 'overview'|'assistant'|'knowledge'|'assets'|'reports'|'activity'|'guide';
export interface AssetRecord {id:string;name:string;category:string;service:string;unit:string;location:string;status:string;criticality:string;installed_at:string;design_reference:string;description:string}
export interface Inspection {id:string;asset_id:string;inspected_at:string;inspection_type:string;metric:string;reading:number;unit:string;outcome:string;inspector:string;notes:string}
export interface Maintenance {id:string;asset_id:string;performed_at:string;work_type:string;status:string;description:string;action_taken:string;next_step:string}
export interface Incident {id:string;asset_id:string;severity:string;status:string;issue:string;recorded_at:string;follow_up:string}
export interface DocItem {id:string;title:string;category:string;description:string;content?:string}
export interface Source {id:string;doc_id:string;title:string;section:string;category:string;excerpt:string;score:number;method:string}
export interface Trace {tool:string;args:Record<string,unknown>;status:string}
export interface ChatResult {answer:string;mode:'live'|'offline';sources:Source[];traces:Trace[];guardrail_blocked?:boolean}
export interface Message {role:'user'|'assistant';content:string;sources?:Source[];traces?:Trace[];mode?:string;id:number}
export interface Report {id:string;asset_id:string;status:'pending'|'approved';summary:string;created_at:string;approved_at:string|null}
export interface Stats {mode:'offline'|'live';live_available:boolean;configured_but_password_missing:boolean;model:string|null;agent_framework?:string;usage:{requests:number;api_calls:number;input_tokens:number;output_tokens:number;estimated_usd:number;limit_usd:number};counts:{assets:number;inspections:number;maintenance:number;incidents:number;reports:number}}
