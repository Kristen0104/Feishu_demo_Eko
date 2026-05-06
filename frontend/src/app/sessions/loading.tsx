export default function SessionsLoading() {
  return (
    <div className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] px-6 py-4">
      <div className="mx-auto flex min-h-[calc(100vh-32px)] max-w-[1680px] animate-pulse overflow-hidden rounded-[34px] border border-slate-200/80 bg-white/70">
        <div className="w-[230px] shrink-0 border-r border-slate-200/80 bg-white/70 px-6 py-6">
          <div className="h-12 w-28 rounded-2xl bg-slate-100" />
          <div className="mt-8 space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-12 rounded-[18px] bg-slate-100" />
            ))}
          </div>
        </div>
        <div className="flex flex-1 flex-col">
          <div className="h-[86px] border-b border-slate-200/80 px-8 py-5">
            <div className="h-10 w-full rounded-2xl bg-slate-100" />
          </div>
          <div className="grid flex-1 grid-cols-[minmax(0,1fr)_392px] gap-6 px-8 py-6">
            <div className="rounded-[28px] bg-white p-6 shadow-[0_12px_32px_rgba(100,116,139,0.08)]">
              <div className="h-11 w-full rounded-2xl bg-slate-100" />
              <div className="mt-5 space-y-3">
                {Array.from({ length: 7 }).map((_, index) => (
                  <div key={index} className="h-24 rounded-[22px] bg-slate-100" />
                ))}
              </div>
            </div>
            <div className="rounded-[28px] bg-white p-6 shadow-[0_12px_32px_rgba(100,116,139,0.08)]">
              <div className="h-8 w-40 rounded-xl bg-slate-100" />
              <div className="mt-6 space-y-4">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="h-24 rounded-[20px] bg-slate-100" />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
