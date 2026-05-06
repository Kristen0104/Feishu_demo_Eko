import { ImageResponse } from "next/og";

export const runtime = "edge";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

/**
 * 避免使用静态 icon.svg：空壳/未同步的 SVG 会让 next-metadata-image-loader + sharp 报
 * "unsupported file type: undefined"。动态 PNG 不依赖本地 SVG 字节。
 */
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0f172a",
          color: "#f8fafc",
          fontSize: 18,
          fontWeight: 700,
        }}
      >
        E
      </div>
    ),
    { ...size },
  );
}
