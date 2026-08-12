import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Arena — AI-Powered Video Clip Generation";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OGImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <span
            style={{
              fontSize: "64px",
              fontWeight: 800,
              color: "#8b5cf6",
              fontFamily: "monospace",
            }}
          >
            &gt;_
          </span>
          <span
            style={{
              fontSize: "64px",
              fontWeight: 700,
              color: "#ffffff",
            }}
          >
            arena
          </span>
        </div>
        <div
          style={{
            fontSize: "36px",
            fontWeight: 600,
            color: "#e2e8f0",
            textAlign: "center",
            maxWidth: "800px",
            lineHeight: 1.3,
          }}
        >
          Turn Long-Form Video Into Viral Clips
        </div>
        <div
          style={{
            fontSize: "20px",
            color: "#94a3b8",
            marginTop: "20px",
            textAlign: "center",
            maxWidth: "600px",
          }}
        >
          AI-powered clipping engine for TikTok, Reels, and Shorts
        </div>
      </div>
    ),
    { ...size }
  );
}
