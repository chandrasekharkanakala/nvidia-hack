import type { WSIncoming, WSOutgoing } from "../types";

type MessageHandler = (data: WSIncoming) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private onMessageHandler: MessageHandler | null = null;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;

  constructor(url: string) {
    this.url = url;
  }

  connect() {
    this.shouldReconnect = true;
    this.ws = new WebSocket(this.url);

    this.ws.onmessage = (event) => {
      const data: WSIncoming = JSON.parse(event.data);
      this.onMessageHandler?.(data);
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.ws?.close();
    this.ws = null;
  }

  send(message: WSOutgoing) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  onMessage(handler: MessageHandler) {
    this.onMessageHandler = handler;
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
