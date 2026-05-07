'use client';

import { useState } from 'react';

interface LogoProps {
  size?: number;
  live?: boolean;
  className?: string;
}

export function Logo({ size = 80, live = true, className = '' }: LogoProps) {
  const cx = size / 2;
  const cy = size / 2;
  const R = size * 0.42;
  const sc = size / 80;

  const hex = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    return [cx + R * Math.cos(a), cy + R * Math.sin(a)];
  });
  const hexD = hex.map((p, i) =>
    `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`
  ).join(" ") + "Z";

  const NODE_R = 0.78;
  const nodes = hex.map(([hx, hy]) => ({
    x: cx + (hx - cx) * NODE_R,
    y: cy + (hy - cy) * NODE_R,
  }));

  const boltPts = [
    [cx + 6 * sc, cy - 15 * sc],
    [cx - 4 * sc, cy - 2 * sc],
    [cx + 1 * sc, cy - 2 * sc],
    [cx - 6 * sc, cy + 15 * sc],
    [cx + 4 * sc, cy + 2 * sc],
    [cx - 2 * sc, cy + 2 * sc],
  ];
  const boltD = boltPts.map((p, i) =>
    `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`
  ).join(" ") + "Z";

  const uid = `mk${size}x${Math.round(R)}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      fill="none"
      style={{ overflow: "visible" }}
      className={className}
    >
      <defs>
        <linearGradient id={`g_${uid}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#02C39A" />
          <stop offset="55%" stopColor="#0891B2" />
          <stop offset="100%" stopColor="#065A82" />
        </linearGradient>

        <filter id={`f_${uid}`} x="-70%" y="-70%" width="240%" height="240%">
          <feGaussianBlur stdDeviation={size * 0.05} result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <clipPath id={`c_${uid}`}>
          <path d={hexD} />
        </clipPath>
      </defs>

      {/* Outer ambient hex glow */}
      <path
        d={hexD}
        stroke={`url(#g_${uid})`}
        strokeWidth={size * 0.014}
        fill="none"
        opacity={0.12}
        transform={`scale(1.22) translate(${(-cx * 0.22).toFixed(2)} ${(-cy * 0.22).toFixed(2)})`}
        strokeLinejoin="round"
      />

      {/* Hex background fill */}
      <path d={hexD} fill="#0B0D14" />
      <path d={hexD} fill={`url(#g_${uid})`} opacity={0.07} />

      {/* Hex border stroke */}
      <path
        d={hexD}
        stroke={`url(#g_${uid})`}
        strokeWidth={size * 0.028}
        fill="none"
        strokeLinejoin="round"
        className={live ? "glow-anim" : undefined}
      />

      {/* Circuit traces from each corner node to center */}
      <g clipPath={`url(#c_${uid})`} opacity={0.28}>
        {nodes.map((n, i) => (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={n.x}
            y2={n.y}
            stroke="#02C39A"
            strokeWidth={size * 0.011}
            strokeDasharray={`${size * 0.05} ${size * 0.038}`}
            className={live ? "dash-anim" : undefined}
            style={live ? { animationDelay: `${i * 0.28}s` } : {}}
          />
        ))}
      </g>

      {/* 6 nodes at hex corner angles */}
      {nodes.map((n, i) => (
        <g key={i}>
          <circle
            cx={n.x}
            cy={n.y}
            r={size * 0.036}
            fill="#0B0D14"
            stroke={`url(#g_${uid})`}
            strokeWidth={size * 0.018}
          />
          <circle
            cx={n.x}
            cy={n.y}
            r={size * 0.013}
            fill="#02C39A"
            className={live ? "pulse-anim" : undefined}
            style={live ? { animationDelay: `${i * 0.48}s` } : {}}
          />
        </g>
      ))}

      {/* Lightning bolt */}
      <path
        d={boltD}
        fill={`url(#g_${uid})`}
        filter={`url(#f_${uid})`}
      />
      <path
        d={boltD}
        fill="white"
        opacity={0.1}
        transform={`translate(${(-size * 0.006).toFixed(2)} ${(-size * 0.006).toFixed(2)})`}
      />

      {/* Center anchor dot */}
      <circle
        cx={cx}
        cy={cy}
        r={size * 0.036}
        fill="#02C39A"
        opacity={0.5}
      />
    </svg>
  );
}
