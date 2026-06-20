"use client";

import { motion } from "framer-motion";

interface Props {
  progress: number; // 0–100
  size?: number;
  stroke?: number;
  className?: string;
}

export default function ProgressRing({ progress, size = 80, stroke = 6, className }: Props) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (progress / 100) * circ;

  return (
    <div className={className} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--primary)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ top: 0, left: 0, width: size, height: size, position: "absolute" }}
      >
        <span className="text-lg font-bold text-[--primary]">{progress}%</span>
      </div>
    </div>
  );
}
