// Global WebSocket reference — avoids circular imports between store and hook
let ws: WebSocket | null = null;

export function setGlobalWs(socket: WebSocket | null) {
  ws = socket;
}

export function getGlobalWs(): WebSocket | null {
  return ws;
}
