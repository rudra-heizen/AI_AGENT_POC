"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  BarVisualizer,
  DisconnectButton,
  useAgent,
  useSession,
  useSessionMessages,
  SessionProvider,
} from "@livekit/components-react";
import type { ReceivedMessage } from "@livekit/components-react";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  TokenSource,
  RoomEvent,
  RemoteParticipant,
} from "livekit-client";
import { CloseIcon } from "@/components/CloseIcon";

export default function InterviewRoom() {
  const router = useRouter();
  const hasConnected = useRef(false);

  const tokenSource = useMemo(() => {
    return TokenSource.endpoint("/api/token");
  }, []);
  const connectOptions = {
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    }
  };

  const session = useSession(tokenSource, {
    roomName: `interview-room-${Math.floor(Math.random() * 10000)}`,
    participantName: `user-${Math.floor(Math.random() * 10000)}`,
  });

  const agent = useAgent(session);
  const messages = useSessionMessages(session);

  // Handle redirect on disconnect
  useEffect(() => {
    if (session.connectionState === "connected") {
      hasConnected.current = true;
    }
    if (session.connectionState === "disconnected" && hasConnected.current) {
      hasConnected.current = false;
      router.push("/thank-you");
    }
  }, [session.connectionState, router]);

  // Detect agent leaving → disconnect client
  useEffect(() => {
    const room = session.room;
    const handleParticipantDisconnected = (participant: RemoteParticipant) => {
      if (participant.identity.startsWith("agent-")) {
        console.log("🔌 Agent left the room, disconnecting client...");
        setTimeout(() => room.disconnect(), 500);
      }
    };
    room.on(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
    return () => {
      room.off(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
    };
  }, [session.room]);

  const startSession = useCallback(() => {
    if (session.isConnected) return;
    session.start();
  }, [session]);

  const isActive = agent.isConnected;

  return (
    <SessionProvider session={session}>
      <main data-lk-theme="default" className="interview-page">
        {/* Top bar with controls */}
        <div className="interview-topbar">
          {!session.isConnected ? (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="start-btn"
              onClick={startSession}
            >
              Start Interview
            </motion.button>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="controls-row"
            >
              <VoiceAssistantControlBar controls={{ leave: false }} />
              <DisconnectButton>
                <CloseIcon />
              </DisconnectButton>
            </motion.div>
          )}
        </div>

        {/* Main content area */}
        <div className="interview-content">
          {/* Left: Visualizer */}
          <div className="voice-panel">
            <div className="visualizer-wrapper">
              <BarVisualizer
                state={agent.state}
                barCount={5}
                trackRef={agent.microphoneTrack}
                className="agent-visualizer"
                options={{ minHeight: 24 }}
              />
            </div>
            <div className="agent-status">
              <span className="agent-status-dot" data-state={agent.state} />
              <span className="agent-status-text">
                {agent.state === "speaking"
                  ? "Alex is speaking..."
                  : agent.state === "listening"
                  ? "Listening..."
                  : agent.state === "thinking"
                  ? "Thinking..."
                  : agent.state === "connecting"
                  ? "Connecting..."
                  : session.isConnected
                  ? "Connected"
                  : "Ready to start"}
              </span>
            </div>
          </div>

          {/* Right: Transcript */}
          <div className={`transcript-panel ${isActive ? "active" : ""}`}>
            <TranscriptChat messages={isActive ? messages.messages : []} />
          </div>
        </div>

        <RoomAudioRenderer />
      </main>
    </SessionProvider>
  );
}

// =============================================================================
// Transcript Chat Panel
// =============================================================================
function TranscriptChat({ messages }: { messages: ReceivedMessage[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="transcript-container">
      <div className="transcript-header">
        <div className="transcript-header-dot" />
        <span>Live Transcript</span>
      </div>
      <div className="transcript-messages" ref={containerRef}>
        <div className="transcript-messages-inner">
          {messages.length === 0 && (
            <div className="transcript-empty">
              Waiting for conversation to start...
            </div>
          )}
          {messages.map((message, index, allMsgs) => {
            const hideName =
              index >= 1 && allMsgs[index - 1].from === message.from;
            const isSelf = message.from?.isLocal ?? false;

            return (
              <div
                key={message.id ?? index}
                className={`chat-message ${isSelf ? "user" : "agent"}`}
              >
                {!hideName && (
                  <span className="chat-sender">
                    {isSelf ? "🧑 You" : `🤖 ${message.from?.name || "Alex"}`}
                  </span>
                )}
                <div className={`chat-bubble ${isSelf ? "user" : "agent"}`}>
                  {message.message}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
