import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { MessageArea } from "./components/MessageArea";
import { InputBar } from "./components/InputBar";
import { MetricsPanel } from "./components/MetricsPanel";
import { useWebSocket } from "./hooks/useWebSocket";

export default function App() {
  useWebSocket();

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        <MessageArea />
        <InputBar />
      </div>
      <MetricsPanel />
    </div>
  );
}
