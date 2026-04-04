"use client";

import dynamic from "next/dynamic";

const InterviewRoom = dynamic(() => import("./InterviewRoom"), {
  ssr: false,
});

export default function Home() {
  return <InterviewRoom />;
}
