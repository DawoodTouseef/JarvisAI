

type MessageHandler = (msg: string) => void;
type BinaryMessageHandler = (data: string | ArrayBuffer | Blob) => void;

class CommunicationManager {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners = new Set<MessageHandler>();
  private queue: string[] = [];
  private shouldReconnect = true;
  private reconnectDelay = 1000; // start with 1s

  constructor(url = "ws://localhost:8000/communicate", autoConnect = true) {
    this.url = url;
    if (autoConnect) this.connect();
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    console.info("WebSocket: connecting to", this.url);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.info("WebSocket: connected");
      // flush queued messages
      while (this.queue.length > 0 && this.ws && this.ws.readyState === WebSocket.OPEN) {
        const msg = this.queue.shift()!;
        this.ws.send(msg);
      }
      // reset reconnect delay
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      console.log("WebSocket: recv ->", event.data);
      for (const fn of this.listeners) fn(event.data);
    };

    this.ws.onclose = (ev) => {
      console.warn("WebSocket: closed", ev);
      if (this.shouldReconnect) {
        const delay = this.reconnectDelay;
        console.info(`WebSocket: reconnecting in ${delay}ms...`);
        setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
          this.connect();
        }, delay);
      }
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket: error", err);
      // errors will usually be followed by close
    };
  }

  sendMessage(message: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      // queue until the socket opens
      this.queue.push(message);
      // attempt a connect if we're not connected
      this.connect();
    }
  }

  sendJSON(obj: unknown) {
    try {
      this.sendMessage(JSON.stringify(obj));
    } catch (err) {
      console.error('WebSocket: failed to send JSON', err);
    }
  }

  onMessage(handler: MessageHandler) {
    this.listeners.add(handler);
    // return unsubscribe
    return () => this.listeners.delete(handler);
  }

  getMessage(): Promise<string> {
    return new Promise((resolve) => {
      const unsubscribe = this.onMessage((msg) => {
        unsubscribe();
        resolve(msg);
      });
    });
  }

  close() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

class HotwordCommunicationManager {
  private url: string;
  private ws: WebSocket | null = null;
  private textListeners = new Set<MessageHandler>();
  private binaryListeners = new Set<BinaryMessageHandler>();
  private shouldReconnect = true;
  private reconnectDelay = 1000;

  constructor(url?: string, autoConnect = true) {
    const base =  'http://localhost:8000';
    const wsUrl = (url || base.replace(/^http/, 'ws')) + '/hotword';
    this.url = wsUrl;
    if (autoConnect) this.connect();
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.ws = new WebSocket(this.url);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      const data = event.data;
      if (typeof data === 'string') {
        for (const fn of this.textListeners) fn(data);
      } else {
        for (const fn of this.binaryListeners) fn(data);
      }
    };

    this.ws.onclose = () => {
      if (this.shouldReconnect) {
        const delay = this.reconnectDelay;
        setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
          this.connect();
        }, delay);
      }
    };

    this.ws.onerror = () => {
      // swallow; onclose handles reconnect
    };
  }

  sendBytes(data: ArrayBuffer | Uint8Array | Blob) {
    const payload = data instanceof Uint8Array ? data.buffer : data;
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(payload);
    }
  }

  onMessage(handler: MessageHandler) {
    this.textListeners.add(handler);
    return () => this.textListeners.delete(handler);
  }

  onBinary(handler: BinaryMessageHandler) {
    this.binaryListeners.add(handler);
    return () => this.binaryListeners.delete(handler);
  }

  close() {
    this.shouldReconnect = false;
    if (this.ws) this.ws.close();
    this.ws = null;
  }
}

class StatusManager {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners = new Set<MessageHandler>();
  private queue: string[] = [];
  private shouldReconnect = true;
  private reconnectDelay = 1000; // start with 1s

  constructor(url = "ws://localhost:8000/info", autoConnect = true) {
    this.url = url;
    if (autoConnect) this.connect();
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      // flush queued messages
      while (this.queue.length > 0 && this.ws && this.ws.readyState === WebSocket.OPEN) {
        const msg = this.queue.shift()!;
        this.ws.send(msg);
      }
      // reset reconnect delay
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      for (const fn of this.listeners) fn(event.data);
    };

    this.ws.onclose = (ev) => {
      if (this.shouldReconnect) {
        const delay = this.reconnectDelay;
        setTimeout(() => {
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 10000);
          this.connect();
        }, delay);
      }
    };

    this.ws.onerror = (err) => {
      console.error("WebSocket: error", err);
      // errors will usually be followed by close
    };
  }

  sendMessage(message: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      // queue until the socket opens
      this.queue.push(message);
      // attempt a connect if we're not connected
      this.connect();
    }
  }

  onMessage(handler: MessageHandler) {
    this.listeners.add(handler);
    // return unsubscribe
    return () => this.listeners.delete(handler);
  }

  getMessage(): Promise<string> {
    return new Promise((resolve) => {
      const unsubscribe = this.onMessage((msg) => {
        unsubscribe();
        resolve(msg);
      });
    });
  }

  close() {
    this.shouldReconnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}




export const Communication = new CommunicationManager();
export const StatusCommunication = new StatusManager();
export const WakeWordCommunication = new HotwordCommunicationManager();