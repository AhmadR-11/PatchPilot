"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, Activity, CheckCircle2, Loader2, GitPullRequest, ArrowRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function PatchPilotDashboard() {
  const [status, setStatus] = useState<"Idle" | "Investigating" | "Awaiting Approval">("Idle");
  const [logs, setLogs] = useState<string[]>([]);
  const [prLink, setPrLink] = useState<string | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom of terminal
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "log") {
          setLogs((prev) => [...prev, data.data]);
        } else if (data.type === "status") {
          setStatus(data.data);
          if (data.data === "Investigating") {
            setPrLink(null);
          }
        } else if (data.type === "pr_link") {
          setPrLink(data.data);
          setStatus("Awaiting Approval");
        }
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    ws.onopen = () => {
      setLogs((prev) => [...prev, "> System: Connected to PatchPilot Backend."]);
    };

    ws.onclose = () => {
      setLogs((prev) => [...prev, "> System: Disconnected from backend. Trying to reconnect..."]);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-8 flex flex-col items-center">
      <div className="w-full max-w-5xl space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between bg-slate-900/50 p-6 rounded-2xl border border-slate-800 backdrop-blur-sm shadow-lg">
          <div className="flex items-center gap-4">
            <div className="bg-indigo-500/20 p-3 rounded-xl border border-indigo-500/30">
              <Terminal className="text-indigo-400 w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
                PatchPilot
              </h1>
              <p className="text-slate-400 text-sm">Autonomous DevOps Monitor</p>
            </div>
          </div>

          {/* Status Indicator */}
          <div className={`flex items-center gap-3 px-5 py-2.5 rounded-full border transition-all duration-500 ${
            status === "Idle" ? "bg-slate-800/50 border-slate-700 text-slate-300" :
            status === "Investigating" ? "bg-amber-500/10 border-amber-500/30 text-amber-400" :
            "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
          }`}>
            {status === "Idle" && <CheckCircle2 className="w-5 h-5" />}
            {status === "Investigating" && <Loader2 className="w-5 h-5 animate-spin" />}
            {status === "Awaiting Approval" && <GitPullRequest className="w-5 h-5 animate-pulse" />}
            <span className="font-medium tracking-wide">{status}</span>
          </div>
        </header>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Terminal Box (takes 2/3) */}
          <div className="lg:col-span-2 flex flex-col bg-[#0d1117] rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
            <div className="flex items-center gap-2 px-4 py-3 bg-slate-900 border-b border-slate-800">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80"></div>
                <div className="w-3 h-3 rounded-full bg-amber-500/80"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
              </div>
              <span className="ml-4 text-xs text-slate-500 font-mono tracking-wider">live-agent-feed.log</span>
            </div>
            <div className="p-6 font-mono text-sm sm:text-base h-[500px] overflow-y-auto space-y-3">
              <AnimatePresence>
                {logs.map((log, i) => {
                  let colorClass = "text-slate-300";
                  if (log.includes("error") || log.includes("fail") || log.includes("⚠️") || log.includes("❌") || log.includes("⛔")) {
                    colorClass = "text-rose-400";
                  } else if (log.includes("✅") || log.includes("🎉") || log.includes("successfully")) {
                    colorClass = "text-emerald-400";
                  } else if (log.includes("🔍") || log.includes("📄") || log.includes("🛠️") || log.includes("🔄")) {
                    colorClass = "text-cyan-300";
                  }

                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={`${colorClass} break-words`}
                    >
                      {log}
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              <div ref={endOfMessagesRef} />
            </div>
          </div>

          {/* Sidebar Area */}
          <div className="space-y-6">
            
            {/* System Metrics */}
            <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-800 shadow-xl">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" /> System Health
              </h3>
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Backend Connection</span>
                    <span className="text-emerald-400 font-medium">Stable</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-400 w-full shadow-[0_0_10px_rgba(52,211,153,0.5)]"></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-300">Agent Readiness</span>
                    <span className={`font-medium ${status === "Investigating" ? "text-amber-400" : "text-emerald-400"}`}>
                      {status === "Investigating" ? "Active" : "Standing By"}
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full transition-all duration-500 w-full ${status === "Investigating" ? "bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]" : "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]"}`}></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Approval Gatekeeper */}
            <AnimatePresence>
              {status === "Awaiting Approval" && prLink && (
                <motion.div
                  initial={{ opacity: 0, y: 20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  className="bg-gradient-to-b from-indigo-900/40 to-slate-900/40 p-6 rounded-2xl border border-indigo-500/30 shadow-[0_0_30px_-5px_rgba(99,102,241,0.25)] relative overflow-hidden"
                >
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-cyan-400"></div>
                  <h3 className="text-lg font-semibold text-white mb-2">Fix Ready for Review</h3>
                  <p className="text-slate-300 text-sm mb-6 leading-relaxed">
                    PatchPilot has identified the issue and pushed a fix. Please review the Pull Request to approve and merge.
                  </p>
                  <a
                    href={prLink}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-center gap-2 w-full bg-indigo-500 hover:bg-indigo-600 text-white font-medium py-3 px-4 rounded-xl transition-all shadow-lg hover:shadow-indigo-500/25 active:scale-[0.98]"
                  >
                    Review & Merge <ArrowRight className="w-4 h-4" />
                  </a>
                </motion.div>
              )}
            </AnimatePresence>
            
          </div>
        </div>
      </div>
    </div>
  );
}
