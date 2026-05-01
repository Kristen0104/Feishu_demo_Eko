export default function SessionDetailLoading() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(210,224,255,0.55),_rgba(246,248,252,1)_32%,_rgba(238,243,255,1)_100%)] px-6 py-4">
      <div className="mx-auto flex min-h-[calc(100vh-32px)] max-w-[1680px] animate-pulse overflow-hidden rounded-[34px] border border-slate-200/80 bg-white/70">
        <div className="w-[176px] shrink-0 border-r border-slate-200/80 px-3 py-5">
          <div className="space-y-3">
            {Array.from({ length: 7 }).map((_, index) => (
              <div key={index} className="h-12 rounded-[18px] bg-slate-100" />
            ))}
          </div>
        </div>
        <div className="flex flex-1 flex-col">
          <div className="h-[72px] border-b border-slate-200/80 px-6 py-4">
            <div className="h-10 rounded-2xl bg-slate-100" />
          </div>
          <div className="grid flex-1 grid-cols-[320px_minmax(0,1fr)_320px] gap-4 px-6 py-6">
            <div className="rounded-[28px] bg-white p-5"><div className="h-full rounded-[22px] bg-slate-100" /></div>
            <div className="space-y-4">
              <div className="h-56 rounded-[28px] bg-white p-5"><div className="h-full rounded-[22px] bg-slate-100" /></div>
              <div className="h-[420px] rounded-[28px] bg-white p-5"><div className="h-full rounded-[22px] bg-slate-100" /></div>
            </div>
            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-32 rounded-[28px] bg-white p-5"><div className="h-full rounded-[22px] bg-slate-100" /></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
