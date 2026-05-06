"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <main style={{ minHeight: "100vh", background: "#f6f8fb", padding: 24, color: "#0f172a" }}>
          <section
            style={{
              margin: "18vh auto 0",
              maxWidth: 520,
              border: "1px solid #e2e8f0",
              borderRadius: 28,
              background: "white",
              padding: 32,
              boxShadow: "0 24px 80px rgba(15,23,42,0.10)",
              fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
            }}
          >
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>Eko Workspace 加载异常</h1>
            <p style={{ marginTop: 12, color: "#64748b", lineHeight: 1.7 }}>
              根布局加载时出现错误。请点击重试，或重启 dev server 后刷新页面。
            </p>
            {error?.message ? (
              <pre
                style={{
                  marginTop: 16,
                  maxHeight: 112,
                  overflow: "auto",
                  borderRadius: 16,
                  background: "#f8fafc",
                  padding: 12,
                  color: "#64748b",
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                {error.message}
              </pre>
            ) : null}
            <button
              type="button"
              onClick={reset}
              style={{
                marginTop: 24,
                height: 44,
                border: 0,
                borderRadius: 16,
                background: "#2563eb",
                color: "white",
                padding: "0 20px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              重新加载
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
