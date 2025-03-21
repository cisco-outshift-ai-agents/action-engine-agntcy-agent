export type BrowserAction =
  | "navigate"
  | "click"
  | "input_text"
  | "screenshot"
  | "get_html"
  | "get_text"
  | "execute_js"
  | "scroll"
  | "switch_tab"
  | "new_tab"
  | "close_tab"
  | "refresh";

export interface BaseToolMessageProps {
  className?: string;
}

export interface BrowserToolProps extends BaseToolMessageProps {
  action: BrowserAction;
  url?: string;
  index?: number;
  text?: string;
  script?: string;
  scroll_amount?: number;
  tab_id?: number;
}

export interface TerminalToolProps extends BaseToolMessageProps {
  command: string;
}

export interface TerminateToolProps extends BaseToolMessageProps {
  status: "success" | "failure";
  reason?: string;
}

export interface ToolResultProps extends BaseToolMessageProps {
  content: string;
}
